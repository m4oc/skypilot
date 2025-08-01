"""
Seeweb provisioner for SkyPilot / Ray autoscaler.

Prerequisites:
    pip install ecsapi
"""

from ecsapi import Api, ServerCreateRequest
import time
from typing import Any,Dict, List, Optional
from sky import sky_logging
from sky.adaptors import seeweb as seeweb_adaptor
from sky.provision.common import ProvisionConfig, ProvisionRecord, ClusterInfo, InstanceInfo
from sky.utils import status_lib

logger = sky_logging.init_logger(__name__)

# --------------------------------------------------------------------------- #
# Useful constants
# --------------------------------------------------------------------------- #
_POLL_INTERVAL = 5         # sec
_MAX_BOOT_TIME = 600       # sec
_NOTE_KEY = "skypilot_cluster"   # we save cluster_name in .notes for filtering

# --------------------------------------------------------------------------- #
#  Class required by the Ray backend
# --------------------------------------------------------------------------- #
class SeewebNodeProvider:
    """Minimalist provisioner for Seeweb ECS."""

    def __init__(self, provider_config: ProvisionConfig, cluster_name: str):
        """
        provider_config: dict populated by template (plan, image, location,
                         remote_key_name, optional gpu…)
        cluster_name   : SkyPilot name on cloud (used in notes)
        """
        self.config = provider_config
        self.cluster_name = cluster_name
        self.ecs: Api = seeweb_adaptor.client()

    # --------------------------------------------------------------------- #
    # 1. bootstrap_instances – no preprocessing needed here
    # --------------------------------------------------------------------- #


    # --------------------------------------------------------------------- #
    # 2. run_instances: restart or create until we reach count
    # --------------------------------------------------------------------- #
    def run_instances(self, config: Dict, count: int) -> None:
        existing = self._query_cluster_nodes()
        running = [s for s in existing
                   if s.status in ("Booted", "Running", "Booting", "PoweringOn")]

        # a) restart Off servers
        for srv in (s for s in existing if s.status == "Off"):
            if len(running) >= count:
                break
            self._power_on(srv.name)
            running.append(srv)

        # b) create new VMs if missing
        while len(running) < count:
            self._create_server()
            running.append({})   # placeholder

    # --------------------------------------------------------------------- #
    # 3. terminate_instances
    # --------------------------------------------------------------------- #
    def terminate_instances(self) -> None:
        for srv in self._query_cluster_nodes():
            logger.info("Deleting server %s …", srv.name)
            self.ecs.delete_server(srv.name)          # DELETE /servers/{name}

    # --------------------------------------------------------------------- #
    # 4. stop_instances
    # --------------------------------------------------------------------- #
    def stop_instances(self) -> None:
        for srv in self._query_cluster_nodes():
            if srv.status in ("Booted", "Running"):
                self._power_off(srv.name)
        
        # Wait for all servers to be actually stopped
        self.wait_instances("Off")

    # --------------------------------------------------------------------- #
    # 5. query_instances
    # --------------------------------------------------------------------- #
    def query_instances(self) -> Dict[str, str]:
        return {srv.name: srv.status for srv in self._query_cluster_nodes()}

    # --------------------------------------------------------------------- #
    # 6. wait_instances
    # --------------------------------------------------------------------- #
    def wait_instances(self, desired_state: str = "Booted") -> None:
        deadline = time.time() + _MAX_BOOT_TIME
        while time.time() < deadline:
            states = {srv.status for srv in self._query_cluster_nodes()}
            if states <= {desired_state}:
                # If all servers are Booted, wait for them to be truly stable
                if desired_state == "Booted":
                    logger.info("Servers in Booted state, checking stability...")
                    if self._wait_for_all_servers_stable():
                        logger.info("All servers are stable")
                        return
                    else:
                        logger.warning("Servers not yet stable, continuing to wait...")
                        time.sleep(_POLL_INTERVAL)
                        continue
                return
            time.sleep(_POLL_INTERVAL)
        raise TimeoutError(f"Nodes are not all in state {desired_state} within timeout")

    def _wait_for_all_servers_stable(self, max_wait: int = 300) -> bool:
        """Waits for all cluster servers to be stable."""
        logger.info("Checking stability of all cluster servers...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            cluster_nodes = self._query_cluster_nodes()
            all_stable = True
            
            for node in cluster_nodes:
                if node.status == "Booted":
                    # Check that server is reachable via ping
                    if not self._ping_server(node.ipv4):
                        logger.warning(f"Server {node.name} ({node.ipv4}) not reachable via ping")
                        all_stable = False
                        break
                    
                    # Check that SSH is available
                    if not self._check_ssh_ready(node.ipv4):
                        logger.warning(f"SSH not available on {node.name} ({node.ipv4})")
                        all_stable = False
                        break
                    
                    logger.info(f"Server {node.name} ({node.ipv4}) is stable")
            
            if all_stable:
                logger.info("All servers are stable")
                # Safety sleep to allow for late reboots
                logger.info("Waiting 15 seconds to allow for late reboots...")
                time.sleep(15)
                return True
            
            logger.info("Waiting for all servers to be stable...")
            time.sleep(_POLL_INTERVAL)
        
        logger.error("Timeout waiting for server stability")
        return False

    def _ping_server(self, server_ip: str) -> bool:
        """Check that server is reachable via ping."""
        try:
            import subprocess
            result = subprocess.run(['ping', '-c', '1', '-W', '5', server_ip], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Error pinging {server_ip}: {e}")
            return False

    def _check_ssh_ready(self, server_ip: str) -> bool:
        """Check that SSH is available on the server."""
        try:
            import subprocess
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
                '-i', '/root/.sky/clients/8f6f0399/ssh/sky-key',
                'ecuser@' + server_ip, 'echo "SSH ready"'
            ], capture_output=True, timeout=15)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Error checking SSH on {server_ip}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # 7. open_ports / cleanup_ports – Seeweb doesn't have security groups
    # ------------------------------------------------------------------ #
    def open_ports(self, ports: List[int]):   # pylint: disable=unused-argument
        pass

    def cleanup_ports(self):
        pass

    # ======================  private helpers  ========================= #
    def _query_cluster_nodes(self):
        """List servers with notes == cluster_name."""
        return [s for s in self.ecs.fetch_servers()
                if s.notes == self.cluster_name]

    def _create_server(self):
        """POST /servers with complete payload."""
        payload = {
            "plan":     self.config.node_config.get("plan"),       # e.g. eCS4
            "image":    self.config.node_config.get("image"),      # e.g. ubuntu-2204
            "location": self.config.node_config.get("location"),   # e.g. it-mi2
            "notes":    self.cluster_name,
            "ssh_key": self.config.authentication_config.get("remote_key_name"),  # remote key
        }

        # Optional GPU
        if "gpu" in self.config.node_config:
            payload.update({
                "gpu":       self.config.node_config.get("gpu"),
                "gpu_label": self.config.node_config.get("gpu_label", ""),
            })
        create_request = ServerCreateRequest(**payload)
        logger.info("Creating Seeweb server %s", payload)
        _, action_id = self.ecs.create_server(create_request, check_if_can_create=False)   # dict with action_id
        self.ecs.watch_action(action_id, max_retry=180, fetch_every=5)

    def _power_on(self, server_id: str):
        self.ecs.turn_on_server(server_id)
        logger.info("Power-on issued to %s", server_id)

    def _power_off(self, server_id: str):
        self.ecs.turn_off_server(server_id)
        logger.info("Power-off issued to %s", server_id)

    def _wait_action(self, action_id: int):
        """Poll action until it completes."""
        while True:
            action = self.ecs.fetch_action(action_id)
            if action["status"] in ("completed", "ok", "no_content"):
                return
            if action["status"] == "error":
                raise RuntimeError(f"Seeweb action {action_id} failed")
            time.sleep(_POLL_INTERVAL)


# =============================================================================
# Standalone functions required by the provisioning interface
# Following Lambda Cloud pattern
# =============================================================================

def run_instances(region: str, cluster_name_on_cloud: str,
                  config: ProvisionConfig) -> ProvisionRecord:
    """Run instances for Seeweb cluster."""
    provider = SeewebNodeProvider(config, cluster_name_on_cloud)
    provider.run_instances(config, config.count)
    
    # Find the head node (for now we take the first server of the cluster)
    cluster_nodes = provider._query_cluster_nodes()
    if not cluster_nodes:
        raise RuntimeError(f"No nodes found for cluster {cluster_name_on_cloud}")
    
    head_node = cluster_nodes[0]
    
    return ProvisionRecord(
        provider_name="Seeweb",
        region=region,
        zone=None,  # Seeweb doesn't use zones
        cluster_name=cluster_name_on_cloud,
        head_instance_id=head_node.name,
        resumed_instance_ids=[],  # Empty for now
        created_instance_ids=[node.name for node in cluster_nodes],
    )


def stop_instances(
    cluster_name_on_cloud: str,
    provider_config: Optional[Dict[str, Any]] = None,
    worker_only: bool = False,
) -> None:
    """Stop instances for Seeweb cluster."""
    del worker_only  # unused - Seeweb doesn't distinguish between head/worker
    assert provider_config is not None
    provider = SeewebNodeProvider(provider_config, cluster_name_on_cloud)
    provider.stop_instances()


def terminate_instances(
    cluster_name_on_cloud: str,
    provider_config: Optional[Dict[str, Any]] = None,
    worker_only: bool = False,
) -> None:
    """Terminate instances for Seeweb cluster."""
    del worker_only  # unused - Seeweb doesn't distinguish between head/worker
    assert provider_config is not None
    provider = SeewebNodeProvider(provider_config, cluster_name_on_cloud)
    provider.terminate_instances()


def wait_instances(
    region: str, cluster_name_on_cloud: str,
    state: Optional[status_lib.ClusterStatus],
) -> None:
    """Wait for instances to reach desired state."""
    # Map ClusterStatus to Seeweb string
    if state == status_lib.ClusterStatus.UP:
        seeweb_state = "Booted"
    elif state == status_lib.ClusterStatus.STOPPED:
        seeweb_state = "Off"
    elif state is None:
        seeweb_state = "Terminated"  # For termination
    else:
        seeweb_state = "Booted"  # Default fallback
    
    # Create Seeweb client directly and wait
    client = seeweb_adaptor.client()
    deadline = time.time() + _MAX_BOOT_TIME
    while time.time() < deadline:
        cluster_nodes = [s for s in client.fetch_servers() if s.notes == cluster_name_on_cloud]
        if not cluster_nodes:
            time.sleep(_POLL_INTERVAL)
            continue
            
        states = {srv.status for srv in cluster_nodes}
        if states <= {seeweb_state}:
            # If all servers are Booted, wait for them to be truly stable
            if seeweb_state == "Booted":
                if _wait_for_all_servers_stable_standalone(cluster_nodes):
                    return
                else:
                    time.sleep(_POLL_INTERVAL)
                    continue
            return
        time.sleep(_POLL_INTERVAL)
    
    raise TimeoutError(f"Nodes are not all in state {seeweb_state} within timeout")


def _wait_for_all_servers_stable_standalone(cluster_nodes, max_wait: int = 300) -> bool:
    """Waits for all cluster servers to be stable (standalone version)."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        all_stable = True
        
        for node in cluster_nodes:
            if node.status == "Booted":
                # Check that server is reachable via ping
                if not _ping_server_standalone(node.ipv4):
                    all_stable = False
                    break
                
                # Check that SSH is available
                if not _check_ssh_ready_standalone(node.ipv4):
                    all_stable = False
                    break
        
        if all_stable:
            # Safety sleep to allow for late reboots
            time.sleep(60)
            return True
        
        time.sleep(_POLL_INTERVAL)
    
    return False


def _ping_server_standalone(server_ip: str) -> bool:
    """Check that server is reachable via ping (standalone version)."""
    try:
        import subprocess
        result = subprocess.run(['ping', '-c', '1', '-W', '5', server_ip], 
                              capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        print(f"Error pinging {server_ip}: {e}")
        return False


def _check_ssh_ready_standalone(server_ip: str) -> bool:
    """Check that SSH is available on the server (standalone version)."""
    try:
        import subprocess
        result = subprocess.run([
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            '-i', '/root/.sky/clients/8f6f0399/ssh/sky-key',
            'ecuser@' + server_ip, 'echo "SSH ready"'
        ], capture_output=True, timeout=15)
        return result.returncode == 0
    except Exception:
        return False


def query_instances(
    cluster_name_on_cloud: str,
    provider_config: Dict[str, Any],
    non_terminated_only: bool = True,
) -> Dict[str, Optional['status_lib.ClusterStatus']]:
    """Query instances status for Seeweb cluster."""
    from sky.utils import status_lib
    
    provider = SeewebNodeProvider(provider_config, cluster_name_on_cloud)
    seeweb_instances = provider.query_instances()
    
    # Map Seeweb status to SkyPilot status
    status_map = {
        'Booted': status_lib.ClusterStatus.UP,      # Seeweb uses "Booted" for running
        'Running': status_lib.ClusterStatus.UP,    # Alternative running state
        'Booting': status_lib.ClusterStatus.INIT,
        'PoweringOn': status_lib.ClusterStatus.INIT,
        'Off': status_lib.ClusterStatus.STOPPED,
        'Stopped': status_lib.ClusterStatus.STOPPED,
        'PoweringOff': status_lib.ClusterStatus.INIT,  # fallback to INIT
    }
    
    result = {}
    for name, seeweb_status in seeweb_instances.items():
        if non_terminated_only and seeweb_status in ('Terminated', 'Deleted'):
            continue
        result[name] = status_map.get(seeweb_status, status_lib.ClusterStatus.INIT)
    
    return result


def get_cluster_info(
    region: str,
    cluster_name_on_cloud: str,
    provider_config: Optional[Dict[str, Any]] = None,
) -> 'ClusterInfo':
    """Get cluster information for Seeweb cluster."""
    # Use Seeweb client to get cluster instances
    client = seeweb_adaptor.client()
    cluster_nodes = [s for s in client.fetch_servers() if s.notes == cluster_name_on_cloud]
    
    if not cluster_nodes:
        raise RuntimeError(f"No instances found for cluster {cluster_name_on_cloud}")
    
    instances = {}
    head_instance = None
    
    for node in cluster_nodes:
        # For Seeweb, we take the first node as head
        if head_instance is None:
            head_instance = node.name
            
        # Get server IP (Seeweb uses 'ipv4' attribute)
        external_ip = node.ipv4
        internal_ip = external_ip  # For Seeweb, internal IP = external IP
        
        instances[node.name] = [
            InstanceInfo(
                instance_id=node.name,
                internal_ip=internal_ip,
                external_ip=external_ip,
                ssh_port=22,
                tags={},
            )
        ]
    
    return ClusterInfo(
        instances=instances,
        head_instance_id=head_instance,
        provider_name='Seeweb',
        provider_config=provider_config,
    )


def open_ports(
    cluster_name_on_cloud: str,
    ports: List[str],
    provider_config: Optional[Dict[str, Any]] = None,
) -> None:
    """Open ports for Seeweb cluster.
    
    Seeweb doesn't support security groups/firewall rules, so this is a no-op.
    """
    del cluster_name_on_cloud, ports, provider_config  # unused
    pass


def cleanup_ports(
    cluster_name_on_cloud: str,
    ports: List[str],
    provider_config: Optional[Dict[str, Any]] = None,
) -> None:
    """Cleanup ports for Seeweb cluster.
    
    Seeweb doesn't support security groups/firewall rules, so this is a no-op.
    """
    del cluster_name_on_cloud, ports, provider_config  # unused
    pass

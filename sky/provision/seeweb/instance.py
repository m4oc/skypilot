"""
Seeweb provisioner per SkyPilot / Ray autoscaler.

Prerequisito:
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
# Costanti utili
# --------------------------------------------------------------------------- #
_POLL_INTERVAL = 5         # sec
_MAX_BOOT_TIME = 600       # sec
_NOTE_KEY = "skypilot_cluster"   # salviamo cluster_name in .notes per filtrare

# --------------------------------------------------------------------------- #
#  Classe richiesta dal backend Ray
# --------------------------------------------------------------------------- #
class SeewebNodeProvider:
    """Provisioner minimalista per Seeweb ECS."""

    def __init__(self, provider_config: ProvisionConfig, cluster_name: str):
        """
        provider_config: dict popolato dal template (plan, image, location,
                         remote_key_name, eventuale gpu…)
        cluster_name   : nome SkyPilot sul cloud (usato in notes)
        """
        self.config = provider_config
        self.cluster_name = cluster_name
        self.ecs: Api = seeweb_adaptor.client()
        print(f"ECS API: {type(self.ecs)}")

    # --------------------------------------------------------------------- #
    # 1. bootstrap_instances – qui non serve pre-elaborare nulla
    # --------------------------------------------------------------------- #
    #def bootstrap_instances(self, config: Dict) -> Dict:   # noqa: D401
    #    print(f"DEBUG13:Bootstrap instances: {config}")
    #    return config

    # --------------------------------------------------------------------- #
    # 2. run_instances: riaccende o crea finché non arriviamo a count
    # --------------------------------------------------------------------- #
    def run_instances(self, config: Dict, count: int) -> None:
        existing = self._query_cluster_nodes()
        running = [s for s in existing
                   if s.status in ("Booted", "Running", "Booting", "PoweringOn")]

        # a) riaccendi Off
        for srv in (s for s in existing if s.status == "Off"):
            if len(running) >= count:
                break
            self._power_on(srv.name)
            running.append(srv)

        # b) crea nuove VM se mancano
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

    # --------------------------------------------------------------------- #
    # 5. query_instances
    # --------------------------------------------------------------------- #
    def query_instances(self) -> Dict[str, str]:
        print(f"DEBUG25:Query instances: {self._query_cluster_nodes()}")
        return {srv.name: srv.status for srv in self._query_cluster_nodes()}

    # --------------------------------------------------------------------- #
    # 6. wait_instances
    # --------------------------------------------------------------------- #
    def wait_instances(self, desired_state: str = "Booted") -> None:
        deadline = time.time() + _MAX_BOOT_TIME
        while time.time() < deadline:
            states = {srv.status for srv in self._query_cluster_nodes()}
            if states <= {desired_state}:
                # Se tutti i server sono Booted, attendi che siano veramente stabili
                if desired_state == "Booted":
                    logger.info("Server in stato Booted, verifico stabilità...")
                    if self._wait_for_all_servers_stable():
                        logger.info("Tutti i server sono stabili")
                        return
                    else:
                        logger.warning("Server non ancora stabili, continuo ad attendere...")
                        time.sleep(_POLL_INTERVAL)
                        continue
                return
            time.sleep(_POLL_INTERVAL)
        raise TimeoutError(f"Nodi non sono tutti in stato {desired_state} entro il timeout")

    def _wait_for_all_servers_stable(self, max_wait: int = 300) -> bool:
        """Attende che tutti i server del cluster siano stabili."""
        logger.info("Verifico stabilità di tutti i server del cluster...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            cluster_nodes = self._query_cluster_nodes()
            all_stable = True
            
            for node in cluster_nodes:
                if node.status == "Booted":
                    # Verifica che il server sia raggiungibile via ping
                    if not self._ping_server(node.ipv4):
                        logger.warning(f"Server {node.name} ({node.ipv4}) non raggiungibile via ping")
                        all_stable = False
                        break
                    
                    # Verifica che SSH sia disponibile
                    if not self._check_ssh_ready(node.ipv4):
                        logger.warning(f"SSH non disponibile su {node.name} ({node.ipv4})")
                        all_stable = False
                        break
                    
                    logger.info(f"Server {node.name} ({node.ipv4}) è stabile")
            
            if all_stable:
                logger.info("Tutti i server sono stabili")
                # Sleep di sicurezza per permettere eventuali reboot tardivi
                logger.info("Attendo 60 secondi per permettere eventuali reboot tardivi...")
                time.sleep(60)
                return True
            
            logger.info("Attendo che tutti i server siano stabili...")
            time.sleep(_POLL_INTERVAL)
        
        logger.error("Timeout nell'attesa della stabilità dei server")
        return False

    def _ping_server(self, server_ip: str) -> bool:
        """Verifica che il server sia raggiungibile via ping."""
        try:
            import subprocess
            result = subprocess.run(['ping', '-c', '1', '-W', '5', server_ip], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Errore nel ping di {server_ip}: {e}")
            return False

    def _check_ssh_ready(self, server_ip: str) -> bool:
        """Verifica che SSH sia disponibile sul server."""
        try:
            import subprocess
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
                '-i', '/root/.sky/clients/8f6f0399/ssh/sky-key',
                'ecuser@' + server_ip, 'echo "SSH ready"'
            ], capture_output=True, timeout=15)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Errore nel controllo SSH di {server_ip}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # 7. open_ports / cleanup_ports – Seeweb non ha security groups
    # ------------------------------------------------------------------ #
    def open_ports(self, ports: List[int]):   # pylint: disable=unused-argument
        pass

    def cleanup_ports(self):
        pass

    # ======================  helper privati  ========================= #
    def _query_cluster_nodes(self):
        """Lista server con notes == cluster_name."""
        return [s for s in self.ecs.fetch_servers()
                if s.notes == self.cluster_name]

    def _create_server(self):
        """POST /servers con payload completo."""
        print(f"DEBUG50: authentication_config = {self.config.authentication_config}")
        print(f"DEBUG51: node_config = {self.config.node_config}")
        payload = {
            "plan":     self.config.node_config.get("plan"),       # es. eCS4
            "image":    self.config.node_config.get("image"),      # es. ubuntu-2204
            "location": self.config.node_config.get("location"),   # es. it-mi2
            "notes":    self.cluster_name,
            "ssh_key": self.config.authentication_config.get("remote_key_name"),  # chiave remota
        }

        # GPU opzionale
        if "gpu" in self.config.node_config:
            payload.update({
                "gpu":       self.config.node_config.get("gpu"),
                "gpu_label": self.config.node_config.get("gpu_label", ""),
            })
        print(f"DEBUG21:Create server: {payload}")
        create_request = ServerCreateRequest(**payload)
        logger.info("Creating Seeweb server %s", payload)
        # DEBUG: ALEX PATCH Falso Vero Dopo patch
        _, action_id = self.ecs.create_server(create_request, check_if_can_create=False)   # dict con action_id
        print(f"DEBUG22:Action ID: {action_id}")
        self.ecs.watch_action(action_id, max_retry=180, fetch_every=5)

    def _power_on(self, server_id: str):
        self.ecs.turn_on_server(server_id)
        logger.info("Power-on issued to %s", server_id)

    def _power_off(self, server_id: str):
        self.ecs.turn_off_server(server_id)
        logger.info("Power-off issued to %s", server_id)

    def _wait_action(self, action_id: int):
        """Poll action finché non termina."""
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
    
    # Trova il nodo head (per ora prendiamo il primo server del cluster)
    cluster_nodes = provider._query_cluster_nodes()
    if not cluster_nodes:
        raise RuntimeError(f"No nodes found for cluster {cluster_name_on_cloud}")
    
    head_node = cluster_nodes[0]
    
    return ProvisionRecord(
        provider_name="Seeweb",
        region=region,
        zone=None,  # Seeweb non usa zone
        cluster_name=cluster_name_on_cloud,
        head_instance_id=head_node.name,
        resumed_instance_ids=[],  # Per ora vuoto
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
    print(f"DEBUG60: wait_instances called with state={state}")
    
    # Mappa ClusterStatus a stringa Seeweb
    if state == status_lib.ClusterStatus.UP:
        seeweb_state = "Booted"
    elif state == status_lib.ClusterStatus.STOPPED:
        seeweb_state = "Off"
    elif state is None:
        seeweb_state = "Terminated"  # Per terminazione
    else:
        seeweb_state = "Booted"  # Default fallback
    
    # Crea direttamente il client Seeweb e aspetta
    client = seeweb_adaptor.client()
    deadline = time.time() + _MAX_BOOT_TIME
    while time.time() < deadline:
        cluster_nodes = [s for s in client.fetch_servers() if s.notes == cluster_name_on_cloud]
        if not cluster_nodes:
            print(f"DEBUG62: No nodes found for cluster {cluster_name_on_cloud}")
            time.sleep(_POLL_INTERVAL)
            continue
            
        states = {srv.status for srv in cluster_nodes}
        print(f"DEBUG63: Current states: {states}, waiting for: {seeweb_state}")
        if states <= {seeweb_state}:
            # Se tutti i server sono Booted, attendi che siano veramente stabili
            if seeweb_state == "Booted":
                print(f"DEBUG64: All nodes reached state {seeweb_state}, checking stability...")
                if _wait_for_all_servers_stable_standalone(cluster_nodes):
                    print(f"DEBUG65: All nodes are stable")
                    return
                else:
                    print(f"DEBUG66: Nodes not yet stable, continuing to wait...")
                    time.sleep(_POLL_INTERVAL)
                    continue
            print(f"DEBUG64: All nodes reached state {seeweb_state}")
            return
        time.sleep(_POLL_INTERVAL)
    
    raise TimeoutError(f"Nodi non sono tutti in stato {seeweb_state} entro il timeout")


def _wait_for_all_servers_stable_standalone(cluster_nodes, max_wait: int = 300) -> bool:
    """Attende che tutti i server del cluster siano stabili (versione standalone)."""
    print("Verifico stabilità di tutti i server del cluster...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        all_stable = True
        
        for node in cluster_nodes:
            if node.status == "Booted":
                # Verifica che il server sia raggiungibile via ping
                if not _ping_server_standalone(node.ipv4):
                    print(f"Server {node.name} ({node.ipv4}) non raggiungibile via ping")
                    all_stable = False
                    break
                
                # Verifica che SSH sia disponibile
                if not _check_ssh_ready_standalone(node.ipv4):
                    print(f"SSH non disponibile su {node.name} ({node.ipv4})")
                    all_stable = False
                    break
                
                print(f"Server {node.name} ({node.ipv4}) è stabile")
        
        if all_stable:
            print("Tutti i server sono stabili")
            # Sleep di sicurezza per permettere eventuali reboot tardivi
            print("Attendo 60 secondi per permettere eventuali reboot tardivi...")
            time.sleep(60)
            return True
        
        print("Attendo che tutti i server siano stabili...")
        time.sleep(_POLL_INTERVAL)
    
    print("Timeout nell'attesa della stabilità dei server")
    return False


def _ping_server_standalone(server_ip: str) -> bool:
    """Verifica che il server sia raggiungibile via ping (versione standalone)."""
    try:
        import subprocess
        result = subprocess.run(['ping', '-c', '1', '-W', '5', server_ip], 
                              capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        print(f"Errore nel ping di {server_ip}: {e}")
        return False


def _check_ssh_ready_standalone(server_ip: str) -> bool:
    """Verifica che SSH sia disponibile sul server (versione standalone)."""
    try:
        import subprocess
        result = subprocess.run([
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            '-i', '/root/.sky/clients/8f6f0399/ssh/sky-key',
            'ecuser@' + server_ip, 'echo "SSH ready"'
        ], capture_output=True, timeout=15)
        return result.returncode == 0
    except Exception as e:
        print(f"Errore nel controllo SSH di {server_ip}: {e}")
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
        result[name] = status_map.get(seeweb_status, status_lib.ClusterStatus.UNKNOWN)
    
    return result


def get_cluster_info(
    region: str,
    cluster_name_on_cloud: str,
    provider_config: Optional[Dict[str, Any]] = None,
) -> 'ClusterInfo':
    """Get cluster information for Seeweb cluster."""
    # Usa il client Seeweb per ottenere le istanze del cluster
    client = seeweb_adaptor.client()
    cluster_nodes = [s for s in client.fetch_servers() if s.notes == cluster_name_on_cloud]
    
    if not cluster_nodes:
        raise RuntimeError(f"No instances found for cluster {cluster_name_on_cloud}")
    
    instances = {}
    head_instance = None
    
    for node in cluster_nodes:
        # Per Seeweb, prendiamo il primo nodo come head
        if head_instance is None:
            head_instance = node.name
            
        # Ottieni l'IP del server (Seeweb usa l'attributo 'ipv4')
        external_ip = node.ipv4
        internal_ip = external_ip  # Per Seeweb, IP interno = IP esterno
        
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

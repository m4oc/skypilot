"""
Seeweb provisioner per SkyPilot / Ray autoscaler.

Prerequisito:
    pip install ecsapi
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from sky import sky_logging
from sky.adaptors import seeweb as seeweb_adaptor

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

    def __init__(self, provider_config: Dict, cluster_name: str):
        """
        provider_config: dict popolato dal template (plan, image, location,
                         remote_key_name, eventuale gpu…)
        cluster_name   : nome SkyPilot sul cloud (usato in notes)
        """
        self.config = provider_config
        self.cluster_name = cluster_name
        self.ecs = seeweb_adaptor.client()

    # --------------------------------------------------------------------- #
    # 1. bootstrap_instances – qui non serve pre-elaborare nulla
    # --------------------------------------------------------------------- #
    def bootstrap_instances(self, config: Dict) -> Dict:   # noqa: D401
        return config

    # --------------------------------------------------------------------- #
    # 2. run_instances: riaccende o crea finché non arriviamo a count
    # --------------------------------------------------------------------- #
    def run_instances(self, config: Dict, count: int) -> None:
        existing = self._query_cluster_nodes()
        running = [s for s in existing
                   if s["status"] in ("Running", "Booting", "PoweringOn")]

        # a) riaccendi Off
        for srv in (s for s in existing if s["status"] == "Off"):
            if len(running) >= count:
                break
            self._power_on(srv["id"])
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
            logger.info("Deleting server %s …", srv["name"])
            self.ecs.servers.delete(srv["id"])          # DELETE /servers/{id}

    # --------------------------------------------------------------------- #
    # 4. stop_instances
    # --------------------------------------------------------------------- #
    def stop_instances(self) -> None:
        for srv in self._query_cluster_nodes():
            if srv["status"] == "Running":
                self._power_off(srv["id"])

    # --------------------------------------------------------------------- #
    # 5. query_instances
    # --------------------------------------------------------------------- #
    def query_instances(self) -> Dict[str, str]:
        return {srv["name"]: srv["status"] for srv in self._query_cluster_nodes()}

    # --------------------------------------------------------------------- #
    # 6. wait_instances
    # --------------------------------------------------------------------- #
    def wait_instances(self, desired_state: str = "Running") -> None:
        deadline = time.time() + _MAX_BOOT_TIME
        while time.time() < deadline:
            states = {srv["status"] for srv in self._query_cluster_nodes()}
            if states <= {desired_state}:
                return
            time.sleep(_POLL_INTERVAL)
        raise TimeoutError(f"Nodi non sono tutti in stato {desired_state} entro il timeout")

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
        return [s for s in self.ecs.servers.list()
                if s.get("notes") == self.cluster_name]

    def _create_server(self):
        """POST /servers con payload completo."""
        payload = {
            "plan":     self.config["plan"],       # es. eCS4
            "image":    self.config["image"],      # es. ubuntu-2204
            "location": self.config["location"],   # es. it-mi2
            "notes":    self.cluster_name,
            "ssh_key_id": self.config["auth"]["remote_key_name"],  # chiave remota
        }

        # GPU opzionale
        if "gpu" in self.config:
            payload.update({
                "gpu":       self.config["gpu"],
                "gpu_label": self.config.get("gpu_label", ""),
            })

        logger.info("Creating Seeweb server %s", payload)
        resp = self.ecs.servers.create(**payload)   # dict con action_id
        self._wait_action(resp["action_id"])

    def _power_on(self, server_id: str):
        self.ecs.servers.action(server_id, type="power_on")
        logger.info("Power-on issued to %s", server_id)

    def _power_off(self, server_id: str):
        self.ecs.servers.action(server_id, type="power_off")
        logger.info("Power-off issued to %s", server_id)

    def _wait_action(self, action_id: int):
        """Poll action finché non termina."""
        while True:
            action = self.ecs.actions.get(action_id)
            if action["status"] in ("completed", "ok", "no_content"):
                return
            if action["status"] == "error":
                raise RuntimeError(f"Seeweb action {action_id} failed")
            time.sleep(_POLL_INTERVAL)

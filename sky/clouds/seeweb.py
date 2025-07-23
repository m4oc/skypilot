"""Seeweb Cloud."""

from __future__ import annotations
import os
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sky import catalog, clouds
from sky.adaptors import seeweb as seeweb_adaptor
from sky.utils import registry, resources_utils

if typing.TYPE_CHECKING:  # evitano import ciclici nei type-checkers
    from sky import resources as resources_lib

# ---------- percorso del file-chiave in stile Lambda -----------------
_SEEWEB_KEY_FILE = '~/.seeweb_cloud/seeweb_keys'
# (il contenuto: ini-like)
#   api_key = <TOKEN>

@registry.CLOUD_REGISTRY.register
class Seeweb(clouds.Cloud):
    """Seeweb GPU Cloud."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    _REPR = 'Seeweb'
    _MAX_CLUSTER_NAME_LEN_LIMIT = 120

    _CLOUD_UNSUPPORTED_FEATURES = {
        clouds.CloudImplementationFeatures.AUTOSTOP: 'Stopping not supported.',
        clouds.CloudImplementationFeatures.STOP: 'Stopping not supported.',
        clouds.CloudImplementationFeatures.SPOT_INSTANCE:
            'Spot is not supported on Seeweb.',
        clouds.CloudImplementationFeatures.MULTI_NODE:
            'Multi-node not supported yet on Seeweb.',
    }

    PROVISIONER_VERSION = clouds.ProvisionerVersion.SKYPILOT
    STATUS_VERSION      = clouds.StatusVersion.SKYPILOT

    # ------------------------------------------------------------------
    # Credenziali
    # ------------------------------------------------------------------
    @classmethod
    def _check_compute_credentials(cls) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """Checks if the user has access credentials to Seeweb's compute service."""
        return seeweb_adaptor.check_compute_credentials()

    @classmethod
    def _check_storage_credentials(cls) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """Checks if the user has access credentials to Seeweb's storage service."""
        return seeweb_adaptor.check_storage_credentials()

    def get_credential_file_mounts(self) -> Dict[str, str]:
        """Monta solo il file-chiave nel nodo del cluster."""
        path = os.path.expanduser(_SEEWEB_KEY_FILE)
        return {_SEEWEB_KEY_FILE: _SEEWEB_KEY_FILE} if os.path.exists(path) else {}


    # ------------------------------------------------------------------
    # Region & instance helpers (invariati)
    # ------------------------------------------------------------------
    def __repr__(self):  return self._REPR
    def is_same_cloud(self, other): return isinstance(other, Seeweb)
    def _cloud_unsupported_features(self): return self._CLOUD_UNSUPPORTED_FEATURES.copy()
    @classmethod
    def _max_cluster_name_length(cls): return cls._MAX_CLUSTER_NAME_LEN_LIMIT

    @classmethod
    def regions_with_offering(cls, instance_type, accelerators, use_spot,
                              region, zone):
        assert zone is None, 'Seeweb does not support zones.'
        if use_spot: return []
        regions = catalog.get_region_zones_for_instance_type(instance_type,
                                                             use_spot,
                                                             'Seeweb')
        if region is not None:
            regions = [r for r in regions if r.name == region]
        return regions

    @classmethod
    def get_vcpus_mem_from_instance_type(cls, instance_type):
        return catalog.get_vcpus_mem_from_instance_type(instance_type,
                                                        clouds='Seeweb')

    # --------------- lancio/risorse -------------------------------------------------
    def make_deploy_resources_variables(self, resources:'resources_lib.Resources',
                                        cluster_name:resources_utils.ClusterName,
                                        region:'clouds.Region',
                                        zones):
        del cluster_name, zones
        resources = resources.assert_launchable()

        image_id = 'ubuntu-2204-cuda12' if resources.accelerators else 'ubuntu-2204'

        return {
            'plan':     resources.instance_type,
            'image':    image_id,
            'location': region.name,
        }

    def instance_type_exists(self, instance_type):       # query su catalogo
        return catalog.instance_type_exists(instance_type, 'Seeweb')

    # (Altri metodi – costi, feasible_resources, ecc. – restano identici
    #  a quelli che avevi già scritto o copiati da Lambda. Ometti qui se
    #  non hai necessità particolari.)

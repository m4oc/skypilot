"""Seeweb Cloud."""

from __future__ import annotations
import os
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Iterator

from sky import catalog
from sky import clouds
from sky.adaptors import seeweb as seeweb_adaptor
from sky.utils import registry, resources_utils
from sky.utils import ux_utils

if typing.TYPE_CHECKING:  # evitano import ciclici nei type-checkers
    from sky import resources as resources_lib
    from sky.volumes import volume as volume_lib
    from sky.utils import status_lib

# ---------- percorso del file-chiave in stile Lambda -----------------
_SEEWEB_KEY_FILE = '~/.seeweb_cloud/seeweb_keys'
# (il contenuto: ini-like)
#   api_key = <TOKEN>

@registry.CLOUD_REGISTRY.register
class Seeweb(clouds.Cloud):
    """Seeweb GPU Cloud."""
    
    _REPR = 'Seeweb'
    _CLOUD_UNSUPPORTED_FEATURES = {
        clouds.CloudImplementationFeatures.MULTI_NODE: 'Multi-node not supported.',
        clouds.CloudImplementationFeatures.CUSTOM_DISK_TIER: 'Custom disk tiers not supported.',
        clouds.CloudImplementationFeatures.STORAGE_MOUNTING: 'Storage mounting not supported.',
        clouds.CloudImplementationFeatures.HIGH_AVAILABILITY_CONTROLLERS: 'High availability controllers not supported.',
        clouds.CloudImplementationFeatures.SPOT_INSTANCE: 'Spot instances not supported.',
        clouds.CloudImplementationFeatures.CLONE_DISK_FROM_CLUSTER: 'Disk cloning not supported.',
        clouds.CloudImplementationFeatures.DOCKER_IMAGE: 'Docker images not supported.',
        clouds.CloudImplementationFeatures.OPEN_PORTS: 'Opening ports not supported.',
        clouds.CloudImplementationFeatures.IMAGE_ID: 'Custom image IDs not supported.',
        clouds.CloudImplementationFeatures.CUSTOM_NETWORK_TIER: 'Custom network tiers not supported.',
        clouds.CloudImplementationFeatures.HOST_CONTROLLERS: 'Host controllers not supported.',
        clouds.CloudImplementationFeatures.CUSTOM_MULTI_NETWORK: 'Custom multi-network not supported.',
    }
    _MAX_CLUSTER_NAME_LEN_LIMIT = 120
    _regions: List[clouds.Region] = []

    PROVISIONER_VERSION = clouds.ProvisionerVersion.SKYPILOT
    STATUS_VERSION = clouds.StatusVersion.SKYPILOT

    @classmethod
    def _unsupported_features_for_resources(
        cls, resources: 'resources_lib.Resources'
    ) -> Dict[clouds.CloudImplementationFeatures, str]:
        return cls._CLOUD_UNSUPPORTED_FEATURES

    @classmethod
    def max_cluster_name_length(cls) -> Optional[int]:
        return cls._MAX_CLUSTER_NAME_LEN_LIMIT

    @classmethod
    def regions(cls) -> List['clouds.Region']:
        """Return available regions for Seeweb."""
        return catalog.regions(clouds='seeweb')

    @classmethod
    def regions_with_offering(cls, instance_type: str,
                              accelerators: Optional[Dict[str, int]],
                              use_spot: bool, region: Optional[str],
                              zone: Optional[str]) -> List[clouds.Region]:
        assert zone is None, 'Seeweb does not support zones.'
        del accelerators, zone  # unused
        if use_spot:
            return []
        regions = catalog.get_region_zones_for_instance_type(
            instance_type, use_spot, 'seeweb')

        if region is not None:
            regions = [r for r in regions if r.name == region]
        return regions

    @classmethod
    def zones_provision_loop(
        cls,
        *,
        region: str,
        num_nodes: int,
        instance_type: str,
        accelerators: Optional[Dict[str, int]] = None,
        use_spot: bool = False,
    ) -> Iterator[None]:
        del num_nodes  # unused
        regions = cls.regions_with_offering(instance_type,
                                            accelerators,
                                            use_spot,
                                            region=region,
                                            zone=None)
        for r in regions:
            assert r.zones is None, r
            yield r.zones

    @classmethod
    def get_zone_shell_cmd(cls) -> Optional[str]:
        """Seeweb doesn't support zones."""
        return None

    def instance_type_to_hourly_cost(self, instance_type: str, use_spot: bool,
                                     region: Optional[str],
                                     zone: Optional[str]) -> float:
        return catalog.get_hourly_cost(instance_type, use_spot=use_spot, region=region, zone=zone, clouds='seeweb')

    def accelerators_to_hourly_cost(self, accelerators: Dict[str, int],
                                    use_spot: bool, region: Optional[str],
                                    zone: Optional[str]) -> float:
        # For Seeweb, accelerator costs are included in instance cost
        return 0.0

    def get_egress_cost(self, num_gigabytes: float):
        # Seeweb doesn't charge for egress (simplified)
        return 0.0

    def make_deploy_resources_variables(
        self,
        resources: 'resources_lib.Resources',
        cluster_name: resources_utils.ClusterName,
        region: 'clouds.Region',
        zones: Optional[List['clouds.Zone']],
        num_nodes: int,
        dryrun: bool = False,
        volume_mounts: Optional[List['volume_lib.VolumeMount']] = None,
    ) -> Dict[str, Any]:
        """Create deployment variables for Seeweb."""
        # Note: Spot instances and multi-node are automatically handled by 
        # the framework via _CLOUD_UNSUPPORTED_FEATURES
        
        resources = resources.assert_launchable()
        acc_dict = self.get_accelerators_from_instance_type(
            resources.instance_type)
        # Standard custom_resources string for Ray (like other clouds)
        custom_resources = resources_utils.make_ray_custom_resources_str(
            acc_dict)
        
        # Seeweb-specific GPU configuration for the provisioner
        seeweb_gpu_config = None
        if resources.accelerators:
            # If the instance has accelerators, prepare GPU configuration
            accelerator_name = list(resources.accelerators.keys())[0]
            accelerator_count = resources.accelerators[accelerator_name]
            seeweb_gpu_config = {
                'gpu': accelerator_count,
                'gpu_label': accelerator_name
            }
        
        # Seeweb uses pre-configured images, default is ubuntu-2204
        # Custom images are not supported (see _CLOUD_UNSUPPORTED_FEATURES)
        image_id = 'ubuntu-2204'
        if resources.image_id is not None:
            # Even though custom images aren't supported, we should handle 
            # the case where someone tries to specify one and provide a clear error
            if None in resources.image_id:
                image_id = resources.image_id[None]
            else:
                assert region.name in resources.image_id, resources.image_id
                image_id = resources.image_id[region.name]
        
        return {
            'instance_type': resources.instance_type,
            'region': region.name,
            'cluster_name': cluster_name,
            'custom_resources': custom_resources,
            'seeweb_gpu_config': seeweb_gpu_config,
            'image_id': image_id,
        }

    @classmethod
    def get_vcpus_mem_from_instance_type(
            cls, instance_type: str) -> Tuple[Optional[float], Optional[float]]:
        return catalog.get_vcpus_mem_from_instance_type(instance_type, clouds='seeweb')

    @classmethod
    def get_accelerators_from_instance_type(
        cls, instance_type: str,
    ) -> Optional[Dict[str, Union[int, float]]]:
        return catalog.get_accelerators_from_instance_type(instance_type, clouds='seeweb')

    @classmethod
    def get_default_instance_type(cls,
                                  cpus: Optional[str] = None,
                                  memory: Optional[str] = None,
                                  disk_tier: Optional[resources_utils.DiskTier] = None,
                                  region: Optional[str] = None,
                                  zone: Optional[str] = None) -> Optional[str]:
        return catalog.get_default_instance_type(cpus=cpus, memory=memory, 
                                                disk_tier=disk_tier, clouds='seeweb')

    def _get_feasible_launchable_resources(
        self, resources: 'resources_lib.Resources'
    ) -> 'resources_utils.FeasibleResources':
        """Get feasible resources for Seeweb."""
        if resources.use_spot:
            return resources_utils.FeasibleResources([], [], 'Spot instances not supported on Seeweb')
        
        if resources.accelerators and len(resources.accelerators) > 1:
            return resources_utils.FeasibleResources([], [], 'Multiple accelerator types not supported on Seeweb')
        
        # Check if instance type exists
        if resources.instance_type and not catalog.instance_type_exists(resources.instance_type, clouds='seeweb'):
            return resources_utils.FeasibleResources([], [], f'Instance type {resources.instance_type} not available on Seeweb')
        
        # Return the resources as feasible
        return resources_utils.FeasibleResources([resources], [], None)

    @classmethod
    def _check_compute_credentials(cls) -> Tuple[bool, Optional[str]]:
        """Check Seeweb compute credentials."""
        try:
            return seeweb_adaptor.check_compute_credentials(), None
        except Exception as e:
            return False, str(e)

    @classmethod
    def _check_storage_credentials(cls) -> Tuple[bool, Optional[str]]:
        """Check Seeweb storage credentials.""" 
        try:
            return seeweb_adaptor.check_storage_credentials(), None
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_user_identities(cls) -> Optional[List[List[str]]]:
        # Seeweb doesn't have user identity concept
        return None

    @classmethod
    def query_status(cls, name: str, tag_filters: Dict[str, str],
                     region: Optional[str], zone: Optional[str],
                     **kwargs) -> List['status_lib.ClusterStatus']:
        """Query the status of Seeweb cluster instances."""
        # Import here to avoid circular imports
        from sky.provision.seeweb import instance as seeweb_instance
        return seeweb_instance.query_instances(name, {})

    def get_credential_file_mounts(self) -> Dict[str, str]:
        """Returns the credential files to mount."""
        return {
            _SEEWEB_KEY_FILE: _SEEWEB_KEY_FILE,
        }

    def instance_type_exists(self, instance_type: str) -> bool:
        """Returns whether the instance type exists for Seeweb."""
        return catalog.instance_type_exists(instance_type, clouds='seeweb')

    @classmethod
    def get_image_size(cls, image_id: str, region: Optional[str]) -> float:
        """Seeweb doesn't support custom images."""
        del image_id, region  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Custom images are not supported on {cls._REPR}. '
                'Seeweb clusters use pre-configured images only.')

    # Image-related methods (not supported)
    @classmethod  
    def create_image_from_cluster(cls,
                                  cluster_name: resources_utils.ClusterName,
                                  region: Optional[str],
                                  zone: Optional[str]) -> str:
        del cluster_name, region, zone  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Creating images from clusters is not supported on {cls._REPR}. '
                'Seeweb does not support custom image creation.')

    @classmethod
    def maybe_move_image(cls, image_id: str, source_region: str,
                         target_region: str, source_zone: Optional[str],
                         target_zone: Optional[str]) -> str:
        del image_id, source_region, target_region, source_zone, target_zone  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Moving images between regions is not supported on {cls._REPR}. '
                'Seeweb does not support custom images.')

    @classmethod
    def delete_image(cls, image_id: str, region: Optional[str]) -> None:
        del image_id, region  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Deleting images is not supported on {cls._REPR}. '
                'Seeweb does not support custom image management.')

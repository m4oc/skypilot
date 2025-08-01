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

# api_key = <TOKEN>  ← You can find this in the Seeweb panel: Compute → API Token → New Token
_SEEWEB_KEY_FILE = '~/.seeweb_cloud/seeweb_keys'

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
        print(f"[DEBUG_SEEWEB105] _unsupported_features_for_resources called with resources: {resources}")
        print(f"[DEBUG_SEEWEB106] resources.cloud: {resources.cloud}")
        print(f"[DEBUG_SEEWEB107] resources.instance_type: {resources.instance_type}")
        print(f"[DEBUG_SEEWEB108] resources.accelerators: {resources.accelerators}")
        print(f"[DEBUG_SEEWEB109] resources.cpus: {resources.cpus}")
        print(f"[DEBUG_SEEWEB110] resources.memory: {resources.memory}")
        print(f"[DEBUG_SEEWEB111] resources.region: {resources.region}")
        print(f"[DEBUG_SEEWEB112] resources.zone: {resources.zone}")
        print(f"[DEBUG_SEEWEB113] resources.use_spot: {resources.use_spot}")
        print(f"[DEBUG_SEEWEB114] resources.is_launchable(): {resources.is_launchable()}")
        return cls._CLOUD_UNSUPPORTED_FEATURES

    @classmethod
    def max_cluster_name_length(cls) -> Optional[int]:
        return cls._MAX_CLUSTER_NAME_LEN_LIMIT

    @classmethod
    def regions(cls) -> List['clouds.Region']:
        """Return available regions for Seeweb."""
        print(f"[DEBUG_SEEWEB115] regions() called")
        regions = catalog.regions(clouds='seeweb')
        print(f"[DEBUG_SEEWEB116] regions() returned: {regions}")
        return regions

    @classmethod
    def regions_with_offering(cls, instance_type: str,
                              accelerators: Optional[Dict[str, int]],
                              use_spot: bool, region: Optional[str],
                              zone: Optional[str]) -> List[clouds.Region]:
        print(f"[DEBUG_SEEWEB117] regions_with_offering called with:")
        print(f"  instance_type: {instance_type}")
        print(f"  accelerators: {accelerators}")
        print(f"  use_spot: {use_spot}")
        print(f"  region: {region}")
        print(f"  zone: {zone}")
        
        assert zone is None, 'Seeweb does not support zones.'
        del zone  # unused
        if use_spot:
            print(f"[DEBUG_SEEWEB118] use_spot=True, returning empty list")
            return []
        
        # Get regions from catalog based on instance type
        # This will read the CSV and return only regions where the instance type exists
        print(f"[DEBUG_SEEWEB119] calling catalog.get_region_zones_for_instance_type")
        regions = catalog.get_region_zones_for_instance_type(
            instance_type, use_spot, 'seeweb')
        print(f"[DEBUG_SEEWEB120] catalog returned regions: {regions}")

        if region is not None:
            regions = [r for r in regions if r.name == region]
            print(f"[DEBUG_SEEWEB121] filtered by region {region}: {regions}")
        
        print(f"[DEBUG_SEEWEB122] regions_with_offering returning: {regions}")
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
        print(f"[DEBUG_SEEWEB123] zones_provision_loop called with:")
        print(f"  region: {region}")
        print(f"  num_nodes: {num_nodes}")
        print(f"  instance_type: {instance_type}")
        print(f"  accelerators: {accelerators}")
        print(f"  use_spot: {use_spot}")
        
        del num_nodes  # unused
        regions = cls.regions_with_offering(instance_type,
                                            accelerators,
                                            use_spot,
                                            region=region,
                                            zone=None)
        print(f"[DEBUG_SEEWEB124] regions_with_offering returned: {regions}")
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
        print(f"[DEBUG_SEEWEB125] instance_type_to_hourly_cost called with:")
        print(f"  instance_type: {instance_type}")
        print(f"  use_spot: {use_spot}")
        print(f"  region: {region}")
        print(f"  zone: {zone}")
        
        cost = catalog.get_hourly_cost(instance_type, use_spot=use_spot, region=region, zone=zone, clouds='seeweb')
        print(f"[DEBUG_SEEWEB126] cost returned: {cost}")
        return cost

    def accelerators_to_hourly_cost(self, accelerators: Dict[str, int],
                                    use_spot: bool, region: Optional[str],
                                    zone: Optional[str]) -> float:
        # For Seeweb, accelerator costs are included in instance cost
        print(f"[DEBUG_SEEWEB127] accelerators_to_hourly_cost called with:")
        print(f"  accelerators: {accelerators}")
        print(f"  use_spot: {use_spot}")
        print(f"  region: {region}")
        print(f"  zone: {zone}")
        print(f"[DEBUG_SEEWEB128] returning 0.0 (costs included in instance cost)")
        return 0.0

    def get_egress_cost(self, num_gigabytes: float):
        # Seeweb doesn't charge for egress (simplified)
        print(f"[DEBUG_SEEWEB129] get_egress_cost called with num_gigabytes: {num_gigabytes}")
        print(f"[DEBUG_SEEWEB130] returning 0.0 (no egress charges)")
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
        print(f"[DEBUG_SEEWEB131] make_deploy_resources_variables called with:")
        print(f"  resources: {resources}")
        print(f"  cluster_name: {cluster_name}")
        print(f"  region: {region}")
        print(f"  zones: {zones}")
        print(f"  num_nodes: {num_nodes}")
        print(f"  dryrun: {dryrun}")
        print(f"  volume_mounts: {volume_mounts}")
        
        # Note: Spot instances and multi-node are automatically handled by 
        # the framework via _CLOUD_UNSUPPORTED_FEATURES
        
        print(f"[DEBUG_SEEWEB132] calling resources.assert_launchable()")
        resources = resources.assert_launchable()
        print(f"[DEBUG_SEEWEB133] assert_launchable() passed")
        
        print(f"[DEBUG_SEEWEB134] calling get_accelerators_from_instance_type")
        acc_dict = self.get_accelerators_from_instance_type(
            resources.instance_type)
        print(f"[DEBUG_SEEWEB135] acc_dict: {acc_dict}")
        
        # Standard custom_resources string for Ray (like other clouds)
        print(f"[DEBUG_SEEWEB136] calling make_ray_custom_resources_str")
        custom_resources = resources_utils.make_ray_custom_resources_str(
            acc_dict)
        print(f"[DEBUG_SEEWEB137] custom_resources: {custom_resources}")
        
        # Seeweb-specific GPU configuration for the provisioner
        seeweb_gpu_config = None
        if resources.accelerators:
            print(f"[DEBUG_SEEWEB138] resources.accelerators found: {resources.accelerators}")
            # If the instance has accelerators, prepare GPU configuration
            accelerator_name = list(resources.accelerators.keys())[0]
            accelerator_count = resources.accelerators[accelerator_name]
            seeweb_gpu_config = {
                'gpu': accelerator_count,
                'gpu_label': accelerator_name
            }
            print(f"[DEBUG_SEEWEB139] seeweb_gpu_config: {seeweb_gpu_config}")
        else:
            print(f"[DEBUG_SEEWEB140] no accelerators found")
        
        # Seeweb uses pre-configured images based on instance type
        # Determine image based on whether the instance type name contains "GPU"
        if resources.instance_type and 'GPU' in resources.instance_type.upper():
            # GPU instance - use image with NVIDIA drivers
            image_id = 'ubuntu-2204-nvidia-gpu-driver'
            print(f"[DEBUG_SEEWEB141] GPU instance detected (name contains 'GPU'), using image: {image_id}")
        else:
            # CPU-only instance - use standard Ubuntu image
            image_id = 'ubuntu-2204'
            print(f"[DEBUG_SEEWEB142] CPU-only instance detected (name doesn't contain 'GPU'), using image: {image_id}")
        
        # Handle custom image_id if specified (though not supported)
        if resources.image_id is not None:
            print(f"[DEBUG_SEEWEB143] resources.image_id found: {resources.image_id}")
            # Even though custom images aren't supported, we should handle 
            # the case where someone tries to specify one and provide a clear error
            if None in resources.image_id:
                image_id = resources.image_id[None]
            else:
                assert region.name in resources.image_id, resources.image_id
                image_id = resources.image_id[region.name]
            print(f"[DEBUG_SEEWEB144] using custom image_id: {image_id}")
        
        result = {
            'instance_type': resources.instance_type,
            'region': region.name,
            'cluster_name': cluster_name,
            'custom_resources': custom_resources,
            'seeweb_gpu_config': seeweb_gpu_config,
            'image_id': image_id,
        }
        print(f"[DEBUG_SEEWEB143] returning result: {result}")
        return result

    @classmethod
    def get_vcpus_mem_from_instance_type(
            cls, instance_type: str) -> Tuple[Optional[float], Optional[float]]:
        print(f"[DEBUG_SEEWEB144] get_vcpus_mem_from_instance_type called with instance_type: {instance_type}")
        result = catalog.get_vcpus_mem_from_instance_type(instance_type, clouds='seeweb')
        print(f"[DEBUG_SEEWEB145] get_vcpus_mem_from_instance_type returned: {result}")
        return result

    @classmethod
    def get_accelerators_from_instance_type(
        cls, instance_type: str,
    ) -> Optional[Dict[str, Union[int, float]]]:
        print(f"[DEBUG_SEEWEB146] get_accelerators_from_instance_type called with instance_type: {instance_type}")
        result = catalog.get_accelerators_from_instance_type(instance_type, clouds='seeweb')
        print(f"[DEBUG_SEEWEB147] get_accelerators_from_instance_type returned: {result}")
        return result

    @classmethod
    def get_default_instance_type(cls,
                                  cpus: Optional[str] = None,
                                  memory: Optional[str] = None,
                                  disk_tier: Optional[resources_utils.DiskTier] = None,
                                  region: Optional[str] = None,
                                  zone: Optional[str] = None) -> Optional[str]:
        print(f"[DEBUG_SEEWEB148] get_default_instance_type called with:")
        print(f"  cpus: {cpus}")
        print(f"  memory: {memory}")
        print(f"  disk_tier: {disk_tier}")
        print(f"  region: {region}")
        print(f"  zone: {zone}")
        
        result = catalog.get_default_instance_type(cpus=cpus, memory=memory, 
                                                disk_tier=disk_tier, clouds='seeweb')
        print(f"[DEBUG_SEEWEB149] get_default_instance_type returned: {result}")
        return result

    def _get_feasible_launchable_resources(
        self, resources: 'resources_lib.Resources'
    ) -> 'resources_utils.FeasibleResources':
        """Get feasible resources for Seeweb."""
        print(f"[DEBUG_SEEWEB150] _get_feasible_launchable_resources called with:")
        print(f"  resources: {resources}")
        print(f"  resources.cloud: {resources.cloud}")
        print(f"  resources.instance_type: {resources.instance_type}")
        print(f"  resources.accelerators: {resources.accelerators}")
        print(f"  resources.cpus: {resources.cpus}")
        print(f"  resources.memory: {resources.memory}")
        print(f"  resources.region: {resources.region}")
        print(f"  resources.zone: {resources.zone}")
        print(f"  resources.use_spot: {resources.use_spot}")
        print(f"  resources.is_launchable(): {resources.is_launchable()}")
        
        if resources.use_spot:
            print(f"[DEBUG_SEEWEB151] use_spot=True, returning empty with error")
            return resources_utils.FeasibleResources([], [], 'Spot instances not supported on Seeweb')
        
        if resources.accelerators and len(resources.accelerators) > 1:
            print(f"[DEBUG_SEEWEB152] multiple accelerators found, returning empty with error")
            return resources_utils.FeasibleResources([], [], 'Multiple accelerator types not supported on Seeweb')
        
        # If no instance_type is specified, try to get a default one
        if not resources.instance_type:
            print(f"[DEBUG_SEEWEB153] no instance_type specified, trying to get default")
            
            # If accelerators are specified, try to find instance type for that accelerator
            if resources.accelerators:
                print(f"[DEBUG_SEEWEB153a] accelerators specified: {resources.accelerators}")
                # Get the first accelerator (we already checked there's only one)
                acc_name, acc_count = list(resources.accelerators.items())[0]
                print(f"[DEBUG_SEEWEB153b] looking for instance type for {acc_name}:{acc_count}")
                
                # Use catalog to find instance type for this accelerator
                instance_types, fuzzy_candidates = catalog.get_instance_type_for_accelerator(
                    acc_name=acc_name,
                    acc_count=acc_count,
                    cpus=resources.cpus,
                    memory=resources.memory,
                    use_spot=resources.use_spot,
                    region=resources.region,
                    zone=resources.zone,
                    clouds='seeweb'
                )
                print(f"[DEBUG_SEEWEB153c] catalog returned instance_types: {instance_types}, fuzzy_candidates: {fuzzy_candidates}")
                
                if instance_types and len(instance_types) > 0:
                    # Use the first (cheapest) instance type
                    selected_instance_type = instance_types[0]
                    print(f"[DEBUG_SEEWEB153d] selected instance type: {selected_instance_type}")
                    resources = resources.copy(instance_type=selected_instance_type)
                    print(f"[DEBUG_SEEWEB153e] new resources: {resources}")
                    print(f"[DEBUG_SEEWEB153f] new resources.is_launchable(): {resources.is_launchable()}")
                else:
                    print(f"[DEBUG_SEEWEB153g] no instance type found for accelerator {acc_name}:{acc_count}")
                    return resources_utils.FeasibleResources([], fuzzy_candidates, 
                        f'No instance type found for accelerator {acc_name}:{acc_count} on Seeweb')
            else:
                # No accelerators specified, use default instance type
                default_instance_type = self.get_default_instance_type(
                    cpus=resources.cpus,
                    memory=resources.memory,
                    region=resources.region,
                    zone=resources.zone
                )
                print(f"[DEBUG_SEEWEB154] get_default_instance_type returned: {default_instance_type}")
                
                if default_instance_type:
                    print(f"[DEBUG_SEEWEB155] creating new resources with instance_type: {default_instance_type}")
                    # Create new resources with the default instance type
                    resources = resources.copy(instance_type=default_instance_type)
                    print(f"[DEBUG_SEEWEB156] new resources: {resources}")
                    print(f"[DEBUG_SEEWEB157] new resources.is_launchable(): {resources.is_launchable()}")
                else:
                    print(f"[DEBUG_SEEWEB158] no default instance type found, returning empty with error")
                    return resources_utils.FeasibleResources([], [], 
                        f'No suitable instance type found for cpus={resources.cpus}, memory={resources.memory}')
        
        # Check if instance type exists
        if resources.instance_type:
            print(f"[DEBUG_SEEWEB159] checking if instance_type exists: {resources.instance_type}")
            exists = catalog.instance_type_exists(resources.instance_type, clouds='seeweb')
            print(f"[DEBUG_SEEWEB160] instance_type_exists returned: {exists}")
            if not exists:
                print(f"[DEBUG_SEEWEB161] instance_type does not exist, returning empty with error")
                return resources_utils.FeasibleResources([], [], f'Instance type {resources.instance_type} not available on Seeweb')
        else:
            print(f"[DEBUG_SEEWEB162] no instance_type specified")
        
        # Set the cloud if not already set
        if not resources.cloud:
            print(f"[DEBUG_SEEWEB163] setting cloud to Seeweb")
            resources = resources.copy(cloud=self)
        
        # Return the resources as feasible
        print(f"[DEBUG_SEEWEB164] returning resources as feasible")
        return resources_utils.FeasibleResources([resources], [], None)

    @classmethod
    def _check_compute_credentials(cls) -> Tuple[bool, Optional[str]]:
        """Check Seeweb compute credentials."""
        print(f"[DEBUG_SEEWEB164] _check_compute_credentials called")
        try:
            result = seeweb_adaptor.check_compute_credentials()
            print(f"[DEBUG_SEEWEB165] _check_compute_credentials returned: {result}")
            return result, None
        except Exception as e:
            print(f"[DEBUG_SEEWEB166] _check_compute_credentials exception: {e}")
            return False, str(e)

    @classmethod
    def _check_storage_credentials(cls) -> Tuple[bool, Optional[str]]:
        """Check Seeweb storage credentials.""" 
        print(f"[DEBUG_SEEWEB167] _check_storage_credentials called")
        try:
            result = seeweb_adaptor.check_storage_credentials()
            print(f"[DEBUG_SEEWEB168] _check_storage_credentials returned: {result}")
            return result, None
        except Exception as e:
            print(f"[DEBUG_SEEWEB169] _check_storage_credentials exception: {e}")
            return False, str(e)

    @classmethod
    def get_user_identities(cls) -> Optional[List[List[str]]]:
        # Seeweb doesn't have user identity concept
        print(f"[DEBUG_SEEWEB170] get_user_identities called, returning None")
        return None

    @classmethod
    def query_status(cls, name: str, tag_filters: Dict[str, str],
                     region: Optional[str], zone: Optional[str],
                     **kwargs) -> List['status_lib.ClusterStatus']:
        """Query the status of Seeweb cluster instances."""
        print(f"[DEBUG_SEEWEB171] query_status called with:")
        print(f"  name: {name}")
        print(f"  tag_filters: {tag_filters}")
        print(f"  region: {region}")
        print(f"  zone: {zone}")
        print(f"  kwargs: {kwargs}")
        
        # Import here to avoid circular imports
        from sky.provision.seeweb import instance as seeweb_instance
        result = seeweb_instance.query_instances(name, {})
        print(f"[DEBUG_SEEWEB172] query_status returned: {result}")
        return result

    def get_credential_file_mounts(self) -> Dict[str, str]:
        """Returns the credential files to mount."""
        print(f"[DEBUG_SEEWEB173] get_credential_file_mounts called")
        result = {
            _SEEWEB_KEY_FILE: _SEEWEB_KEY_FILE,
        }
        print(f"[DEBUG_SEEWEB174] get_credential_file_mounts returned: {result}")
        return result

    def instance_type_exists(self, instance_type: str) -> bool:
        """Returns whether the instance type exists for Seeweb."""
        print(f"[DEBUG_SEEWEB175] instance_type_exists called with instance_type: {instance_type}")
        result = catalog.instance_type_exists(instance_type, clouds='seeweb')
        print(f"[DEBUG_SEEWEB176] instance_type_exists returned: {result}")
        return result

    @classmethod
    def get_image_size(cls, image_id: str, region: Optional[str]) -> float:
        """Seeweb doesn't support custom images."""
        print(f"[DEBUG_SEEWEB177] get_image_size called with image_id: {image_id}, region: {region}")
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
        print(f"[DEBUG_SEEWEB178] create_image_from_cluster called with:")
        print(f"  cluster_name: {cluster_name}")
        print(f"  region: {region}")
        print(f"  zone: {zone}")
        
        del cluster_name, region, zone  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Creating images from clusters is not supported on {cls._REPR}. '
                'Seeweb does not support custom image creation.')

    @classmethod
    def maybe_move_image(cls, image_id: str, source_region: str,
                         target_region: str, source_zone: Optional[str],
                         target_zone: Optional[str]) -> str:
        print(f"[DEBUG_SEEWEB179] maybe_move_image called with:")
        print(f"  image_id: {image_id}")
        print(f"  source_region: {source_region}")
        print(f"  target_region: {target_region}")
        print(f"  source_zone: {source_zone}")
        print(f"  target_zone: {target_zone}")
        
        del image_id, source_region, target_region, source_zone, target_zone  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Moving images between regions is not supported on {cls._REPR}. '
                'Seeweb does not support custom images.')

    @classmethod
    def delete_image(cls, image_id: str, region: Optional[str]) -> None:
        print(f"[DEBUG_SEEWEB180] delete_image called with:")
        print(f"  image_id: {image_id}")
        print(f"  region: {region}")
        
        del image_id, region  # unused
        with ux_utils.print_exception_no_traceback():
            raise ValueError(
                f'Deleting images is not supported on {cls._REPR}. '
                'Seeweb does not support custom image management.')

#!/usr/bin/env python3
"""
Targeted debug script to trace the exact execution path of:
sky launch -c madrid --infra Seeweb --instance-type ECS1GPU2

This script will help understand exactly where the region comes from in this specific command.
"""

import os
import sys
import logging
from typing import Optional, List

# Add the sky directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sky'))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def trace_launch_command():
    """Trace the exact execution path of the launch command."""
    print("=" * 80)
    print("TRACING SKY LAUNCH COMMAND EXECUTION")
    print("=" * 80)
    print("Command: sky launch -c madrid --infra Seeweb --instance-type ECS1GPU2")
    print()
    
    try:
        # Step 1: Parse the command line arguments
        print("STEP 1: Command Line Argument Parsing")
        print("-" * 40)
        
        # Simulate the command line arguments
        args = {
            'cluster': 'madrid',
            'infra': 'Seeweb',
            'instance_type': 'ECS1GPU2',
            'entrypoint': (),
            'dryrun': False,
            'detach_run': False,
            'backend_name': None,
            'name': None,
            'workdir': None,
            'cloud': None,
            'region': None,
            'zone': None,
            'gpus': None,
            'cpus': None,
            'memory': None,
            'num_nodes': None,
            'use_spot': None,
            'image_id': None,
            'env_file': None,
            'env': [],
            'secret': [],
            'disk_size': None,
            'disk_tier': None,
            'network_tier': None,
            'ports': (),
            'idle_minutes_to_autostop': None,
            'down': False,
            'retry_until_up': False,
            'yes': False,
            'no_setup': False,
            'clone_disk_from': None,
            'fast': False,
            'async_call': False,
            'config_override': None,
            'git_url': None,
            'git_ref': None,
        }
        
        print("Parsed arguments:")
        for key, value in args.items():
            if value is not None:
                print(f"  {key}: {value}")
        
        # Step 2: Handle infra/cloud/region/zone options
        print("\nSTEP 2: Infra/Cloud/Region/Zone Handling")
        print("-" * 40)
        
        from sky.client.cli.command import _handle_infra_cloud_region_zone_options
        
        cloud, region, zone = _handle_infra_cloud_region_zone_options(
            args['infra'], args['cloud'], args['region'], args['zone']
        )
        
        print(f"After _handle_infra_cloud_region_zone_options:")
        print(f"  Cloud: {cloud}")
        print(f"  Region: {region}")
        print(f"  Zone: {zone}")
        
        # Step 3: Create task with overrides
        print("\nSTEP 3: Task Creation with Overrides")
        print("-" * 40)
        
        from sky.client.cli.command import _make_task_or_dag_from_entrypoint_with_overrides
        
        task_or_dag = _make_task_or_dag_from_entrypoint_with_overrides(
            entrypoint=args['entrypoint'],
            name=args['name'],
            workdir=args['workdir'],
            cloud=cloud,
            region=region,
            zone=zone,
            gpus=args['gpus'],
            cpus=args['cpus'],
            memory=args['memory'],
            instance_type=args['instance_type'],
            num_nodes=args['num_nodes'],
            use_spot=args['use_spot'],
            image_id=args['image_id'],
            env=args['env'],
            secret=args['secret'],
            disk_size=args['disk_size'],
            disk_tier=args['disk_tier'],
            network_tier=args['network_tier'],
            ports=args['ports'],
            config_override=args['config_override'],
            git_url=args['git_url'],
            git_ref=args['git_ref'],
        )
        
        print(f"Created task: {task_or_dag}")
        if hasattr(task_or_dag, 'resources'):
            print(f"Task resources: {task_or_dag.resources}")
            print(f"  Cloud: {task_or_dag.resources.cloud}")
            print(f"  Region: {task_or_dag.resources.region}")
            print(f"  Zone: {task_or_dag.resources.zone}")
            print(f"  Instance type: {task_or_dag.resources.instance_type}")
        
        # Step 4: Check if resources are launchable
        print("\nSTEP 4: Resource Launchability Check")
        print("-" * 40)
        
        if hasattr(task_or_dag, 'resources'):
            resources = task_or_dag.resources
            print(f"Is launchable: {resources.is_launchable()}")
            
            if resources.is_launchable():
                try:
                    valid_regions = resources.get_valid_regions_for_launchable()
                    print(f"Valid regions for launch: {len(valid_regions)}")
                    
                    for i, region_obj in enumerate(valid_regions):
                        print(f"  Region {i+1}: {region_obj.name}")
                        if region_obj.zones:
                            for zone_obj in region_obj.zones:
                                print(f"    Zone: {zone_obj.name}")
                                
                except Exception as e:
                    print(f"Error getting valid regions: {e}")
        
        # Step 5: Optimize resources
        print("\nSTEP 5: Resource Optimization")
        print("-" * 40)
        
        if hasattr(task_or_dag, 'resources'):
            from sky import optimizer
            
            try:
                optimized_resources = optimizer.optimize(task_or_dag.resources)
                print(f"Optimization result: {len(optimized_resources) if optimized_resources else 0} options")
                
                if optimized_resources:
                    for i, opt_resource in enumerate(optimized_resources):
                        print(f"  Option {i+1}:")
                        print(f"    Cloud: {opt_resource.cloud}")
                        print(f"    Region: {opt_resource.region}")
                        print(f"    Zone: {opt_resource.zone}")
                        print(f"    Instance type: {opt_resource.instance_type}")
                        
            except Exception as e:
                print(f"Error in optimization: {e}")
        
        # Step 6: Check cloud-specific behavior
        print("\nSTEP 6: Cloud-Specific Behavior")
        print("-" * 40)
        
        if hasattr(task_or_dag, 'resources') and task_or_dag.resources.cloud:
            cloud_obj = task_or_dag.resources.cloud
            print(f"Cloud object: {cloud_obj}")
            print(f"Cloud type: {type(cloud_obj)}")
            
            # Check if this cloud has regions_with_offering method
            if hasattr(cloud_obj, 'regions_with_offering'):
                try:
                    regions = cloud_obj.regions_with_offering(
                        task_or_dag.resources.instance_type,
                        task_or_dag.resources.accelerators,
                        task_or_dag.resources.use_spot,
                        task_or_dag.resources.region,
                        task_or_dag.resources.zone
                    )
                    print(f"Cloud regions_with_offering result: {len(regions)} regions")
                    for region_obj in regions:
                        print(f"  - {region_obj.name}")
                        
                except Exception as e:
                    print(f"Error calling regions_with_offering: {e}")
        
        # Step 7: Check service catalog
        print("\nSTEP 7: Service Catalog Check")
        print("-" * 40)
        
        try:
            from sky.clouds import service_catalog
            
            # Check what clouds are available
            print("Available clouds in service catalog:")
            try:
                # This might not work for all clouds, but let's try
                for cloud_name in ['aws', 'gcp', 'azure', 'seeweb']:
                    try:
                        regions = service_catalog.get_region_zones(clouds=cloud_name)
                        print(f"  {cloud_name}: {len(regions)} regions")
                    except Exception as e:
                        print(f"  {cloud_name}: Error - {e}")
            except Exception as e:
                print(f"Error checking service catalog: {e}")
                
        except Exception as e:
            print(f"Error importing service catalog: {e}")
        
        # Step 8: Check configuration
        print("\nSTEP 8: Configuration Check")
        print("-" * 40)
        
        try:
            from sky import skypilot_config
            
            config = skypilot_config.get_loaded_config()
            if config:
                print("Configuration keys:")
                for key in config.keys():
                    if 'region' in key.lower() or 'infra' in key.lower() or 'seeweb' in key.lower():
                        print(f"  {key}: {config[key]}")
            else:
                print("No configuration loaded")
                
        except Exception as e:
            print(f"Error checking configuration: {e}")
            
    except Exception as e:
        print(f"Error in trace_launch_command: {e}")
        import traceback
        traceback.print_exc()

def check_seeweb_specific():
    """Check Seeweb-specific configurations and behavior."""
    print("\n" + "=" * 80)
    print("SEEWEB-SPECIFIC CHECKS")
    print("=" * 80)
    
    try:
        # Check if Seeweb is in the cloud registry
        from sky.clouds import registry
        
        print("Checking Seeweb in cloud registry:")
        if 'seeweb' in registry.CLOUD_REGISTRY.clouds:
            print("  ✓ Seeweb found in cloud registry")
            seeweb_cloud = registry.CLOUD_REGISTRY.from_str('seeweb')
            print(f"  Cloud object: {seeweb_cloud}")
        else:
            print("  ✗ Seeweb NOT found in cloud registry")
            print("  Available clouds:")
            for cloud in registry.CLOUD_REGISTRY.clouds:
                print(f"    - {cloud}")
        
        # Check if there's a Seeweb cloud implementation
        try:
            from sky.clouds import seeweb
            print("  ✓ Seeweb cloud module found")
        except ImportError:
            print("  ✗ Seeweb cloud module not found")
        
        # Check service catalog for Seeweb
        try:
            from sky.clouds import service_catalog
            
            try:
                regions = service_catalog.get_region_zones(clouds='seeweb')
                print(f"  ✓ Seeweb regions in catalog: {len(regions)}")
                for region in regions:
                    print(f"    - {region.name}")
            except Exception as e:
                print(f"  ✗ Error getting Seeweb regions: {e}")
                
        except Exception as e:
            print(f"  ✗ Error accessing service catalog: {e}")
            
    except Exception as e:
        print(f"Error in check_seeweb_specific: {e}")

def main():
    """Run the debug script."""
    print("SKYPILOT LAUNCH COMMAND DEBUG")
    print("=" * 80)
    print("This script traces the exact execution path of the sky launch command")
    print("to understand where the region comes from when using --infra Seeweb")
    print()
    
    trace_launch_command()
    check_seeweb_specific()
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)
    print("The output above shows the step-by-step execution of the sky launch command.")
    print("Look for:")
    print("1. How the --infra Seeweb argument is parsed")
    print("2. Whether Seeweb is recognized as a valid cloud")
    print("3. What regions are available for Seeweb")
    print("4. How the final region is selected by the optimizer")

if __name__ == "__main__":
    main() 
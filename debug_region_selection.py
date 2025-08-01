#!/usr/bin/env python3
"""
Debug script to understand region selection in SkyPilot when using --infra Seeweb

This script traces the region selection process step by step to understand where
the region comes from when running:
sky api stop && sleep 1 && sky api start && sleep 1 && sky launch -c madrid --infra Seeweb --instance-type ECS1GPU2
"""

import os
import sys
import logging
from typing import Optional, List

# Add the sky directory to the path so we can import sky modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sky'))

# Configure logging to see debug information
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def debug_infra_parsing():
    """Debug the infra string parsing process."""
    print("=" * 60)
    print("DEBUGGING INFRA STRING PARSING")
    print("=" * 60)
    
    try:
        from sky.utils import infra_utils
        
        # Test the infra string parsing
        infra_string = "Seeweb"
        print(f"Testing infra string: '{infra_string}'")
        
        infra_info = infra_utils.InfraInfo.from_str(infra_string)
        print(f"Parsed infra info:")
        print(f"  Cloud: {infra_info.cloud}")
        print(f"  Region: {infra_info.region}")
        print(f"  Zone: {infra_info.zone}")
        
        # Test with different formats
        test_cases = [
            "Seeweb",
            "Seeweb/madrid", 
            "Seeweb/madrid/zone1",
            "aws",
            "aws/us-east-1",
            "gcp/us-central1"
        ]
        
        print("\nTesting various infra string formats:")
        for test_case in test_cases:
            try:
                info = infra_utils.InfraInfo.from_str(test_case)
                print(f"  '{test_case}' -> Cloud: {info.cloud}, Region: {info.region}, Zone: {info.zone}")
            except Exception as e:
                print(f"  '{test_case}' -> ERROR: {e}")
                
    except Exception as e:
        print(f"Error in infra parsing debug: {e}")

def debug_cloud_registry():
    """Debug the cloud registry to see available clouds."""
    print("\n" + "=" * 60)
    print("DEBUGGING CLOUD REGISTRY")
    print("=" * 60)
    
    try:
        from sky.clouds import registry
        
        print("Available clouds in registry:")
        for cloud_name in registry.CLOUD_REGISTRY.clouds:
            print(f"  - {cloud_name}")
            
        # Try to get the Seeweb cloud
        try:
            seeweb_cloud = registry.CLOUD_REGISTRY.from_str("Seeweb")
            print(f"\nSeeweb cloud object: {seeweb_cloud}")
            print(f"Seeweb cloud type: {type(seeweb_cloud)}")
        except Exception as e:
            print(f"\nError getting Seeweb cloud: {e}")
            
    except Exception as e:
        print(f"Error in cloud registry debug: {e}")

def debug_service_catalog():
    """Debug the service catalog to see available regions for Seeweb."""
    print("\n" + "=" * 60)
    print("DEBUGGING SERVICE CATALOG")
    print("=" * 60)
    
    try:
        from sky.clouds import service_catalog
        
        # Check if Seeweb has a catalog
        try:
            regions = service_catalog.get_region_zones(clouds='seeweb')
            print(f"Seeweb regions from catalog: {regions}")
        except Exception as e:
            print(f"Error getting Seeweb regions from catalog: {e}")
            
        # Check for instance type ECS1GPU2
        try:
            instance_regions = service_catalog.get_region_zones_for_instance_type(
                'ECS1GPU2', use_spot=False, clouds='seeweb')
            print(f"Regions with ECS1GPU2 instance: {instance_regions}")
        except Exception as e:
            print(f"Error getting regions for ECS1GPU2: {e}")
            
    except Exception as e:
        print(f"Error in service catalog debug: {e}")

def debug_resources_creation():
    """Debug the Resources object creation and region selection."""
    print("\n" + "=" * 60)
    print("DEBUGGING RESOURCES CREATION")
    print("=" * 60)
    
    try:
        from sky import resources as resources_lib
        from sky.clouds import registry
        
        # Create a Resources object similar to what would be created by the command
        print("Creating Resources object with infra='Seeweb' and instance_type='ECS1GPU2'")
        
        resources = resources_lib.Resources(
            infra='Seeweb',
            instance_type='ECS1GPU2'
        )
        
        print(f"Created resources: {resources}")
        print(f"Cloud: {resources.cloud}")
        print(f"Region: {resources.region}")
        print(f"Zone: {resources.zone}")
        print(f"Instance type: {resources.instance_type}")
        
        # Check if the resources are launchable
        print(f"Is launchable: {resources.is_launchable()}")
        
        if resources.is_launchable():
            try:
                valid_regions = resources.get_valid_regions_for_launchable()
                print(f"Valid regions for launch: {valid_regions}")
                
                if valid_regions:
                    print("Details of valid regions:")
                    for region in valid_regions:
                        print(f"  - {region.name}")
                        if region.zones:
                            for zone in region.zones:
                                print(f"    Zone: {zone.name}")
                else:
                    print("No valid regions found!")
                    
            except Exception as e:
                print(f"Error getting valid regions: {e}")
                
    except Exception as e:
        print(f"Error in resources creation debug: {e}")

def debug_optimizer():
    """Debug the optimizer to see how it selects regions."""
    print("\n" + "=" * 60)
    print("DEBUGGING OPTIMIZER")
    print("=" * 60)
    
    try:
        from sky import optimizer
        from sky import resources as resources_lib
        
        # Create resources
        resources = resources_lib.Resources(
            infra='Seeweb',
            instance_type='ECS1GPU2'
        )
        
        print(f"Resources to optimize: {resources}")
        
        # Try to optimize the resources
        try:
            optimized_resources = optimizer.optimize(resources)
            print(f"Optimized resources: {optimized_resources}")
            
            if optimized_resources:
                print("Optimization results:")
                for i, opt_resource in enumerate(optimized_resources):
                    print(f"  Option {i+1}:")
                    print(f"    Cloud: {opt_resource.cloud}")
                    print(f"    Region: {opt_resource.region}")
                    print(f"    Zone: {opt_resource.zone}")
                    print(f"    Instance type: {opt_resource.instance_type}")
                    
        except Exception as e:
            print(f"Error in optimization: {e}")
            
    except Exception as e:
        print(f"Error in optimizer debug: {e}")

def debug_config():
    """Debug the SkyPilot configuration."""
    print("\n" + "=" * 60)
    print("DEBUGGING SKYPILOT CONFIG")
    print("=" * 60)
    
    try:
        from sky import skypilot_config
        
        # Check the loaded config
        config = skypilot_config.get_loaded_config()
        print(f"Loaded config keys: {list(config.keys()) if config else 'None'}")
        
        if config:
            # Check for any region-specific configurations
            for key, value in config.items():
                if 'region' in key.lower() or 'infra' in key.lower():
                    print(f"  {key}: {value}")
                    
    except Exception as e:
        print(f"Error in config debug: {e}")

def debug_environment():
    """Debug the environment variables and system state."""
    print("\n" + "=" * 60)
    print("DEBUGGING ENVIRONMENT")
    print("=" * 60)
    
    # Check environment variables
    relevant_env_vars = [
        'SKYPILOT_CONFIG_PATH',
        'SKYPILOT_CONFIG',
        'SKY_CONFIG_PATH',
        'SKY_CONFIG',
        'HOME',
        'USER'
    ]
    
    print("Environment variables:")
    for var in relevant_env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"  {var}: {value}")
    
    # Check if ~/.sky/config.yaml exists
    home = os.environ.get('HOME', '')
    if home:
        sky_config_path = os.path.join(home, '.sky', 'config.yaml')
        if os.path.exists(sky_config_path):
            print(f"\nSkyPilot config file exists: {sky_config_path}")
            try:
                with open(sky_config_path, 'r') as f:
                    content = f.read()
                    print(f"Config file content (first 500 chars):")
                    print(content[:500])
                    if len(content) > 500:
                        print("... (truncated)")
            except Exception as e:
                print(f"Error reading config file: {e}")
        else:
            print(f"\nSkyPilot config file does not exist: {sky_config_path}")

def main():
    """Run all debug functions."""
    print("SKYPILOT REGION SELECTION DEBUG SCRIPT")
    print("=" * 60)
    print("This script will help debug where the region comes from when running:")
    print("sky api stop && sleep 1 && sky api start && sleep 1 && sky launch -c madrid --infra Seeweb --instance-type ECS1GPU2")
    print()
    
    debug_environment()
    debug_config()
    debug_infra_parsing()
    debug_cloud_registry()
    debug_service_catalog()
    debug_resources_creation()
    debug_optimizer()
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)
    print("Check the output above to understand how the region is determined.")
    print("Key points to look for:")
    print("1. How the 'Seeweb' infra string is parsed")
    print("2. Whether Seeweb is recognized as a valid cloud")
    print("3. What regions are available for Seeweb")
    print("4. How the optimizer selects the final region")

if __name__ == "__main__":
    main() 
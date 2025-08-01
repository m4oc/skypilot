#!/usr/bin/env python3
"""
Simple script to check if Seeweb is properly configured in SkyPilot.
"""

import os
import sys

# Add the sky directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sky'))

def check_seeweb_cloud():
    """Check if Seeweb cloud is available."""
    print("Checking Seeweb cloud availability...")
    
    try:
        # Check if Seeweb is in the cloud registry
        from sky.utils import registry
        
        print(f"Available clouds: {list(registry.CLOUD_REGISTRY.keys())}")
        
        if 'seeweb' in registry.CLOUD_REGISTRY:
            print("✓ Seeweb found in cloud registry")
            
            # Try to get the Seeweb cloud object
            try:
                seeweb_cloud = registry.CLOUD_REGISTRY.from_str('seeweb')
                print(f"✓ Seeweb cloud object: {seeweb_cloud}")
                
                # Check if it has the required methods
                if hasattr(seeweb_cloud, 'regions_with_offering'):
                    print("✓ Seeweb has regions_with_offering method")
                else:
                    print("✗ Seeweb missing regions_with_offering method")
                    
            except Exception as e:
                print(f"✗ Error getting Seeweb cloud object: {e}")
        else:
            print("✗ Seeweb NOT found in cloud registry")
            
    except Exception as e:
        print(f"Error checking cloud registry: {e}")

def check_seeweb_catalog():
    """Check if Seeweb has catalog data."""
    print("\nChecking Seeweb catalog data...")
    
    try:
        from sky.catalog import seeweb_catalog
        
        try:
            regions = seeweb_catalog.get_region_zones()
            print(f"✓ Seeweb regions in catalog: {len(regions)}")
            for region in regions:
                print(f"  - {region.name}")
                
        except Exception as e:
            print(f"✗ Error getting Seeweb regions: {e}")
            
    except Exception as e:
        print(f"Error accessing service catalog: {e}")

def check_seeweb_instance_types():
    """Check if ECS1GPU2 instance type is available for Seeweb."""
    print("\nChecking ECS1GPU2 instance type for Seeweb...")
    
    try:
        from sky.catalog import seeweb_catalog
        
        try:
            regions = seeweb_catalog.get_region_zones_for_instance_type(
                'ECS1GPU2', use_spot=False)
            print(f"✓ ECS1GPU2 available in {len(regions)} regions")
            for region in regions:
                print(f"  - {region.name}")
                
        except Exception as e:
            print(f"✗ Error checking ECS1GPU2 availability: {e}")
            
    except Exception as e:
        print(f"Error accessing service catalog: {e}")

def check_seeweb_module():
    """Check if Seeweb cloud module exists."""
    print("\nChecking Seeweb cloud module...")
    
    try:
        from sky.clouds import seeweb
        print("✓ Seeweb cloud module found")
        
        # Check if it has the required methods
        if hasattr(seeweb, 'Seeweb'):
            print("✓ Seeweb class found")
            
            # Try to instantiate it
            try:
                seeweb_instance = seeweb.Seeweb()
                print("✓ Seeweb class can be instantiated")
                
                # Check if it has regions_with_offering
                if hasattr(seeweb_instance, 'regions_with_offering'):
                    print("✓ Seeweb instance has regions_with_offering method")
                else:
                    print("✗ Seeweb instance missing regions_with_offering method")
                    
            except Exception as e:
                print(f"✗ Error instantiating Seeweb: {e}")
        else:
            print("✗ Seeweb class not found")
            
    except ImportError:
        print("✗ Seeweb cloud module not found")
    except Exception as e:
        print(f"Error checking Seeweb module: {e}")

def check_config():
    """Check SkyPilot configuration for Seeweb."""
    print("\nChecking SkyPilot configuration...")
    
    try:
        from sky import skypilot_config
        
        # Try to get the config using the correct method
        try:
            config = skypilot_config.get_config()
            if config:
                print("✓ Configuration loaded")
                
                # Look for Seeweb-related config
                seeweb_config = {}
                for key, value in config.items():
                    if 'seeweb' in key.lower():
                        seeweb_config[key] = value
                        
                if seeweb_config:
                    print("Seeweb-related configuration:")
                    for key, value in seeweb_config.items():
                        print(f"  {key}: {value}")
                else:
                    print("No Seeweb-specific configuration found")
            else:
                print("No configuration loaded")
        except AttributeError:
            print("get_config method not found, trying alternative...")
            # Try alternative method
            try:
                config = skypilot_config._get_loaded_config()
                if config:
                    print("✓ Configuration loaded (alternative method)")
                else:
                    print("No configuration loaded")
            except Exception as e:
                print(f"Error with alternative config method: {e}")
                
    except Exception as e:
        print(f"Error checking configuration: {e}")

def main():
    """Run all checks."""
    print("SEEWEB SKYPILOT SETUP CHECK")
    print("=" * 50)
    
    check_seeweb_cloud()
    check_seeweb_catalog()
    check_seeweb_instance_types()
    check_seeweb_module()
    check_config()
    
    print("\n" + "=" * 50)
    print("CHECK COMPLETE")
    print("=" * 50)
    print("If you see any ✗ marks above, those indicate issues that need to be resolved.")
    print("The most common issues are:")
    print("1. Seeweb cloud not properly registered")
    print("2. Missing catalog data for Seeweb")
    print("3. Missing or incorrect cloud implementation")

if __name__ == "__main__":
    main() 
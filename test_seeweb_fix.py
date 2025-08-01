#!/usr/bin/env python3
"""
Test script to verify if the Seeweb _get_feasible_launchable_resources fix works
"""

import sys
import os

# Add the sky directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sky'))

def test_seeweb_resources():
    """Test if Seeweb can create feasible launchable resources."""
    try:
        from sky.clouds import seeweb
        from sky import resources as resources_lib
        
        print("Testing Seeweb cloud creation...")
        cloud = seeweb.Seeweb()
        print(f"✓ Seeweb cloud created: {cloud}")
        
        print("\nTesting resource creation with CPU/memory...")
        # Create resources with CPU and memory (like --cpus 2+ --memory 4+)
        resources = resources_lib.Resources(
            cloud=cloud,
            cpus='2+',
            memory='4+'
        )
        print(f"✓ Resources created: {resources}")
        
        print("\nTesting _get_feasible_launchable_resources...")
        # This should not raise an AssertionError anymore
        feasible_resources = cloud._get_feasible_launchable_resources(resources)
        print(f"✓ Feasible resources created: {feasible_resources}")
        
        if feasible_resources.resources_list:
            print(f"✓ Found {len(feasible_resources.resources_list)} feasible resources")
            for i, res in enumerate(feasible_resources.resources_list):
                print(f"  Resource {i+1}: {res}")
                print(f"    Instance type: {res.instance_type}")
                print(f"    Cloud: {res.cloud}")
                print(f"    Is launchable: {res.is_launchable()}")
        else:
            print("⚠ No feasible resources found")
            if feasible_resources.hint:
                print(f"  Hint: {feasible_resources.hint}")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_seeweb_resources()
    sys.exit(0 if success else 1) 
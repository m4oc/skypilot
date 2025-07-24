#!/usr/bin/env python3
"""Script di debug per l'integrazione Seeweb."""

import sys
import traceback
from pathlib import Path

# Aggiungi il path di sky al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / 'sky'))

def test_seeweb_credentials():
    """Test delle credenziali Seeweb."""
    print("=== TEST CREDENZIALI SEEWEB ===")
    try:
        from sky.adaptors import seeweb as seeweb_adaptor
        success, error = seeweb_adaptor.check_compute_credentials()
        if success:
            print("✅ Credenziali Seeweb: OK")
            return True
        else:
            print(f"❌ Credenziali Seeweb: {error}")
            return False
    except Exception as e:
        print(f"❌ Errore nel test credenziali: {e}")
        traceback.print_exc()
        return False

def test_seeweb_catalog():
    """Test del catalog Seeweb."""
    print("\n=== TEST CATALOG SEEWEB ===")
    try:
        from sky.catalog import seeweb_catalog
        
        # Test regioni
        regions = seeweb_catalog.regions()
        print(f"Regioni disponibili: {len(regions)}")
        for region in regions:
            print(f"  - {region.name}")
        
        # Test istanze per regione bg-sof1
        print(f"\nTest istanze per regione bg-sof1:")
        regions_for_ecs1 = seeweb_catalog.get_region_zones_for_instance_type('eCS1', use_spot=False)
        print(f"Regioni per eCS1: {len(regions_for_ecs1)}")
        for region in regions_for_ecs1:
            print(f"  - {region.name}")
        
        # Verifica se bg-sof1 è presente
        bg_sof1_present = any(r.name == 'bg-sof1' for r in regions_for_ecs1)
        print(f"bg-sof1 presente per eCS1: {bg_sof1_present}")
        
        return len(regions_for_ecs1) > 0
        
    except Exception as e:
        print(f"❌ Errore nel test catalog: {e}")
        traceback.print_exc()
        return False

def test_seeweb_cloud():
    """Test della classe Seeweb cloud."""
    print("\n=== TEST SEEWEB CLOUD ===")
    try:
        from sky.clouds import seeweb
        
        cloud = seeweb.Seeweb()
        
        # Test regioni
        regions = cloud.regions()
        print(f"Regioni da cloud: {len(regions)}")
        
        # Test regions_with_offering
        regions_with_offering = cloud.regions_with_offering(
            instance_type='eCS1',
            accelerators=None,
            use_spot=False,
            region='bg-sof1',
            zone=None
        )
        print(f"Regioni con offering per eCS1 in bg-sof1: {len(regions_with_offering)}")
        for region in regions_with_offering:
            print(f"  - {region.name}")
        
        # Test zones_provision_loop
        print("\nTest zones_provision_loop:")
        zones_yielded = 0
        for zones in cloud.zones_provision_loop(
            region='bg-sof1',
            num_nodes=1,
            instance_type='eCS1',
            accelerators=None,
            use_spot=False
        ):
            zones_yielded += 1
            print(f"  Zone yielded: {zones}")
        
        print(f"Totale zone yielded: {zones_yielded}")
        
        return zones_yielded > 0
        
    except Exception as e:
        print(f"❌ Errore nel test cloud: {e}")
        traceback.print_exc()
        return False

def test_seeweb_api_direct():
    """Test diretto delle API Seeweb."""
    print("\n=== TEST API SEEWEB DIRETTE ===")
    try:
        from sky.adaptors import seeweb as seeweb_adaptor
        
        client = seeweb_adaptor.client()
        
        # Test fetch_servers
        print("Fetching servers...")
        servers = client.fetch_servers()
        print(f"Servers trovati: {len(servers)}")
        
        # Test fetch_plans
        print("Fetching plans...")
        plans = client.fetch_plans()
        print(f"Plans trovati: {len(plans)}")
        for i, plan in enumerate(plans[:3]):  # Solo i primi 3
            print(f"  Plan {i+1}: {getattr(plan, 'name', 'unknown')} - CPU: {getattr(plan, 'cpu', 'unknown')} - RAM: {getattr(plan, 'ram', 'unknown')}")
        
        # Test fetch_regions
        print("Fetching regions...")
        regions = client.fetch_regions()
        print(f"Regions trovate: {len(regions)}")
        for i, region in enumerate(regions):
            print(f"  Region {i+1}: {getattr(region, 'location', getattr(region, 'name', str(region)))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test API dirette: {e}")
        traceback.print_exc()
        return False

def test_provisioner():
    """Test del provisioner Seeweb."""
    print("\n=== TEST PROVISIONER SEEWEB ===")
    try:
        from sky.provision.seeweb import instance as seeweb_instance
        
        # Test query_instances (non dovrebbe creare nulla)
        print("Test query_instances...")
        instances = seeweb_instance.query_instances(
            cluster_name_on_cloud='test-debug-cluster',
            provider_config={
                'plan': 'eCS1',
                'image': 'ubuntu-2204',
                'location': 'bg-sof1',
                'auth': {'remote_key_name': 'test'}
            },
            non_terminated_only=True
        )
        print(f"Instances trovate: {len(instances)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test provisioner: {e}")
        traceback.print_exc()
        return False

def main():
    """Main function per eseguire tutti i test."""
    print("🔍 DEBUG INTEGRAZIONE SEEWEB")
    print("=" * 50)
    
    tests = [
        ("Credenziali", test_seeweb_credentials),
        ("Catalog", test_seeweb_catalog),
        ("Cloud", test_seeweb_cloud),
        ("API Dirette", test_seeweb_api_direct),
        ("Provisioner", test_provisioner),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Errore nel test {test_name}: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 RIEPILOGO RISULTATI:")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 Tutti i test sono passati!")
    else:
        print("\n⚠️  Alcuni test sono falliti. Controllare i dettagli sopra.")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main()) 
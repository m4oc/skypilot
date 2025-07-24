#!/usr/bin/env python3
"""Script di debug per il provisioning Seeweb."""

import sys
import traceback
from pathlib import Path

# Aggiungi il path di sky al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / 'sky'))

def test_seeweb_provisioning():
    """Test del provisioning Seeweb."""
    print("=== TEST PROVISIONING SEEWEB ===")
    try:
        from sky.provision.seeweb.instance import SeewebNodeProvider
        
        # Configurazione di test
        provider_config = {
            'plan': 'eCS1',
            'image': 'ubuntu-2204',
            'location': 'bg-sof1',
            'auth': {
                'remote_key_name': 'test-key'  # Questo potrebbe essere il problema
            }
        }
        
        cluster_name = 'test-debug-cluster'
        
        print(f"Creando provider con config: {provider_config}")
        provider = SeewebNodeProvider(provider_config, cluster_name)
        
        # Test query existing nodes
        print("Query existing nodes...")
        existing_nodes = provider._query_cluster_nodes()
        print(f"Nodi esistenti: {len(existing_nodes)}")
        
        # Test query instances method
        print("Test query_instances...")
        instances = provider.query_instances()
        print(f"Instances: {instances}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test provisioning: {e}")
        traceback.print_exc()
        return False

def test_seeweb_api_create_server():
    """Test diretto della creazione server via API."""
    print("\n=== TEST API CREATE SERVER ===")
    try:
        from sky.adaptors import seeweb as seeweb_adaptor
        
        client = seeweb_adaptor.client()
        
        # Prima controlliamo le chiavi SSH disponibili
        print("Fetching SSH keys...")
        try:
            ssh_keys = client.fetch_ssh_keys()  # Questo metodo potrebbe non esistere
            print(f"SSH keys disponibili: {len(ssh_keys)}")
            for i, key in enumerate(ssh_keys[:3]):
                print(f"  Key {i+1}: {getattr(key, 'name', getattr(key, 'id', str(key)))}")
        except AttributeError as e:
            print(f"Metodo fetch_ssh_keys non disponibile: {e}")
            print("Proviamo altri metodi...")
            
            # Proviamo a listare tutti i metodi disponibili sul client
            methods = [method for method in dir(client) if not method.startswith('_')]
            print(f"Metodi disponibili sul client: {methods}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test API create server: {e}")
        traceback.print_exc()
        return False

def test_ssh_key_issue():
    """Test per verificare il problema delle chiavi SSH."""
    print("\n=== TEST SSH KEY ISSUE ===")
    try:
        from sky.adaptors import seeweb as seeweb_adaptor
        
        client = seeweb_adaptor.client()
        
        # Proviamo a simulare la creazione di un server
        test_payload = {
            "plan": "eCS1",
            "image": "ubuntu-2204", 
            "location": "bg-sof1",
            "notes": "test-debug-cluster",
            "ssh_key_id": "test-key"  # Questa chiave potrebbe non esistere
        }
        
        print(f"Test payload: {test_payload}")
        print("NOTA: Non creeremo realmente il server, solo testiamo la validazione")
        
        # Invece di creare, proviamo a vedere se ci sono errori di validazione
        # Controlliamo se il metodo create_server esiste
        if hasattr(client, 'create_server'):
            print("✅ Metodo create_server disponibile")
        else:
            print("❌ Metodo create_server NON disponibile")
            
        # Controlliamo altri metodi correlati
        server_methods = [method for method in dir(client) if 'server' in method.lower()]
        print(f"Metodi server disponibili: {server_methods}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test SSH key: {e}")
        traceback.print_exc()
        return False

def main():
    """Main function per eseguire tutti i test."""
    print("🔍 DEBUG PROVISIONING SEEWEB")
    print("=" * 50)
    
    tests = [
        ("Provisioning", test_seeweb_provisioning),
        ("API Create Server", test_seeweb_api_create_server),
        ("SSH Key Issue", test_ssh_key_issue),
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
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 
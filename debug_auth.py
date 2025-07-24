#!/usr/bin/env python3
"""Script di debug per l'autenticazione Seeweb."""

import sys
import traceback
from pathlib import Path

# Aggiungi il path di sky al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / 'sky'))

def test_seeweb_client_methods():
    """Test dei metodi disponibili nel client Seeweb."""
    print("=== TEST METODI CLIENT SEEWEB ===")
    try:
        from sky.adaptors import seeweb as seeweb_adaptor
        
        client = seeweb_adaptor.client()
        
        # Lista tutti i metodi disponibili
        all_methods = [method for method in dir(client) if not method.startswith('_')]
        print(f"Metodi disponibili nel client: {all_methods}")
        
        # Controlla se esistono metodi per SSH keys
        ssh_methods = [method for method in all_methods if 'ssh' in method.lower() or 'key' in method.lower()]
        print(f"Metodi correlati a SSH/keys: {ssh_methods}")
        
        # Controlla se esiste l'attributo sshkeys
        if hasattr(client, 'sshkeys'):
            print("✅ Attributo 'sshkeys' disponibile")
            sshkeys_methods = [method for method in dir(client.sshkeys) if not method.startswith('_')]
            print(f"Metodi in client.sshkeys: {sshkeys_methods}")
        else:
            print("❌ Attributo 'sshkeys' NON disponibile")
        
        # Prova a chiamare fetch_ssh_keys se esiste
        if hasattr(client, 'fetch_ssh_keys'):
            print("Tentativo di chiamare fetch_ssh_keys...")
            ssh_keys = client.fetch_ssh_keys()
            print(f"SSH keys trovate: {len(ssh_keys)}")
            for i, key in enumerate(ssh_keys[:2]):
                print(f"  Key {i+1}: {type(key)} - {key}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test client methods: {e}")
        traceback.print_exc()
        return False

def test_seeweb_auth_function():
    """Test della funzione setup_seeweb_authentication."""
    print("\n=== TEST SETUP_SEEWEB_AUTHENTICATION ===")
    try:
        from sky import authentication
        
        # Configurazione di test
        test_config = {
            'auth': {
                'ssh_user': 'root',
                'ssh_private_key': '/path/to/key'
            },
            'provider': {
                'type': 'external',
                'module': 'sky.provision.seeweb'
            }
        }
        
        print("Tentativo di chiamare setup_seeweb_authentication...")
        result_config = authentication.setup_seeweb_authentication(test_config)
        print(f"✅ Configurazione risultante: {result_config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nel test auth function: {e}")
        traceback.print_exc()
        return False

def main():
    """Main function per eseguire tutti i test."""
    print("🔍 DEBUG AUTENTICAZIONE SEEWEB")
    print("=" * 50)
    
    tests = [
        ("Client Methods", test_seeweb_client_methods),
        ("Auth Function", test_seeweb_auth_function),
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
#!/usr/bin/env python3
"""Script per debuggare la struttura del server Seeweb e trovare l'IP."""

import sys
sys.path.insert(0, 'sky')

from sky.adaptors import seeweb as seeweb_adaptor

def main():
    print("=== DEBUG STRUTTURA SERVER SEEWEB ===")
    
    try:
        client = seeweb_adaptor.client()
        servers = client.fetch_servers()
        
        print(f"Numero di server: {len(servers)}")
        
        for i, server in enumerate(servers[:3]):  # Solo primi 3 server
            print(f"\n--- SERVER {i+1} ---")
            print(f"Tipo: {type(server)}")
            print(f"Nome: {getattr(server, 'name', 'N/A')}")
            print(f"Status: {getattr(server, 'status', 'N/A')}")
            print(f"Notes: {getattr(server, 'notes', 'N/A')}")
            
            # Proviamo vari attributi per l'IP
            ip_attrs = ['ip', 'public_ip', 'external_ip', 'ipv4', 'address', 'ip_address']
            for attr in ip_attrs:
                if hasattr(server, attr):
                    value = getattr(server, attr)
                    print(f"{attr}: {value}")
            
            # Stampiamo tutti gli attributi disponibili
            print("Tutti gli attributi:")
            for attr in dir(server):
                if not attr.startswith('_'):
                    try:
                        value = getattr(server, attr)
                        print(f"  {attr}: {value}")
                    except:
                        print(f"  {attr}: <error>")
        
    except Exception as e:
        print(f"Errore: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 
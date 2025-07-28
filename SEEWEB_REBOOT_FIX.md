# Fix per i Reboot di Seeweb

## Problema

I server Seeweb possono riavviarsi durante il processo di provisioning di SkyPilot, causando errori di connessione SSH e fallimenti nell'avvio di Ray. L'errore tipico è:

```
ssh: connect to host 217.168.232.223 port 22: Connection refused
```

## Soluzione Implementata

### 1. Template YAML (`sky/templates/seeweb-ray.yml.j2`)

#### Setup Commands Robusti
- **Funzione `wait_for_system_stable()`**: Verifica che il sistema sia stabile dopo eventuali reboot
- **Retry Logic**: Tentativi multipli per fermare/disabilitare `unattended-upgrades`
- **Sleep Strategici**: Attese di 30, 15, 20 secondi tra le fasi di installazione
- **Verifica Finale**: Controllo che conda e ray siano installati correttamente

#### Comandi di Avvio Ray Robusti
- **Retry Logic**: Fino a 10 tentativi per avviare Ray
- **Verifica Sistema**: Controllo che il sistema sia stabile prima di ogni tentativo
- **Verifica Rete**: Ping per assicurarsi che la rete sia disponibile
- **Logging Dettagliato**: Messaggi informativi per debugging

#### Configurazione SSH Migliorata
- **Timeout Aumentati**: `ConnectTimeout 60`, `ServerAliveInterval 60`
- **Keep-Alive**: `TCPKeepAlive yes` per mantenere connessioni attive
- **Retry SSH**: `ServerAliveCountMax 10` per più tentativi

### 2. Provider Seeweb (`sky/provision/seeweb/instance.py`)

#### Timeout Aumentati
- `_POLL_INTERVAL`: da 5 a 10 secondi
- `_MAX_BOOT_TIME`: da 600 a 900 secondi
- `_MAX_RETRY`: 5 tentativi per operazioni critiche
- `_RETRY_DELAY`: 30 secondi tra i retry

#### Retry Logic Robusta
- **Gestione Errori Consecutivi**: Reset dopo 3 errori consecutivi
- **Logging Migliorato**: Messaggi dettagliati per debugging
- **Timeout Intelligente**: Attesa più lunga dopo errori multipli

## Come Testare

### 1. Test Base
```bash
# Crea un cluster di test
sky launch --cloud seeweb --region it-mi2 --instance-type eCS4 test-cluster

# Verifica lo stato
sky status test-cluster

# Esegui un job di test
sky exec test-cluster "echo 'Hello from Seeweb!'"
```

### 2. Test di Stress
```bash
# Crea un cluster multi-nodo
sky launch --cloud seeweb --region it-mi2 --instance-type eCS4 --num-nodes 3 stress-test

# Esegui job paralleli
sky exec stress-test "sleep 60 && echo 'Job 1 completed'"
sky exec stress-test "sleep 30 && echo 'Job 2 completed'"
sky exec stress-test "sleep 45 && echo 'Job 3 completed'"
```

### 3. Monitoraggio Log
```bash
# Controlla i log di provisioning
sky api logs -l sky-YYYY-MM-DD-HH-MM-SS-XXXXXX/provision.log

# Cerca messaggi specifici
grep "Sistema stabile" provision.log
grep "Tentativo.*avvio Ray" provision.log
grep "Ray avviato con successo" provision.log
```

## Indicatori di Successo

1. **Setup Commands**: Messaggi "Setup completato con successo"
2. **Ray Avvio**: "Ray avviato con successo!" nei log
3. **Stato Cluster**: `sky status` mostra `UP` per tutti i nodi
4. **Job Execution**: I job si completano senza errori SSH

## Troubleshooting

### Se il problema persiste:

1. **Aumenta i timeout**:
   ```python
   _MAX_BOOT_TIME = 1200  # 20 minuti
   _RETRY_DELAY = 60      # 1 minuto
   ```

2. **Verifica la configurazione Seeweb**:
   ```bash
   # Controlla le chiavi API
   cat ~/.seeweb_cloud/seeweb_keys
   
   # Testa la connessione API
   python -c "from ecsapi import Api; print('API OK')"
   ```

3. **Log dettagliati**:
   ```bash
   # Abilita debug logging
   export SKY_LOG_LEVEL=DEBUG
   sky launch --cloud seeweb ...
   ```

## Note Tecniche

- I reboot di Seeweb sono normali durante l'installazione di pacchetti
- La soluzione è progettata per essere non-intrusiva e retrocompatibile
- I timeout sono calibrati per l'infrastruttura Seeweb
- Il retry logic previene fallimenti temporanei senza impattare le performance

## Contributi

Questa soluzione è basata su:
- Analisi dei log di errore
- Pattern di retry da altri provider cloud
- Best practices per gestione reboot in ambienti cloud
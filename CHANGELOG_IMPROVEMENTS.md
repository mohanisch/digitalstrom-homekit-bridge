# Changelog - Verbesserungen

## Threading Modernisierung ✅

### Geänderte Dateien:
- `dsbridge/__main__.py`
- `dsbridge/homekit/__init__.py`
- `dsbridge/digitalstrom/websocket/__init__.py`

### Änderungen:
1. **Ersetzt `_thread` durch `threading` Modul**
   - Verwendung von `threading.Thread` statt `_thread.start_new_thread`
   - Threads als Daemon-Threads markiert für automatisches Cleanup
   - Thread-Referenzen gespeichert für besseres Management

2. **Graceful Shutdown**
   - Signal Handler für SIGINT und SIGTERM hinzugefügt
   - `_shutdown_event` für koordiniertes Shutdown
   - Proper Exception Handling in Threads

3. **WebSocket Reconnect-Logik**
   - Automatisches Reconnect mit Exponential Backoff
   - Konfigurierbare Reconnect-Delays (1s bis 60s)
   - Besseres Error Handling und Logging

## Request Handler Verbesserungen ✅

### Geänderte Dateien:
- `dsbridge/digitalstrom/request_handler.py`
- `dsbridge/digitalstrom/helper.py`

### Änderungen:
1. **Connection Pooling**
   - Verwendung von `HTTPAdapter` mit Connection Pool
   - Pool-Größe: 10 Connections, max 20
   - Wiederverwendung von TCP-Verbindungen

2. **Retry-Logik**
   - Automatische Retries für fehlgeschlagene Requests
   - Exponential Backoff (0.5s, 1s, 2s)
   - Retry für Server-Fehler (5xx) und Rate Limiting (429)
   - Decorator `@retry_on_failure` für einfache Wiederverwendung

3. **SSL-Verifikation konfigurierbar**
   - Standard: SSL-Verifikation aktiviert
   - Konfigurierbar über Umgebungsvariable `DSS_VERIFY_SSL`
   - Warnung im Log wenn SSL deaktiviert ist

4. **Besseres Error Handling**
   - Proper Exception Handling für alle Request-Typen
   - Detailliertes Logging von Fehlern
   - HTTP-Status-Codes werden geloggt
   - Response-Bodies werden bei Fehlern geloggt (erste 200 Zeichen)

## Error Handling und Retry-Logik ✅

### Geänderte Dateien:
- `dsbridge/digitalstrom/device_collector.py`
- `dsbridge/digitalstrom/eventpatcher.py`
- `dsbridge/digitalstrom/websocket/__init__.py`

### Änderungen:
1. **Device Collector**
   - Try-Except Blöcke um alle API-Calls
   - Fallback-Werte bei Fehlern
   - Validierung von API-Responses
   - Detailliertes Logging

2. **Event Patcher**
   - Error Handling für alle Patch-Operationen
   - Logging von Fehlern ohne Thread-Abbruch
   - Validierung von Konfiguration beim Initialisieren

3. **WebSocket**
   - Exception Handling für alle Callbacks
   - JSON-Decode-Fehler werden abgefangen
   - Graceful Handling von Verbindungsfehlern
   - Reconnect-Logik mit Backoff

## Technische Details

### Neue Abhängigkeiten:
- Keine neuen Abhängigkeiten erforderlich
- `urllib3` wird bereits von `requests` mitgebracht

### Umgebungsvariablen:
- `DSS_VERIFY_SSL`: SSL-Verifikation steuern (default: 'true')
  - Mögliche Werte: 'true', '1', 'yes', 'on' → SSL aktiviert
  - Alle anderen Werte → SSL deaktiviert

### Rückwärtskompatibilität:
- ✅ Alle Änderungen sind rückwärtskompatibel
- ✅ Bestehende Konfigurationen funktionieren weiterhin
- ✅ Standard-Verhalten bleibt gleich (SSL aktiviert)

## Migration

### Keine Migration erforderlich!
Die Änderungen sind vollständig rückwärtskompatibel. Bestehende Installationen funktionieren ohne Änderungen.

### Optional: SSL-Verifikation deaktivieren
Falls selbst-signierte Zertifikate verwendet werden:
```bash
export DSS_VERIFY_SSL=false
```

## Performance-Verbesserungen

1. **Connection Pooling**: Reduziert Overhead bei wiederholten Requests
2. **Retry-Logik**: Verhindert temporäre Fehler durch automatische Wiederholung
3. **WebSocket Reconnect**: Automatische Wiederherstellung bei Verbindungsabbrüchen

## Sicherheitsverbesserungen

1. **SSL-Verifikation standardmäßig aktiviert**: Schutz vor Man-in-the-Middle Angriffen
2. **Warnung bei deaktivierter SSL**: Bewusstsein für Sicherheitsrisiken
3. **Proper Error Handling**: Verhindert Information Leakage durch Fehlermeldungen

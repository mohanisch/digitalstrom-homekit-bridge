# Performance-Optimierungen für Raspberry Pi 2

## Durchgeführte Optimierungen

### 1. Polling-Intervalle reduziert ✅
- **Vorher:** Alle Accessories pollten alle 3 Sekunden
- **Nachher:** Alle Accessories pollten alle 2 Sekunden
- **Dateien:**
  - `dsbridge/homekit/accessories/type_lights.py`
  - `dsbridge/homekit/accessories/type_switch.py`
  - `dsbridge/homekit/accessories/type_windowcover.py`
  - `dsbridge/homekit/accessories/type_valve.py`

### 2. Early Exit bei unveränderten States ✅
- **Optimierung:** Wenn keine Änderungen erkannt werden, wird die Verarbeitung früh beendet
- **Vorteil:** Spart CPU-Zyklen auf dem Raspberry Pi
- **Implementierung:**
  - Prüfung ob `recently_changed` False ist UND Werte gleich sind
  - Sofortiger Return ohne weitere Verarbeitung

### 3. Logging-Overhead reduziert ✅
- **Vorher:** Viele `logger.info()` Aufrufe für jeden Update
- **Nachher:** `logger.debug()` für häufige Updates, `logger.info()` nur für wichtige Events
- **Vorteil:** Deutlich weniger I/O-Overhead auf dem Pi
- **Geänderte Dateien:**
  - `dsbridge/homekit/accessories/type_lights.py`
  - `dsbridge/digitalstrom/websocket/__init__.py`

### 4. Retry-Delays reduziert ✅
- **Vorher:** 
  - `max_retries=3`
  - `backoff_factor=0.5` (0.5s, 1s, 2s Delays)
- **Nachher:**
  - `max_retries=2`
  - `backoff_factor=0.2` (0.2s, 0.4s Delays)
- **Vorteil:** Schnellere Fehlerbehandlung, weniger Wartezeit
- **Geänderte Dateien:**
  - `dsbridge/digitalstrom/request_handler.py`

### 5. State-Check-Optimierung ✅
- **Optimierung:** Reduziertes Zeitfenster für `recently_changed` von 10 auf 5 Sekunden
- **Vorteil:** Schnellere Erkennung von Änderungen

## Erwartete Performance-Verbesserungen

1. **Schnellere Reaktionszeit:** 
   - Polling-Intervall von 3s auf 2s reduziert
   - Retry-Delays deutlich reduziert

2. **Weniger CPU-Last:**
   - Early Exit spart Verarbeitungszeit
   - Reduziertes Logging spart I/O

3. **Weniger Netzwerk-Traffic:**
   - Weniger Retries bei Fehlern
   - Effizienteres State-Caching

## Weitere Optimierungsmöglichkeiten (optional)

### Batch-Updates
- Mehrere Accessories gleichzeitig aktualisieren statt einzeln
- Aktuell: Jedes Accessory ruft `get_device_state()` einzeln auf

### State-Caching
- Caching von States zwischen Polling-Zyklen
- Nur bei WebSocket-Events aktualisieren

### Async-Optimierungen
- Mehr asynchrone Verarbeitung
- Parallele API-Calls wo möglich

## Monitoring

Um die Performance zu überwachen:
- Logs auf `DEBUG` setzen für detaillierte Timing-Informationen
- CPU-Last des Containers überwachen
- Response-Zeiten der API-Calls messen

## Konfiguration

Die Optimierungen sind automatisch aktiv. Für noch bessere Performance auf sehr schwachen Systemen:

1. **Log-Level auf WARNING setzen:**
   ```bash
   --loglevel WARNING
   ```

2. **Polling-Intervalle weiter erhöhen** (falls nötig):
   - In den Accessory-Dateien `run_at_interval(2)` auf `run_at_interval(5)` ändern

3. **WebSocket priorisieren:**
   - WebSocket-Events sind bereits optimiert
   - Stellen sicher, dass WebSocket-Verbindung stabil ist

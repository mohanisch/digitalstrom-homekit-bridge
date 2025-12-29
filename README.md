# Digital Strom HomeKit Bridge

Mit dieser Bridge ist es möglich, seine digitalStrom-Installation in HomeKit zu integrieren. 

Allerdings muss beachtet werden, dass die Ansätze von digitalStrom und HomeKit unterschiedlich sind. 

digitalStrom basiert grundsätzlich auf Szenen, unterstützt jedoch auch die Bedienung einzelner Geräte. HomeKit ist Geräte orientiert. 

Die Bridge versucht jedoch beide Welten zusammenzuführen. Werden Geräte, z.B. eine Lampe, in HomeKit bedient, wird zwischen Szenen und nicht-Szenen unterschieden. Schaltet HomeKit eine Lampe aus (Helligkeit = 0 %) bzw. ein (Helligkeit = 100 %), wird für dieses Gerät die entsprechende Szene geschaltet. Für Zonen/Räume gilt Ähnliches. Werden über eine HomeKit-Szene alle Geräte gleichen Typs angesprochen, dann wird jeweils die Szene des Raumes für ein/aus geschaltet. Erkennbar daran, dass z.B. alle Lampen gleichzeitig aus gehen und nicht nacheinander zeitversetzt. 

## Technische Voraussetzung

Es wird empfohlen, mindestens einen Raspberry Pi 3B+ zu verwenden.

## Übersicht

Die Bridge ermöglicht die Integration Ihrer Digital Strom-Installation in Apple HomeKit. Sie unterstützt:
- **Licht-Klemmen** (dimmbar, Farbsteuerung, Farbtemperatur)
- **Schatten-Klemmen** (Jalousien/Rollos)
- **Sensoren** (Temperatur, Luftfeuchtigkeit, Helligkeit, Bewegung)
- **Benutzerdefinierte Zustände** (als Schalter, Sprinkler, etc.)
- **Philips Hue** Integration über Plan44
- **Web-Dashboard** zur Konfiguration und Steuerung

## Technische Voraussetzungen

- **Hardware**: Mindestens Raspberry Pi 3B+ oder vergleichbar
- **Betriebssystem**: Linux mit Docker-Unterstützung oder Python 3.9+
- **Netzwerk**: Zugriff auf Digital Strom-Server (Standard: Port 8080 HTTP, 8090 WebSocket)
- **HomeKit**: iOS-Gerät zum Pairing

## Installation

### Docker Compose (Empfohlen)

1. **Repository klonen oder Dateien kopieren**
   ```bash
   git clone <repository-url>
   cd Digital Strom-homekit-bridge
   ```

2. **Docker Compose starten**
   ```bash
   docker-compose up -d
   ```

3. **Logs anzeigen**
   ```bash
   docker-compose logs -f
   ```

4. **Container stoppen**
   ```bash
   docker-compose down
   ```

Die Konfiguration wird in `./data` gespeichert (relativ zum Repository-Verzeichnis).

### Docker (Manuell)

```bash
docker run -d \
    --name=dsbridge \
    --network=host \
    --volume dsbridge-data:/data \
    marcohanisch/Digital Strom-homekit-bridge:latest
```

### Python Installation

```bash
pip install dsbridge
dsbridge --dss-hostname 10.11.12.200 \
  --persist-file-path /opt/dsbridge/data \
  --config-path /opt/dsbridge/conf
```

## Konfiguration

### Erste Einrichtung

1. **Dashboard öffnen**: `http://<bridge-ip>:8081`
2. **Onboarding starten**:
   - Digital Strom-Server-Adresse eingeben
   - Token generieren (falls nötig)
   - Geräte auswählen, die in HomeKit erscheinen sollen
3. **HomeKit Pairing**:
   - QR-Code scannen oder Code eingeben
   - Bridge in Home-App hinzufügen

### Umgebungsvariablen

- `DSS_HOSTNAME`: Hostname/IP des Digital Strom-Servers
- `DSS_VERIFY_SSL`: SSL-Zertifikat-Verifizierung (Standard: `true`, setze `false` für selbstsignierte Zertifikate)
- `PERSIST_FILE_PATH`: Pfad für persistente Daten (Standard: `/data`)
- `CONFIG_PATH`: Pfad für Konfigurationsdateien
- `HOMEKIT_PORT`: Port für HomeKit (Standard: 51826)

### Konfigurationsdatei (config.yml)

Die Konfiguration wird automatisch im Dashboard erstellt. Manuelle Bearbeitung ist möglich:

```yaml
entities:
  - application: lights
    dsuid: <device-id>
    entity_id: <entity-id>
    name: <Gerätename>
    zone: <Zonenname>
    service: lights
    support:
      brightness: true
      color: true
      colortemp: true
```

## Getestete Geräte

### Digital Strom Klemmen

#### Licht-Klemmen
- **GE-TKM210** - Dimmbare Klemme (getestet)
- **GE-SDM200** - Dimmbare Klemme (getestet)
- **GE-KM200** - Dimmbare Klemme (getestet)
- **GE-SDS200-CW** - Dimmbare Klemme mit Farbtemperatur (getestet)
- **GE-KL200** - Ein/Aus Klemme (getestet)

#### Schatten-Klemmen
- **GR-KL200** - Positionsgesteuerte Jalousie (getestet)

### Philips Hue / Plan44 Integration

- **Philips Hue White and Color** (LCA001) - RGB + Farbtemperatur (getestet)
- **Philips Hue White Ambiance** - Farbtemperatur (getestet)
- **Livarno Lux LED Strip** (HG06104A) - RGB + Farbtemperatur (getestet)
- **IKEA TRADFRI**
  - TRADFRI transformer 10W
  - TRADFRI transformer 30W
  - TRADFRI control outlet
  - Tradfiri bulb E27 WS opal 1000lm
  - TRADFRI bulb E27 CWS opal 600lm colour
- **Scripted Devices über Plan44**
  - Shelly Plus 1  - Joker Klemme 

### Sensoren

- **Temperatur** - Raumtemperatur-Sensoren (getestet)
- **Luftfeuchtigkeit** - Feuchtigkeitssensoren (getestet)
- **Helligkeit** - Helligkeitssensoren (getestet)
- **Bewegung** - Bewegungsmelder (getestet)

### Benutzerdefinierte Zustände

- **Schalter** - Ein/Aus-Schalter (getestet)
- **Abwesend** - Abwesenheitsstatus (getestet)

## Features

### Web-Dashboard

- **Geräteübersicht**: Alle konfigurierten Geräte nach Zonen gruppiert
- **Echtzeit-Updates**: Automatische Aktualisierung via Server-Sent Events (SSE)
- **Gerätesteuerung**: 
  - Ein/Aus schalten
  - Dimmen (0-100%)
  - Farbsteuerung (RGB)
  - Farbtemperatur
  - Jalousien-Position
- **Konfiguration**: 
  - Geräte auswählen
  - Zonen sortieren
  - Bridge neu starten

### HomeKit Integration

- **Szenen**: Automatische Umwandlung von HomeKit-Szenen in Digital Strom-Szenen
- **Gerätesteuerung**: Direkte Steuerung einzelner Geräte
- **Sensoren**: Automatische Übernahme von Raum-Sensoren

# Digital Strom HomeKit Bridge

This bridge enables integration of your digitalStrom installation into HomeKit.

However, it should be noted that the approaches of digitalStrom and HomeKit differ.

digitalStrom is fundamentally based on scenes, but also supports controlling individual devices. HomeKit is device-oriented.

The bridge attempts to bring both worlds together. When devices, such as a lamp, are controlled in HomeKit, a distinction is made between scenes and non-scenes. When HomeKit turns a lamp off (brightness = 0%) or on (brightness = 100%), the corresponding scene is activated for this device. Similar applies to zones/rooms. When all devices of the same type are addressed via a HomeKit scene, the room's scene is switched on/off. This is recognizable by the fact that, for example, all lamps turn off simultaneously and not sequentially with a time delay.

## Quick Start / Onboarding

This section guides you through the initial setup of the Digital Strom HomeKit Bridge.

### Step 1: Install and Start the Bridge

Choose your preferred installation method (see [Installation](#installation) section for details):

**Docker Compose (Recommended):**
```bash
docker-compose up -d
```

**Docker:**
```bash
docker run -d \
    --name=dsbridge \
    --network=host \
    --volume ./config:/config \
    --environment DSS_HOSTNAME=<digitalstrom-server-ip> \
    --environment DSS_VERIFY_SSL=false \
    --environment CONFIG_PATH=/config \
    --environment PERSIST_FILE_PATH=/config \
    ghcr.io/mohanisch/digitalstrom-homekit-bridge:latest
```

### Step 2: Access the Web Dashboard

1. Open your web browser and navigate to: `http://<bridge-ip>:8081`
   - Replace `<bridge-ip>` with the IP address of the device running the bridge
   - If running locally, use `http://localhost:8081`

2. You should see the bridge's web dashboard

### Step 3: Connect to Digital Strom Server

1. In the dashboard, start the onboarding process
2. Enter your **Digital Strom admin password**
4. Click **Connect** to establish the connection

### Step 4: Select Devices

1. After connecting, the bridge will discover all available devices from your Digital Strom installation
2. Browse through the list of devices organized by zones/rooms
3. **Select the devices** you want to appear in HomeKit:
   - Light clamps (dimmable, color, color temperature)
   - Shade clamps (blinds/shutters)
   - Sensors (temperature, humidity, brightness, motion)
   - Custom states (switches, etc.)
4. You can configure device names and organize them by zones
5. Click **Save Configuration**

### Step 5: Pair with HomeKit

1. After saving the configuration, the bridge will display a **HomeKit pairing code** and **QR code**
   - If not displayed, navigate to the **HomeKit Pairing** section through the dashboard menu or use `http://<bridge-ip>:8081/onboarding/pairing`
2. On your iOS device:
   - Open the **Home app**
   - Tap **Add Accessory** or the **+** button
   - Scan the **QR code** displayed in the dashboard, or
   - Tap **"Don't have a code or can't scan?"** and enter the 8-digit pairing code manually
3. Follow the prompts in the Home app to complete the pairing
4. The bridge and all selected devices will now appear in your Home app

### Step 6: Verify Setup

1. Check that all selected devices appear in the Home app
2. Test device control:
   - Turn lights on/off
   - Adjust brightness
   - Control colors (if supported)
   - Test shade/blind control
3. Verify sensor data is updating in HomeKit
4. Test HomeKit scenes with your Digital Strom devices

### Troubleshooting

- **Can't access dashboard**: Check firewall settings and ensure port 8081 is accessible
- **Connection to Digital Strom fails**: Verify server address and network connectivity
- **HomeKit pairing fails**: Ensure your iOS device and bridge are on the same network
- **Devices not appearing**: Check device selection in the dashboard and restart the bridge if needed

For more detailed configuration options, see the [Configuration](#configuration) section.

## Technical Requirements

It is recommended to use at least a Raspberry Pi 3B+.

## Overview

The bridge enables integration of your Digital Strom installation into Apple HomeKit. It supports:
- **Light Clamps** (dimmable, color control, color temperature)
- **Shade Clamps** (blinds/shutters)
- **Sensors** (temperature, humidity, brightness, motion)
- **Custom States** (as switches, sprinklers, etc.)
- **Philips Hue** integration via Plan44
- **Web Dashboard** for configuration and control

## Technical Requirements

- **Hardware**: At least Raspberry Pi 3B+ or equivalent
- **Operating System**: Linux with Docker support or Python 3.9+
- **Network**: Access to Digital Strom server (default: port 8080 HTTP, 8090 WebSocket)
- **HomeKit**: iOS device for pairing

## Installation

### Docker Compose (Recommended)

1. **Clone repository or copy files**
   ```bash
   git clone <repository-url>
   cd Digital Strom-homekit-bridge
   ```

2. **Start Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **View logs**
   ```bash
   docker-compose logs -f
   ```

4. **Stop container**
   ```bash
   docker-compose down
   ```

Configuration is saved in `./config/config.yml` (host folder `./config` mounted to `/config` in the container).

### Docker (Manual)

```bash
docker run -d \
    --name=dsbridge \
    --network=host \
    --volume dsbridge-data:/data \
    ghcr.io/mohanisch/digitalstrom-homekit-bridge:latest
```

### Python Installation

```bash
pip install dsbridge
dsbridge --dss-hostname 10.11.12.200 \
  --persist-file-path /opt/dsbridge/data \
  --config-path /opt/dsbridge/conf
```

## Configuration

### Initial Setup

1. **Open Dashboard**: `http://<bridge-ip>:8081`
2. **Start Onboarding**:
   - Enter Digital Strom server address
   - Generate token (if necessary)
   - Select devices that should appear in HomeKit
3. **HomeKit Pairing**:
   - Scan QR code or enter code
   - Add bridge to Home app

### Environment Variables

- `DSS_HOSTNAME`: Hostname/IP of the Digital Strom server
- `DSS_VERIFY_SSL`: SSL certificate verification (default: `true`, set `false` for self-signed certificates)
- `PERSIST_FILE_PATH`: Path for HomeKit pairing state (default: `/tmp`, use `/config` in Docker)
- `CONFIG_PATH`: Config directory or file (default from `--config-path`, typically `/config`)
- `HOMEKIT_PORT`: Port for HomeKit (default: 51826)

### Configuration File (config.yml)

Configuration is automatically created in the dashboard. Manual editing is possible:

```yaml
entities:
  - application: lights
    dsuid: <device-id>
    entity_id: <entity-id>
    name: <Device Name>
    zone: <Zone Name>
    service: lights
    support:
      brightness: true
      color: true
      colortemp: true
```

## Tested Devices

### Digital Strom Clamps

#### Light Clamps
- **GE-TKM210** - Dimmable clamp (tested)
- **GE-SDM200** - Dimmable clamp (tested)
- **GE-KM200** - Dimmable clamp (tested)
- **GE-SDS200-CW** - Dimmable clamp with color temperature (tested)
- **GE-KL200** - On/Off clamp (tested)

#### Shade Clamps
- **GR-KL200** - Position-controlled blind (tested)

### Philips Hue / Plan44 Integration

- **Philips Hue White and Color** (LCA001) - RGB + color temperature (tested)
- **Philips Hue White Ambiance** - Color temperature (tested)
- **Livarno Lux LED Strip** (HG06104A) - RGB + color temperature (tested)
- **IKEA TRADFRI**
  - TRADFRI transformer 10W
  - TRADFRI transformer 30W
  - TRADFRI control outlet
  - Tradfiri bulb E27 WS opal 1000lm
  - TRADFRI bulb E27 CWS opal 600lm colour
- **Scripted Devices via Plan44**
  - Shelly Plus 1  - Joker Clamp

### Sensors

- **Temperature** - Room temperature sensors (tested)
- **Humidity** - Humidity sensors (tested)
- **Brightness** - Brightness sensors (tested)
- **Motion** - Motion detectors (tested)

### Custom States

- **Switch** - On/Off switch (tested)
- **Away** - Away status (tested)

## Features

### Web Dashboard

- **Device Overview**: All configured devices grouped by zones
- **Real-time Updates**: Automatic updates via Server-Sent Events (SSE)
- **Device Control**: 
  - Turn on/off
  - Dimming (0-100%)
  - Color control (RGB)
  - Color temperature
  - Blind position
- **Configuration**: 
  - Select devices
  - Sort zones
  - Restart bridge

### HomeKit Integration

- **Scenes**: Automatic conversion of HomeKit scenes to Digital Strom scenes
- **Device Control**: Direct control of individual devices
- **Sensors**: Automatic adoption of room sensors

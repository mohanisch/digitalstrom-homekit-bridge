"""
Dashboard
"""

import json
import logging
import os
import queue
import threading
import time
from io import BytesIO

import base36
import prometheus_client
import psutil
from flask import Flask, render_template, redirect, request, Response
from pyqrcode import QRCode
from waitress import serve

from dsbridge import config
from dsbridge.digitalstrom import state_collector, device_collector
from dsbridge.digitalstrom.helper import create_application_token
from dsbridge.helper import read_config, write_config
from dsbridge.homekit import homekit
from dsbridge.homekit import start_homekit, stop_homekit
from dsbridge.metrics import REQUESTS, SYSTEM_USAGE

logger = logging.getLogger(__name__)

# Mapping of application names to Bootstrap Icons
ICON_MAPPING = {
    # Lights
    'lights': 'lightbulb',
    'light': 'lightbulb',

    # Shades/Blinds (window covering, not macOS window)
    'shades': 'layers',
    'shade': 'layers',
    'windowcovering': 'layers',
    'window': 'layers',

    # Sensors
    'temperature': 'thermometer-half',
    'humidity': 'droplet',
    'brightness': 'sun',
    'motion': 'person-walking',
    'motiondetector': 'person-walking',

    # Switches
    'switch': 'power',
    'button': 'circle',
    'joker': 'toggle-on',
    'manualstate': 'sliders',
    'absent': 'door-closed',
    'absentstate': 'door-closed',

    # Audio
    'audio': 'speaker',
    'speaker': 'speaker',
    'sprinkler': 'droplet-fill',

    # Other
    'sensor': 'sensors',
    'plug': 'plug',
    'socket': 'outlet',
    'thermostat': 'thermometer',
    'heater': 'fire',
    'ventilation': 'wind',
    'air': 'snow',
    'conditioning': 'snow',
    'garage': 'garage',
    'door': 'door-open',
    'lock': 'lock',
    'camera': 'camera',
    'tv': 'tv',
    'router': 'router',
    'washer': 'washer',
    'pool': 'water',
    'solar': 'sun',
    'weather': 'cloud-sun',
    'pet': 'heart',
    'alarm': 'bell',
    'doorbell': 'bell-fill',
    'key': 'key',
    'smartphone': 'phone',
    'remote': 'remote',
    'vacuum': 'robot',
    'recycling': 'recycle',
    'houseplant': 'flower1',
    'power': 'lightning',
    'cold': 'snowflake',
    'eye': 'eye',
    'electric': 'stove',
    'range': 'stove',
}

DEFAULT_ICON = 'circle'


def get_bootstrap_icon(application: str, is_active: bool = True) -> str:
    """
    Get Bootstrap Icon name for given application with state-aware icons.
    
    Args:
        application: Application name (e.g., 'lights', 'temperature', 'manualState')
        is_active: Whether the device is active/on (default: True)
        
    Returns:
        Bootstrap Icon name (e.g., 'lightbulb' or 'lightbulb-off')
    """
    if not application:
        return DEFAULT_ICON

    # Normalize application name (lowercase, remove spaces, handle camelCase)
    app_normalized = application.lower().strip().replace(' ', '').replace('-', '')

    # Get base icon
    base_icon = None

    # Direct match
    if app_normalized in ICON_MAPPING:
        base_icon = ICON_MAPPING[app_normalized]
    else:
        # Try camelCase variants (e.g., "manualState" -> "manualstate")
        app_variants = [
            app_normalized,
            application.lower().strip(),
            application.lower().strip().replace(' ', ''),
        ]

        for variant in app_variants:
            if variant in ICON_MAPPING:
                base_icon = ICON_MAPPING[variant]
                break

        # Partial match (e.g., "air conditioning indoor" -> "air")
        if not base_icon:
            for key, icon in ICON_MAPPING.items():
                if key in app_normalized or app_normalized.startswith(key) or key.startswith(app_normalized):
                    base_icon = icon
                    break

    if not base_icon:
        base_icon = DEFAULT_ICON

    # Return state-aware icon based on device state
    # For absent: active=True means absent (door-open), active=False means present (door-closed)
    if base_icon == 'door-closed':
        # Special handling for absent: active = absent (door-open), inactive = present (door-closed)
        return 'door-open' if is_active else 'door-closed'

    # For other icons, return off variant when inactive
    if not is_active:
        # Icons that have -off variants
        off_variants = {
            'lightbulb': 'lightbulb-off',
            'power': 'power',
            'toggle-on': 'toggle-off',
            'layers': 'layers',  # Shades stay the same
            'speaker': 'speaker',
            'tv': 'tv',
            'camera': 'camera-off',
            'lock': 'unlock',
            'bell-fill': 'bell',
            'bell': 'bell-slash',
        }

        if base_icon in off_variants:
            return off_variants[base_icon]

    return base_icon


http = Flask(__name__)

# Queue for broadcasting device status updates to connected clients
_status_update_queue = queue.Queue()

# Cache for device status to avoid multiple API calls
_cached_device_status = None
_cached_status_lock = threading.Lock()
_cached_status_timestamp = 0
http.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
http.config['TEMPLATES_AUTO_RELOAD'] = True
http.jinja_env.auto_reload = True


# Add custom Jinja2 filter for Bootstrap icons
# Jinja2 filters receive the value as first parameter, additional args follow
def bootstrap_icon_filter(application, is_active=True):
    """Jinja2 filter wrapper for get_bootstrap_icon.
    
    Usage in template: {{ application | bootstrap_icon(is_active) }}
    """
    return get_bootstrap_icon(application, is_active)


http.jinja_env.filters['bootstrap_icon'] = bootstrap_icon_filter


@http.route("/")
def root():
    """
    Main entrypoint
    """
    REQUESTS.inc()

    if 'token' not in config.read_config_file():
        return redirect("/onboarding/start", code=302)

    # from ..digitalstrom import state_collector
    entities = config.read_config_file()['entities']
    states = state_collector.gather_devices_status()

    res = {}
    sensors_by_zone = {}
    devices_by_zone = {}

    for item in entities:
        # Check if device is available (has state from digitalSTROM)
        is_available = item['entity_id'] in states
        item['available'] = is_available

        if is_available:
            item.update({"state": states[item['entity_id']]})

        zone = item['zone']
        # Separate sensors from devices
        if item.get('service') == 'sensor':
            sensors_by_zone.setdefault(zone, []).append(item)
        else:
            # Check if device has shadePositionOutside (shades)
            if item.get('application') == 'shades' and item['entity_id'] in states:
                shade_state = states[item['entity_id']].get('states', {})
                if 'shadePositionOutside' in shade_state:
                    # Add shade position info
                    item['shade_position'] = shade_state['shadePositionOutside'].get('value', 0)
            # Check if device supports RGB color and/or colortemp
            support = item.get('support', {})
            has_rgb_color = support.get('color', False) and (
                        support.get('hue', False) or support.get('saturation', False))
            has_colortemp = support.get('colortemp', False)

            if item.get('application') == 'lights':
                if has_rgb_color:
                    if item['entity_id'] in states:
                        color_state = states[item['entity_id']].get('states', {})
                        if 'hue' in color_state:
                            item['hue'] = color_state['hue'].get('value', 0)
                        if 'saturation' in color_state:
                            item['saturation'] = color_state['saturation'].get('value', 0)
                    item['supports_rgb_color'] = True
                else:
                    item['supports_rgb_color'] = False

                if has_colortemp:
                    if item['entity_id'] in states:
                        colortemp_state = states[item['entity_id']].get('states', {})
                        if 'colortemp' in colortemp_state:
                            # Convert mired (140-500) to percent (0-100) for display
                            colortemp_mired = colortemp_state['colortemp'].get('value', 0)
                            if isinstance(colortemp_mired, (int, float)) and 140 <= colortemp_mired <= 500:
                                item['colortemp'] = int(round((500 - colortemp_mired) / 3.6))
                            else:
                                item['colortemp'] = 0
                    item['supports_colortemp'] = True
                else:
                    item['supports_colortemp'] = False
            devices_by_zone.setdefault(zone, []).append(item)

    # Combine sensors and devices for each zone
    res = {}
    all_zones = set(sensors_by_zone.keys()) | set(devices_by_zone.keys())

    # Get zone order from config, if available
    config_data = config.read_config_file()
    zone_order = config_data.get('zone_order', [])

    # Use saved order if available, otherwise use sorted zones
    if zone_order and isinstance(zone_order, list):
        # Filter to only include zones that actually exist
        ordered_zones = [z for z in zone_order if z in all_zones]
        # Add any missing zones at the end
        missing_zones = sorted(all_zones - set(ordered_zones))
        ordered_zones = ordered_zones + missing_zones
    else:
        ordered_zones = sorted(all_zones)

    for zone in ordered_zones:
        res[zone] = {
            'sensors': sensors_by_zone.get(zone, []),
            'devices': devices_by_zone.get(zone, [])
        }

    return render_template(
        'dashboard_main.html',
        entities=res,
        single_zone=None
    )


@http.route("/zone/<zone_name>", methods=['GET'])
def zone_view(zone_name):
    """
    Display a single zone
    """
    entities = config.read_config_file()['entities']
    states = state_collector.gather_devices_status()

    res = {}
    sensors_by_zone = {}
    devices_by_zone = {}

    for item in entities:
        # Check if device is available (has state from digitalSTROM)
        is_available = item['entity_id'] in states
        item['available'] = is_available

        if is_available:
            item['state'] = states[item['entity_id']]

        zone = item['zone']

        # Only process items from the requested zone
        if zone != zone_name:
            continue

        if is_available:
            item.update({"state": states[item['entity_id']]})

        # Separate sensors from devices
        if item.get('service') == 'sensor':
            sensors_by_zone.setdefault(zone, []).append(item)
        else:
            # Check if device has shadePositionOutside (shades)
            if item.get('application') == 'shades' and item['entity_id'] in states:
                shade_state = states[item['entity_id']].get('states', {})
                if 'shadePositionOutside' in shade_state:
                    # Add shade position info
                    item['shade_position'] = shade_state['shadePositionOutside'].get('value', 0)
            # Check if device supports RGB color and/or colortemp
            support = item.get('support', {})
            has_rgb_color = support.get('color', False) and (
                        support.get('hue', False) or support.get('saturation', False))
            has_colortemp = support.get('colortemp', False)

            if item.get('application') == 'lights':
                if has_rgb_color:
                    if item['entity_id'] in states:
                        color_state = states[item['entity_id']].get('states', {})
                        if 'hue' in color_state:
                            item['hue'] = color_state['hue'].get('value', 0)
                        if 'saturation' in color_state:
                            item['saturation'] = color_state['saturation'].get('value', 0)
                    item['supports_rgb_color'] = True
                else:
                    item['supports_rgb_color'] = False

                if has_colortemp:
                    if item['entity_id'] in states:
                        colortemp_state = states[item['entity_id']].get('states', {})
                        if 'colortemp' in colortemp_state:
                            # Convert mired (140-500) to percent (0-100) for display
                            colortemp_mired = colortemp_state['colortemp'].get('value', 0)
                            if isinstance(colortemp_mired, (int, float)) and 140 <= colortemp_mired <= 500:
                                item['colortemp'] = int(round((500 - colortemp_mired) / 3.6))
                            else:
                                item['colortemp'] = 0
                    item['supports_colortemp'] = True
                else:
                    item['supports_colortemp'] = False
            devices_by_zone.setdefault(zone, []).append(item)

    # Check if zone exists
    all_zones = set(sensors_by_zone.keys()) | set(devices_by_zone.keys())
    if zone_name not in all_zones:
        return redirect('/')

    res[zone_name] = {
        'sensors': sensors_by_zone.get(zone_name, []),
        'devices': devices_by_zone.get(zone_name, [])
    }

    return render_template(
        'dashboard_main.html',
        entities=res,
        single_zone=zone_name
    )


@http.route("/metrics")
def metrics():
    """
    Responding metrics
    """
    content_type_latest = str('text/plain; version=0.0.4; charset=utf-8')

    SYSTEM_USAGE.labels('cpu_percent').set(psutil.Process(os.getpid()).cpu_percent())
    SYSTEM_USAGE.labels('memory_usage').set(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024)
    return Response(prometheus_client.generate_latest(), mimetype=content_type_latest)


@http.route("/homekit/state")
def homekit_state():
    """
    Returning true if homekit is paired
    """
    state = homekit.bridge_state()
    return str(state.paired)


@http.route("/save-devices", methods=['POST'])
def save_devices():
    """
    Saving devices
    """
    request_data = request.get_json()

    devices = request_data['devices']
    devices_subapplication = request_data['device_subapplication']

    entities = device_collector.get_entities()

    device_obj = []
    for device in devices:
        dev = ({v['entity_id']: v for v in entities}).get(device)
        if devices_subapplication.get(device):
            dev['service'] = devices_subapplication.get(device)
        # Ensure support is always a dict, not None
        if dev.get('support') is None:
            dev['support'] = {}
        device_obj.append(dev)

    zoneids = []
    for i in device_obj:
        if 'zoneid' in i:
            zoneids.append(i['zoneid'])

    zone_obj = []
    for zoneid in zoneids:
        zone_devices = device_collector.get_zone(zoneid)['devices']
        zone = {
            "id": zoneid,
            "applications": zone_devices
        }
        zone_obj.append(zone)

    write_config(config.args.config_path + '/config.yml', {'entities': device_obj, 'zones': zone_obj})
    restart_bridge()
    return {"ok": True}


@http.route("/api/requesttoken", methods=['GET', 'POST'])
def request_token():
    """
    Getting password from user input and requests a token on ds server
    """
    response = None
    if request.method == 'POST':
        # modify/update the information for <user_id>
        password = request.form.get('password')
        response = create_application_token(password)

    if response['ok']:
        data = {"token": response['token']}
        write_config(config.args.config_path + '/config.yml', data)

    return response


@http.route("/device-status/<entity_id>", methods=['GET'])
def get_device_status(entity_id):
    """
    Get current device status
    """
    try:
        states = state_collector.gather_devices_status()
        device_state = states.get(entity_id, {})

        if not device_state:
            return {"ok": False, "error": "Device not found"}, 404

        is_on = device_state.get('states', {}).get('on', False)
        return {"ok": True, "on": is_on, "state": device_state}
    except Exception as e:
        logger.error("Error getting device status: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/api/all-device-status", methods=['GET'])
def get_all_device_status():
    """
    Get current status for all devices
    """
    try:
        states = state_collector.gather_devices_status()
        entities = config.read_config_file()['entities']

        result = {}
        for entity in entities:
            entity_id = entity.get('entity_id')
            if entity_id in states:
                device_state = states[entity_id]
                is_on = device_state.get('states', {}).get('on', False)
                result[entity_id] = {
                    "on": is_on,
                    "state": device_state
                }

        return {"ok": True, "devices": result}
    except Exception as e:
        logger.error("Error getting all device status: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/api/status-updates", methods=['GET'])
def status_updates():
    """
    Server-Sent Events endpoint for real-time device status updates
    """
    logger.info("SSE endpoint called - new client connecting")

    def event_stream():
        logger.info("SSE: Starting event stream")
        while True:
            try:
                # Wait for status update (with timeout to allow checking if connection is still alive)
                try:
                    update = _status_update_queue.get(timeout=30)
                    logger.debug("SSE: Received update from queue: type=%s", update.get('type'))
                    if update.get('type') == 'status_changed':
                        # Use states from WebSocket event if available (to avoid duplicate API calls)
                        states = update.get('states')
                        if not states:
                            logger.warning("SSE: No states in update, fetching from API")
                            # Fallback: fetch if not provided in update (shouldn't happen, but safety)
                            states = state_collector.gather_devices_status()

                        entities = config.read_config_file()['entities']

                        result = {}
                        for entity in entities:
                            entity_id = entity.get('entity_id')
                            if entity_id in states:
                                device_state = states[entity_id]
                                is_on = device_state.get('states', {}).get('on', False)
                                result[entity_id] = {
                                    "on": is_on,
                                    "state": device_state
                                }

                        logger.debug("SSE: Sending update with %d devices", len(result))
                        yield f"data: {json.dumps({'ok': True, 'devices': result})}\n\n"
                except queue.Empty:
                    # Send keepalive ping
                    yield ": keepalive\n\n"
            except Exception as e:
                logger.error("Error in status update stream: %s", e, exc_info=True)
                break

    logger.debug("SSE: Returning Response object")

    return Response(event_stream(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


@http.route("/set-colortemp", methods=['POST'])
def set_colortemp():
    """
    Set light color temperature
    """
    try:
        request_data = request.get_json()
        entity_id = request_data.get('entity_id')
        colortemp_percent = int(request_data.get('colortemp', 0))

        if not entity_id:
            return {"ok": False, "error": "entity_id missing"}, 400

        if colortemp_percent < 0 or colortemp_percent > 100:
            return {"ok": False, "error": "colortemp must be between 0 and 100"}, 400

        # Convert percent (0-100) to mired (140-500)
        # 0% = warm (500 mired, ~2000K), 100% = cold (140 mired, ~7000K)
        colortemp = int(round(500 - (colortemp_percent * 3.6)))

        # Get entity from config
        entities = config.read_config_file()['entities']
        entity = next((e for e in entities if e['entity_id'] == entity_id), None)

        if not entity:
            return {"ok": False, "error": "Entity not found"}, 404

        # Check if device supports colortemp
        if not entity.get('support', {}).get('colortemp', False):
            return {"ok": False, "error": "Device does not support color temperature"}, 400

        dsuid = entity.get('dsuid', '')

        # Use patch_device_status directly (same as event_handler does for non-scene attributes)
        from dsbridge.digitalstrom import event_patcher
        if event_patcher is None:
            return {"ok": False, "error": "Event patcher not initialized"}, 500

        # Get current brightness to include in the update
        from dsbridge.digitalstrom import state_collector
        states = state_collector.gather_devices_status()
        brightness = 100  # Default brightness
        if entity_id in states:
            brightness_state = states[entity_id].get('states', {}).get('brightness')
            if brightness_state:
                brightness = brightness_state.get('value', 100)

        # Round brightness to integer (digitalSTROM API expects integer values)
        brightness = int(round(brightness))

        # Set colortemp and brightness using patch_device_status (same as HomeKit does)
        try:
            event_patcher.patch_device_status(dsuid, {'colortemp': colortemp, 'brightness': brightness})
            logger.info("Set colortemp for device %s to %d (brightness=%d)", entity_id, colortemp, brightness)
        except Exception as patch_error:
            logger.error("Error setting colortemp via patch_device_status for device %s: %s", entity_id, patch_error,
                         exc_info=True)
            return {"ok": False, "error": f"Error setting colortemp: {str(patch_error)}"}, 500

        return {"ok": True, "colortemp": colortemp}
    except Exception as e:
        logger.error("Error setting colortemp: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/set-color", methods=['POST'])
def set_color():
    """
    Set light color (hue and saturation or x/y coordinates)
    """
    try:
        request_data = request.get_json()
        entity_id = request_data.get('entity_id')
        hue = int(request_data.get('hue', 0))
        saturation = int(request_data.get('saturation', 0))

        if not entity_id:
            return {"ok": False, "error": "entity_id missing"}, 400

        if hue < 0 or hue > 360:
            return {"ok": False, "error": "hue must be between 0 and 360"}, 400

        if saturation < 0 or saturation > 100:
            return {"ok": False, "error": "saturation must be between 0 and 100"}, 400

        # Get entity from config
        entities = config.read_config_file()['entities']
        entity = next((e for e in entities if e['entity_id'] == entity_id), None)

        if not entity:
            return {"ok": False, "error": "Entity not found"}, 404

        # Check if device supports RGB color (not just colortemp)
        support = entity.get('support', {})
        has_rgb_color = support.get('color', False) and (support.get('hue', False) or support.get('saturation', False))

        if not has_rgb_color:
            return {"ok": False, "error": "Device does not support RGB color (only colortemp available)"}, 400

        dsuid = entity.get('dsuid', '')
        has_hue = support.get('hue', False)
        has_saturation = support.get('saturation', False)

        # Get current brightness to calculate XY coordinates (if needed)
        from dsbridge.digitalstrom import state_collector
        states = state_collector.gather_devices_status()
        brightness = 100  # Default brightness
        if entity_id in states:
            brightness_state = states[entity_id].get('states', {}).get('brightness')
            if brightness_state:
                brightness = brightness_state.get('value', 100)

        # Round brightness to integer (digitalSTROM API expects integer values)
        brightness = int(round(brightness))

        from dsbridge.digitalstrom import event_patcher
        if event_patcher is None:
            return {"ok": False, "error": "Event patcher not initialized"}, 500

        # Use patch_device_status directly (same as event_handler does for non-scene attributes)
        # This matches how HomeKit sets colors when there are no zone scenes

        _attributes = {}

        # Check if device supports hue directly (Philips Hue) or needs XY coordinates
        if has_hue:
            # Device supports hue directly (Philips Hue)
            if has_saturation:
                _attributes['hue'] = hue
                _attributes['saturation'] = saturation
            else:
                _attributes['hue'] = hue
            logger.info("Set color for device %s (Hue) to hue=%d, saturation=%d", entity_id, hue,
                        saturation if has_saturation else 0)
        else:
            # Device needs XY coordinates (non-Philips Hue)
            # Import HSV to XY conversion functions
            from dsbridge.homekit.accessories.type_lights import get_xy
            try:
                xy = get_xy(hue, saturation, brightness)
                _attributes['x'] = xy[0]
                _attributes['y'] = xy[1]
                logger.info("Set color for device %s (XY) to x=%.4f, y=%.4f (hue=%d, saturation=%d, brightness=%d)",
                            entity_id, xy[0], xy[1], hue, saturation, brightness)
            except Exception as xy_error:
                logger.error("Error converting HSV to XY for device %s: %s", entity_id, xy_error, exc_info=True)
                return {"ok": False, "error": f"Error converting color: {str(xy_error)}"}, 500

        # Add brightness to attributes (as integer)
        _attributes['brightness'] = brightness

        # Use patch_device_status directly (same as event_handler.py line 198)
        try:
            event_patcher.patch_device_status(dsuid, _attributes)
        except Exception as patch_error:
            logger.error("Error setting color via patch_device_status for device %s: %s", entity_id, patch_error,
                         exc_info=True)
            return {"ok": False, "error": f"Error setting color: {str(patch_error)}"}, 500

        return {"ok": True, "hue": hue, "saturation": saturation}
    except Exception as e:
        logger.error("Error setting color: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/set-shade-position", methods=['POST'])
def set_shade_position():
    """
    Set shade position (0-100)
    """
    try:
        request_data = request.get_json()
        entity_id = request_data.get('entity_id')
        position = int(request_data.get('position', 0))

        if not entity_id:
            return {"ok": False, "error": "entity_id missing"}, 400

        if position < 0 or position > 100:
            return {"ok": False, "error": "position must be between 0 and 100"}, 400

        # Get entity from config
        entities = config.read_config_file()['entities']
        entity = next((e for e in entities if e['entity_id'] == entity_id), None)

        if not entity:
            return {"ok": False, "error": "Entity not found"}, 404

        # Check if device is a shade
        if entity.get('application') != 'shades':
            return {"ok": False, "error": "Device is not a shade"}, 400

        dsuid = entity.get('dsuid', '')

        from dsbridge.digitalstrom import event_patcher
        if event_patcher is None:
            return {"ok": False, "error": "Event patcher not initialized"}, 500

        # Set shade position using patch_device_status
        event_patcher.patch_device_status(dsuid, {'shadePositionOutside': position})

        logger.info("Set shade position for device %s to %d%%", entity_id, position)

        return {"ok": True, "position": position}
    except Exception as e:
        logger.error("Error setting shade position: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/set-brightness", methods=['POST'])
def set_brightness():
    """
    Set device brightness (0-100)
    """
    try:
        request_data = request.get_json()
        entity_id = request_data.get('entity_id')
        brightness = int(request_data.get('brightness', 0))

        if not entity_id:
            return {"ok": False, "error": "entity_id missing"}, 400

        if brightness < 0 or brightness > 100:
            return {"ok": False, "error": "brightness must be between 0 and 100"}, 400

        # Get entity from config
        entities = config.read_config_file()['entities']
        entity = next((e for e in entities if e['entity_id'] == entity_id), None)

        if not entity:
            return {"ok": False, "error": "Entity not found"}, 404

        # Check if device supports brightness
        if not entity.get('support', {}).get('brightness', False):
            return {"ok": False, "error": "Device does not support brightness"}, 400

        dsuid = entity.get('dsuid', '')

        from dsbridge.digitalstrom import event_patcher
        if event_patcher is None:
            return {"ok": False, "error": "Event patcher not initialized"}, 500

        # Set brightness using patch_device_status
        event_patcher.patch_device_status(dsuid, {'brightness': brightness})

        logger.info("Set brightness for device %s (%s) to %d%%", entity_id, entity.get('application'), brightness)

        return {"ok": True, "brightness": brightness}
    except Exception as e:
        logger.error("Error setting brightness: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/toggle-device", methods=['POST'])
def toggle_device():
    """
    Toggle device state (on/off)
    """
    try:
        request_data = request.get_json()
        entity_id = request_data.get('entity_id')

        if not entity_id:
            return {"ok": False, "error": "entity_id missing"}, 400

        # Get entity from config
        entities = config.read_config_file()['entities']
        entity = next((e for e in entities if e['entity_id'] == entity_id), None)

        if not entity:
            return {"ok": False, "error": "Entity not found"}, 404

        # Get current state
        states = state_collector.gather_devices_status()
        current_state = states.get(entity_id, {}).get('states', {})
        is_on = current_state.get('on', False)

        # Determine action based on application type
        application = entity.get('application', '')
        service = entity.get('service', '')
        dsuid = entity.get('dsuid', '')

        from dsbridge.digitalstrom import event_patcher
        if event_patcher is None:
            return {"ok": False, "error": "Event patcher not initialized"}, 500

        # Handle different device types
        if application in ('absent', 'manualState'):
            # Use patch_switch
            new_state = 'inactive' if is_on else 'active'
            if application == 'absent':
                new_state = 'present' if is_on else 'absent'
            event_patcher.patch_switch(dsuid, new_state)
        elif application in ('lights', 'shades', 'joker'):
            # Use patch_device_scenario
            action = 'off' if is_on else 'on'
            event_patcher.patch_device_scenario(dsuid, action)
        else:
            return {"ok": False, "error": f"Unsupported application: {application}"}, 400

        logger.info("Toggled device %s (%s) from %s to %s", entity_id, application, is_on, not is_on)

        return {"ok": True, "new_state": not is_on}
    except Exception as e:
        logger.error("Error toggling device: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/restart-bridge", methods=['POST'])
def restart_bridge():
    """
    Restart bridge after user request
    """
    stop_homekit()
    time.sleep(2.4)
    start_homekit()

    return {"success": True}


@http.route("/config/zones", methods=['GET'])
def config_zones():
    """
    Configuration page for zone ordering
    """
    try:
        # Get all zones from entities
        entities = config.read_config_file()['entities']
        zones = set()
        for item in entities:
            if 'zone' in item:
                zones.add(item['zone'])

        # Get current zone order from config
        config_data = config.read_config_file()
        zone_order = config_data.get('zone_order', [])

        # Use saved order if available, otherwise use sorted zones
        if zone_order and isinstance(zone_order, list):
            # Filter to only include zones that actually exist
            ordered_zones = [z for z in zone_order if z in zones]
            # Add any missing zones at the end
            missing_zones = sorted(zones - set(ordered_zones))
            ordered_zones = ordered_zones + missing_zones
        else:
            ordered_zones = sorted(zones)

        return render_template(
            'config_zones.html',
            zones=ordered_zones
        )
    except Exception as e:
        logger.error("Error loading zone config: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/save-zone-order", methods=['POST'])
def save_zone_order():
    """
    Save zone order to config
    """
    try:
        request_data = request.get_json()
        zone_order = request_data.get('zone_order', [])

        if not isinstance(zone_order, list):
            return {"ok": False, "error": "zone_order must be a list"}, 400

        # Read current config
        config_path = config.args.config_path + '/config.yml'
        config_data = read_config(config_path)

        # Update zone order
        config_data['zone_order'] = zone_order

        # Write back to config
        write_config(config_path, config_data)

        logger.info("Saved zone order: %s", zone_order)

        return {"ok": True, "zone_order": zone_order}
    except Exception as e:
        logger.error("Error saving zone order: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@http.route("/onboarding/<step>", methods=['GET'])
def onboarding(step):
    """
    Handling the onboarding steps
    """
    dstoken = False
    initial_config = False
    paired = False

    if dstoken:
        step = 'devices'
    if initial_config:
        step = 'pairing'
    if paired:
        return redirect("/", code=302)

    if step == 'start':
        return render_template(
            'onboarding_main.html'
        )
    if step == 'devices':
        # Ensure apartment data is loaded before getting entities
        try:
            device_collector.load_apartment_data()
        except Exception as e:
            logger.error("Error loading apartment data: %s", e, exc_info=True)

        entities = device_collector.get_entities()
        cur_config = read_config(config.args.config_path + '/config.yml')

        # Create a lookup dict for configured entities and their service type
        configured_services = {}
        if "entities" in cur_config:
            for entity in cur_config['entities']:
                entity_id = entity.get('entity_id')
                service = entity.get('service', 'switch')  # Default to 'switch'
                configured_services[entity_id] = {
                    'configured': True,
                    'service': service,
                }

        res = {}
        for item in entities:
            # Skip entities without zone field
            if 'zone' not in item:
                logger.warning("Entity %s has no zone field, skipping", item.get('entity_id', 'unknown'))
                continue

            entity_id = item['entity_id']
            if entity_id in configured_services:
                item.update({
                    'configured': True,
                    'configured_service': configured_services[entity_id]['service']
                })
            else:
                item.update({
                    'configured': False,
                    'configured_service': None
                })
            res.setdefault(item['zone'], []).append(item)

        logger.debug("Grouped entities by zone: %s", list(res.keys()))

        return render_template(
            'onboarding_devices.html',
            entities=res
        )
    if step == 'pairing':
        bridge_state = homekit.bridge_state()
        stream = BytesIO()
        QRCode(xhm_uri(bridge_state.pincode, bridge_state.setup_id)).svg(
            stream,
            scale=5,
            xmldecl=False,
            svgns=False,
            module_color='#2c3d2d'
        )
        qrcode = stream.getvalue().decode('utf-8')

        return render_template(
            'onboarding_pairing.html',
            qrcode=qrcode,
            pincode=bridge_state.pincode.decode()
        )

    return None


def xhm_uri(pincode, setup_id):
    """
    Generates the X-HM:// uri (Setup Code URI)

    :rtype: str
    """
    payload = 0
    payload |= 0 & 0x7  # version

    payload <<= 4
    payload |= 0 & 0xF  # reserved bits

    payload <<= 8
    payload |= 2 & 0xFF  # category

    payload <<= 4
    payload |= 2 & 0xF  # flags

    payload <<= 27
    payload |= (
            int(pincode.replace(b"-", b""), 10) & 0x7FFFFFFF
    )  # pincode

    encoded_payload = base36.dumps(payload).upper()
    encoded_payload = encoded_payload.rjust(9, "0")

    return "X-HM://" + encoded_payload + setup_id


def run_server():
    """
    Starting the flask server
    """
    serve(http, host="0.0.0.0", port=8081)

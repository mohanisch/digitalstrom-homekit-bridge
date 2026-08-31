"""Per-device sensors from the dSS JSON API (temperature, humidity, brightness)."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import requests

from ..json_client import DssJsonClient
from ...config import read_config_file as c

logger = logging.getLogger(__name__)

SENSOR_TYPE_NAMES = {
    9: "temperature",
    11: "brightness",
    13: "humidity",
}

HOMEKIT_SENSOR_TYPES = {
    9: ("temperature", "Temperature"),
    11: ("brightness", "Brightness"),
    13: ("humidity", "Humidity"),
}

SENSOR_LABELS = {
    9: "Temperatur",
    11: "Helligkeit",
    13: "Luftfeuchtigkeit",
}

LIVE_SENSOR_TYPES = {9, 11, 13}

_json_client: Optional[DssJsonClient] = None
_json_client_token: Optional[str] = None
_refresh_thread_started = False
_refresh_lock = threading.Lock()


def device_sensors_enabled() -> bool:
    value = os.environ.get("DSS_DEVICE_SENSORS_ENABLED", "true").lower()
    return value in ("1", "true", "yes", "on")


def sensors_live_enabled() -> bool:
    value = os.environ.get("DSS_DEVICE_SENSORS_LIVE", "false").lower()
    return value in ("1", "true", "yes", "on")


def refresh_interval_seconds() -> int:
    try:
        return max(15, int(os.environ.get("DSS_DEVICE_SENSORS_REFRESH_SECONDS", "60")))
    except ValueError:
        return 60


def scale_sensor_value(sensor_type: int, value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        scaled = float(value)
    except (TypeError, ValueError):
        return None

    if sensor_type in (9, 13, 18) and scaled == int(scaled) and abs(scaled) > 200:
        scaled /= 100.0
    return scaled


def _get_json_client() -> DssJsonClient:
    global _json_client, _json_client_token

    config = c()
    token = config.get("token")
    if not token:
        raise ValueError("No token found in configuration")

    if _json_client is None or _json_client_token != token:
        _json_client = DssJsonClient(token)
        _json_client_token = token

    return _json_client


def _entity_id(dsuid: str, sensor_index: int) -> str:
    return "{}.sensor{}".format(dsuid, sensor_index)


def _display_name(device_name: str, sensor_type: int, sensor_count: int) -> str:
    if sensor_count == 1:
        return device_name
    label = SENSOR_LABELS.get(sensor_type, SENSOR_TYPE_NAMES.get(sensor_type, "Sensor"))
    return "{} {}".format(device_name, label)


def _iter_homekit_sensors(devices: List[Dict[str, Any]]):
    for device in devices:
        dsuid = device.get("dSUID") or device.get("id")
        if not dsuid:
            continue

        device_name = str(device.get("name") or dsuid).strip()
        zone_id = device.get("zoneID")
        supported = [
            (index, sensor)
            for index, sensor in enumerate(device.get("sensors") or [])
            if sensor.get("type") in HOMEKIT_SENSOR_TYPES
        ]

        for sensor_index, sensor in supported:
            sensor_type = sensor["type"]
            state_key, char_name = HOMEKIT_SENSOR_TYPES[sensor_type]
            yield {
                "dsuid": dsuid,
                "device_name": device_name,
                "zone_id": zone_id,
                "sensor_index": sensor_index,
                "sensor_type": sensor_type,
                "state_key": state_key,
                "char_name": char_name,
                "sensor_count": len(supported),
            }


class DeviceSensors:
    """Discover and track vdSD device sensors exposed to HomeKit."""

    def get_entities(self, get_zone: Callable[[Any], Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if not device_sensors_enabled():
            return []

        entities: List[Dict[str, Any]] = []
        try:
            client = _get_json_client()
            client.ensure_session()
            if not client.zone_names:
                client.load_zone_names()

            for item in _iter_homekit_sensors(client.get_devices()):
                zone_name = "unknown"
                if item["zone_id"] is not None:
                    zone_obj = get_zone(item["zone_id"])
                    if zone_obj:
                        zone_name = zone_obj["name"]
                    else:
                        zone_name = client.zone_names.get(int(item["zone_id"]), "unknown")

                entities.append({
                    "entity_id": _entity_id(item["dsuid"], item["sensor_index"]),
                    "dsuid": item["dsuid"],
                    "name": _display_name(
                        item["device_name"],
                        item["sensor_type"],
                        item["sensor_count"],
                    ),
                    "zoneid": item["zone_id"],
                    "zone": zone_name,
                    "chars": [item["char_name"]],
                    "support": None,
                    "application": item["state_key"],
                    "service": "sensor",
                    "sensor_index": item["sensor_index"],
                    "sensor_type": item["sensor_type"],
                    "present": True,
                })
        except Exception as err:
            logger.error("Error discovering device sensors: %s", err, exc_info=True)

        return entities

    def gather_state(self, timestamp: int) -> Dict[str, Dict[str, Any]]:
        if not device_sensors_enabled():
            return {}

        states: Dict[str, Dict[str, Any]] = {}
        try:
            client = _get_json_client()
            client.ensure_session()
            live_reads = sensors_live_enabled()

            for device in client.get_devices():
                dsuid = device.get("dSUID") or device.get("id")
                if not dsuid:
                    continue

                for sensor_index, sensor in enumerate(device.get("sensors") or []):
                    sensor_type = sensor.get("type")
                    if sensor_type not in HOMEKIT_SENSOR_TYPES:
                        continue

                    state_key, _char_name = HOMEKIT_SENSOR_TYPES[sensor_type]
                    value = sensor.get("value")

                    if live_reads and sensor_type in LIVE_SENSOR_TYPES:
                        try:
                            live = client.get_sensor_value(
                                dsuid,
                                sensor_index=sensor_index,
                                sensor_type=sensor_type,
                            )
                            if isinstance(live, dict):
                                value = live.get(
                                    "sensorValueFloat",
                                    live.get("value", value),
                                )
                        except requests.RequestException as err:
                            logger.debug(
                                "Live sensor read failed for %s[%s]: %s",
                                dsuid,
                                sensor_index,
                                err,
                            )

                    scaled = scale_sensor_value(sensor_type, value)
                    if scaled is None:
                        continue

                    entity_id = _entity_id(dsuid, sensor_index)
                    states[entity_id] = {
                        "states": {state_key: {"value": round(scaled, 2)}},
                        "last_change": timestamp,
                    }
        except requests.HTTPError as err:
            if err.response is not None and err.response.status_code in (401, 403):
                client.reset_session()
            logger.warning("Device sensor state collection failed: %s", err)
        except requests.RequestException as err:
            logger.warning("Device sensor state collection failed: %s", err)
        except Exception as err:
            logger.error("Error gathering device sensor states: %s", err, exc_info=True)

        return states


_device_sensors = DeviceSensors()


def get_entities(get_zone: Callable[[Any], Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return _device_sensors.get_entities(get_zone)


def gather_state(timestamp: int) -> Dict[str, Dict[str, Any]]:
    return _device_sensors.gather_state(timestamp)


def start_periodic_refresh(state_collector) -> None:
    """Refresh cached device sensor values between websocket events."""
    global _refresh_thread_started

    if not device_sensors_enabled():
        return

    with _refresh_lock:
        if _refresh_thread_started:
            return
        _refresh_thread_started = True

    interval = refresh_interval_seconds()

    def refresh_loop():
        while True:
            time.sleep(interval)
            try:
                states = gather_state(int(time.time()))
                if states:
                    state_collector._device_states.update(states)
            except Exception as err:
                logger.debug("Periodic device sensor refresh failed: %s", err)

    thread = threading.Thread(
        target=refresh_loop,
        daemon=True,
        name="device-sensor-refresh",
    )
    thread.start()
    logger.info("Device sensor refresh every %d seconds", interval)

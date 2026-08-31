"""Minimal client for the digitalSTROM JSON API."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from ..config import args

logger = logging.getLogger(__name__)


class DssJsonClient:
    """Synchronous JSON API client using the application login token."""

    def __init__(self, token: str, timeout: float = 15.0):
        self._base_url = "https://{}:{}/json".format(
            args.dss_hostname,
            args.dss_http_port,
        )
        self._token = token
        self._timeout = timeout
        self._session_token: Optional[str] = None
        self._zone_names: Dict[int, str] = {}

        env_verify = os.environ.get("DSS_VERIFY_SSL", "true").lower()
        self._verify_ssl = env_verify in ("true", "1", "yes", "on")

        self._session = requests.Session()

    @property
    def zone_names(self) -> Dict[int, str]:
        return self._zone_names

    def reset_session(self) -> None:
        self._session_token = None

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        query = dict(params or {})
        if self._session_token:
            query.setdefault("token", self._session_token)

        response = self._session.get(
            "{}/{}".format(self._base_url, path.lstrip("/")),
            params=query,
            timeout=self._timeout,
            verify=self._verify_ssl,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("ok") is False:
            raise requests.RequestException(
                payload.get("message", "dSS JSON API error")
            )

        return payload.get("result", payload)

    def ensure_session(self) -> None:
        if self._session_token:
            return

        result = self._request(
            "system/loginApplication",
            {"loginToken": self._token},
        )
        token = result.get("token") if isinstance(result, dict) else None
        if not token:
            raise requests.RequestException("JSON login returned no session token")
        self._session_token = token

    def load_zone_names(self) -> None:
        structure = self._request("apartment/getStructure")
        zones: Dict[int, str] = {}
        apartment = structure.get("apartment", structure) if isinstance(structure, dict) else {}

        def walk(items):
            for zone in items or []:
                zone_id = zone.get("id")
                name = str(zone.get("name") or "").strip()
                if zone_id not in (None, 0, "0", 65534, "65534") and name:
                    zones[int(zone_id)] = name
                walk(zone.get("zones"))

        if isinstance(apartment, dict):
            walk(apartment.get("zones"))
        self._zone_names = zones

    def get_devices(self) -> List[Dict[str, Any]]:
        self.ensure_session()
        result = self._request("apartment/getDevices")
        if isinstance(result, list):
            return result
        return result.get("devices", [])

    def get_sensor_value(
        self,
        dsuid: str,
        sensor_index: Optional[int] = None,
        sensor_type: Optional[int] = None,
    ) -> Any:
        params: Dict[str, Any] = {"dsuid": dsuid}
        if sensor_index is not None:
            params["sensorIndex"] = sensor_index
        if sensor_type is not None:
            params["sensorType"] = sensor_type
        return self._request("device/getSensorValue2", params)

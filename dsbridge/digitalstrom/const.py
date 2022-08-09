from dsbridge.homekit.const import *

DEVICE_SUPPORT = {
    "GE-KL200": {
        "application": "lights",
        "support": ['on']
    },
    "GE-KM200": {
        "application": "lights",
        "support": ['on']
    },
    "GE-SDM200": {
        "application": "lights",
        "support": ['on', 'brightness']
    },
    "GE-SDS200-CW": {
        "application": "lights",
        "support": ['on', 'brightness']
    },
    "GE-TKM210": {
        "application": "lights",
        "support": ['on', 'brightness']
    },
    "GE-TKM230": {
        "application": "lights",
        "support": ['on', 'brightness']
    },
    "Extended color light: LCA001": {
        "application": "lights",
        "support": ['on', 'brightness', CHAR_HUE, CHAR_SATURATION, CHAR_COLOR_TEMPERATURE]
    },
    "GR-KL200": {
        "application": "shades",
        "support": [CHAR_HOLD_POSITION, CHAR_CURRENT_POSITION, CHAR_TARGET_POSITION]
    },
}

HUE_DEVICES = [
    "Extended color light: LCA001"
]

DEVICES_CHARS = {
    "light": {
        "switched": 'On',
        "gradual": "Brightness",
        "colortemp": "Saturation",
        "hue": "Hue",
    },
    "shades": {
        "positional": ['CurrentPosition', 'TargetPosition', 'PositionState']
    }
}

SMART_HOME_API = "api/v1/apartment"
PROPERTY_API = "json/property"
SYSTEM_API = "json/system"

ENOCEAN_DEVICES = {
    "Id Rf EnOcean Motion input": ["Motion", "Brightness"]
}


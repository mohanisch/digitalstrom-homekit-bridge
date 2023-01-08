SMART_HOME_API = "/api/v1/apartment"
PROPERTY_API = "/json/property"
SYSTEM_API = "/json/system"

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

ENOCEAN_DEVICES = {
    "Id Rf EnOcean Motion input": ["Motion", "Brightness"]
}


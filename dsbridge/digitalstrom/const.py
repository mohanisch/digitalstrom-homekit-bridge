DS_DEVICES = {
    "GE-KL200": {},
    "GE-KM200": {},
    "GE-SDM200": {},
    "GE-SDS200-CW": {},
    "GE-TKM210": {},
    "GE-TKM230": {},
    "GR-KL200": {},
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

HUE_CERTIFIED = [
    "LCA001",
    "LCT014",
    "LCT015",
    "LCT016"
]

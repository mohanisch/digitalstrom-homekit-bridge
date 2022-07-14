STATE_ON = "on"
STATE_OFF = "off"
STATE_UP = "up"
STATE_DOWN = "down"

CONTROL = {
    "lights": {
        "id": "brightness",
        "device": {
            0: STATE_OFF,
            100: STATE_ON
        },
        "scene": {
            0: STATE_OFF,
            100: STATE_ON
        }
    },
    "shades": {
        "id": "shadePositionOutside",
        "device": {
            0: STATE_OFF,
            100: STATE_ON
        },
        "scene": {
            0: STATE_DOWN,
            100: STATE_UP
        }
    },
}

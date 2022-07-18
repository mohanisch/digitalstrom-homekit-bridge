STATE_ON = "on"
STATE_OFF = "off"
STATE_UP = "up"
STATE_DOWN = "down"
STATE_ACTIVE = "active"
STATE_INACTIVE = "inactive"
STATE_PRESENT = "present"
STATE_ABSENT = "absent"


CONTROL = {
    "lights": {
        "id": "brightness",
        "device_scene": {
            0: STATE_OFF,
            100: STATE_ON
        },
        "zone_scene": {
            0: STATE_OFF,
            100: STATE_ON
        }
    },
    "shades": {
        "id": "shadePositionOutside",
        "device_scene": {
            0: STATE_OFF,
            100: STATE_ON
        },
        "zone_scene": {
            0: STATE_DOWN,
            100: STATE_UP
        }
    },
    "absent": {
        "id": "active",
        "device": {
            0: STATE_PRESENT,
            1: STATE_ABSENT
        }
    },
    "manualState": {
        "id": "active",
        "device": {
            0: STATE_INACTIVE,
            1: STATE_ACTIVE
        }
    },
}

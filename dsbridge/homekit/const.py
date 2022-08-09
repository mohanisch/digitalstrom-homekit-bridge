STATE_ON = "on"
STATE_OFF = "off"
STATE_UP = "up"
STATE_DOWN = "down"
STATE_ACTIVE = "active"
STATE_INACTIVE = "inactive"
STATE_PRESENT = "present"
STATE_ABSENT = "absent"

CHAR_ON = "On"
CHAR_BRIGHTNESS = "Brightness"
CHAR_HUE = "Hue"
CHAR_SATURATION = "Saturation"
CHAR_COLOR_TEMPERATURE = "ColorTemperature"
CHAR_ACTIVE = "Active"
CHAR_NAME = "Name"
CHAR_VALVE_TYPE = "ValveType"
CHAR_INUSE = "InUse"
CHAR_REMAIN_DURATION = "RemainingDuration"
CHAR_SET_DURATION = "SetDuration"
CHAR_HOLD_POSITION = "HoldPosition"
CHAR_TARGET_POSITION = "TargetPosition"
CHAR_CURRENT_POSITION = "CurrentPosition"
CHAR_POSITION_STATE = "PositionState"
CHAR_TARGET_HORIZONTAL_TILT_ANGLE = "TargetHorizontalTiltAngle"
CHAR_CURRENT_HORIZONTAL_TILT_ANGLE = "CurrentHorizontalTiltAngle"

ATTR_BRIGHTNESS = "brightness"
ATTR_HUE = "hue"
ATTR_COLOR = "color"
ATTR_COLORTEMP = "colortemp"
ATTR_HS_COLOR = "hs_color"
ATTR_COLOR_MODE = "color_mode"
ATTR_SHADE_POSITION_OUTSIDE = "shadePositionOutside"

COLOR_MODE_WHITE = "white"

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

from typing import Final

MAJOR_VERSION: Final = 0
MINOR_VERSION: Final = 0
PATCH_VERSION: Final = "1"
__short_version__: Final = f"{MAJOR_VERSION}.{MINOR_VERSION}"
__version__: Final = f"{__short_version__}.{PATCH_VERSION}"

REQUIRED_PYTHON_VER: Final[tuple[int, int, int]] = (3, 9, 0)
RESTART_EXIT_CODE: Final = 100

BRIDGE_MODEL = "Bridge"
BRIDGE_NAME = "Home Assistant Bridge"
SHORT_BRIDGE_NAME = "HASS Bridge"
SHORT_ACCESSORY_NAME = "HASS Accessory"
BRIDGE_SERIAL_NUMBER = "dshomekit.bridge"
MANUFACTURER = "Home Assistant"

ATTR_MANUFACTURER = None
ATTR_INTEGRATION = None
ATTR_MODEL = None

CONF_NAME: Final = "name"

DOMAIN = "dsbridge"
HOMEKIT_FILE = ".homekit.state"
HOMEKIT_PAIRING_QR = "dsbridge-pairing-qr"
HOMEKIT_PAIRING_QR_SECRET = "dsbridge-pairing-qr-secret"

STATE_ON = "on"
CHAR_ON = "On"
CHAR_BRIGHTNESS = "Brightness"
CHAR_HUE = "Hue"
CHAR_SATURATION = "Saturation"
CHAR_COLOR_TEMPERATURE = "ColorTemperature"
CHAR_ACTIVE = "Active"
CHAR_NAME = "Name"

ATTR_BRIGHTNESS = "brightness"
ATTR_HUE = "hue"
ATTR_COLOR_TEMP = "color_temp"
ATTR_HS_COLOR = "hs_color"
ATTR_COLOR_MODE = "color_mode"
COLOR_MODE_WHITE = "white"

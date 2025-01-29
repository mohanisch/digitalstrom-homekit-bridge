from typing import Final

MAJOR_VERSION: Final = "2"
MINOR_VERSION: Final = "1"
PATCH_VERSION: Final = "4"
__short_version__: Final = f"{MAJOR_VERSION}.{MINOR_VERSION}"
__version__: Final = f"{__short_version__}.{PATCH_VERSION}"

REQUIRED_PYTHON_VER: Final[tuple[int, int, int]] = (3, 9, 0)
RESTART_EXIT_CODE: Final = 100

BRIDGE_NAME = "digitalStrom Homekit Bridge"
BRIDGE_SERIAL_NUMBER = __version__
MANUFACTURER = "Marco Hanisch"

STATUS_READY = 0
STATUS_RUNNING = 1
STATUS_STOPPED = 2
STATUS_WAIT = 3

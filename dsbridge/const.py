from pathlib import Path
from typing import Final


def _get_version():
    """Read version from VERSION file in project root."""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            version = f.read().strip()
            return version
    return None


__version__: Final = _get_version()
_version_parts = __version__.split(".")
MAJOR_VERSION: Final = _version_parts[0] if len(_version_parts) > 0 else "2"
MINOR_VERSION: Final = _version_parts[1] if len(_version_parts) > 1 else "3"
PATCH_VERSION: Final = _version_parts[2] if len(_version_parts) > 2 else "0"
__short_version__: Final = f"{MAJOR_VERSION}.{MINOR_VERSION}"

REQUIRED_PYTHON_VER: Final[tuple[int, int, int]] = (3, 9, 0)
RESTART_EXIT_CODE: Final = 100

BRIDGE_NAME = "Digital Strom Homekit Bridge"
BRIDGE_SERIAL_NUMBER = __version__

STATUS_READY = 0
STATUS_RUNNING = 1
STATUS_STOPPED = 2
STATUS_WAIT = 3

import _thread
import sys
import threading
import time

from .dashboard import run_server
from .const import REQUIRED_PYTHON_VER


def validate_python() -> None:
    if sys.version_info[:3] < REQUIRED_PYTHON_VER:
        print(
            f"{REQUIRED_PYTHON_VER[0]}.{REQUIRED_PYTHON_VER[1]}.{REQUIRED_PYTHON_VER[2]}"
        )
        sys.exit(1)


def check_threads() -> None:
    """Check if there are any lingering threads."""
    try:
        nthreads = sum(
            thread.is_alive() and not thread.daemon for thread in threading.enumerate()
        )
        if nthreads > 1:
            sys.stderr.write(f"Found {nthreads} non-daemonic threads.\n")

    except AssertionError:
        sys.stderr.write("Failed to count non-daemonic threads.\n")


def start_websocket():
    from .config import read_config_file
    while True:
        time.sleep(2)
        c = read_config_file()
        if 'token' in c and c['token']:
            from .digitalstrom.websocket import start_websocket
            start_websocket()
            break


def start_homekit():
    from .config import read_config_file
    while True:
        time.sleep(2)
        c = read_config_file()

        if 'entities' in c:
            from .homekit import start_homekit
            start_homekit()
            break


def main():
    validate_python()
    _thread.start_new_thread(start_websocket, ())
    _thread.start_new_thread(start_homekit, ())

    run_server()

    check_threads()


if __name__ == '__main__':
    sys.exit(main())

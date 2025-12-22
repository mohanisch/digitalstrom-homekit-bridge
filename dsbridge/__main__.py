import logging
import signal
import sys
import threading
import time

from .dashboard import run_server
from .const import REQUIRED_PYTHON_VER

logger = logging.getLogger(__name__)

# Thread references for graceful shutdown
_websocket_thread = None
_homekit_thread = None
_shutdown_event = threading.Event()


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
    """Start websocket in a separate thread."""
    from .config import read_config_file
    
    # Wait for token to be available
    while not _shutdown_event.is_set():
        try:
            c = read_config_file()
            if 'token' in c and c['token']:
                from .digitalstrom.websocket import start_websocket
                start_websocket()
                break
        except Exception as e:
            logger.error("Error starting websocket: %s", e, exc_info=True)
        
        # Wait 2 seconds before checking again (or until shutdown event)
        if _shutdown_event.wait(timeout=2):
            break


def start_homekit():
    """Start homekit in a separate thread."""
    from .config import read_config_file
    
    # Wait for entities to be configured
    while not _shutdown_event.is_set():
        try:
            c = read_config_file()
            if 'entities' in c:
                from .homekit import start_homekit
                start_homekit()
                break
        except Exception as e:
            logger.error("Error starting homekit: %s", e, exc_info=True)
        
        # Wait 2 seconds before checking again (or until shutdown event)
        if _shutdown_event.wait(timeout=2):
            break


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received signal %d, shutting down...", signum)
    _shutdown_event.set()
    
    # Stop homekit gracefully
    try:
        from .homekit import stop_homekit
        stop_homekit()
    except Exception as e:
        logger.error("Error stopping homekit: %s", e)
    
    sys.exit(0)


def main():
    global _websocket_thread, _homekit_thread
    
    validate_python()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start websocket thread
    _websocket_thread = threading.Thread(
        target=start_websocket,
        daemon=True,
        name="websocket"
    )
    _websocket_thread.start()
    
    # Start homekit thread
    _homekit_thread = threading.Thread(
        target=start_homekit,
        daemon=True,
        name="homekit"
    )
    _homekit_thread.start()

    try:
        run_server()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error("Fatal error in main: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        _shutdown_event.set()
        check_threads()


if __name__ == '__main__':
    sys.exit(main())

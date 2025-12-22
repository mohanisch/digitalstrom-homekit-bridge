import json
import logging
import threading
import time
import websocket

from dsbridge.metrics import WS_REQUESTS_CHANGE
from .. import state_collector, device_collector
from ...config import read_config_file as c, args
from ...helper import remove_control_characters

logger = logging.getLogger(__name__)

# Thread reference for websocket
_websocket_thread = None
_shutdown_event = threading.Event()


def start_websocket():
    """Start websocket connection in a separate thread."""
    global _websocket_thread
    
    config_file = c()
    if config_file.get('token'):
        dswebsocket = DsWebsocket()
        if _websocket_thread is None or not _websocket_thread.is_alive():
            _websocket_thread = threading.Thread(
                target=dswebsocket.start,
                daemon=True,
                name="websocket-runner"
            )
            _websocket_thread.start()
        else:
            logger.warning("Websocket thread is already running")
    else:
        logger.warning("No token found in config, cannot start websocket")


class DsWebsocket:
    """WebSocket client for digitalStrom notifications with automatic reconnect."""
    
    # Reconnect configuration
    INITIAL_RECONNECT_DELAY = 1  # seconds
    MAX_RECONNECT_DELAY = 60  # seconds
    RECONNECT_BACKOFF_MULTIPLIER = 2
    
    def __init__(self):
        self.host = f"ws://{args.dss_hostname}:{args.ws_port}/api/v1/apartment/notifications"
        self.ws = None
        self.running = True
        self.reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._connection_attempts = 0

    def start(self):
        """Start websocket connection with automatic reconnect."""
        logger.info("Starting websocket connection to %s", self.host)
        
        while self.running and not _shutdown_event.is_set():
            try:
                websocket.enableTrace(False)
                self.ws = websocket.WebSocketApp(
                    self.host,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                
                # This will block until connection closes
                self.ws.run_forever()
                
            except Exception as e:
                logger.error("Unexpected error in websocket: %s", e, exc_info=True)
            
            # Only reconnect if we're still running and not shutting down
            if self.running and not _shutdown_event.is_set():
                self._schedule_reconnect()
        
        logger.info("Websocket thread stopped")

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff."""
        self._connection_attempts += 1
        logger.info(
            "Websocket disconnected. Reconnecting in %d seconds (attempt %d)...",
            self.reconnect_delay,
            self._connection_attempts
        )
        
        # Wait for reconnect delay or shutdown event
        if _shutdown_event.wait(timeout=self.reconnect_delay):
            self.running = False
            return
        
        # Increase delay for next attempt (exponential backoff)
        self.reconnect_delay = min(
            self.reconnect_delay * self.RECONNECT_BACKOFF_MULTIPLIER,
            self.MAX_RECONNECT_DELAY
        )

    def on_open(self, ws):
        """Called when websocket connection is established."""
        # Reset reconnect delay on successful connection
        self.reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._connection_attempts = 0
        
        try:
            obj = {
                "protocol": "json",
                "version": 1
            }
            ws.send(json.dumps(obj))
            logger.info("Websocket connected successfully")
        except Exception as e:
            logger.error("Error sending initial websocket message: %s", e, exc_info=True)

    def on_message(self, ws, message):
        """Handle incoming websocket messages."""
        try:
            WS_REQUESTS_CHANGE.inc()
            
            cleaned_message = remove_control_characters(message)
            _message = json.loads(cleaned_message)
            
            logger.debug("Received websocket message: %s", _message.get('arguments', [{}])[0].get('type', 'unknown') if _message.get('arguments') else 'no arguments')
            
            if "arguments" in _message and len(_message['arguments']) > 0:
                event_type = _message['arguments'][0].get('type')
                
                if event_type == 'apartmentStatusChanged':
                    logger.info("Apartment status changed - updating device states")
                    try:
                        state_collector.gather_devices_status()
                        logger.debug("Device states updated successfully")
                    except Exception as e:
                        logger.error("Error gathering device status: %s", e, exc_info=True)

                elif event_type == 'apartmentStructureChanged':
                    logger.info("Apartment structure changed - reloading device data")
                    try:
                        device_collector.load_apartment_data()
                        logger.debug("Device data reloaded successfully")
                    except Exception as e:
                        logger.error("Error loading apartment data: %s", e, exc_info=True)
                else:
                    logger.debug("Unhandled event type: %s", event_type)
            else:
                logger.debug("Websocket message without arguments: %s", _message)
                        
        except json.JSONDecodeError as e:
            logger.error("Failed to parse websocket message: %s. Raw message: %s", e, message[:200])
        except Exception as e:
            logger.error("Error processing websocket message: %s", e, exc_info=True)

    def on_error(self, ws, error):
        """Handle websocket errors."""
        if isinstance(error, Exception):
            logger.error("Websocket error: %s", error, exc_info=True)
        else:
            logger.error("Websocket error: %s", error)

    def on_close(self, ws, close_status_code, close_msg):
        """Handle websocket close events."""
        if close_status_code:
            logger.info(
                "Websocket closed with code %d: %s",
                close_status_code,
                close_msg or "No message"
            )
        else:
            logger.info("Websocket closed")
        
        # If close was unexpected (not from shutdown), we'll reconnect
        if self.running and not _shutdown_event.is_set():
            logger.debug("Websocket will attempt to reconnect")

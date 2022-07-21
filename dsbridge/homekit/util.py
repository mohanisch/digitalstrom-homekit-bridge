import io
import logging
import secrets

import pyqrcode

from collections.abc import Callable, Hashable
from typing import TypeVar

CALLABLE_T = TypeVar("CALLABLE_T", bound=Callable)


class Registry(dict):
    """Registry of items."""

    def register(self, name: Hashable) -> Callable[[CALLABLE_T], CALLABLE_T]:
        """Return decorator to register item with a specific name."""

        def decorator(func: CALLABLE_T) -> CALLABLE_T:
            """Register decorated function."""
            self[name] = func
            return func

        return decorator


def async_show_setup_message(entry_id, bridge_name, pincode, uri):
    """Display persistent notification with setup information."""
    pin = pincode.decode()
    logging.info("Pincode: %s", pin)

    buffer = io.BytesIO()
    url = pyqrcode.create(uri)
    url.svg(buffer, scale=5, module_color="#000", background="#FFF")
    pairing_secret = secrets.token_hex(32)

    message = (
        f"To set up {bridge_name} in the Home App, "
        f"scan the QR code or enter the following code:\n"
        f"### {pin}\n"
        f"![image](/api/homekit/pairingqr?{entry_id}-{pairing_secret})"
    )
    return message


def async_suppress_setup_message() -> None:
    """Underline the notice and remove the QR code."""

import io
import logging
import secrets

import pyqrcode


def async_show_setup_message(hass, entry_id, bridge_name, pincode, uri):
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
    print(message)
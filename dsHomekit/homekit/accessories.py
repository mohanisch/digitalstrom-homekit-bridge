"""Extend the basic Accessory and Bridge functions."""
import logging

from dsHomekit.utils.registry import Registry

TYPES = Registry()


def get_accessory(driver, device, aid):
    """Take state and return an accessory object if supported."""
    a_type = None
    name = device['name']

    if device['service'] == "alarm_control_panel":
        a_type = "SecuritySystem"

    elif device['service'] == "shades":
        a_type = "WindowCovering"

    elif device['service'] == "lights":
        a_type = "Light"

    elif device['service'] == "sensor":
        if 'Temperature' in device['chars']:
            a_type = "TemperatureSensor"
        elif 'Humidity' in device['chars']:
            a_type = "HumiditySensor"
        elif 'Brightness' in device['chars']:
            a_type = "LightSensor"

    elif device['service'] in (
            "automation",
            "button",
            "input_boolean",
            "input_button",
            "remote",
            "scene",
            "script",
    ):
        a_type = "Switch"

    if a_type is None:
        return None

    logging.info('Add "%s (%s)" as "%s"', name, device['dsuid'], a_type)
    return TYPES[a_type](driver, name, aid, device=device)

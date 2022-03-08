"""Extend the basic Accessory and Bridge functions."""
import logging

from pyhap import util
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_OTHER
from dsHomekit.utils.registry import Registry

TYPES = Registry()


def get_accessory(driver, device, aid):
    """Take state and return an accessory object if supported."""
    a_type = None
    name = device['name']

    if device['service'] == "alarm_control_panel":
        a_type = "SecuritySystem"

    elif device['service'] == "windowcover":

        # device_class = state.attributes.get(ATTR_DEVICE_CLASS)

        # if device_class in (
        #         cover.CoverDeviceClass.GARAGE,
        #         cover.CoverDeviceClass.GATE,
        # ) and features & (cover.SUPPORT_OPEN | cover.SUPPORT_CLOSE):
        #     a_type = "GarageDoorOpener"
        # elif (
        #         device_class == cover.CoverDeviceClass.WINDOW
        #         and features & cover.SUPPORT_SET_POSITION
        # ):
        #     a_type = "Window"
        # elif features & cover.SUPPORT_SET_POSITION:
        #     a_type = "WindowCovering"
        # elif features & (cover.SUPPORT_OPEN | cover.SUPPORT_CLOSE):
        #     a_type = "WindowCoveringBasic"
        # elif features & cover.SUPPORT_SET_TILT_POSITION:
        #     # WindowCovering and WindowCoveringBasic both support tilt
        #     # only WindowCovering can handle the covers that are missing
        #     # SUPPORT_SET_POSITION, SUPPORT_OPEN, and SUPPORT_CLOSE
        #     a_type = "WindowCovering"
        a_type = "WindowCovering"

    # elif state.domain == "fan":
    #     a_type = "Fan"
    #
    elif device['service'] == "light":
        a_type = "Light"

    elif device['service'] == "sensor":
        if 'Temperature' in device['chars']:
            a_type = "TemperatureSensor"
        elif 'Humidity' in device['chars']:
            a_type = "HumiditySensor"
        elif 'Brightness' in device['chars']:
            a_type = "LightSensor"
    #
    # elif state.domain == "switch":
    #     switch_type = config.get(CONF_TYPE, TYPE_SWITCH)
    #     a_type = SWITCH_TYPES[switch_type]
    #
    # elif state.domain == "vacuum":
    #     a_type = "Vacuum"
    #
    # elif state.domain == "remote" and features & SUPPORT_ACTIVITY:
    #     a_type = "ActivityRemote"
    #
    # elif state.domain in (
    #         "automation",
    #         "button",
    #         "input_boolean",
    #         "input_button",
    #         "remote",
    #         "scene",
    #         "script",
    # ):
    #     a_type = "Switch"
    #
    # elif state.domain in ("input_select", "select"):
    #     a_type = "SelectSwitch"
    #
    # elif state.domain == "water_heater":
    #     a_type = "WaterHeater"
    #
    # elif state.domain == "camera":
    #     a_type = "Camera"

    if a_type is None:
        return None

    logging.info('Add "%s (%s)" as "%s"', name, device['dsuid'], a_type)
    return TYPES[a_type](driver, name, aid, dsuid=device['dsuid'], chars=device['chars'])


class HomeAccessory(Accessory):
    """Adapter class for Accessory."""

    category = CATEGORY_OTHER

    def __init__(self, driver, display_name, aid=None):
        super().__init__(driver, display_name, aid)



    def async_update_event_state_callback(self, event):
        """Handle state change event listener callback."""
        self.async_update_state_callback(event.data.get("new_state"))

    def async_update_state_callback(self, new_state):
        """Handle state change listener callback."""
        logging.debug("New_state: %s", new_state)
        if new_state is None:
            return
        self.async_update_state(new_state)

    #@Accessory.run_at_interval(3)
    # async def run(self):
    #     from dsHomekit.digitalstrom import collector
    #     s = collector.get_device_state()
    #     state = device_services = ({v['id']: v['states'] for v in s}).get(self.dsuid)
    #     from dsHomekit.homekit import async_track_state_change_event
    #
    #     self._subscriptions.append(
    #         async_track_state_change_event(
    #             [self.dsuid], self.async_update_event_state_callback
    #         )
    #     )

    async def stop(self):
        """Cancel any subscriptions when the bridge is stopped."""
        while self._subscriptions:
            self._subscriptions.pop(0)()
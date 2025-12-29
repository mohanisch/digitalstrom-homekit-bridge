import logging
import time

from pyhap.const import CATEGORY_LIGHTBULB

from dsbridge.helper import threaded
from . import ACC_TYPES, DsAccessory

logger = logging.getLogger(__name__)
from ..const import (
    STATE_ON,
    CHAR_ON,
    CHAR_BRIGHTNESS,
    CHAR_HUE,
    CHAR_SATURATION,
    CHAR_COLOR_TEMPERATURE,
    ATTR_BRIGHTNESS, ATTR_COLORTEMP, ATTR_COLOR
)
from .. import event_decider
from ...digitalstrom import state_collector
from rgbxy import Converter


def hsv_to_rgb(hue, saturation, value):
    """
    This function takes
     hue - 0 - 360 Deg
     s - 0 - 100 %
     v - 0 - 100 %
    """

    h_pri = hue / 60
    _saturation = saturation / 100
    _value = value / 100

    if saturation <= 0.0:
        return int(0), int(0), int(0)

    chroma = _value * _saturation  # Chroma
    X = chroma * (1 - abs(h_pri % 2 - 1))

    rgb_pri = [0.0, 0.0, 0.0]

    if 0 <= h_pri <= 1:
        rgb_pri = [chroma, X, 0]
    elif 1 <= h_pri <= 2:
        rgb_pri = [X, chroma, 0]
    elif 2 <= h_pri <= 3:
        rgb_pri = [0, chroma, X]
    elif 3 <= h_pri <= 4:
        rgb_pri = [0, X, chroma]
    elif 4 <= h_pri <= 5:
        rgb_pri = [X, 0, chroma]
    elif 5 <= h_pri <= 6:
        rgb_pri = [chroma, 0, X]
    else:
        rgb_pri = [0, 0, 0]

    m = _value - chroma

    return int((rgb_pri[0] + m) * 255), int((rgb_pri[1] + m) * 255), int((rgb_pri[2] + m) * 255)


def get_xy(h, s, v):
    rgb = hsv_to_rgb(h, s, v)
    converter = Converter()
    xy = converter.rgb_to_xy(rgb[0], rgb[1], rgb[2])
    return xy[0], xy[1]


@ACC_TYPES.register("Light")
class Light(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_LIGHTBULB)

        self.accessory_state = 0
        self.brightness = 100
        self.saturation = None
        self.hue = 255
        self.xy = None

        self._subscriptions = []
        self.states = None

        self.brightness_supported = self.support[ATTR_BRIGHTNESS] if ATTR_BRIGHTNESS in self.support else False
        self.colortemp_supported = self.support[ATTR_COLORTEMP] if ATTR_COLORTEMP in self.support else False
        self.color_supported = self.support[ATTR_COLOR] if ATTR_COLOR in self.support else False

        self.states = state_collector.get_device_state(self.entity_id)

        if self.brightness_supported:
            self.chars.append(CHAR_BRIGHTNESS)
        if self.colortemp_supported:
            self.chars.append(CHAR_COLOR_TEMPERATURE)
        if self.color_supported:
            self.chars.extend([CHAR_HUE, CHAR_SATURATION])
        self.chars.append(CHAR_ON)

        serv_light = self.add_preload_service('Lightbulb', chars=self.chars)
        self.char_on = serv_light.configure_char(CHAR_ON, value=0)

        if self.brightness_supported:
            self.char_brightness = serv_light.configure_char(CHAR_BRIGHTNESS, value=100)

        if self.colortemp_supported:
            self.char_colortemp = serv_light.configure_char(CHAR_COLOR_TEMPERATURE, value=100)

        if self.color_supported:
            self.char_hue = serv_light.configure_char(CHAR_HUE, value=0)
            self.char_saturation = serv_light.configure_char(CHAR_SATURATION, value=75)

        serv_light.setter_callback = self._set_chars
        self.async_update_state(self.states)

    @threaded
    def _set_chars(self, char_values):
        logger.debug("Light _set_chars: %s", char_values)

        # Mark that user just changed the state - ignore external updates for a short time
        self.mark_user_action()

        if self.char_on.value == 0:  # and self.char_brightness != 0:
            self.brightness = 0
            self.accessory_state = 0
        else:
            if self.brightness_supported:
                self.brightness = self.char_brightness.value
                self.accessory_state = 1
            else:
                self.brightness = 100
                self.accessory_state = 1

        _attributes = {}

        for char in char_values.keys():
            if char == "Hue":
                if self.color_supported and hasattr(self, 'char_hue'):
                    if self.support.get('hue'):
                        _attributes.update({'hue': self.char_hue.value})
                    else:
                        if self.brightness > 0 and hasattr(self, 'char_saturation'):
                            self.xy = get_xy(self.char_hue.value, self.char_saturation.value, self.brightness)
                            _attributes.update({'x': self.xy[0]})
                            _attributes.update({'y': self.xy[1]})
            if char == "ColorTemperature":
                if self.colortemp_supported and hasattr(self, 'char_colortemp'):
                    _attributes.update({'colortemp': self.char_colortemp.value})
            if char == "Saturation":
                if self.color_supported and hasattr(self, 'char_saturation'):
                    _attributes.update({'saturation': self.char_saturation.value})

        _attributes.update({'brightness': self.brightness})

        event_decider.device_event(
            self.entity_id,
            self.dsuid,
            self.zoneid,
            _attributes,
            "lights"
        )

    def set_hue(self, value):
        # Lets only write the new RGB values if the power is on
        # otherwise update the hue value only
        if self.accessory_state == 1:
            self.hue = value
        else:
            self.hue = value

    def set_saturation(self, value):
        self.saturation = value
        self.set_hue(self.hue)

    @DsAccessory.run_at_interval(2)  # Reduced from 3 to 2 seconds for faster response
    async def run(self):
        """Handle accessory driver started event - update state from digitalStrom."""
        try:
            current_time = int(time.time())

            # Ignore updates if user just changed the state (prevents race condition)
            if self.should_ignore_update():
                logger.debug("Ignoring state update for %s - user action was %d seconds ago",
                             self.entity_id, current_time - self._last_user_action)
                return

            device_services = state_collector.get_device_state(self.entity_id)

            # Check if state was recently updated (within last 5 seconds for faster response)
            # This prevents unnecessary updates but still catches WebSocket events
            recently_changed = current_time - 5 < device_services.get('last_change', 0)

            # Early exit if nothing changed recently and values match - saves CPU on Pi
            if not recently_changed:
                # Quick check if brightness matches current value
                brightness_state = device_services.get('states', {}).get(ATTR_BRIGHTNESS)
                if brightness_state:
                    current_brightness = round(brightness_state.get('value', 0))
                    if (self.brightness == current_brightness and
                            self.accessory_state == bool(current_brightness)):
                        return  # No changes, skip processing

            for char, values in device_services['states'].items():
                if char == ATTR_BRIGHTNESS:
                    # Get raw value from digitalStrom
                    raw_value = values.get('value', 0)
                    _value = round(raw_value)

                    # Update state if changed
                    new_state = bool(_value)
                    if self.accessory_state != new_state:
                        self.accessory_state = new_state
                        self.char_on.set_value(self.accessory_state, should_notify=True)
                        try:
                            self.char_on.notify()
                            logger.debug("Updated light %s state to %s", self.entity_id, self.accessory_state)
                        except Exception as notify_error:
                            logger.error("Error notifying state change: %s", notify_error, exc_info=True)

                    # Always update brightness if value differs
                    if self.brightness != _value:
                        old_brightness = self.brightness
                        self.brightness = _value
                        if self.brightness_supported:
                            # Ensure brightness is in valid range (0-100)
                            brightness_to_set = max(0, min(100, int(_value)))

                            # Set value and notify
                            self.char_brightness.set_value(brightness_to_set)
                            try:
                                self.char_brightness.notify()
                                logger.debug("Updated light %s brightness from %s to %s",
                                             self.entity_id, old_brightness, brightness_to_set)
                            except Exception as notify_error:
                                logger.error("Error notifying brightness change: %s", notify_error, exc_info=True)
                        else:
                            logger.debug("Light %s brightness changed but brightness not supported", self.entity_id)

                if char == "saturation" and recently_changed:
                    _value = round(values['value'])
                    if self.saturation != _value:
                        self.saturation = _value
                        if self.color_supported and hasattr(self, 'char_saturation'):
                            self.char_saturation.set_value(self.saturation)
                            self.char_saturation.notify()
                            logger.debug("Updated light %s saturation to %s", self.entity_id, self.saturation)

                if char == "colortemp" and recently_changed:
                    _value = round(values['value'])
                    if self.colortemp_supported and hasattr(self, 'char_colortemp'):
                        self.char_colortemp.set_value(_value)
                        self.char_colortemp.notify()
                        logger.debug("Updated light %s color temp to %s", self.entity_id, _value)
        except KeyError:
            # Device state not found yet, skip this update
            logger.debug("Device state not found for %s, skipping update", self.entity_id)
        except Exception as e:
            logger.error("Error updating light state for %s: %s", self.entity_id, e, exc_info=True)

    def async_update_state(self, new_state):
        """Update light after state change."""

        # Handle State
        state = new_state['states']['on']
        attributes = new_state['attributes']

        logger.debug("async_update_state for %s: state=%s, attributes=%s", self.entity_id, state, attributes)

        self.char_on.set_value(state)
        self.char_on.notify()
        self.accessory_state = state

        if (
                self.brightness_supported
                and (brightness := attributes.get(ATTR_BRIGHTNESS)) is not None
                and isinstance(brightness, (int, float))
        ):
            # Use brightness from attributes, not self.brightness
            if brightness == 0 and state == STATE_ON:
                brightness = 1
            logger.debug("async_update_state: Setting brightness to %s (from attributes)", brightness)
            self.brightness = brightness
            self.char_brightness.set_value(brightness)
            self.char_brightness.notify()
        # Handle Brightness

        # Handle Color - color must always be set before color temperature
        # or the iOS UI will not display it correctly.
        # if self.color_supported:
        #     if color_temp := attributes.get(ATTR_COLOR_TEMP):
        #         hue, saturation = color_temperature_to_hs(
        #             color_temperature_mired_to_kelvin(color_temp)
        #         )
        #     elif color_mode == COLOR_MODE_WHITE:
        #         hue, saturation = 0, 0
        #     else:
        #         hue, saturation = attributes.get(ATTR_HS_COLOR, (None, None))
        #     if isinstance(hue, (int, float)) and isinstance(saturation, (int, float)):
        #         self.char_hue.set_value(round(hue, 0))
        #         self.char_saturation.set_value(round(saturation, 0))
        #         if color_mode_changed:
        #             # If the color temp changed, be sure to force the color to update
        #             self.char_hue.notify()
        #             self.char_saturation.notify()
        #
        # # Handle white channels
        # if CHAR_COLOR_TEMPERATURE in self.chars:
        #     color_temp = None
        #     if self.color_temp_supported:
        #         color_temp = attributes.get(ATTR_COLOR_TEMP)
        #     elif color_mode == COLOR_MODE_WHITE:
        #         color_temp = self.min_mireds
        #     if isinstance(color_temp, (int, float)):
        #         self.char_color_temp.set_value(round(color_temp, 0))
        #         if color_mode_changed:
        #             self.char_color_temp.notify()

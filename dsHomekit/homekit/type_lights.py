import logging
import time

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_LIGHTBULB

from dsHomekit.digitalstrom import collector
from dsHomekit.homekit.accessories import TYPES, HomeAccessory
from dsHomekit import digitalstrom
from dsHomekit.utils.helper import threaded

from dsHomekit.const import (
    STATE_ON,
    CHAR_ON,
    CHAR_BRIGHTNESS, ATTR_HS_COLOR, ATTR_COLOR_TEMP, COLOR_MODE_WHITE, ATTR_BRIGHTNESS, ATTR_COLOR_MODE
)


@TYPES.register("Light")
class Light(Accessory):
    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, dsuid=None, chars=None):
        super().__init__(*args)

        self.chars = chars
        self.dsuid = dsuid
        self.accessory_state = 0
        self.brightness = 100
        self.saturation = None
        self.hue = 255

        self._subscriptions = []

        self.states = None

        self.brightness_supported = True
        self.color_supported = False

        self.states = collector.get_device_state(self.dsuid)

        serv_light = self.add_preload_service('Lightbulb', chars=self.chars)
        self.char_on = serv_light.configure_char(CHAR_ON, value=0)

        if self.brightness_supported:
            self.char_brightness = serv_light.configure_char(CHAR_BRIGHTNESS, value=100)

        if 'Hue' in self.chars:
            self.color_supported = True
            self.char_hue = serv_light.configure_char(
                'Hue', setter_callback=self.set_hue)

        if 'Saturation' in self.chars:
            self.char_saturation = serv_light.configure_char(
                'Saturation', setter_callback=self.set_saturation)

        serv_light.setter_callback = self._set_chars
        self.async_update_state(self.states)


    @threaded
    def _set_chars(self, char_values):
        logging.debug("Light _set_chars: %s", char_values)

        if self.char_on.value == 0 and self.char_brightness != 0:
            self.brightness = 0
        else:
            self.brightness = self.char_brightness.value

        # TODO: Muss anders funktionieren
        digitalstrom.patch_device(
            self.dsuid,
            self.brightness,
            'brightness')
        for char, value in char_values.items():
            if char == "Saturation":
                # TODO: Muss anders funktionieren
                digitalstrom.patch_device(
                    self.dsuid,
                    self.char_saturation.value,
                    'saturation'
                )
            if char == "Hue":
                # TODO: Muss anders funktionieren
                digitalstrom.patch_device(
                    self.dsuid,
                    self.char_hue.value,
                    'hue'
                )

    # def set_state(self, value):
    #     self.accessory_state = value
    #     if value:
    #         self.accessory_state = value
    #
    #     if self.brightness == 0:
    #         print("set_state: if ->", self.brightness)
    #         self.brightness = self.char_brightness.value
    #         self.set_brightness(self.brightness)
    #     else:
    #         print("set_state: else ->", self.brightness)
    #         self.accessory_state = 0
    #         self.set_brightness(0)

    def set_hue(self, value):
        # Lets only write the new RGB values if the power is on
        # otherwise update the hue value only
        if self.accessory_state == 1:
            self.hue = value
        else:
            self.hue = value

    def set_brightness(self, value):
        self.char_brightness.set_value(value)
        # self.brightness = value

    def set_saturation(self, value):
        self.saturation = value
        self.set_hue(self.hue)

    def hsv_to_rgb(self, h, s, v):
        """
        This function takes
         h - 0 - 360 Deg
         s - 0 - 100 %
         v - 0 - 100 %
        """

        hPri = h / 60
        s = s / 100
        v = v / 100

        if s <= 0.0:
            return int(0), int(0), int(0)

        C = v * s  # Chroma
        X = C * (1 - abs(hPri % 2 - 1))

        RGB_Pri = [0.0, 0.0, 0.0]

        if 0 <= hPri <= 1:
            RGB_Pri = [C, X, 0]
        elif 1 <= hPri <= 2:
            RGB_Pri = [X, C, 0]
        elif 2 <= hPri <= 3:
            RGB_Pri = [0, C, X]
        elif 3 <= hPri <= 4:
            RGB_Pri = [0, X, C]
        elif 4 <= hPri <= 5:
            RGB_Pri = [X, 0, C]
        elif 5 <= hPri <= 6:
            RGB_Pri = [C, 0, X]
        else:
            RGB_Pri = [0, 0, 0]

        m = v - C

        return int((RGB_Pri[0] + m) * 255), int((RGB_Pri[1] + m) * 255), int((RGB_Pri[2] + m) * 255)

    @Accessory.run_at_interval(3)
    async def run(self):
        """Handle accessory driver started event."""
        device_services = collector.get_device_state(self.dsuid)
        current_time = int(time.time())

        for char, values in device_services['states'].items():
            if char == ATTR_BRIGHTNESS and current_time-3 < device_services['last_change']:
                _value = round(values['value'])
                if self.accessory_state != bool(_value):
                    self.accessory_state = bool(_value)
                    self.char_on.set_value(self.accessory_state)

                if self.brightness != _value:
                    self.brightness = _value
                    self.char_brightness.set_value(self.brightness)

    def async_update_state(self, new_state):
        """Update light after state change."""
        # Handle State
        state = new_state['states']['on']
        attributes = new_state['attributes']

        self.char_on.set_value(int(state == STATE_ON))
        self.accessory_state = state

        # color_mode = attributes.get(ATTR_COLOR_MODE)
        # color_mode_changed = self._previous_color_mode != color_mode
        # self._previous_color_mode = color_mode

        # Handle Brightness
        if (
                self.brightness_supported
                and (brightness := attributes[ATTR_BRIGHTNESS]) is not None
                and isinstance(brightness, (int, float))
        ):
            brightness = self.brightness
            if brightness == 0 and state == STATE_ON:
                brightness = 1
            self.char_brightness.set_value(brightness)
            # if color_mode_changed:
            #     self.char_brightness.notify()

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

"""Class to hold all cover accessories."""
import logging
from pyhap.accessory import Accessory
from pyhap.const import (
    CATEGORY_WINDOW_COVERING,
)
from dsHomekit.homekit import collector
from . import event_decider
from dsHomekit.homekit.accessories import TYPES
from dsHomekit.helper import threaded


@TYPES.register("WindowCovering")
class WindowsCovering(Accessory):
    """Generate a base Window Covering accessory for a cover entity.

    This class is used for WindowCoveringBasic and
    WindowCovering
    """

    category = CATEGORY_WINDOW_COVERING

    def __init__(self, *args, device=None):
        """Initialize a WindowsCovering accessory object."""
        super().__init__(*args)

        self.chars = device['chars']
        self.dsuid = device['dsuid']
        self.entity_id = device['entity_id']
        self.zoneid = device['zoneid']

        self._supports_stop = True
        self._supports_tilt = False

        self.current_position = 0
        self.target_position = 0
        self.position_state = 0

        if self._supports_stop:
            self.chars.append('HoldPosition')
        if self._supports_tilt:
            self.chars.extend(['TargetHorizontalTiltAngle', 'CurrentHorizontalTiltAngle'])

        self.chars.append('Name')

        self.serv_cover = self.add_preload_service('WindowCovering', chars=self.chars)

        if self._supports_stop:
            self.char_hold_position = self.serv_cover.configure_char(
                'HoldPosition', setter_callback=self.set_stop
            )

        if self._supports_tilt:
            self.char_target_tilt = self.serv_cover.configure_char(
                'TargetHorizontalTiltAngle', setter_callback=self.set_tilt
            )
            self.char_current_tilt = self.serv_cover.configure_char(
                'CurrentHorizontalTiltAngle', value=0
            )

        self.char_name = self.serv_cover.configure_char(
            'Name', value=device['name']
        )

        self.char_current_position = self.serv_cover.configure_char(
            'CurrentPosition', 0)
        self.char_target_position = self.serv_cover.configure_char(
            'TargetPosition', value=0, setter_callback=self.move_cover)
        self.char_position_state = self.serv_cover.configure_char(
            'PositionState', 0)

    def set_stop(self, value):
        """Stop the cover motion from HomeKit."""
        logging.debug("%s: Set stop at %d", self.entity_id, value)

        if value != 1:
            return

    def set_tilt(self, value):
        """Set tilt to value if call came from HomeKit."""
        logging.debug("%s: Set tilt to %d", self.entity_id, value)

    @threaded
    def move_cover(self, value):
        """Move cover to value if call came from HomeKit."""
        logging.debug("%s: Set position to %d", self.dsuid, value)

        _attributes = {}
        _attributes.update({'shadePositionOutside': self.char_target_position.value})

        event_decider.device_event(
            self.dsuid,
            self.zoneid,
            _attributes,
            "shades"
        )
        self.char_target_position.set_value(value)

    @Accessory.run_at_interval(3)
    async def run(self):
        device_services = collector.get_device_state(self.entity_id)

        for char, values in device_services['states'].items():
            if char == 'shadePositionOutside':
                _target_value = round(values['targetvalue'])
                _current_value = round(values['value'])
                _position_state = 2 if self.target_position == self.current_position else 1
                if self.target_position != _target_value or self.current_position != _current_value:
                    self.target_position = _target_value
                    self.current_position = _current_value

                    self.char_current_position.set_value(self.current_position)
                    self.char_target_position.set_value(self.target_position)

                    self.char_position_state.set_value(_position_state)

    # @callback
    # def async_update_state(self, new_state):
    #     """Update cover position and tilt after state changed."""
    #     # update tilt
    #     if not self._supports_tilt:
    #         return
    #     current_tilt = new_state.attributes.get(ATTR_CURRENT_TILT_POSITION)
    #     if not isinstance(current_tilt, (float, int)):
    #         return
    #     # HomeKit sends values between -90 and 90.
    #     # We'll have to normalize to [0,100]
    #     current_tilt = (current_tilt / 100.0 * 180.0) - 90.0
    #     current_tilt = int(current_tilt)
    #     self.char_current_tilt.set_value(current_tilt)
    #     self.char_target_tilt.set_value(current_tilt)

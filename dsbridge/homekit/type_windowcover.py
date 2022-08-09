"""Class to hold all cover accessories."""
import logging
from pyhap.const import CATEGORY_WINDOW_COVERING
from . import event_decider
from .const import CHAR_HOLD_POSITION, CHAR_TARGET_HORIZONTAL_TILT_ANGLE, CHAR_CURRENT_HORIZONTAL_TILT_ANGLE, \
    CHAR_CURRENT_POSITION, CHAR_TARGET_POSITION, CHAR_POSITION_STATE, ATTR_SHADE_POSITION_OUTSIDE
from ..homekit import collector
from ..homekit.accessories import TYPES, DsAccessory
from ..helper import threaded


@TYPES.register("WindowCovering")
class WindowsCovering(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_WINDOW_COVERING)

        self.stop_supported = True
        self.tilt_supported = False

        self.current_position = 0
        self.target_position = 0
        self.position_state = 0

        if self.stop_supported:
            self.chars.append(CHAR_HOLD_POSITION)
        if self.tilt_supported:
            self.chars.extend([CHAR_TARGET_HORIZONTAL_TILT_ANGLE, CHAR_CURRENT_HORIZONTAL_TILT_ANGLE])

        self.chars.append('Name')

        self.serv_cover = self.add_preload_service('WindowCovering', chars=self.chars)

        if self.stop_supported:
            self.char_hold_position = self.serv_cover.configure_char(
                CHAR_HOLD_POSITION, setter_callback=self.set_stop
            )

        if self.tilt_supported:
            self.char_target_tilt = self.serv_cover.configure_char(
                CHAR_TARGET_HORIZONTAL_TILT_ANGLE, setter_callback=self.set_tilt
            )
            self.char_current_tilt = self.serv_cover.configure_char(
                CHAR_CURRENT_HORIZONTAL_TILT_ANGLE, value=0
            )

        self.char_current_position = self.serv_cover.configure_char(
            CHAR_CURRENT_POSITION, 0)
        self.char_target_position = self.serv_cover.configure_char(
            CHAR_TARGET_POSITION, value=0, setter_callback=self.move_cover)
        self.char_position_state = self.serv_cover.configure_char(
            CHAR_POSITION_STATE, 0)

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
        _attributes.update({ATTR_SHADE_POSITION_OUTSIDE: self.char_target_position.value})

        event_decider.device_event(
            self.entity_id,
            self.dsuid,
            self.zoneid,
            _attributes,
            "shades"
        )
        self.char_target_position.set_value(value)

    @DsAccessory.run_at_interval(3)
    async def run(self):
        device_services = collector.get_device_state(self.entity_id)

        for attr, values in device_services['states'].items():
            if attr == ATTR_SHADE_POSITION_OUTSIDE:
                _target_value = round(values['targetvalue'])
                _current_value = round(values['value'])
                _position_state = 2 if self.target_position == self.current_position else 1
                if self.target_position != _target_value or self.current_position != _current_value:
                    self.target_position = _target_value
                    self.current_position = _current_value

                    self.char_current_position.set_value(self.current_position)
                    self.char_target_position.set_value(self.target_position)

                    self.char_position_state.set_value(_position_state)

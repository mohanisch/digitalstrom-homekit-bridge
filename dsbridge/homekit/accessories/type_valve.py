import logging
import time

from pyhap.const import CATEGORY_SPRINKLER

from .. import event_decider
from ..const import CHAR_ACTIVE, CHAR_VALVE_TYPE, CHAR_INUSE, CHAR_REMAIN_DURATION, CHAR_SET_DURATION
from ..accessories import ACC_TYPES, DsAccessory
from ...helper import threaded

from ...digitalstrom import state_collector


@ACC_TYPES.register("Sprinkler")
class Sprinkler(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SPRINKLER)

        self.accessory_state = False
        self.states = state_collector.get_device_state(self.entity_id)

        self.serv_sprinkler = self.add_preload_service(
            'Valve', [
                CHAR_ACTIVE,
                CHAR_VALVE_TYPE,
                CHAR_INUSE,
                CHAR_REMAIN_DURATION,
                CHAR_SET_DURATION,
            ])
        self.char_active = self.serv_sprinkler.configure_char(
            CHAR_ACTIVE, value=0,
        )
        self.char_type = self.serv_sprinkler.configure_char(
            CHAR_VALVE_TYPE, value=1,
        )
        self.char_inuse = self.serv_sprinkler.configure_char(
            CHAR_INUSE, value=0,
        )
        self.char_remaining_duration = self.serv_sprinkler.configure_char(
            CHAR_REMAIN_DURATION
        )
        self.char_set_duration = self.serv_sprinkler.configure_char(
            CHAR_SET_DURATION, value=60
        )

        self.serv_sprinkler.setter_callback = self._set_chars

    @threaded
    def _set_chars(self, char_values):
        logging.debug("Valve _set_chars: %s", char_values)
        print("Valve _set_chars: %s", char_values)
        _attributes = {}

        if self.char_active.value == 0:
            self.accessory_state = False
            self.char_inuse.set_value(0)
        else:
            self.char_remaining_duration.set_value(self.char_set_duration.value)
            self.char_inuse.set_value(1)
            self.accessory_state = True

        if CHAR_ACTIVE in char_values:
            _attributes.update({'active': char_values[CHAR_ACTIVE]})

        if len(_attributes):
            event_decider.device_event(
                self.entity_id,
                self.dsuid,
                self.zoneid,
                _attributes,
                self.application
            )

    @DsAccessory.run_at_interval(3)
    async def run(self):

        device_state = state_collector.get_device_state(self.entity_id)
        current_time = int(time.time())

        _value = device_state['states']['on']

        if self.char_remaining_duration.value <= 0:
            if self.accessory_state:
                self.accessory_state = False
            else:
                self.char_remaining_duration.set_value(self.char_set_duration.value)

        if self.char_remaining_duration.value > 0:
            self.char_remaining_duration.set_value(self.char_remaining_duration.value - 3)

        if self.accessory_state != bool(_value) and current_time-3 < device_state['last_change']:
            self.accessory_state = bool(_value)
            self.char_active.set_value(self.accessory_state)
            self.char_inuse.set_value(self.accessory_state)



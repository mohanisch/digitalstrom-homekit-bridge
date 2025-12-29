import logging
import time

from pyhap.const import CATEGORY_SWITCH

from dsbridge.helper import threaded
from dsbridge.homekit import event_decider
from dsbridge.homekit.accessories import ACC_TYPES, DsAccessory
from dsbridge.homekit.const import CHAR_ON
from ...digitalstrom import state_collector


@ACC_TYPES.register("Switch")
class Switch(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SWITCH)

        self.accessory_state = False
        self.states = state_collector.get_device_state(self.entity_id)

        serv_switch = self.add_preload_service('Switch')
        self.char_on = serv_switch.configure_char(
            CHAR_ON, value=False,
        )

        serv_switch.setter_callback = self._set_chars
        self.async_update_state(self.states)

    @threaded
    def _set_chars(self, char_values):
        logging.debug("Switch _set_chars: %s", char_values)

        # Mark that user just changed the state - ignore external updates for a short time
        self.mark_user_action()

        _attributes = {}

        if self.char_on.value == 0:
            self.accessory_state = False
        else:
            self.accessory_state = True

        _attributes.update({'active': char_values[CHAR_ON]})

        event_decider.device_event(
            self.entity_id,
            self.dsuid,
            self.zoneid,
            _attributes,
            self.application
        )

    @DsAccessory.run_at_interval(2)  # Reduced from 3 to 2 seconds for faster response
    async def run(self):
        """Update switch state from digitalStrom."""
        try:
            current_time = int(time.time())

            # Ignore updates if user just changed the state (prevents race condition)
            if current_time < self._ignore_updates_until:
                logging.debug("Ignoring state update for %s - user action was %d seconds ago",
                              self.entity_id, current_time - self._last_user_action)
                return

            device_state = state_collector.get_device_state(self.entity_id)

            # Check if state was recently updated (within last 5 seconds)
            recently_changed = current_time - 5 < device_state.get('last_change', 0)
            _value = device_state['states']['on']

            # Early exit if no changes - saves CPU on Pi
            if not recently_changed and self.accessory_state == bool(_value):
                return

            # Always update if state changed, or if recently updated
            if recently_changed or self.accessory_state != bool(_value):
                if self.accessory_state != bool(_value):
                    self.accessory_state = bool(_value)
                    self.char_on.set_value(self.accessory_state)
                    self.char_on.notify()
                    logging.debug("Updated switch %s state to %s", self.entity_id, self.accessory_state)
        except KeyError:
            # Device state not found yet, skip this update
            logging.debug("Device state not found for %s, skipping update", self.entity_id)
        except Exception as e:
            logging.error("Error updating switch state for %s: %s", self.entity_id, e, exc_info=True)

    def async_update_state(self, new_state):
        """Update switch state after state changed."""

        current_state = new_state['states']['on']
        self.accessory_state = current_state
        logging.debug("%s: Set current state to %s", self.dsuid, current_state)
        self.char_on.set_value(current_state)

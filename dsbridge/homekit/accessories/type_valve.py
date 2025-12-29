import logging
import time

from pyhap.const import CATEGORY_SPRINKLER

from .. import event_decider
from ..accessories import ACC_TYPES, DsAccessory
from ..const import CHAR_ACTIVE, CHAR_VALVE_TYPE, CHAR_INUSE, CHAR_REMAIN_DURATION, CHAR_SET_DURATION
from ...digitalstrom import state_collector
from ...helper import threaded


@ACC_TYPES.register("Sprinkler")
class Sprinkler(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SPRINKLER)

        self.accessory_state = False
        self.states = state_collector.get_device_state(self.entity_id)
        self._auto_turned_off = False  # Flag to track if we auto-turned off
        self._timer_enabled = False  # Flag to track if timer should run (only when activated via HomeKit)

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
        # Mark that user just changed the state - ignore external updates for a short time
        self.mark_user_action()

        _attributes = {}

        # Handle SET_DURATION changes
        if CHAR_SET_DURATION in char_values:
            new_duration = char_values[CHAR_SET_DURATION]
            # If valve is currently active, update remaining duration immediately
            if self.char_active.value == 1 and self.char_inuse.value == 1:
                self.char_remaining_duration.set_value(new_duration)
                logging.debug("Updated remaining duration to %d seconds while valve is active", new_duration)
            # Otherwise, just update the set duration (will be used next time valve is activated)
            else:
                logging.debug("Set duration changed to %d seconds (valve inactive, will use on next activation)",
                              new_duration)

        # Handle ACTIVE changes
        if CHAR_ACTIVE in char_values:
            active_value = char_values[CHAR_ACTIVE]
            if active_value == 0:
                # Turn off valve via HomeKit - IMPORTANT: Set InUse first, then Active
                # This prevents iOS from getting stuck in "stopping" state
                self.accessory_state = False
                self._auto_turned_off = False  # Clear flag on manual turn-off
                self._timer_enabled = False  # Disable timer
                self.char_remaining_duration.set_value(0)
                self.char_inuse.set_value(0)
                self.char_inuse.notify()
                self.char_active.set_value(0)
                self.char_active.notify()
                self.char_remaining_duration.notify()
                _attributes.update({'active': 0})
            else:
                # Turn on valve via HomeKit - start timer
                self._auto_turned_off = False  # Clear flag on manual turn-on
                self._timer_enabled = True  # Enable timer when activated via HomeKit
                self.char_remaining_duration.set_value(self.char_set_duration.value)
                self.char_inuse.set_value(1)
                self.char_inuse.notify()
                self.accessory_state = True
                _attributes.update({'active': 1})
                logging.debug("Valve activated via HomeKit with duration %d seconds", self.char_set_duration.value)

        if len(_attributes):
            event_decider.device_event(
                self.entity_id,
                self.dsuid,
                self.zoneid,
                _attributes,
                self.application
            )

    @DsAccessory.run_at_interval(2)  # Reduced from 3 to 2 seconds for faster response
    async def run(self):
        """Update valve state from digitalStrom."""
        try:
            # Ignore updates if user just changed the state (prevents race condition)
            if self.should_ignore_update():
                return

            device_state = state_collector.get_device_state(self.entity_id)
            current_time = int(time.time())

            # Check if state was recently updated (within last 5 seconds)
            recently_changed = current_time - 5 < device_state.get('last_change', 0)
            _value = device_state['states']['on']

            # Update timer if valve is active AND timer is enabled
            if self.accessory_state and self._timer_enabled and self.char_remaining_duration.value > 0:
                new_remaining = max(0, self.char_remaining_duration.value - 2)
                self.char_remaining_duration.set_value(new_remaining)

                # Auto-turn off valve when timer reaches 0
                if new_remaining <= 0:
                    logging.info("Valve timer expired for %s, turning off automatically", self.entity_id)
                    # Update state first
                    self.accessory_state = False
                    self._timer_enabled = False  # Disable timer
                    # Set flag to prevent re-enabling from digitalSTROM until it confirms off
                    self._auto_turned_off = True
                    # IMPORTANT: Set InUse to 0 FIRST, then Active to 0
                    # This prevents iOS from getting stuck in "stopping" state
                    # HomeKit expects: InUse=0, then Active=0 for proper stop sequence
                    # Set remaining duration first
                    self.char_remaining_duration.set_value(0)
                    # Set InUse to 0 first and notify immediately
                    self.char_inuse.set_value(0)
                    self.char_inuse.notify()
                    # Then set Active to 0 - CRITICAL: Use set_value with notify=True to ensure HomeKit updates
                    self.char_active.set_value(0)
                    self.char_active.notify()
                    # Notify remaining duration
                    self.char_remaining_duration.notify()
                    logging.info("Updated HomeKit characteristics: inuse=0, active=0, remaining=0, timer disabled")
                    # Send event directly to digitalSTROM (bypass event_decider since no HAP events)
                    # For manualState, we need to use patch_switch directly
                    logging.info("Sending direct patch_switch to turn off valve %s (dsuid=%s, application=%s)",
                                 self.entity_id, self.dsuid, self.application)
                    from ...digitalstrom import event_patcher
                    if event_patcher is None:
                        logging.error("event_patcher is not initialized, cannot send turn-off event")
                    else:
                        # manualState uses 'inactive' state for active=0
                        event_patcher.patch_switch(self.dsuid, 'inactive')
                        logging.debug("Direct patch_switch sent for valve %s", self.entity_id)
                    # Mark user action with longer duration to prevent re-sync from digitalSTROM
                    # Give digitalSTROM time to process the change (20 seconds should be enough)
                    self.mark_user_action(duration=20)
                    return

            # Early exit if no changes - saves CPU on Pi
            if not recently_changed and self.accessory_state == bool(_value):
                return

            # Update state from digitalSTROM if it changed externally
            if recently_changed or self.accessory_state != bool(_value):
                if self.accessory_state != bool(_value):
                    # If we auto-turned off, only accept "off" from digitalSTROM, ignore "on" until confirmed
                    if self._auto_turned_off and bool(_value):
                        logging.debug(
                            "Ignoring digitalSTROM 'on' state for %s - waiting for confirmation of auto-turn-off",
                            self.entity_id
                        )
                        return

                    # If digitalSTROM confirms "off" after auto-turn-off, clear the flag
                    if self._auto_turned_off and not bool(_value):
                        logging.debug("digitalSTROM confirmed valve %s is off, clearing auto-turn-off flag",
                                      self.entity_id)
                        self._auto_turned_off = False

                    self.accessory_state = bool(_value)
                    if self.accessory_state:
                        # Turn on from digitalSTROM: Set Active first, then InUse
                        # DO NOT start timer - timer is only for HomeKit activations
                        self._timer_enabled = False  # Timer disabled for external activations
                        self.char_active.set_value(1)
                        self.char_active.notify()
                        self.char_inuse.set_value(1)
                        self.char_inuse.notify()
                        # Keep remaining duration at 0 (no timer for external activations)
                        self.char_remaining_duration.set_value(0)
                        self.char_remaining_duration.notify()
                        logging.debug("Valve activated from digitalSTROM - timer disabled")
                    else:
                        # Turn off: Set InUse to 0 FIRST, then Active to 0
                        # This prevents iOS from getting stuck in "stopping" state
                        self.char_remaining_duration.set_value(0)
                        self.char_inuse.set_value(0)
                        self.char_inuse.notify()
                        self.char_active.set_value(0)
                        self.char_active.notify()
                        self.char_remaining_duration.notify()
                    logging.debug("Updated valve %s state to %s", self.entity_id, self.accessory_state)
        except KeyError:
            logging.debug("Device state not found for %s, skipping update", self.entity_id)
        except Exception as e:
            logging.error("Error updating valve state for %s: %s", self.entity_id, e, exc_info=True)

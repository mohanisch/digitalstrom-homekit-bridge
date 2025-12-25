"""Class to hold all cover accessories."""
import logging
import time
from pyhap.const import CATEGORY_WINDOW_COVERING
from dsbridge.homekit import event_decider
from dsbridge.homekit.const import CHAR_HOLD_POSITION, CHAR_TARGET_HORIZONTAL_TILT_ANGLE, CHAR_CURRENT_HORIZONTAL_TILT_ANGLE, \
    CHAR_CURRENT_POSITION, CHAR_TARGET_POSITION, CHAR_POSITION_STATE, ATTR_SHADE_POSITION_OUTSIDE
from dsbridge.homekit import state_collector
from dsbridge.homekit.accessories import ACC_TYPES, DsAccessory
from dsbridge.helper import threaded


@ACC_TYPES.register("WindowCovering")
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
        try:
            logging.debug("%s: Set stop at %d", self.entity_id, value)
            if value != 1:
                return
            # TODO: Implement stop functionality
            logging.debug("%s: Stop requested", self.entity_id)
        except Exception as e:
            logging.error("Error in set_stop for %s: %s", self.entity_id, e, exc_info=True)

    def set_tilt(self, value):
        """Set tilt to value if call came from HomeKit."""
        logging.debug("%s: Set tilt to %d", self.entity_id, value)

    @threaded
    def move_cover(self, value):
        """Move cover to value if call came from HomeKit."""
        try:
            logging.info("%s: Setting position to %d", self.entity_id, value)
            
            # Mark that user just changed the state - ignore external updates for a short time
            self.mark_user_action()
            
            # Update local state immediately
            self.target_position = value
            self.position_state = 1  # Moving
            
            # Set the characteristic values
            self.char_target_position.set_value(value)
            self.char_position_state.set_value(1)  # Moving
            
            # Notify clients immediately
            try:
                self.char_target_position.notify()
                self.char_position_state.notify()
            except Exception as notify_error:
                logging.error("Error notifying position change: %s", notify_error, exc_info=True)
            
            # Send event to digitalStrom
            _attributes = {}
            _attributes.update({ATTR_SHADE_POSITION_OUTSIDE: value})

            event_decider.device_event(
                self.entity_id,
                self.dsuid,
                self.zoneid,
                _attributes,
                "shades"
            )
            logging.debug("%s: Position change event sent to digitalStrom", self.entity_id)
        except Exception as e:
            logging.error("Error in move_cover for %s: %s", self.entity_id, e, exc_info=True)

    @DsAccessory.run_at_interval(2)  # Reduced from 3 to 2 seconds for faster response
    async def run(self):
        """Update window cover state from digitalStrom."""
        try:
            current_time = int(time.time())
            
            # Ignore updates if user just changed the state (prevents race condition)
            if self.should_ignore_update():
                logging.debug("Ignoring state update for %s - user action was %d seconds ago", 
                             self.entity_id, current_time - self._last_user_action)
                return
            
            device_services = state_collector.get_device_state(self.entity_id)
            
            # Check if state was recently updated (within last 5 seconds)
            recently_changed = current_time - 5 < device_services.get('last_change', 0)
            
            # Early exit if no changes - saves CPU on Pi
            if not recently_changed:
                shade_state = device_services.get('states', {}).get(ATTR_SHADE_POSITION_OUTSIDE)
                if shade_state:
                    target_val = round(shade_state.get('targetvalue', 0))
                    current_val = round(shade_state.get('value', 0))
                    if (self.target_position == target_val and 
                        self.current_position == current_val):
                        return

            for attr, values in device_services['states'].items():
                if attr == ATTR_SHADE_POSITION_OUTSIDE:
                    _target_value = round(values['targetvalue'])
                    _current_value = round(values['value'])
                    _position_state = 2 if _target_value == _current_value else 1
                    
                    # Always update if values changed, or if recently updated
                    if recently_changed or self.target_position != _target_value or self.current_position != _current_value:
                        self.target_position = _target_value
                        self.current_position = _current_value

                        self.char_current_position.set_value(self.current_position)
                        self.char_target_position.set_value(self.target_position)
                        self.char_position_state.set_value(_position_state)
                        
                        # Notify clients of changes
                        try:
                            self.char_current_position.notify()
                            self.char_target_position.notify()
                            self.char_position_state.notify()
                            logging.debug("Updated window cover %s: target=%s, current=%s, state=%s", 
                                        self.entity_id, _target_value, _current_value, _position_state)
                        except Exception as notify_error:
                            logging.error("Error notifying window cover changes: %s", notify_error, exc_info=True)
        except KeyError:
            logging.debug("Device state not found for %s, skipping update", self.entity_id)
        except Exception as e:
            logging.error("Error updating window cover state for %s: %s", self.entity_id, e, exc_info=True)

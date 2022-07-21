import logging
import time

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SPEAKER

from .const import CHAR_ON, STATE_ON, CHAR_ACTIVE, CHAR_NAME
from ..homekit import collector
from ..homekit.accessories import TYPES, DsAccessory
from ..helper import threaded
from . import event_decider


@TYPES.register("Speaker")
class Speaker(DsAccessory):

    SOURCES = {
        'HDMI 1': 3,
        'HDMI 2': 3,
        'HDMI 3': 3,
    }

    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SPEAKER)

        self.accessory_state = False

        #self.states = collector.get_device_state(self.entity_id)

        self.set_info_service(
            manufacturer='HaPK',
            model='Raspberry Pi',
            firmware_revision='1.0',
            serial_number='1'
        )

        tv_service = self.add_preload_service(
            'Television', ['Name',
                           'ConfiguredName',
                           'Active',
                           'ActiveIdentifier',
                           'RemoteKey',
                           'SleepDiscoveryMode'],
        )
        self._active = tv_service.configure_char(
            'Active', value=0,
            setter_callback=self._on_active_changed,
        )
    #     tv_service.configure_char(
    #         'ActiveIdentifier', value=1,
    #         setter_callback=self._on_active_identifier_changed,
    #     )
    #     tv_service.configure_char(
    #         'RemoteKey', setter_callback=self._on_remote_key,
    #     )
    #     tv_service.configure_char('Name', value=self.display_name)
    #     # TODO: implement persistence for ConfiguredName
    #     tv_service.configure_char('ConfiguredName', value=self.display_name)
    #     tv_service.configure_char('SleepDiscoveryMode', value=1)
    #
    #     for idx, (source_name, source_type) in enumerate(self.SOURCES.items()):
    #         input_source = self.add_preload_service('InputSource', ['Name', 'Identifier'])
    #         input_source.configure_char('Name', value=source_name)
    #         input_source.configure_char('Identifier', value=idx + 1)
    #         # TODO: implement persistence for ConfiguredName
    #         input_source.configure_char('ConfiguredName', value=source_name)
    #         input_source.configure_char('InputSourceType', value=source_type)
    #         input_source.configure_char('IsConfigured', value=1)
    #         input_source.configure_char('CurrentVisibilityState', value=0)
    #
    #         tv_service.add_linked_service(input_source)
    #
    #     tv_speaker_service = self.add_preload_service(
    #         'TelevisionSpeaker', ['Active',
    #                               'VolumeControlType',
    #                               'VolumeSelector', 'Mute']
    #     )
    #     tv_speaker_service.configure_char('Active', value=1)
    #     # Set relative volume control
    #     tv_speaker_service.configure_char('VolumeControlType', value=1)
    #     tv_speaker_service.configure_char(
    #         'Mute', setter_callback=self._on_mute,
    #     )
    #     tv_speaker_service.configure_char(
    #         'VolumeSelector', setter_callback=self._on_volume_selector,
    #     )
    #
    # def _on_active_changed(self, value):
    #     print('Turn %s' % ('on' if value else 'off'))
    #
    # def _on_active_identifier_changed(self, value):
    #     print('Change input to %s' % list(self.SOURCES.keys())[value - 1])
    #
    # def _on_remote_key(self, value):
    #     print('Remote key %d pressed' % value)
    #
    # def _on_mute(self, value):
    #     print('Mute' if value else 'Unmute')
    #
    # def _on_volume_selector(self, value):
    #     print('%screase volume' % ('In' if value == 0 else 'De'))
    #
    # @threaded
    # def _set_chars(self, char_values):
    #     logging.debug("Valve _set_chars: %s", char_values)
    #     _attributes = {}
    #
    #     if self.char_mute.value == 0:
    #         self.accessory_state = False
    #     else:
    #         self.accessory_state = True
    #
    #     _attributes.update({'active': char_values['Active']})

    # TODO: Muss anders funktionieren
    # event_decider.device_event(
    #     self.dsuid,
    #     self.zoneid,
    #     _attributes,
    #     "audio"
    # )
    #
    # @Accessory.run_at_interval(3)
    # async def run(self):
    #
    #     device_state = collector.get_device_state(self.entity_id)
    #     current_time = int(time.time())
    #
    #     _value = device_state['state'] == STATE_ON
    #
    #     if self.accessory_state != bool(_value) and current_time-3 < device_state['last_change']:
    #         self.accessory_state = bool(_value)
    #         self.char_on.set_value(self.accessory_state)
    #
    # def async_update_state(self, new_state):
    #     """Update switch state after state changed."""
    #
    #     current_state = new_state['state'] == STATE_ON
    #     self.accessory_state = current_state
    #     logging.debug("%s: Set current state to %s", self.dsuid, current_state)
    #     self.char_on.set_value(current_state)

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR

from dsHomekit.digitalstrom import collector
from dsHomekit.homekit.accessories import TYPES

@TYPES.register("TemperatureSensor")
class TemperatureSensor(Accessory):
    category = CATEGORY_SENSOR

    def __init__(self, *args, dsuid=None, chars=None, support=None):
        super().__init__(*args)

        self.chars = chars
        self.dsuid = dsuid
        self.temperature = 0

        serv_temp = self.add_preload_service('TemperatureSensor')
        self.char_temp = serv_temp.configure_char('CurrentTemperature')

    @Accessory.run_at_interval(60)
    async def run(self):
        device_services = collector.get_device_state(self.dsuid)
        for char, values in device_services['states'].items():
            if char == 'temperature':
                _value = round(values['value'], 2)
                if self.temperature != _value:
                    self.temperature = _value
                    self.char_temp.set_value(self.temperature)


@TYPES.register("HumiditySensor")
class HumiditySensor(Accessory):
    category = CATEGORY_SENSOR

    def __init__(self, *args, dsuid=None, chars=None, support=None):
        super().__init__(*args)

        self.chars = chars
        self.dsuid = dsuid
        self.humidity = 80

        serv_temp = self.add_preload_service('HumiditySensor')
        self.char_temp = serv_temp.configure_char('CurrentRelativeHumidity')

    @Accessory.run_at_interval(60)
    async def run(self):
        device_services = collector.get_device_state(self.dsuid)
        for char, values in device_services['states'].items():
            if char == 'humidity':
                _value = round(values['value'], 2)
                if self.humidity != _value:
                    self.humidity = _value
                    self.char_temp.set_value(self.humidity)

@TYPES.register("LightSensor")
class LightSensor(Accessory):
    category = CATEGORY_SENSOR

    def __init__(self, *args, dsuid=None, chars=None, support=None):
        super().__init__(*args)

        self.chars = chars
        self.dsuid = dsuid
        self.illuminance = 5

        serv_temp = self.add_preload_service('LightSensor')
        self.char_temp = serv_temp.configure_char('CurrentAmbientLightLevel')

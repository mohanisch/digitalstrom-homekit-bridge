from pyhap.const import CATEGORY_SENSOR

from ..homekit import collector
from ..homekit.accessories import TYPES, DsAccessory


@TYPES.register("TemperatureSensor")
class TemperatureSensor(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SENSOR)

        self.temperature = 0

        serv_temp = self.add_preload_service('TemperatureSensor')
        self.char_temp = serv_temp.configure_char('CurrentTemperature')

    @DsAccessory.run_at_interval(3)
    async def run(self):
        device_services = collector.get_device_state(self.entity_id)
        for char, values in device_services['states'].items():
            if char == 'temperature':
                _value = round(values['value'], 2)
                if self.temperature != _value:
                    self.temperature = _value
                    self.char_temp.set_value(self.temperature)


@TYPES.register("HumiditySensor")
class HumiditySensor(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SENSOR)

        self.humidity = 80

        serv_temp = self.add_preload_service('HumiditySensor')
        self.char_temp = serv_temp.configure_char('CurrentRelativeHumidity')

    @DsAccessory.run_at_interval(60)
    async def run(self):
        device_services = collector.get_device_state(self.entity_id)
        for char, values in device_services['states'].items():
            if char == 'humidity':
                _value = round(values['value'], 2)
                if self.humidity != _value:
                    self.humidity = _value
                    self.char_temp.set_value(self.humidity)


@TYPES.register("LightSensor")
class LightSensor(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SENSOR)

        self.brightness = 0

        serv_light = self.add_preload_service('LightSensor')
        self.char_lightlevel = serv_light.configure_char('CurrentAmbientLightLevel')

    @DsAccessory.run_at_interval(60)
    async def run(self):
        device_services = collector.get_device_state(self.entity_id)
        for char, values in device_services['states'].items():
            if char == 'brightness':
                _value = round(values['value'], 2)
                if self.brightness != _value:
                    self.brightness = _value
                    self.char_lightlevel.set_value(self.brightness)


@TYPES.register("MotionSensor")
class MotionSensor(DsAccessory):
    def __init__(self, *args):
        super().__init__(*args, category=CATEGORY_SENSOR)

        self.motion = False

        serv_motion = self.add_preload_service('MotionSensor')
        self.char_motion = serv_motion.configure_char('MotionDetected')

    @DsAccessory.run_at_interval(2)
    async def run(self):
        device_services = collector.get_device_state(self.entity_id)
        for char, values in device_services['states'].items():
            if char == 'motion':
                _value = round(values['value'], 2)
                if self.motion != _value:
                    self.motion = _value
                    self.char_motion.set_value(self.motion)

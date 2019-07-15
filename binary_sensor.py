import logging
from datetime import timedelta
import requests
import voluptuous as vol

from homeassistant.components.binary_sensor import (BinarySensorDevice, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_MONITORED_CONDITIONS, ATTR_ATTRIBUTION, CONF_HOST, CONF_SCAN_INTERVAL)
from homeassistant.util import Throttle

__version__ = '0.0.5'

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)
CONF_ATTRIBUTION = "Data provided by Emfit QS"
DATA_ARLO = 'data_emfitqs'
DEFAULT_BRAND = 'Emfit'
DOMAIN = 'emfitqs'

INTERVAL = 10
HOST = '192.168.1.40'

SENSOR_PREFIX = 'EmfitQS '

SENSOR_TYPES = {
    'pres': ['Presence', '', 'mdi:hotel']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    host = config.get(CONF_HOST)

    try:
        data = EmfitQSData(host)
        data.update()
        sensors = []
        for resource in config[CONF_MONITORED_CONDITIONS]:
            sensor_type = resource.lower()
            if sensor_type == "pres":         
                sensors.append(EmfitQSBinarySensor(data.data['ser'], data, sensor_type))
        add_entities(sensors)
        return True
    except requests.exceptions.HTTPError as error:
        _LOGGER.error(error)
        return False

class EmfitQSData(object):    

    def __init__(self, host):
        self._host = host
        self.data = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):      
        entries = {}
        r = requests.get('http://{0}/dvmstatus.htm'.format(self._host))
        if r.status_code == 200:
            elements = r.text.replace("<br>",'').lower().split('\r\n')
            filtered = list(filter(None, elements))
            for f in filtered:
                entry = f.split("=")
                entry_name = entry[0].replace(':', '').replace(' ', '_').replace(',', '')
                if entry_name=="pres":
                    if entry[1]=="0":
                        entry_value = "off"
                    else:
                        entry_value = "on"
                else:
                    entry_value = entry[1]
                entries[entry_name] = entry_value
        self.data = entries
        _LOGGER.debug("Data = %s", self.data)
        
class EmfitQSBinarySensor(BinarySensorDevice):

    def __init__(self, serial, data, sensor_type):
        self.data = data
        self.type = sensor_type
        self._name = SENSOR_PREFIX + serial + ' ' + SENSOR_TYPES[self.type][0]
        self._unit = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    def update(self):
        self.data.update()
        data = self.data.data

        self._state = data[self.type]

    @property
    def device_class(self):
        return "occupancy"

    @property
    def device_state_attributes(self):       
        attrs = {}

        attrs[ATTR_ATTRIBUTION] = CONF_ATTRIBUTION

        return attrs
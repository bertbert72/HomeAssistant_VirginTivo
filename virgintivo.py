"""
Support for the Virgin Tivo boxes

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xyz
"""
import logging
import socket
import time
import re
import errno
from socket import error as SocketError

import voluptuous as vol

from homeassistant.components.media_player import (
    DOMAIN, MEDIA_PLAYER_SCHEMA, PLATFORM_SCHEMA, SUPPORT_SELECT_SOURCE,
    MediaPlayerDevice)
from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_NAME, CONF_HOST, CONF_PORT, STATE_OFF, STATE_ON,
    CONF_USERNAME,CONF_PASSWORD)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_VIRGINTIVO = SUPPORT_SELECT_SOURCE

CONF_TIVOS = 'tivos'
CONF_CHANNELS = 'channels'
CONF_HDVER = 'hdver'
CONF_PLUSONE = 'plusone'
CONF_SHOW = 'show'
CONF_SHOWBYDEFAULT = 'showbydefault'
CONF_HDVERBYDEFAULT = 'hdverbydefault'

DATA_VIRGINTIVO = 'virgintivo'
DATA_GUIDEURL = 'https://virgintvgo.virginmedia.com/en/tv/watch-tv.html'

TIVO_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_NAME): cv.string,
})

CHANNEL_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_HDVER, default=""): cv.string,
    vol.Optional(CONF_PLUSONE, default=""): cv.string,
    vol.Optional(CONF_SHOW, default="unset"): cv.string,
})

CONF_PROGRAMME = 'programme'
CONF_STARTTIME = 'starttime'
CONF_ENDTIME = 'endtime'
CONF_LOGO = 'logo'
CONF_PICTURE = 'picture'

GUIDE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_PROGRAMME): cv.string,
    vol.Required(CONF_STARTTIME): cv.string,
    vol.Required(CONF_ENDTIME): cv.string,
    vol.Required(CONF_LOGO): cv.string,
    vol.Required(CONF_PICTURE): cv.string,
})


#SERVICE_SETALLTIVOS = 'virgintivo_set_all_tivos'
#ATTR_SOURCE = 'channel'

#VIRGINTIVO_SETALLTIVOS_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
#    vol.Required(ATTR_SOURCE): cv.string
#})


# Valid tivo ids: 1-9
TIVO_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=9))

# Valid channel ids: 1-99
CHANNEL_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=999))

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend({
        vol.Optional(CONF_SHOWBYDEFAULT, default="True"): cv.string,
        vol.Optional(CONF_HDVERBYDEFAULT, default=False): cv.boolean,
        vol.Required(CONF_TIVOS): vol.Schema({TIVO_IDS: TIVO_SCHEMA}),
        vol.Required(CONF_CHANNELS): vol.Schema({CHANNEL_IDS: CHANNEL_SCHEMA}),
    }))


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Virgin Tivo platform."""
    if DATA_VIRGINTIVO not in hass.data:
        hass.data[DATA_VIRGINTIVO] = {}

    showByDefault = config.get(CONF_SHOWBYDEFAULT)

    channels = {}
    channels_enabled = {}
    hdvers = {}
    for channel_id, extra in config[CONF_CHANNELS].items():
        #_LOGGER.debug("Key [%s] = [%s]",channel_id,extra[CONF_SHOW])
        channels[channel_id] = extra[CONF_NAME]
        hdvers[channel_id] = extra[CONF_HDVER] if config.get(CONF_HDVERBYDEFAULT) else ""
        if (showByDefault == 'True' and extra[CONF_SHOW] != 'False') or (showByDefault == 'False' and extra[CONF_SHOW] == 'True'):
            channels_enabled[channel_id] = extra[CONF_NAME]

    #_LOGGER.debug("Channel list is [%s]",channels)
    #_LOGGER.debug("Channel enabled list is [%s]",channels_enabled)

    devices = []
    for tivo_id, extra in config[CONF_TIVOS].items():
        _LOGGER.info("Adding Tivo %d - %s", tivo_id, extra[CONF_NAME])
        unique_id = "{}-{}".format(extra[CONF_HOST], tivo_id)
        device = VirginTivo(extra[CONF_HOST], channels, channels_enabled, hdvers, tivo_id, extra[CONF_NAME])
        hass.data[DATA_VIRGINTIVO][unique_id] = device
        devices.append(device)

    add_devices(devices, True)

    #def service_handle(service):
    #    """Handle for services."""
    #    entity_ids = service.data.get(ATTR_ENTITY_ID)
    #    channel = service.data.get(ATTR_SOURCE)
    #    if entity_ids:
    #        devices = [device for device in hass.data[DATA_VIRGINTIVO].values()
    #                   if device.entity_id in entity_ids]

    #    else:
    #        devices = hass.data[DATA_VIRGINTIVO].values()

    #    for device in devices:
    #        if service.service == SERVICE_SETALLTIVOS:
    #            device.set_all_tivos(channel)

    #hass.services.register(DOMAIN, SERVICE_SETALLTIVOS, service_handle,
    #                       schema=VIRGINTIVO_SETALLTIVOS_SCHEMA)


class VirginTivo(MediaPlayerDevice):
    """Representation of a Virgin Tivo box."""

    def __init__(self, host, channels, channels_enabled, hdvers, tivo_id, tivo_name):
        """Initialize new Tivo."""
        self._host = host
        self._channel_id_name = channels
        self._channel_name_id = {v: k for k, v in channels.items()}
        self._channel_name_id_enabled = {v: k for k, v in channels_enabled.items()}
        # ordered list of all channel names
        self._channel_names = sorted(self._channel_name_id_enabled.keys(),
                                    key=lambda v: self._channel_name_id_enabled[v])
        self._hdvers = hdvers
        self._tivo_id = tivo_id
        self._name = tivo_name
        #self._state = STATE_ON
        self._channel = None
        self._sock = None
        self._port = 31339
        self._last_msg = ""

        _LOGGER.debug("Initialising connection to %s",self._host)
        self.connect()

    def update(self):
        """Retrieve latest state."""
        idx = 0
        
        self.connect()
        data = self._last_msg
        if data == "":
            _LOGGER.debug("Not on live TV")
        else:
            currStatus = re.search('(?<=CH_STATUS )\d+', data)
            if currStatus is None:
                currStatus = re.search('(?<=CH_FAILED )\w+', data)
                if currStatus is not None:
                    currStatus = currStatus.group(0)
                    _LOGGER.warning("Failure message is [%s]",currStatus)
                    if currStatus != "NO_LIVE":
                        self.disconnect()
            else:
                currStatus = currStatus.group(0)
                _LOGGER.debug("[%s]: [%s]",self._name, currStatus)
                idx = int(currStatus)

                #self._state = STATE_ON
                if idx in self._channel_id_name:
                    self._channel = self._channel_id_name[idx]
                else:
                    self._channel = None

    def connect(self):
        bufsize=1024
        idx = 0
        try:
            data = self._sock.recv(bufsize).decode()
            _LOGGER.debug("Using existing connection to ", self._name)
            _LOGGER.debug("Data = [%s]", data)
            self._last_msg = data
        except socket.timeout:
            _LOGGER.debug("Using existing connection to ", self._name)
            pass
        except Exception as e:
            try:
                _LOGGER.debug("Connection attempt gave: " + str(e))
                _LOGGER.debug("Connecting to [%s]...", self._host)
                self._sock = socket.socket()
                self._sock.settimeout(1)
                self._sock.connect((self._host, self._port))
                data = self._sock.recv(bufsize).decode()
                _LOGGER.debug("Data = [%s]", data)
                self._last_msg = data
            except Exception:
                raise

    def disconnect(self):
        _LOGGER.debug("Disconnecting from [%s]...", self._host)
        #self._sock.shutdown()
        self._sock.close()

    @property
    def name(self):
        """Return the name of the tivo."""
        return self._name

    #@property
    #def state(self):
    #    """Return the state of the tivo."""
    #    return self._state

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_VIRGINTIVO

    @property
    def media_title(self):
        """Return the current channel as media title."""
        return self._channel

    @property
    def source(self):
        """Return the current input channel of the device."""
        return self._channel

    @property
    def source_list(self):
        """List of available input channels."""
        return self._channel_names

    #def set_all_tivos(self, channel):
    #    """Set all tivos to one channel."""
    #    if channel not in self._channel_name_id:
    #        return
    #    idx = self._channel_name_id[channel]
    #    _LOGGER.debug("Setting all tivos channel to %s", idx)
    #    #self._virgintivo.set_all_tivo_channel(idx)

    def select_source(self, channel):
        """Set input channel."""
        if channel not in self._channel_name_id:
            return
        idx = self._channel_name_id[channel]
        if self._hdvers[idx] != "":
            idx = self._hdvers[idx]
            _LOGGER.debug("Automatically switching to HD channel")
        _LOGGER.debug("Setting %s channel to [%s]", self._name, idx)

        bufsize=1024
        try:
            self.connect()
            tosend = "SETCH " + str(idx) + "\r"
            _LOGGER.debug("Sending request to %s: [%s]", self._name, tosend)
            try:
                self._sock.sendall(tosend.encode())
            except socket.timeout:
                _LOGGER.warning("Connection timed out...")

            #self.disconnect()

            return
        except Exception:
            raise

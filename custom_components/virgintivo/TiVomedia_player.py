"""
Support for generic Tivo boxes

This component provides basic control for Tivo devices.
"""
import logging
import socket
import time
import re

import voluptuous as vol

try:
    from homeassistant.components.media_player import MediaPlayerEntity
except ImportError:
    from homeassistant.components.media_player import MediaPlayerDevice as MediaPlayerEntity

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    DOMAIN, MediaType
)
from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_NAME, CONF_HOST, CONF_PORT, STATE_OFF, STATE_PLAYING, 
    STATE_PAUSED, ATTR_COMMAND, CONF_SCAN_INTERVAL
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_TIVO = (
    MediaPlayerEntityFeature.NEXT_TRACK | 
    MediaPlayerEntityFeature.PREVIOUS_TRACK |
    MediaPlayerEntityFeature.TURN_ON | 
    MediaPlayerEntityFeature.TURN_OFF | 
    MediaPlayerEntityFeature.PLAY | 
    MediaPlayerEntityFeature.PAUSE |
    MediaPlayerEntityFeature.STOP
)

MEDIA_PLAYER_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.comp_entity_ids,
})

DATA_TIVO = 'tivo'
TIVO_PORT = 31339

TIVO_SERVICE_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_COMMAND): cv.string,
})

TIVO_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=TIVO_PORT): cv.port,
    vol.Required(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=TIVO_PORT): cv.port,
    vol.Required(CONF_NAME): cv.string,
})

SERVICE_FIND_REMOTE = DATA_TIVO + '_find_remote'
SERVICE_IRCODE = DATA_TIVO + '_ircode'
SERVICE_KEYBOARD = DATA_TIVO + '_keyboard'
SERVICE_LAST_CHANNEL = DATA_TIVO + '_last_channel'
SERVICE_LIVE_TV = DATA_TIVO + '_live_tv'
SERVICE_SEARCH = DATA_TIVO + '_search'
SERVICE_SUBTITLES_OFF = DATA_TIVO + '_subtitles_off'
SERVICE_SUBTITLES_ON = DATA_TIVO + '_subtitles_on'
SERVICE_TELEPORT = DATA_TIVO + '_teleport'

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Tivo platform."""
    if DATA_TIVO not in hass.data:
        hass.data[DATA_TIVO] = []

    tivo_device = TivoDevice(
        config[CONF_HOST], 
        config[CONF_PORT], 
        config[CONF_NAME]
    )
    hass.data[DATA_TIVO].append(tivo_device)
    add_devices(hass.data[DATA_TIVO], True)

    def service_handle(service):
        """Handle for services."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        command = service.data.get(ATTR_COMMAND)

        if entity_ids:
            tivos = [device for device in hass.data[DATA_TIVO] if device.entity_id in entity_ids]
        else:
            tivos = hass.data[DATA_TIVO]

        for tivo in tivos:
            if service.service == SERVICE_FIND_REMOTE:
                tivo.find_remote()
            elif service.service == SERVICE_IRCODE:
                tivo.ircode(command)
            elif service.service == SERVICE_KEYBOARD:
                tivo.keyboard(command)
            elif service.service == SERVICE_LAST_CHANNEL:
                tivo.last_channel()
            elif service.service == SERVICE_LIVE_TV:
                tivo.live_tv()
            elif service.service == SERVICE_SEARCH:
                tivo.search(command)
            elif service.service == SERVICE_SUBTITLES_OFF:
                tivo.subtitles_off()
            elif service.service == SERVICE_SUBTITLES_ON:
                tivo.subtitles_on()
            elif service.service == SERVICE_TELEPORT:
                tivo.teleport(command)

    hass.services.register(DOMAIN, SERVICE_FIND_REMOTE, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_IRCODE, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_KEYBOARD, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_LAST_CHANNEL, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_LIVE_TV, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_SEARCH, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_SUBTITLES_OFF, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_SUBTITLES_ON, service_handle, schema=TIVO_SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_TELEPORT, service_handle, schema=TIVO_SERVICE_SCHEMA)


class TivoDevice(MediaPlayerEntity): 
    """Representation of a generic Tivo box."""

    def __init__(self, host, port, name): 
        """Initialize the Tivo device."""
        self._host = host
        self._port = port
        self._name = name
        self._state = STATE_OFF
        self._channel_name = None 
        self._last_channel = None 
        self._sock = None
        self._last_msg = ""
        self._paused = False
        self._connected = False
        self._running_command = False
        self._running_update = False

    def connect(self):
        """Connect to the Tivo box."""
        bufsize = 1024
        try:
            if not self._connected:
                _LOGGER.debug("%s: Connecting to socket", self._name)
                self._sock = socket.socket()
                self._sock.settimeout(1)
                self._sock.connect((self._host, self._port))
                _LOGGER.debug("%s: Connected OK", self._name)
                self._connected = True
            _LOGGER.debug("%s: Reading data from socket", self._name)
            data = self._sock.recv(bufsize).decode()
            _LOGGER.debug("%s: Response data [%s]", self._name, data)
            self._last_msg = data
            self._state = STATE_PAUSED if self._paused else STATE_PLAYING
        except socket.timeout:
            _LOGGER.debug("%s: Socket timeout in 'connect'", self._name)
            self._state = STATE_OFF
        except Exception as e:
            try:
                _LOGGER.debug("%s: Connection attempt gave [%s]", self._name, str(e))
                _LOGGER.debug("%s: Connecting to [%s]", self._name, self._host)
                self._sock = socket.socket()
                self._sock.settimeout(1)
                self._sock.connect((self._host, self._port))
                self._connected = True
                data = self._sock.recv(bufsize).decode()
                _LOGGER.debug("%s: Response data [%s]", self._name, data)
                self._last_msg = data
                self._state = STATE_PAUSED if self._paused else STATE_PLAYING
            except (socket.timeout, socket.gaierror, OSError) as e:
                if self._last_msg is not None:
                    _LOGGER.warning("%s: %s, will retry", self._name, str(e))
                    self._last_msg = None
                self.disconnect()
                _LOGGER.debug("%s: General socket error in 'connect'", self._name)

    def disconnect(self):
        """Disconnect from the Tivo box."""
        if self._running_update or self._running_command:
            _LOGGER.debug("%s: Not disconnecting due to update/command running", self._name)
        else:
            if self._sock:
                _LOGGER.debug("%s: Disconnecting from [%s]", self._name, self._host)
                self._sock.close()
            self._connected = False

    def tivo_cmd(self, cmd):
        """Send command to Tivo box."""
        self._running_command = True
        self.connect()
        if self._connected:
            upper_cmd = cmd.upper()
            _LOGGER.debug("%s: Sending request [%s]", self._name, upper_cmd.replace('\r', '\\r'))
            try:
                self._sock.sendall(upper_cmd.encode())
                self._running_command = False
                self.disconnect() 
            except socket.timeout:
                _LOGGER.warning("%s: Connection timed out", self._name)
        else:
            _LOGGER.warning("%s: Cannot send command when not connected", self._name)
        self._running_command = False

    def update(self):
        """Retrieve latest state."""
        if not self._running_update:
            self._running_update = True
            self.connect()
            self._running_update = False
            self.disconnect() 

        data = self._last_msg
        if data is None or data == "":
            _LOGGER.debug("%s: Not on live TV", self._name)
        else:
            new_status = re.search(r'(?<=CH_STATUS )(\d+)', data)
            if new_status is None:
                new_status = re.search(r'(?<=CH_FAILED )(\w+)', data)
                if new_status is not None:
                    new_status = new_status.group(0)
                    _LOGGER.warning("%s: Failure message is [%s]", self._name, new_status)
                    if new_status != "NO_LIVE":
                        self.disconnect()
            else:
                new_status = new_status.group(0)
                # ... (Handle channel status if needed) ...

    # ... (Keep or remove the following methods based on your needs) ...
    def find_remote(self):
        """Find the remote."""
        self.tivo_cmd("IRCODE FIND_REMOTE\r")

    def ircode(self, cmd):
        """Send an IR code."""
        self.tivo_cmd(f"IRCODE {cmd}\r")

    def keyboard(self, cmd):
        """Send a keyboard command."""
        self.tivo_cmd(f"KEYBOARD {cmd}\r")

    def last_channel(self):
        """Go to the last channel."""
        if self._last_channel:
            self.select_source(self._last_channel)

    def live_tv(self):
        """Go to live TV."""
        self.tivo_cmd("IRCODE LIVETV\r")

    def search(self, cmd):
        """Search for content."""
        self.tivo_cmd("TELEPORT SEARCH\r")
        time.sleep(0.5)
        result = ""
        for character in cmd:
            char = character.replace(' ', 'SPACE')
            result += f"KEYBOARD {char}\r"
        result += "KEYBOARD RIGHT\r"
        self.tivo_cmd(result)
        time.sleep(1)
        self.tivo_cmd("KEYBOARD SELECT\r")

    def subtitles_off(self):
        """Turn off subtitles."""
        self.tivo_cmd("IRCODE CC_OFF\r")

    def subtitles_on(self):
        """Turn on subtitles."""
        self.tivo_cmd("IRCODE CC_ON\r")

    def teleport(self, cmd):
        """Teleport to a specific screen."""
        self.tivo_cmd(f"TELEPORT {cmd}\r")

    # ... (Generic media player methods) ...
    def media_previous_track(self):
        """Send previous track command."""
        self.last_channel()

    def media_next_track(self):
        """Send next track command."""
        # ... (Implement if needed) ...

    def media_play(self):
        """Send play command."""
        cmd = "IRCODE PLAY\r"
        self.tivo_cmd(cmd)
        self._state = STATE_PLAYING
        self._paused = False

    def media_pause(self):
        """Send pause command."""
        cmd = "IRCODE PAUSE\r"
        self.tivo_cmd(cmd)
        self._state = STATE_PAUSED
        self._paused = True

    def media_stop(self):
        """Send stop command."""
        cmd = "IRCODE STOP\r"
        self.tivo_cmd(cmd)
        self._state = STATE_PLAYING
        self._paused = False

    def turn_on(self):
        """Turn the media player on."""
        if self._state == STATE_OFF:
            cmd = "IRCODE STANDBY\r"
            self.tivo_cmd(cmd)
            time.sleep(0.5)

    def turn_off(self):
        """Turn the media player off."""
        if self._state in (STATE_PLAYING, STATE_PAUSED):
            cmd = "IRCODE STANDBY\rIRCODE STANDBY\r"
            self.tivo_cmd(cmd)
            self._state = STATE_OFF
            time.sleep(0.5)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def supported_features(self):
        """Flag media commands that are supported."""
        return SUPPORT_TIVO

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MediaType.TVSHOW 

    # ... (Other properties and methods you want to keep) ...

"""
Support for the Virgin Tivo boxes

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/virgintivo
"""
import logging
import socket
import time
import re
import types
import requests
import json
from datetime import datetime, timedelta
import copy

import voluptuous as vol

from homeassistant.components.media_player import (
    DOMAIN, MEDIA_PLAYER_SCHEMA, PLATFORM_SCHEMA, SUPPORT_SELECT_SOURCE,
    MediaPlayerDevice, MEDIA_TYPE_TVSHOW, SUPPORT_NEXT_TRACK, SUPPORT_PREVIOUS_TRACK)
from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_NAME, CONF_HOST, CONF_PORT, STATE_OFF, STATE_ON)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_VIRGINTIVO = SUPPORT_SELECT_SOURCE + SUPPORT_NEXT_TRACK + SUPPORT_PREVIOUS_TRACK

DATA_VIRGINTIVO = 'virgintivo'
TIVO_PORT = 31339
GUIDE_HOST = 'web-api-pepper.horizon.tv'
GUIDE_PATH = 'oesp/api/GB/eng/web/'
GUIDE_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 '
                               'Safari/537.36'}

CONF_TIVOS = 'tivos'                      # list of Tivo boxes
CONF_CHANNELS = 'channels'                # list of channels
CONF_GUIDE = 'guide'                      # guide parameters

CONF_FORCEHD = 'force_hd'                 # switch to HD channel if available
CONF_LOGO = 'logo'                        # Logo for channel
CONF_HDCHANNEL = 'hd_channel'             # HD version of channel
CONF_PLUSONE = 'plus_one'                 # +1 version of channel
CONF_SHOW = 'show'                        # show channel in source list
CONF_TARGET = 'target'                    # hass entity to switch
CONF_SOURCE = 'source'                    # source to switch to
CONF_DEFAULTISSHOW = 'default_is_show'    # show all channels in source list by default
CONF_CACHE_HOURS = 'cache_hours'          # how many hours of guide to load into cache
CONF_PICTURE_REFRESH = 'picture_refresh'  # how long before updating screen capture
CONF_ENABLE_GUIDE = 'enable_guide'        # show guide

TIVO_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_FORCEHD, default=False): cv.boolean,
})

CHANNEL_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_LOGO, default=""): cv.string,
    vol.Optional(CONF_HDCHANNEL, default=None): cv.positive_int,
    vol.Optional(CONF_PLUSONE, default=None): cv.positive_int,
    vol.Optional(CONF_SHOW, default="UNSET"): cv.string,
    vol.Optional(CONF_TARGET, default=""): cv.string,
    vol.Optional(CONF_SOURCE, default=""): cv.string,
})

GUIDE_SCHEMA = vol.Schema({
    vol.Optional(CONF_CACHE_HOURS, default=12): cv.positive_int,
    vol.Optional(CONF_PICTURE_REFRESH, default=60): cv.positive_int,
    vol.Optional(CONF_ENABLE_GUIDE, default=True): cv.boolean,
})

# Valid tivo ids: 1-9
TIVO_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=9))

# Valid channel ids: 1-999
CHANNEL_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=999))

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend({
        vol.Optional(CONF_DEFAULTISSHOW, default=True): cv.boolean,
        vol.Optional(CONF_FORCEHD, default=False): cv.boolean,
        vol.Required(CONF_TIVOS): vol.Schema({TIVO_IDS: TIVO_SCHEMA}),
        vol.Required(CONF_CHANNELS): vol.Schema({CHANNEL_IDS: CHANNEL_SCHEMA}),
        vol.Optional(CONF_GUIDE): vol.Schema(GUIDE_SCHEMA),
    }))


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Virgin Tivo platform."""
    if DATA_VIRGINTIVO not in hass.data:
        hass.data[DATA_VIRGINTIVO] = {}

    show_by_default = config.get(CONF_DEFAULTISSHOW)

    guide = types.SimpleNamespace()
    guide.channels = {}
    guide.listings = {}
    if CONF_GUIDE in config:
        guide.cache_hours = config[CONF_GUIDE][CONF_CACHE_HOURS]
        guide.picture_refresh = config[CONF_GUIDE][CONF_PICTURE_REFRESH]
        guide.enable_guide = config[CONF_GUIDE][CONF_ENABLE_GUIDE]
    else:
        guide.cache_hours = 12
        guide.picture_refresh = 60
        guide.enable_guide = True

    channels = {}
    for channel_id, entry in config[CONF_CHANNELS].items():
        channel_info = {
            CONF_NAME: entry[CONF_NAME],
            CONF_LOGO: entry[CONF_LOGO],
            CONF_HDCHANNEL: entry[CONF_HDCHANNEL],
            CONF_PLUSONE: entry[CONF_PLUSONE],
            CONF_SHOW: (show_by_default or entry[CONF_SHOW] == 'True') and entry[CONF_SHOW] != 'False',
            CONF_TARGET: entry[CONF_TARGET],
            CONF_SOURCE: entry[CONF_SOURCE],
        }
        channels[channel_id] = channel_info

    # _LOGGER.debug("Channel list is [%s]", str(channels))

    devices = []
    for tivo_id, extra in config[CONF_TIVOS].items():
        _LOGGER.info("Adding Tivo %d - %s", tivo_id, extra[CONF_NAME])
        unique_id = "{}-{}".format(extra[CONF_HOST], tivo_id)
        force_hd_on_tv = config.get(CONF_FORCEHD) or extra.get(CONF_FORCEHD)
        _LOGGER.debug("Force HD on TV is %s", str(force_hd_on_tv))
        try:
            device = VirginTivo(extra[CONF_HOST], channels, tivo_id, extra[CONF_NAME], force_hd_on_tv, guide)
            hass.data[DATA_VIRGINTIVO][unique_id] = device
            devices.append(device)
        except socket.gaierror:
            # Will no longer happen
            _LOGGER.warning("Could not find Tivo %d - %s", tivo_id, extra[CONF_NAME])
            pass

    add_devices(devices, True)


class VirginTivo(MediaPlayerDevice):
    """Representation of a Virgin Tivo box."""

    def __init__(self, host, channels, tivo_id, tivo_name,
                 force_hd_on_tv, guide):
        """Initialize new Tivo."""
        self._host = host
        self._channel_id_name = {k: v[CONF_NAME] for k, v in channels.items()}
        self._channel_name_id = {v[CONF_NAME]: k for k, v in channels.items()}
        channel_name_id_enabled = {v[CONF_NAME]: k for k, v in channels.items() if v[CONF_SHOW]}
        self._channel_names = sorted(channel_name_id_enabled.keys(), key=lambda v: channel_name_id_enabled[v])
        self._channels = channels
        self._target_ids = {k: v[CONF_TARGET] for k, v in channels.items() if v[CONF_TARGET] != ""}
        self._sources = {k: v[CONF_SOURCE] for k, v in channels.items() if v[CONF_TARGET] != ""}
        self._tivo_id = tivo_id
        self._name = tivo_name
        self._state = STATE_OFF
        self._channel = None
        self._channel_id = None
        self._sock = None
        self._port = TIVO_PORT
        self._last_msg = ""
        self._force_hd_on_tv = force_hd_on_tv
        self._guide = guide
        self._guide_channel = None
        self._last_screen_grab = 0

        _LOGGER.debug("%s: initialising connection to [%s]", self._name, self._host)
        self.connect()
        if self._guide.enable_guide:
            self.get_guide_channels()

    def get_guide_channels(self):
        """Retrieve list of channels available in guide"""

        try:
            if not self._guide.channels:
                _LOGGER.debug("Retrieving guide channels")
                url = 'https://{0}/{1}/channels'.format(GUIDE_HOST, GUIDE_PATH)
                response = requests.get(url, headers=GUIDE_HEADERS)
                channels_data = json.loads(response.text)
                for channel in channels_data["channels"]:
                    ch_number = channel["channelNumber"]
                    _LOGGER.debug("New channel [%s]", str(ch_number))
                    urls = channel["stationSchedules"][0]["station"]["images"]
                    ch_info = {
                        "channel_number": ch_number,
                        "id": channel["stationSchedules"][0]["station"]["id"],
                        "title": channel["stationSchedules"][0]["station"]["title"],
                        "url": next(iter([a["url"] for a in urls if a["assetType"] == "imageStream"]), None),
                        "logo": next(iter([a["url"] for a in urls if a["assetType"] == "station-logo-large"]), None),
                    }
                    self._guide.channels[ch_number] = ch_info
                    hd_channel = self._channels[ch_number][CONF_HDCHANNEL]
                    plus_one_channel = self._channels[ch_number][CONF_PLUSONE]
                    if hd_channel:
                        self._guide.channels[hd_channel] = copy.deepcopy(ch_info)
                        self._guide.channels[hd_channel]["channel_number"] = hd_channel
                        self._guide.channels[hd_channel]["title"] += " HD"
                        _LOGGER.debug("Copied channel [%d] to HD channel [%d]", ch_number, hd_channel)

                    if plus_one_channel:
                        self._guide.channels[plus_one_channel] = copy.deepcopy(ch_info)
                        self._guide.channels[plus_one_channel]["channel_number"] = plus_one_channel
                        self._guide.channels[plus_one_channel]["title"] += " +1"
                        self._guide.channels[plus_one_channel]["url"] = None
                        _LOGGER.debug("Copied channel [%d] to +1 channel [%d]", ch_number, plus_one_channel)

            else:
                _LOGGER.debug("Guide already populated")

        except Exception as e:
            _LOGGER.debug("Error getting guide channel list [%s]", str(e))
            raise

    def get_guide_listings(self, channel_id):
        """Retrieve list of programs for a channel"""

        sd_channel = self.get_sd_channel(channel_id)
        hd_channel = self._channels[sd_channel][CONF_HDCHANNEL]
        plus_one_channel = self._channels[sd_channel][CONF_PLUSONE]

        try:
            if sd_channel not in self._guide.listings \
                    or self._guide.listings[sd_channel]["next_refresh"] < datetime.now():
                start_time = int(time.time() - 3600 * 6) * 1000
                end_time = start_time + (3600 * self._guide.picture_refresh * 1000)
                ch_id = self._guide.channels[sd_channel]["id"]
                _LOGGER.debug("%s: retrieving guide for channel %s", self._name, str(ch_id))
                url = "https://{0}/{1}/listings?byStationId={2}&byStartTime={3}~{4}&sort=startTime"\
                    .format(GUIDE_HOST, GUIDE_PATH, ch_id, start_time, end_time)

                prog_channel = {
                    "next_refresh": 0,
                    "listings": [],
                }
                self._guide.listings[sd_channel] = prog_channel

                # _LOGGER.debug("*** url request: [%s]", url);
                response = requests.get(url, headers=GUIDE_HEADERS)
                listings_data = json.loads(response.text)
                # _LOGGER.debug("*** response: [%s]", str(response.text))
                prog_end_time = datetime.now()
                for listing in listings_data["listings"]:
                    prog_start_time = datetime.fromtimestamp(listing["startTime"] / 1000)
                    prog_end_time = datetime.fromtimestamp(listing["endTime"] / 1000)
                    prog_id = listing["stationId"]
                    prog_title = listing["program"]["title"]
                    if "description" in listing["program"]:
                        prog_description = listing["program"]["description"]
                    else:
                        prog_description = listing["program"]["longDescription"]
                    prog_type = listing["program"]["medium"]
                    if "seriesEpisodeNumber" in listing["program"] and "seriesNumber" in listing["program"]:
                        prog_episode_number = listing["program"]["seriesEpisodeNumber"]
                        prog_series_number = listing["program"]["seriesNumber"]
                    else:
                        prog_episode_number = None
                        prog_series_number = None
                    if "secondaryTitle" in listing["program"]:
                        prog_episode_title = listing["program"]["secondaryTitle"]
                    else:
                        prog_episode_title = None

                    prog_info = {
                        "title": prog_title,
                        "description": prog_description,
                        "id": prog_id,
                        "start_time": prog_start_time,
                        "end_time": prog_end_time,
                        "duration": prog_end_time - prog_start_time,
                        "prog_type": prog_type,
                        "prog_episode_title": prog_episode_title,
                        "prog_episode_number": prog_episode_number,
                        "prog_series_number": prog_series_number,
                    }

                    self._guide.listings[sd_channel]["listings"].append(prog_info)
                    self._guide.listings[sd_channel]["next_refresh"] = prog_end_time
                    _LOGGER.debug("Added [%s] to channel [%d]", prog_title, sd_channel)

                if hd_channel:
                    self._guide.listings[hd_channel] = prog_channel
                    _LOGGER.debug("Copied listing [%d] to HD channel [%d]", sd_channel, hd_channel)

                if plus_one_channel:
                    self._guide.listings[plus_one_channel] = copy.deepcopy(prog_channel)
                    _LOGGER.debug("Copied listing [%d] to +1 channel [%d]", sd_channel, plus_one_channel)
                    for prog in self._guide.listings[plus_one_channel]["listings"]:
                        prog["start_time"] += timedelta(hours=1)
                        prog["end_time"] += timedelta(hours=1)
                    _LOGGER.debug("Updated times for +1 channel [%d]", plus_one_channel)

                _LOGGER.debug("Next refresh for channel [%d]: %s", sd_channel, prog_end_time.strftime('%Y-%m-%d %H:%M'))

        except Exception as e:
            _LOGGER.debug("Error getting listings [%s]", str(e))

    def get_current_prog(self):
        """Determine currently running program"""

        if self._guide_channel:
            channel_id = self._guide_channel["channel_number"]
            if channel_id in self._guide.listings:
                current_datetime = datetime.now()
                for listing in self._guide.listings[channel_id]["listings"]:
                    if listing["start_time"] <= current_datetime < listing["end_time"]:
                        return listing

        return None

    def get_sd_channel(self, channel_id):
        """Get the SD version of a given channel"""

        sd_channel = channel_id
        for key, channel in self._channels.items():
            if channel[CONF_HDCHANNEL] == sd_channel:
                sd_channel = key

        for key, channel in self._channels.items():
            if channel[CONF_PLUSONE] == sd_channel:
                sd_channel = key

        return sd_channel

    def is_plus_one_channel(self, channel_id):
        """Check if channel is +1"""

        for key, channel in self._channels.items():
            if channel[CONF_PLUSONE] == channel_id:
                return True

        return False

    def is_hd_channel(self, channel_id):
        """Check if channel is +1"""

        for key, channel in self._channels.items():
            if channel[CONF_HDCHANNEL] == channel_id:
                return True

        return False

    def update(self):
        """Retrieve latest state."""

        self.connect()
        data = self._last_msg
        if data == "":
            _LOGGER.debug("%s: not on live TV", self._name)
        else:
            new_status = re.search('(?<=CH_STATUS )\d+', data)
            if new_status is None:
                new_status = re.search('(?<=CH_FAILED )\w+', data)
                if new_status is not None:
                    new_status = new_status.group(0)
                    _LOGGER.warning("%s: failure message is [%s]", self._name, new_status)
                    if new_status != "NO_LIVE":
                        self.disconnect()
            else:
                new_status = new_status.group(0)
                idx = int(new_status)
                if self._channel is not None and idx != self._channel_name_id[self._channel]:
                    _LOGGER.debug("%s: changing to channel [%s]", self._name, new_status)

                if idx in self._target_ids:
                    _LOGGER.debug("%s: switcher source triggered %s,%s,%s", self._name, str(idx), self._sources[idx],
                                  self._target_ids[idx])
                    state = self.hass.states.get(self._target_ids[idx])
                    if state is not None:
                        service_data = dict([("entity_id", self._target_ids[idx]), ("source", self._sources[idx])])
                        self.hass.services.call('media_player', 'select_source', service_data)
                        if self._channel is not None:
                            _LOGGER.debug("%s: reset channel back to [%d]",
                                          self._name, self._channel_name_id[self._channel])
                            idx = self._channel_name_id[self._channel]
                            self.select_source(self._channel_id_name[idx])

                if self._force_hd_on_tv and self._channels[idx][CONF_HDCHANNEL]:
                    idx = self._channels[idx][CONF_HDCHANNEL]
                    _LOGGER.debug("%s: forcing HD channel [%s]", self._name, idx, self._channel_id_name[idx])
                    self.select_source(self._channel_id_name[idx])

                # self._state = STATE_ON
                if idx in self._channel_id_name:
                    self._channel = self._channel_id_name[idx]
                    self._channel_id = idx
                else:
                    self._channel = None

                if idx in self._guide.channels:
                    _LOGGER.debug("%s: guide found for channel %d (%d)", self._name, idx, idx)
                    self._guide_channel = self._guide.channels[idx]
                else:
                    _LOGGER.debug("%s: no guide found for channel %d", self._name, idx)
                    self._guide_channel = None

        # Check listing each time
        if self._guide_channel is not None:
            self.get_guide_listings(self._guide_channel["channel_number"])

    def connect(self):
        bufsize = 1024
        try:
            data = self._sock.recv(bufsize).decode()
            # _LOGGER.debug("%s: using existing connection", self._name)
            # _LOGGER.debug("%s: response data [%s]", self._name, data)
            self._last_msg = data
            self._state = STATE_ON
        except socket.timeout:
            # _LOGGER.debug("%s: using existing connection", self._name)
            self._state = STATE_ON
            pass
        except Exception as e:
            try:
                _LOGGER.debug("%s: connection attempt gave [%s]", self._name, str(e))
                _LOGGER.debug("%s: connecting to [%s]", self._name, self._host)
                self._sock = socket.socket()
                self._sock.settimeout(1)
                self._sock.connect((self._host, self._port))
                data = self._sock.recv(bufsize).decode()
                _LOGGER.debug("%s: response data [%s]", self._name, data)
                self._last_msg = data
                self._state = STATE_ON
            except socket.timeout:
                _LOGGER.warning("%s: timeout on connection, will retry", self._name)
                self._state = STATE_OFF
                pass
            except socket.gaierror:
                _LOGGER.warning("%s: could not find Tivo, will retry", self._name)
                self._state = STATE_OFF
                pass
            except Exception:
                raise

    def disconnect(self):
        _LOGGER.debug("%s: disconnecting from [%s]", self._name, self._host)
        # self._sock.shutdown()
        self._sock.close()

    @property
    def name(self):
        """Return the name of the tivo."""
        return self._name

    @property
    def state(self):
        """Return the state of the tivo."""
        return self._state

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_VIRGINTIVO

    @property
    def media_content_type(self):
        """Return the content type of current playing media."""
        current_prog = self.get_current_prog()
        if current_prog:
            # MEDIA_TYPE_MOVIE doesn't display as much info
            # return MEDIA_TYPE_MOVIE if current_prog["prog_type"] == "Movie" else MEDIA_TYPE_TVSHOW
            return MEDIA_TYPE_TVSHOW
        else:
            return None
            
    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        # NB: doesn't seem to be functional with TV shows
        current_prog = self.get_current_prog()
        if current_prog:
            return int(current_prog["duration"].total_seconds())
        else:
            return None

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        # NB: doesn't seem to be functional with TV shows
        current_prog = self.get_current_prog()
        if current_prog:
            return int((datetime.now() - current_prog["start_time"]).total_seconds())
        else:
            return None

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        pic_url = None
        if self._channel_id and (self._last_screen_grab + self._guide.picture_refresh) <= time.time():
            if self._guide_channel:
                pic_url = self._guide_channel["url"]
                if not pic_url:
                    pic_url = self._guide_channel["logo"]
                if "?" not in pic_url and "Channel_Logos" not in pic_url:
                    pic_url = pic_url + "?" + str(int(time.time()))
            else:
                if self._channels[self._channel_id][CONF_LOGO] != "":
                    pic_url = self._channels[self._channel_id][CONF_LOGO]

        return pic_url

    @property
    def media_series_title(self):
        """Title of series of current playing media, TV show only."""
        current_prog = self.get_current_prog()
        if current_prog:
            title = current_prog["title"]

            season = current_prog["prog_series_number"]
            if season:
                title += " S " + season + ", Ep " + current_prog["prog_episode_number"]

            episode_title = current_prog["prog_episode_title"]
            if episode_title:
                title += ": " + episode_title

            start_time = current_prog["start_time"].strftime('%H:%M')
            end_time = current_prog["end_time"].strftime('%H:%M')
            display_time = '{0} - {1}'.format(start_time, end_time)

            title += " " + display_time

            return title
        else:
            return None

    @property
    def media_season(self):
        """Season of current playing media, TV show only."""
        # disabled to allow inclusion in media series title
        # current_prog = self.get_current_prog()
        # if current_prog:
        #     return current_prog["prog_series_number"]
        # else:
        #     return None
        return None

    @property
    def media_episode(self):
        """Episode of current playing media, TV show only."""
        # disabled to allow inclusion in media series title
        # current_prog = self.get_current_prog()
        # if current_prog:
        #     return current_prog["prog_episode_number"]
        # else:
        #     return None
        return None

    @property
    def media_title(self):
        """Return the current channel as media title."""
        return self._channel

    def media_previous_track(self):
        """Send previous track command."""

        this_channel = self._channel_id
        plus_one = self._channels[this_channel][CONF_PLUSONE]
        if plus_one:
            self.select_source(self._channels[plus_one][CONF_NAME])
        else:
            for key, channel in self._channels.items():
                if channel[CONF_HDCHANNEL] == this_channel:
                    sd_channel = key
                    plus_one = self._channels[sd_channel][CONF_PLUSONE]
                    if plus_one:
                        self.select_source(self._channels[plus_one][CONF_NAME])

    def media_next_track(self):
        """Send next track command."""

        if self.is_plus_one_channel(self._channel_id):
            self.select_source(self._channels[self.get_sd_channel(self._channel_id)][CONF_NAME])

    @property
    def source(self):
        """Return the current input channel of the device."""
        return self._channel

    @property
    def source_list(self):
        """List of available input channels."""
        return self._channel_names

    def select_source(self, channel):
        """Set input channel."""
        if channel not in self._channel_name_id:
            return
        idx = self._channel_name_id[channel]
        if self._channels[idx][CONF_HDCHANNEL]:
            idx = self._channels[idx][CONF_HDCHANNEL]
            _LOGGER.debug("%s: automatically switching to HD channel", self._name)
        _LOGGER.debug("%s: setting channel to [%d]", self._name, idx)

        try:
            self.connect()
            cmd = "SETCH " + str(idx) + "\r"
            _LOGGER.debug("%s: sending request [%s]", self._name, cmd)
            try:
                self._sock.sendall(cmd.encode())
            except socket.timeout:
                _LOGGER.warning("%s: connection timed out", self._name)

            return
        except Exception:
            raise

"""
Denon Heos notification service.
"""
import asyncio
import logging

import voluptuous as vol

import aioheos
import homeassistant.helpers.config_validation as cv
from homeassistant.components.media_player import (  # pylint: disable=no-name-in-module
    PLATFORM_SCHEMA, MEDIA_TYPE_MUSIC,
    SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP,
    SUPPORT_STOP, SUPPORT_PAUSE, SUPPORT_PLAY_MEDIA, SUPPORT_SELECT_SOURCE,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_NEXT_TRACK, SUPPORT_SEEK,
    SUPPORT_PLAY, MediaPlayerDevice)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD, STATE_PAUSED, STATE_PLAYING, STATE_UNKNOWN)

REQUIREMENTS = ['https://github.com/jarlebh/aioheos/archive/0.3.0.zip#aioheos==0.3.0']

# REQUIREMENTS= ['aioheos==0.3.0']

DEFAULT_NAME = 'HEOS Player'

SUPPORT_HEOS = SUPPORT_PLAY | SUPPORT_STOP | SUPPORT_PAUSE | SUPPORT_PLAY_MEDIA | \
               SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | SUPPORT_SELECT_SOURCE | \
               SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_STEP | SUPPORT_SEEK

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string
})

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discover_info=None):
    # pylint: disable=unused-argument
    """Setup the HEOS platform."""

    host = config.get(CONF_HOST)
    user = config.get(CONF_USERNAME)
    pwd = config.get(CONF_PASSWORD)

    hass.loop.set_debug(True)
    heos_controller = aioheos.AioHeosController(hass.loop, host, user, pwd,
                                                verbose=True)
    yield from heos_controller.connect(
        host=host,
        callback=None
    )
    media_players = []
    for player in heos_controller.get_players():
        media_players.append(HeosMediaPlayer(hass, player))

    for group in heos_controller.get_groups():
        media_players.append(HeosGroup(hass, group))

    async_add_devices(media_players)

    for player in media_players:
        hass.async_create_task(player.async_updater())

    heos_controller.new_device_callback = lambda new_device: async_add_devices([new_device])


class HeosMediaPlayer(MediaPlayerDevice):
    """ The media player ."""

    # pylint: disable=abstract-method
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, hass, heos_player):
        """Initialize"""
        self._hass = hass
        self.heos_player = heos_player
        self.heos_player.state_change_callback = self.async_schedule_update_ha_state
        print("HEOS __init__:{}".format(self.heos_player.name))
        self._name = heos_player.name
        self._unique_id = "player-{}".format(heos_player.player_id)
        self._state = None

    @asyncio.coroutine
    def async_update(self):
        """Retrieve latest state."""
        print("HEOS async_update player:{}".format(self.heos_player.name))
        self.heos_player.request_update()
        return True

    @asyncio.coroutine
    async def async_updater(self):
        """Retrieve latest state."""
        print("HEOS async_updater player:{}".format(self.heos_player.name))
        await self._hass.async_add_executor_job(self.heos_player.request_update)
        return True

    @property
    def unique_id(self):
        """Return the HEOS Id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def volume_level(self):
        """Volume level of the device (0..1)."""
        volume = self.heos_player.volume
        return float(volume) / 100.0

    @property
    def state(self):
        if self.heos_player:
            self._state = self.heos_player.play_state
        if self._state == 'stop':
            return STATE_PAUSED
        elif self._state == 'pause':
            return STATE_PAUSED
        elif self._state == 'play':
            return STATE_PLAYING
        else:
            return STATE_UNKNOWN

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_artist(self):
        """Artist of current playing media."""
        return self.heos_player.media_artist

    @property
    def media_title(self):
        """Album name of current playing media."""
        return self.heos_player.media_title

    @property
    def media_album_name(self):
        """Album name of current playing media."""
        return self.heos_player.media_album

    @property
    def media_image_url(self):
        """Return the image url of current playing media."""
        return self.heos_player.media_image_url

    @property
    def media_content_id(self):
        """Return the content ID of current playing media."""
        return self.heos_player.media_id

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        muted_state = self.heos_player.mute
        return muted_state == 'on'

    @asyncio.coroutine
    def async_mute_volume(self, mute):  # pylint: disable=unused-argument
        """Mute volume"""
        self.heos_player.toggle_mute()

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        return self.heos_player.duration / 1000.0

    @property
    def media_position_updated_at(self):
        return self.heos_player.current_position_updated_at

    @property
    def media_position(self):
        return self.heos_player.current_position / 1000.0

    @property
    def available(self):
        """Return True if entity is available."""
        return self.heos_player.online

    @asyncio.coroutine
    def async_media_next_track(self):
        """Go TO next track."""
        self.heos_player.play_next()

    @asyncio.coroutine
    def async_media_previous_track(self):
        """Go TO previous track."""
        self.heos_player.play_prev()

    @asyncio.coroutine
    def async_media_seek(self, position):
        # pylint: disable=no-self-use
        """Seek to posistion."""
        print('MEDIA SEEK', position)

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        return SUPPORT_HEOS

    @asyncio.coroutine
    def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self.heos_player.set_volume(volume * 100)

    @asyncio.coroutine
    def async_media_play(self):
        """Play media player."""
        self.heos_player.play()

    @asyncio.coroutine
    def async_media_stop(self):
        """Stop media player."""
        self.heos_player.stop()

    @asyncio.coroutine
    def async_media_pause(self):
        """Pause media player."""
        self.heos_player.pause()

    @asyncio.coroutine
    def async_media_play_pause(self):
        """Play or pause the media player."""
        if self._state == 'play':
            yield from self.async_media_pause()
        else:
            yield from self.async_media_play()

    @property
    def source(self):
        """Name of the current input source."""
        return self.heos_player.source_name

    @property
    def source_list(self):
        """List of available input sources."""
        return self.heos_player.source_list()

    @asyncio.coroutine
    def async_select_source(self, source):
        """Select the playlist."""
        if source.startswith("Favorites__"):
            for fav in self.heos_player.favourites_list():
                if fav['name'] == source.split("Favorites__",1)[1]:
                    self.heos_player.play_favorite(fav['mid'])
        else:
            for source in self.heos_player.get_music_sources():
                if source['name'] == source.split("Favorites__",1)[1]:
                    self.heos_player.play_favorite(source['sid'])

class HeosGroup(HeosMediaPlayer):
    def __init__(self, hass, heos_group):
        """Initialize"""
        super().__init__(hass, heos_group)
        self._unique_id = "group-{}".format(heos_group.player_id)
        self._name = "Group {}".format(heos_group.name)

    @property
    def unique_id(self):
        """Return the HEOS Group Id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the group."""
        return self._name

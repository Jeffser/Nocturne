# player.py

from gi.repository import Adw, GLib, GObject, Gst, Gio

from mpris_server.adapters import MprisAdapter
from mpris_server.events import EventAdapter
from mpris_server.server import Server
from mpris_server import Metadata, ValidMetadata, Track, Position, Volume, Rate, PlayState, DbusObj, MetadataObj, ActivePlaylist, PlaylistEntry, MprisInterface

from ...integrations import get_current_integration
from ...integrations.discord_rpc import DiscordRPC
from urllib.parse import urlparse
import threading, io, base64, logging, gc
from PIL import Image, ImageFilter
from colorthief import ColorThief

logger = logging.getLogger(__name__)

Gst.init(None)

class PlayerAdapter(MprisAdapter):
    # Implementations from https://github.com/alexdelorenzo/mpris_server/blob/master/src/mpris_server/adapters.py

    def __init__(self, player):
        self.player = player
        self.last_cover_art = {'id': '', 'url': ''}
        super().__init__()

    # -- RootAdapter --

    def get_desktop_entry(self) -> str:
        return "com.jeffser.Nocturne"

    def can_fullscreen(self) -> bool:
        return False

    def can_quit(self) -> bool:
        return True

    def can_raise(self) -> bool:
        return True

    def has_tracklist(self) -> bool:
        return False

    def quit(self):
        integration = get_current_integration()
        if integration:
            integration.loaded_models.get('currentSong').set_property('songId', None)

    def set_fullscreen(self, value:bool):
        # def can_fullscreen returns false
        pass

    def set_raise(self, value:bool):
        # TODO idk maybe raise the window and open the sheet?
        pass

    # -- PlayerAdapter --

    def metadata(self) -> ValidMetadata:
        integration = get_current_integration()
        if not integration:
            return MetadataObj()
        current_song_model = integration.loaded_models.get('currentSong')
        song = integration.loaded_models.get(current_song_model.get_property('songId'))
        if not song:
            return MetadataObj()

        if self.last_cover_art.get('id') != song.get_property('id'):
            self.last_cover_art['id'] = song.get_property('id')
            self.last_cover_art['url'] = integration.getCoverArtUrl(song.get_property('id'))

        if song.get_property('radioStreamUrl'):
            if not (title := current_song_model.get_property("displaySongTitle")):
                title = song.get_property('title')
            if not (artist := current_song_model.get_property("displaySongArtist")):
                artist = song.get_property('title') #sets station name to artist if the song has a title
            if artist == title: #fall back to stream URL for artist so MPRIS widgets don't show duplicate labels
                artist = urlparse(song.get_property('radioStreamUrl')).netloc
            artists = [artist]
            album = song.get_property('title')
        else:
            album = song.get_property('album')
            artists = ([a.get('name') for a in song.get_property('artists')] or [song.get_property('artist')])
            title = song.get_property('title')

        return MetadataObj(
            album=album,
            art_url=self.last_cover_art.get('url'),
            artists=artists,
            as_text=[song.get_property('title')],
            length=song.get_property('duration')*1000000,
            title=title,
            track_id='/com/jeffser/Nocturne/track/{}'.format(song.get_property('id')),
            track_number=0
        )

    def can_control(self) -> bool:
        return True

    def can_go_next(self) -> bool:
        return True

    def can_go_previous(self) -> bool:
        return True

    def can_pause(self) -> bool:
        return True

    def can_play(self) -> bool:
        return True

    def can_seek(self) -> bool:
        return True

    def get_current_position(self) -> Position:
        # Unused
        # Microseconds
        success, position = self.player.gst.query_position(Gst.Format.TIME)
        return Position(position/1000) # Microsecond

    def get_rate(self) -> Rate:
        return Rate(1)

    def get_maximum_rate(self) -> Rate:
        return Rate(1)

    def get_minimum_rate(self) -> Rate:
        return Rate(1)

    def get_next_track(self) -> Track:
        pass

    def get_playstate(self) -> PlayState:
        success, state, pending = self.player.gst.get_state(0)
        return PlayState.PLAYING if state == Gst.State.PLAYING else PlayState.PAUSED

    def get_previous_track(self) -> Track:
        pass

    def get_shuffle(self) -> bool:
        # Shuffle isn't a thing in Nocturne the queue is what it is for the most part
        return False

    def get_volume(self) -> Volume:
        return Volume(self.player.gst.get_property("volume"))

    def is_mute(self) -> bool:
        return self.player.gst.get_property("volume") == 0

    def is_playlist(self) -> bool:
        # Again, the queue is what it is, I'm not sure if I can get this info
        return False

    def is_repeating(self) -> bool:
        return self.player.settings.get_value('playback-mode').unpack() == 'repeat-one'

    def next(self):
        self.player.handle_song_change_request("next")

    def open_uri(self, uri:str):
        # ?
        pass

    def pause(self):
        self.player.gst.set_state(Gst.State.PAUSED)

    def play(self):
        self.player.gst.set_state(Gst.State.PLAYING)

    def previous(self):
        self.player.handle_song_change_request("previous")

    def resume(self):
        self.player.gst.set_state(Gst.State.PLAYING)

    def seek(self, time:Position, track_id: DbusObj | None = None):
        self.player.gst.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            time*1000
        )
        self.player.emit_changes(self.player.mpris.player, changes=['Position'])

    def set_maximum_rate(self, value:Rate):
        # Idk
        pass

    def set_minimum_rate(self, value:Rate):
        # Idk
        pass

    def set_mute(self, value:bool):
        # TODO I'm not sure what to do when unmuting, should I save previous volume?
        pass

    def set_rate(self, value:Rate):
        # Idk
        pass

    def set_repeating(self, value:bool):
        self.player.settings.set_string('playback-mode', 'repeat-one' if value else 'consecutive')

    def set_shuffle(self, value:bool):
        # TODO not sure how I could implement this
        pass

    def set_volume(self, value:Volume):
        self.player.settings.set_double('volume', value)

    def stop(self):
        self.player.gst.set_state(Gst.State.NULL)

    def activate_playlist(self, id:DbusObj):
        pass

    def get_active_playlist(self) -> ActivePlaylist:
        #TODO
        pass

    def get_playlists(self, index:int, max_count:int, order:str, reverse:bool) -> list[PlaylistEntry]:
        #TODO
        return []

    def add_track(self, uri:str, after_track:DbusObj, set_as_current:bool):
        pass

    def can_edit_tracks(self) -> bool:
        return False

    def get_tracks(self) -> list[DbusObj]:
        return []

    def get_tracks_metadata(self, track_ids:list[DbusObj]) -> list[Metadata]:
        return []

    def go_to(self, track_id:DbusObj):
        pass

    def remove_track(self, track_id:DbusObj):
        pass

class Player(EventAdapter):
    __gtype_name__ = 'NocturnePlayer'

    def __init__(self, application):
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.set_double("volume", self.settings.get_value("volume").unpack())
        self.application = application
        self.gst = Gst.ElementFactory.make("playbin", "music-player")
        self.gst.connect("source-setup", self.on_source_setup)
        try:
            self.gst.set_property("video-sink", Gst.ElementFactory.make("gtk4paintablesink", "video-sink"))
        except:
            logger.warning("Video dependency not found")
        self.gst.connect("video-changed", self.video_changed)

        self.bin = Gst.Bin.new("audio-filter-bin")

        # Equalizer
        self.equalizer = Gst.ElementFactory.make("equalizer-nbands", "equalizer")
        self.bin.add(self.equalizer)
        self.equalizer.set_property("num-bands", 6)
        for i in range(self.equalizer.get_property("num-bands")):
            band = self.equalizer.get_child_by_index(i)
            self.settings.bind(
                "eq-band-{}".format(i),
                band,
                "gain",
                Gio.SettingsBindFlags.DEFAULT
            )

        # ReplayGain
        self.rg_volume = Gst.ElementFactory.make("rgvolume", "replaygain")
        self.rg_limiter = Gst.ElementFactory.make("rglimiter", "limiter")
        self.bin.add(self.rg_volume)
        self.bin.add(self.rg_limiter)
        self.rg_volume.set_property("album-mode", True)

        # Spectrum
        self.spectrum = Gst.ElementFactory.make("spectrum", "spectrum-analyzer")
        self.bin.add(self.spectrum)
        self.settings.bind(
            "visualizer-bar-n",
            self.spectrum,
            "bands",
            Gio.SettingsBindFlags.DEFAULT
        )
        self.spectrum.set_property("threshold", -60)
        self.spectrum.set_property("post-messages", True)
        self.spectrum.set_property("message-magnitude", True)
        self.spectrum.set_property("multi-channel", True)
        self.spectrum.set_property("interval", 50000000)

        # Links
        self.equalizer.link(self.rg_volume)
        self.rg_volume.link(self.rg_limiter)
        self.rg_limiter.link(self.spectrum)

        sink_pad = Gst.GhostPad.new("sink", self.equalizer.get_static_pad("sink"))
        src_pad = Gst.GhostPad.new("src", self.spectrum.get_static_pad("src"))
        self.bin.add_pad(sink_pad)
        self.bin.add_pad(src_pad)
        self.gst.set_property("audio-filter", self.bin)
        self.gst.set_property("buffer-duration", 5 * Gst.SECOND)
        self.gst.set_property("buffer-size", 10 * 1024 * 1024) # 10MB I think

        self.updating_volume = False
        self.settings.connect("changed::volume", self.settings_volume_changed)
        self.gst.connect("notify::volume", self.gst_volume_changed)

        self.bus = self.gst.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", lambda bus, msg: self.handle_song_change_request("end") if msg.src == self.gst else None)
        self.bus.connect("message::error", lambda bus, msg: logger.error(msg.parse_error()[0]))
        self.bus.connect("message::state-changed", self.handle_message_state_changed)
        self.bus.connect("message::tag", self.handle_message_tag)
        self.bus.connect("message::element", self.handle_message_element)

        self.adapter = PlayerAdapter(self)
        self.mpris = Server("com.jeffser.Nocturne", adapter=self.adapter)
        super().__init__(root=self.mpris.root, player=self.mpris.player)
        self.interface = MprisInterface("Nocturne", self.adapter)
        self.mpris_published = False
        try:
            self.mpris.publish()
            self.mpris_published = True
        except Exception as e:
            print("Failed to publish MPRIS:", e)
        GLib.timeout_add(64, self.update_stream_progress)

        self.last_song = ''
        self.pause_next_change = False
        self.last_gst_state_type = -1
        self.discord_rpc = DiscordRPC(self)
        self.settings.connect('changed::discord-rpc-enabled', lambda *_: self.discord_rpc.update())
        self.settings.connect('changed::discord-rpc-client-id', lambda *_: self.discord_rpc.update())
        integration = get_current_integration()
        # Connect to Current Song
        connections = {
            'title': self.update_title,
            'radioStreamUrl': self.update_radioStreamUrl,
            'artists': self.update_artists,
            'trackGain': self.update_trackGain,
            'albumGain': self.update_albumGain,
            'gdkPaintable': lambda paintable: threading.Thread(target=self.update_palette, args=(paintable,), daemon=True).start()
        }
        for parameter, callback in connections.items():
            integration.connect_to_current_song(parameter, callback)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'songId', lambda *_: self.discord_rpc.update())
        integration.connect_to_model('currentSong', 'displaySongTitle', lambda *_: self.discord_rpc.update())
        integration.connect_to_model('currentSong', 'displaySongArtist', lambda *_: self.discord_rpc.update())

    def settings_volume_changed(self, settings, key):
        if not self.updating_volume:
            self.updating_volume = True
            try:
                value = settings.get_value(key).unpack() ** 3
                self.gst.set_property('volume', value)
            finally:
                self.updating_volume = False

    def gst_volume_changed(self, gst, gp):
        if not self.updating_volume:
            self.updating_volume = True
            try:
                value = gst.get_property('volume')
                value = value ** (1/3) if value > 0 else 0.0
                self.settings.set_double('volume', value)
            finally:
                self.updating_volume = False

    def on_source_setup(self, playbin, source):
        try:
            if GObject.type_is_a(source, Gst.ElementFactory.find("souphttpsrc").get_element_type()):
                if integration := get_current_integration():
                    source.set_property("ssl-strict", not integration.get_property('trustServer'))
        except:
            pass

    def video_changed(self, playbin):
        integration = get_current_integration()
        if playbin.get_property('n-video') or 0 > 0:
            songId = integration.loaded_models.get('currentSong').get_property('songId')
            integration.loaded_models.get('currentSong').set_property('videoId', songId)
        else:
            integration.loaded_models.get('currentSong').set_property('videoId', "")

    # ---

    def handle_song_change_request(self, action:str):
        # action can be next, previous or end (song ended)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId

        if current_song_id:
            position = integration.loaded_models.get('currentSong').get_property('positionSeconds')
            song = integration.loaded_models.get(current_song_id)
            duration = song.get_property('duration') if song else 0

            if action == "end" or (duration > 0 and position >= (duration / 2)):
                threading.Thread(target=integration.scrobble, args=(current_song_id,), daemon=True).start()

        mode = self.settings.get_value('playback-mode').unpack()

        if action != "end" and mode == "repeat-one":
            mode = "consecutive"

        if action == "previous" and integration.loaded_models.get('currentSong').get_property('positionSeconds') > 5:
            self.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                0
            )
            return

        id_list = [so.get_string() for so in integration.loaded_models.get('currentSong').get_property('queueModel')]

        integration.loaded_models.get('currentSong').set_property('magnitudes', {})
        if len(id_list) > 0:
            if not current_song_id: # fallback in case nothing was playing
                integration.loaded_models.get('currentSong').set_property('songId', id_list[0])

            elif mode in ('consecutive', 'repeat-all'):
                try:
                    next_index = id_list.index(current_song_id) + (1 if action in ("next", "end") else -1)
                except ValueError: # index was not found
                    next_index = 0

                if mode == 'consecutive':
                    if next_index < 0:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[0])
                    elif next_index < len(id_list):
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[next_index])
                    elif self.settings.get_value('auto-play').unpack():
                        self.auto_play()
                elif mode == 'repeat-all':
                    if next_index < len(id_list) and next_index >= 0:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[next_index])
                    else:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[0])
                        self.gst.seek_simple(
                            Gst.Format.TIME,
                            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                            0
                        )

            elif mode == 'repeat-one':
                self.gst.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    0
                )
        else:
            integration.loaded_models.get('currentSong').set_property('songId', None)

    def auto_play(self):
        if integration := get_current_integration():
            generated_queue = integration.loaded_models.get('currentSong').get_property('generatedQueue')
            if generated_queue.get_property('n-items') == 0:
                self.application.get_active_window().activate_action(
                    "app.generate_auto_play_queue",
                    GLib.Variant('b', True)
                )
            else:
                self.application.get_active_window().activate_action(
                    "app.play_songs",
                    GLib.Variant("as", [so.get_string() for so in list(generated_queue)])
                )

    def handle_spectrum(self, struct):
        serialized = struct.serialize_full(Gst.SerializeFlags.NONE)
        channels_str = serialized.split('< < ')[1].split(' > >;')[0].replace('(float)', '').split(' >, < ')
        channels = []
        for c in channels_str:
            channels.append([float(m.strip()) for m in c.split(', ')[:int(self.spectrum.get_property('bands')/2)]])
        integration = get_current_integration()
        timestamp = struct.get_uint64('stream-time')[1] / 1000000000
        magnitudes = [(60-abs(m)) / 60 * self.settings.get_value("volume").unpack() for m in channels[0] + list(reversed(channels[1]))]
        if timestamp and magnitudes:
            if not integration.loaded_models.get('currentSong').get_property('magnitudes'):
                integration.loaded_models.get('currentSong').set_property('magnitudes', {})
            integration.loaded_models.get('currentSong').magnitudes[timestamp] = magnitudes

    def handle_message_element(self, bus, message):
        if message.src == self.spectrum:
            struct = message.get_structure()
            if struct and struct.get_name() == "spectrum" and self.settings.get_value('show-visualizer').unpack():
                threading.Thread(target=self.handle_spectrum, args=(struct,), daemon=True).start()

    def handle_message_state_changed(self, bus, message):
        if message.src == self.gst:
            old_state, new_state, pending_state = message.parse_state_changed()
            if pending_state == Gst.State.VOID_PENDING and new_state != Gst.State.READY:
                integration = get_current_integration()
                if not integration.loaded_models.get('currentSong').get_property('seeking'):
                    is_playing = new_state == Gst.State.PLAYING
                    integration.loaded_models.get("currentSong").set_property("buttonState", 'pause' if is_playing else 'play')
                    self.emit_changes(self.mpris.player, changes=['Metadata', 'PlaybackStatus'])
                    self.discord_rpc.update()

    def handle_message_tag(self, bus, message):
        integration = get_current_integration()
        if model := integration.loaded_models.get('currentSong'):
            if song_model := integration.loaded_models.get(model.get_property('songId')):
                if song_model.get_property('radioStreamUrl'): # is radio
                    if tag_list := message.parse_tag():
                        success_title, title = tag_list.get_string(Gst.TAG_TITLE)
                        if not (success_title and title and title != 'null'):
                            title = ""
                        success_artist, artist = tag_list.get_string(Gst.TAG_ARTIST)
                        if not(success_artist and artist and artist != 'null'):
                            artist = ""
                        if title and not artist: #Handle Shoutcast metadata
                            parts = title.split(" - ", 1)
                            if len(parts) == 2:
                                artist = parts[0]
                                title = parts[1]
                        title = title.strip()
                        artist = artist.strip()
                        emit_changes = False
                        current_title = model.get_property('displaySongTitle')
                        if title and current_title != title:
                            model.set_property('displaySongTitle', title)
                            emit_changes = True
                        current_artist = model.get_property('displaySongArtist')
                        if artist and current_artist != artist:
                            model.set_property('displaySongArtist', artist)
                            emit_changes = True

                        if emit_changes:
                            self.emit_changes(self.mpris.player, changes=['Metadata', 'PlaybackStatus'])

    def update_stream_progress(self):
        if integration := get_current_integration():
            if integration.loaded_models.get('currentSong').get_property('seeking'):
                return True
            success, position = self.gst.query_position(Gst.Format.TIME)
            current_song = integration.loaded_models.get('currentSong')
            if success:
                seconds = position / Gst.SECOND
                current_song.set_property('positionSeconds', seconds)
        return True


    def restore_play_queue(self):
        integration = get_current_integration()
        songs = self.application.external_songs
        if songs:
            for song in songs:
                integration.loaded_models[song.id] = song
            song_list = [s.id for s in songs]
            current_id = song_list[0]
        else:
            current_id, song_list = integration.getPlayQueue()
            for song in song_list:
                integration.verifySong(song)
        if len(song_list) > 0:
            if len(self.application.external_songs) == 0:
               self.pause_next_change = True
            self.application.get_active_window().activate_action(
                "app.play_songs",
                GLib.Variant("as", song_list)
            )
        self.application.external_songs = []

    def update_palette(self, paintable):
        # Load Image
        if not paintable:
            return
        raw_bytes = paintable.save_to_png_bytes().get_data()
        if not raw_bytes:
            return
        img_io = io.BytesIO(raw_bytes)

        # Generate Palette
        palette = ColorThief(img_io).get_palette(quality=10, color_count=2)

        # Blur Image
        with Image.open(img_io) as img:
            small_img = img.resize((24, 24))
            blurred_img = small_img.filter(ImageFilter.GaussianBlur(radius=2))
            if blurred_img.mode != "RGBA":
                blurred_img = blurred_img.convert("RGBA")
            blurred_img.putalpha(int(255 * 0.3))
            buffer = io.BytesIO()
            blurred_img.save(buffer, format="PNG")
            blur_str = "data:image/png;base64,{}".format(base64.b64encode(buffer.getvalue()).decode("utf-8"))

        # Make and Load CSS
        css = f"""
        window.dynamic-accent {{
            --accent-color: oklab(from rgb({','.join([str(c) for c in palette[0]])}) var(--standalone-color-oklab));
        }}

        window.popout-window.dynamic-bg-blur,
        window.dynamic-bg-blur bottom-sheet#main-bottom-sheet sheet > stack,
        window.dynamic-bg-blur:not(.global-dynamic-bg-gradient):not(.global-dynamic-bg-blur) overlay-split-view .main_sidebar,
        window.global-dynamic-bg-blur {{
            background-image: url("{blur_str}");
        }}

        window.popout-window.dynamic-bg-gradient,
        window.dynamic-bg-gradient bottom-sheet#main-bottom-sheet sheet > stack,
        window.dynamic-bg-gradient:not(.global-dynamic-bg-gradient):not(.global-dynamic-bg-blur) overlay-split-view .main_sidebar,
        window.global-dynamic-bg-gradient {{
            background-image: linear-gradient(
                to bottom,
                rgba({','.join([str(c) for c in palette[0]])},0.4),
                rgba({','.join([str(c) for c in palette[1]])},0.4)
            );
        }}
        """

        self.application.css_provider.load_from_string(css)
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('accentColor', palette[0])

    def update_title(self, title:str):
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('displaySongTitle', title)

    def update_radioStreamUrl(self, radioStreamUrl:str):
        pass #Maybe add the radio stream URL to the currentSong or something?

    def update_artists(self, artists:list):
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('displaySongArtist', artists[0].get('name') if len(artists) > 0 else '')

    def update_trackGain(self, trackGain:float):
        if self.settings.get_value('use-gain').unpack():
            self.rg_volume.set_property('fallback-gain', trackGain)
            self.rg_volume.set_property('album-mode', False)

    def update_albumGain(self, albumGain:float):
        if self.settings.get_value('use-gain').unpack() and self.rg_volume.get_property('fallback-gain') == 0.0:
            self.rg_volume.set_property('fallback-gain', albumGain)
            self.rg_volume.set_property('album-mode', True)

    def song_changed(self, song_id:str):
        integration = get_current_integration()

        if song_id:
            if song_id != self.last_song:
                self.last_song = song_id
                threading.Thread(target=integration.scrobble, args=(song_id,), kwargs={'submission': False}, daemon=True).start()

                # Volume warning
                if self.gst.get_property('volume') == 0:
                    if active_window := self.application.props.active_window:
                        active_window.toast_overlay.add_toast(Adw.Toast(
                            title=_("Warning: Song changed but volume is set to 0")
                        ))

                if stream_url := integration.get_stream_url(song_id):
                    self.gst.set_state(Gst.State.READY)
                    self.gst.set_property('uri', stream_url)
                    if self.pause_next_change:
                        self.gst.set_state(Gst.State.PAUSED)
                        self.pause_next_change = False
                    else:
                        self.gst.set_state(Gst.State.PLAYING)

                    # Fix duration
                    if model := integration.loaded_models.get(song_id):
                        if not model.get_property('duration'):
                            self.gst.get_state(Gst.CLOCK_TIME_NONE)
                            success, duration = self.gst.query_duration(Gst.Format.TIME)
                            if success:
                                model.set_property('duration', duration / Gst.SECOND)
                else:
                    self.gst.set_state(Gst.State.NULL)
        else:
            self.gst.set_state(Gst.State.NULL)
        gc.collect()

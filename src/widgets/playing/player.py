# player.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst, Gio

from mpris_server.adapters import MprisAdapter
from mpris_server.events import EventAdapter
from mpris_server.server import Server
from mpris_server import Metadata, ValidMetadata, Track, Position, Volume, Rate, PlayState, DbusObj, MetadataObj, ActivePlaylist, PlaylistEntry, MprisInterface

from ...constants import MPRIS_COVER_PATH
from ...integrations import get_current_integration
from ..lyrics import LyricsDialog
from urllib.parse import urlparse
import threading, os

Gst.init(None)

class PlayerAdapter(MprisAdapter):
    # Implementations from https://github.com/alexdelorenzo/mpris_server/blob/master/src/mpris_server/adapters.py

    def __init__(self, player):
        self.player = player
        super().__init__()

    # -- RootAdapter --

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

        return MetadataObj(
            album=song.get_property('album'),
            art_url='file://{}'.format(MPRIS_COVER_PATH),
            artists=[urlparse(song.get_property('streamUrl')).netloc.capitalize()] if song.get_property('isRadio') and song.get_property('streamUrl') else [a.get('name') for a in song.get_property('artists')],
            as_text=[song.get_property('title')],
            length=song.get_property('duration')*1000000,
            title=self.player.control_page.title_el.get_label() if song.get_property('isRadio') else song.get_property('title'), # So it uses dynamic radio titles
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
        button_state = self.player.control_page.state_stack_el.get_visible_child_name()
        return PlayState.PLAYING if button_state == 'pause' else PlayState.PAUSED
        pass

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
        integration = get_current_integration()
        if integration:
            return integration.loaded_models.get('currentSong').get_property('playbackMode') == 'repeat-one'
        return False

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
        integration = get_current_integration()
        if integration:
            integration.loaded_models.get('currentSong').set_property('playbackMode', "repeat-one" if value else "consecutive")

    def set_shuffle(self, value:bool):
        # TODO not sure how I could implement this
        pass

    def set_volume(self, value:Volume):
        self.player.control_page.volume_el.set_value(value)

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

    def __init__(self, control_page):
        self.control_page = control_page
        self.gst = Gst.ElementFactory.make("playbin", "music-player")
        self.gst.set_property('volume', 0.25)
        self.bus = self.gst.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)

        self.adapter = PlayerAdapter(self)
        self.mpris = Server("com.jeffser.Nocturne", adapter=self.adapter)
        super().__init__(root=self.mpris.root, player=self.mpris.player)
        self.interface = MprisInterface('com.jeffser.Nocturne', self.adapter)
        self.mpris_published = False
        try:
            self.mpris.publish()
            self.mpris_published = True
        except Exception as e:
            print("Failed to publish MPRIS:", e)
        GLib.timeout_add(500, self.update_stream_progress)

    # ---

    def handle_new_state(self, state):
        if not self.control_page.is_seeking:
            stack_page_name = 'play' if state in (Gst.State.NULL, Gst.State.READY, Gst.State.PAUSED) else 'pause'
            integration = get_current_integration()
            integration.loaded_models.get("currentSong").set_property("buttonState", stack_page_name)
            if root := self.control_page.get_root():
                if stack_page_name == 'pause':
                    root.add_css_class('playing')
                else:
                    root.remove_css_class('playing')
            self.emit_changes(self.mpris.player, changes=['Metadata', 'PlaybackStatus'])

    def set_dynamic_title(self, title:str):
        # called by on_player_message (useful for radios)
        if title == self.control_page.title_el.get_label():
            return
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        model = integration.loaded_models.get(current_song_id)
        if model and model.get_property('isRadio'):
            self.control_page.title_el.set_label(title or model.get_property('title'))
            self.control_page.title_el.set_tooltip_text(title or model.get_property('title'))
            root = self.control_page.get_root()
            if root:
                root.footer.title_el.set_label(title or model.get_property('title'))
            self.emit_changes(self.mpris.player, changes=['Metadata'])

    def handle_song_change_request(self, action:str):
        # action can be next, previous or end (song ended)
        self.gst.set_state(Gst.State.READY)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId

        mode = integration.loaded_models.get('currentSong').get_property('playbackMode')

        if action != "end" and mode == "repeat-one":
            mode = "consecutive"

        if action == "previous" and integration.loaded_models.get('currentSong').get_property('positionSeconds') > 5:
            integration.loaded_models.get('currentSong').set_property('songId', current_song_id)
            return

        id_list = self.control_page.get_root().queue_page.song_list_el.get_all_ids()

        if len(id_list) > 0:
            if not current_song_id: # fallback in case nothing was playing
                integration.loaded_models.get('currentSong').set_property(songId, id_list[0])

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
                    elif Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('auto-play').unpack():
                        threading.Thread(target=self.auto_play).start()
                elif mode == 'repeat-all':
                    if next_index < len(id_list) and next_index >= 0:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[next_index])
                    else:
                        integration.loaded_models.get('currentSong').set_property('songId', id_list[0])

            elif mode == 'repeat-one':
                integration.loaded_models.get('currentSong').set_property('songId', current_song_id)
        else:
            integration.loaded_models.get('currentSong').set_property('songId', None)

    def auto_play(self):
        root = self.control_page.get_root()
        if len(root.queue_page.generated_queue) == 0:
            root.queue_page.generate_auto_play_queue()
        root.queue_page.replace_queue(root.queue_page.generated_queue)

    def on_message(self, bus, message):
        if message.type == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            self.handle_new_state(new_state)
        elif message.type == Gst.MessageType.EOS:
            self.handle_song_change_request("end")
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: {}".format(err.message))
        elif message.type == Gst.MessageType.TAG:
            taglist = message.parse_tag()
            for i in range(taglist.n_tags()):
                name = taglist.nth_tag_name(i)
                value = taglist.get_value_index(name, 0)
                if name == 'title' and value:
                    self.set_dynamic_title(value)

    def update_stream_progress(self):
        if self.control_page.is_seeking:
            return True # don't update if seeking but keep the loop alive
        integration = get_current_integration()
        if integration:
            success, position = self.gst.query_position(Gst.Format.TIME)
            current_song = integration.loaded_models.get('currentSong')
            if success:
                seconds = position / Gst.SECOND
                current_song.set_property('positionSeconds', seconds)
        return True


    def restore_play_queue(self):
        integration = get_current_integration()
        songs = self.control_page.get_root().get_application().external_songs
        if songs:
            for song in songs:
                integration.loaded_models[song.id] = song
            song_list = [s.id for s in songs]
            current_id = song_list[0]
        else:
            current_id, song_list = integration.getPlayQueue()
        if len(song_list) > 0:
            if len(self.control_page.get_root().get_application().external_songs) == 0:
               self.control_page.pause_next_change = True
            self.control_page.get_root().queue_page.replace_queue(song_list, current_id)
        self.control_page.get_root().get_application().external_songs = []


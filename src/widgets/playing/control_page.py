# control_page.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst
from ...navidrome import get_current_integration
import threading, random
from datetime import datetime

Gst.init(None)

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/control_page.ui')
class PlayingControlPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingControlPage'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    album_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    volume_button_el = Gtk.Template.Child()
    volume_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()

    def __init__(self):
        # Used to disconnect star_el when song changes
        self.starred_connection = None
        self.last_song_id = None

        integration = get_current_integration()
        super().__init__()
        integration.connect_to_model('currentSong', 'songId', self.song_changed, use_gtk_thread=False)

        integration.loaded_models.get('currentSong').bind_property(
            "positionSeconds",
            self.progress_el.get_adjustment(),
            "value",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            None,
            None
        )

        self.is_seeking = False
        self.player = Gst.ElementFactory.make("playbin", "music-player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_player_message)
        self.volume_el.set_value(1) ##TODO save volume within sessions

    @Gtk.Template.Callback()
    def view_queue(self, button):
        self.get_ancestor(Adw.NavigationView).push_by_tag('queue')

    @Gtk.Template.Callback()
    def seek_start(self, gesture, n_press, x, y):
        self.is_seeking = True

    @Gtk.Template.Callback()
    def seek_end(self, gesture):
        self.is_seeking = False

    @Gtk.Template.Callback()
    def progress_bar_changed(self, adjustment):
        if self.is_seeking:
            nanoseconds = int(adjustment.get_value() * Gst.SECOND)
            self.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.player.set_state(Gst.State.PLAYING)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.player.set_state(Gst.State.PAUSED)

    @Gtk.Template.Callback()
    def next_clicked(self, button):
        self.handle_song_change_request("next")

    @Gtk.Template.Callback()
    def previous_clicked(self, button):
        self.handle_song_change_request("previous")

    @Gtk.Template.Callback()
    def on_volume_changed(self, scale_el):
        value = scale_el.get_value()
        self.player.set_property("volume", value)
        if value == 0:
            self.volume_button_el.set_icon_name("speaker-0-symbolic")
        elif value < 0.33:
            self.volume_button_el.set_icon_name("speaker-1-symbolic")
        elif value < 0.66:
            self.volume_button_el.set_icon_name("speaker-2-symbolic")
        else:
            self.volume_button_el.set_icon_name("speaker-3-symbolic")

    def handle_new_state(self, state):
        if not self.is_seeking:
            stack_page_name = 'play' if state in (Gst.State.NULL, Gst.State.READY, Gst.State.PAUSED) else 'pause'
            self.state_stack_el.set_visible_child_name(stack_page_name)

    def handle_song_change_request(self, action:str):
        # action can be next, previous or end (song ended)
        self.player.set_state(Gst.State.READY)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId

        mode = 'repeat-one' # modes = normal, repeat-one, repeat-all, random

        if action != "end" and mode == "repeat-one":
            mode = "normal"

        if action == "previous" and integration.loaded_models.get('currentSong').positionSeconds > 5:
            integration.loaded_models['currentSong'].songId = current_song_id
            return

        id_list = self.get_ancestor(Adw.NavigationView).find_page('queue').song_list_el.get_all_ids()

        if len(id_list) > 0:
            if not current_song_id: # fallback in case nothing was playing
                integration.loaded_models['currentSong'].songId = id_list[0]

            elif mode in ('normal', 'repeat-all'):
                next_index = id_list.index(current_song_id) + (1 if action in ("next", "end") else -1)
                if next_index < len(id_list) and next_index >= 0:
                    integration.loaded_models['currentSong'].songId = id_list[next_index]
                elif mode == 'repeat-all':
                    integration.loaded_models['currentSong'].songId = id_list[0]
                else:
                    ''
                    ##NOTE
                    # Here's where I could handle automatically adding more songs with radio

            elif mode == 'repeat-one':
                integration.loaded_models['currentSong'].songId = current_song_id

            elif mode == 'random':
                integration.loaded_models['currentSong'].songId = random.choice(id_list)

    def on_player_message(self, bus, message):
        if message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.player:
                old_state, new_state, pending_state = message.parse_state_changed()
                self.handle_new_state(new_state)

        elif message.type == Gst.MessageType.EOS:
            self.handle_song_change_request("end")

        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: {}".format(err.message))

    def change_bottom_sheet_state(self, playing:bool):
        bottom_sheet = self.get_ancestor(Adw.BottomSheet)
        if bottom_sheet:
            bottom_sheet.set_can_open(playing)
            if not playing:
                bottom_sheet.set_open(False)
            bottom_sheet.set_reveal_bottom_bar(playing)

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        model = integration.loaded_models.get(song_id)
        if model:
            self.title_el.set_label(model.title)
            self.artist_el.get_child().set_label(model.artists[0].get('name'))
            self.artist_el.set_action_target_value(GLib.Variant.new_string(model.artists[0].get('id')))
            self.album_el.get_child().set_label(model.album)
            self.album_el.set_action_target_value(GLib.Variant.new_string(model.albumId))
            self.progress_el.get_adjustment().set_upper(model.duration)
            integration.loaded_models.get('currentSong').positionSeconds = 0
            threading.Thread(target=self.update_cover_art).start()
            self.start_current_song()
        GLib.idle_add(self.change_bottom_sheet_state, bool(song_id))

        if self.last_song_id and self.starred_connection:
            integration.loaded_models.get(self.last_song_id).disconnect(self.starred_connection)

        if model:
            self.star_el.set_action_target_value(GLib.Variant.new_string(song_id))
            self.starred_connection = integration.connect_to_model(song_id, 'starred', self.update_starred)
            self.last_song_id = song_id
        else:
            self.star_el.set_action_target_value(GLib.Variant.new_string(""))
            self.starred_connection = None
            self.last_song_id = None


    def update_cover_art(self):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').songId
        song = integration.loaded_models.get(song_id)
        if song:
            paintable = integration.getCoverArt(song.coverArt, 480)
            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
            else:
                GLib.idle_add(self.cover_el.set_from_paintable, None)

    def update_starred(self, starred:str):
        if starred:
            self.star_el.add_css_class('suggested-action')
            self.star_el.set_icon_name('starred-symbolic')
            local_dt = datetime.fromisoformat(starred).astimezone()
            self.star_el.set_tooltip_text(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.star_el.remove_css_class('suggested-action')
            self.star_el.set_icon_name('non-starred-symbolic')
            self.star_el.set_tooltip_text(_('Star'))

    def start_current_song(self):
        integration = get_current_integration()
        self.player.set_state(Gst.State.READY)
        songId = integration.loaded_models.get('currentSong').songId
        if songId:
            stream_url = integration.get_stream_url(songId)
            self.player.set_property('uri', stream_url)
            self.player.set_state(Gst.State.PLAYING)
            GLib.timeout_add(500, self.update_stream_progress)

    def update_stream_progress(self):
        if self.is_seeking:
            return True # don't update if seeking but keep the loop alive
        integration = get_current_integration()
        success, position = self.player.query_position(Gst.Format.TIME)
        if success:
            seconds = position / Gst.SECOND
            integration.loaded_models.get('currentSong').positionSeconds = seconds

        return True
        

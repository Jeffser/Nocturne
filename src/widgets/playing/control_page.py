# control_page.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst, Gio
from ...navidrome import get_current_integration
import threading, random, io, colorsys
from datetime import datetime, timedelta
from PIL import Image
from colorthief import ColorThief
from urllib.parse import urlparse

Gst.init(None)

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/control_page.ui')
class PlayingControlPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingControlPage'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    radio_homepage_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    album_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    positive_progress_el = Gtk.Template.Child()
    negative_progress_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    show_sidebar_el = Gtk.Template.Child()
    volume_button_el = Gtk.Template.Child()
    volume_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    mode_button_el = Gtk.Template.Child()

    def __init__(self):
        # Used to disconnect star_el when song changes
        self.starred_connection = None
        self.last_song_id = None
        super().__init__()

        self.is_seeking = False
        self.player = Gst.ElementFactory.make("playbin", "music-player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_player_message)
        self.volume_el.set_value(0.25) ##TODO save volume within sessions
        self.player.set_property("volume", 0.25)
        GLib.idle_add(self.setup_sidebar_button_connection)
        GLib.timeout_add(500, self.update_stream_progress)

    def setup(self):
        # Called after login
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', self.song_changed, use_gtk_thread=False)

        integration.loaded_models.get('currentSong').bind_property(
            "positionSeconds",
            self.progress_el.get_adjustment(),
            "value",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            None,
            None
        )

    def setup_sidebar_button_connection(self):
        self.get_root().breakpoint_el.connect('apply', lambda *_: self.show_sidebar_el.set_visible(True))
        self.get_root().breakpoint_el.connect('unapply', lambda *_: self.show_sidebar_el.set_visible(False))
        condition = self.get_root().breakpoint_el.get_condition().to_string()
        is_small = self.get_root().get_width() < int(condition.split(': ')[1].strip('sp'))
        self.show_sidebar_el.set_visible(is_small)

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
        value = round(scale_el.get_value(), 2)
        self.player.set_property("volume", value)
        if value == 0:
            self.volume_button_el.set_icon_name("speaker-0-symbolic")
        elif value < 0.33:
            self.volume_button_el.set_icon_name("speaker-1-symbolic")
        elif value < 0.66:
            self.volume_button_el.set_icon_name("speaker-2-symbolic")
        else:
            self.volume_button_el.set_icon_name("speaker-3-symbolic")

    @Gtk.Template.Callback()
    def mode_changed(self, button):
        integration = get_current_integration()
        self.mode_button_el.set_icon_name(button.get_icon_name())
        self.mode_button_el.set_tooltip_text(button.get_tooltip_text())
        self.mode_button_el.get_popover().popdown()
        integration.loaded_models['currentSong'].playbackMode = button.get_name()

    @Gtk.Template.Callback()
    def show_content_clicked(self, button):
        view = self.get_ancestor(Adw.NavigationSplitView)
        if view:
            view.set_show_content(True)

    def handle_new_state(self, state):
        if not self.is_seeking:
            stack_page_name = 'play' if state in (Gst.State.NULL, Gst.State.READY, Gst.State.PAUSED) else 'pause'
            self.state_stack_el.set_visible_child_name(stack_page_name)
            root = self.get_root()
            if root:
                root.footer.state_stack_el.set_visible_child_name(stack_page_name)
                if stack_page_name == 'pause':
                    root.add_css_class('playing')
                else:
                    root.remove_css_class('playing')

    def auto_play(self):
        GLib.idle_add(self.get_root().queue_page.autoplay_spinner_el.set_visible, True)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId
        current_song = integration.loaded_models.get(current_song_id)
        if current_song:
            similar_songs = integration.getSimilarSongs(current_song.artists[0].get('id'))
            if len(similar_songs) > 1 and False:
                GLib.idle_add(self.get_root().queue_page.replace_queue, similar_songs)
            else:
                random_songs = integration.getRandomSongs()
                GLib.idle_add(self.get_root().queue_page.replace_queue, random_songs)
        GLib.idle_add(self.get_root().queue_page.autoplay_spinner_el.set_visible, False)

    def handle_song_change_request(self, action:str):
        # action can be next, previous or end (song ended)
        self.player.set_state(Gst.State.READY)
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').songId

        mode = integration.loaded_models['currentSong'].playbackMode

        if action != "end" and mode == "repeat-one":
            mode = "consecutive"

        if action == "previous" and integration.loaded_models.get('currentSong').positionSeconds > 5:
            integration.loaded_models['currentSong'].songId = current_song_id
            return

        id_list = self.get_root().queue_page.song_list_el.get_all_ids()

        if len(id_list) > 0:
            if not current_song_id: # fallback in case nothing was playing
                integration.loaded_models['currentSong'].songId = id_list[0]

            elif mode in ('consecutive', 'repeat-all'):
                try:
                    next_index = id_list.index(current_song_id) + (1 if action in ("next", "end") else -1)
                except ValueError: # index was not found
                    next_index = 0

                if mode == 'consecutive':
                    if next_index < 0:
                        integration.loaded_models['currentSong'].songId = id_list[0]
                    elif next_index < len(id_list):
                        integration.loaded_models['currentSong'].songId = id_list[next_index]
                    elif Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('auto-play').unpack():
                        threading.Thread(target=self.auto_play).start()
                elif mode == 'repeat-all':
                    if next_index < len(id_list) and next_index >= 0:
                        integration.loaded_models['currentSong'].songId = id_list[next_index]
                    else:
                        integration.loaded_models['currentSong'].songId = id_list[0]

            elif mode == 'repeat-one':
                integration.loaded_models['currentSong'].songId = current_song_id
        else:
            integration.loaded_models['currentSong'].songId = None

    def set_dynamic_title(self, title:str):
        # called by on_player_message (useful for radios)
        if title == self.title_el.get_label():
            return
        integration = get_current_integration()
        model = integration.loaded_models.get(integration.loaded_models.get('currentSong'))
        if model and model.isRadio:
            self.title_el.set_label(title or model.title)
            self.title_el.set_tooltip_text(title or model.title)
            root = self.get_root()
            if root:
                root.footer.title_el.set_label(title or model.title)

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

        elif message.type == Gst.MessageType.TAG:
            taglist = message.parse_tag()
            for i in range(taglist.n_tags()):
                name = taglist.nth_tag_name(i)
                value = taglist.get_value_index(name, 0)
                if name == 'title' and value:
                    self.set_dynamic_title(value)

    def change_bottom_sheet_state(self, playing:bool):
        bottom_sheet = self.get_ancestor(Adw.BottomSheet)
        if bottom_sheet:
            bottom_sheet.set_can_open(playing)
            if not playing:
                bottom_sheet.set_open(False)
            bottom_sheet.set_reveal_bottom_bar(playing)

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        if not song_id:
            self.player.set_state(Gst.State.NULL)
        GLib.idle_add(self.change_bottom_sheet_state, bool(song_id))

        model = integration.loaded_models.get(song_id)
        if model:
            # Title
            self.title_el.set_label(model.title)
            self.title_el.set_tooltip_text(model.title)

            # HomePage (radio)
            if model.isRadio:
                self.radio_homepage_el.get_child().set_label(urlparse(model.homePageUrl).netloc.capitalize())
                self.radio_homepage_el.set_action_target_value(GLib.Variant.new_string(model.homePageUrl))
                self.radio_homepage_el.set_tooltip_text(model.homePageUrl)
            self.radio_homepage_el.set_visible(model.isRadio and model.homePageUrl)

            # Timestamp (radio)
            self.positive_progress_el.set_visible(not model.isRadio)
            self.negative_progress_el.set_visible(not model.isRadio)

            # Artist
            if len(model.artists) > 0:
                self.artist_el.get_child().set_label(model.artists[0].get('name'))
                self.artist_el.set_action_target_value(GLib.Variant.new_string(model.artists[0].get('id')))
                self.artist_el.set_tooltip_text(model.artists[0].get('name'))
            self.artist_el.set_visible(model.artists)

            # Album
            self.album_el.get_child().set_label(model.album)
            self.album_el.set_action_target_value(GLib.Variant.new_string(model.albumId))
            self.album_el.set_tooltip_text(model.album)
            self.album_el.set_visible(model.album)

            # Progressbar
            self.progress_el.get_adjustment().set_upper(model.duration)
            self.progress_el.set_visible(not model.isRadio)
            integration.loaded_models.get('currentSong').positionSeconds = 0

            # Star
            self.star_el.set_visible(not model.isRadio)

            # Cover
            threading.Thread(target=self.update_cover_art).start()

            self.start_current_song()

        if self.last_song_id and self.starred_connection:
            integration.loaded_models.get(self.last_song_id).disconnect(self.starred_connection)

        if model:
            self.star_el.set_action_name('app.toggle_star')
            self.star_el.set_action_target_value(GLib.Variant.new_string(song_id))
            self.starred_connection = integration.connect_to_model(song_id, 'starred', self.update_starred)
            self.last_song_id = song_id
        else:
            self.star_el.set_action_name('')
            self.star_el.set_action_target_value(GLib.Variant.new_string(""))
            self.starred_connection = None
            self.last_song_id = None

    def update_palette(self, raw_bytes:bytes):
        img_io = io.BytesIO(raw_bytes)
        palette = ColorThief(img_io).get_palette(quality=10, color_count=2)
        css = f"""
        @media (prefers-color-scheme: dark) {{
            .dynamic-accent-bg > * {{
                background-image: linear-gradient(
                    to bottom right,
                    rgba({','.join([str(c) for c in palette[0]])},0.25),
                    rgba({','.join([str(c) for c in palette[1]])},0.25)
                );
            }}
        }}
        @media (prefers-color-scheme: light) {{
            .dynamic-accent-bg > * {{
                background-image: linear-gradient(
                    to bottom right,
                    rgba({','.join([str(c) for c in palette[0]])},0.40),
                    rgba({','.join([str(c) for c in palette[1]])},0.40)
                );
            }}
        }}
        .dynamic-accent-bg {{
            transition: background-image 0.5s ease-in-out;
        }}
        """

        stack_el = self.get_ancestor(Gtk.Stack)
        stack_el.add_css_class('dynamic-accent-bg')
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def update_cover_art(self):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').songId
        if song_id:
            raw_bytes, paintable = integration.getCoverArtWithBytes(song_id)
            if raw_bytes:
                threading.Thread(target=self.update_palette, args=(raw_bytes,)).start()
            if paintable:
                GLib.idle_add(self.cover_el.set_paintable, paintable)
                GLib.idle_add(self.cover_el.set_visible, True)
            else:
                GLib.idle_add(self.cover_el.set_paintable, None)
                GLib.idle_add(self.cover_el.set_visible, False)

    def update_starred(self, starred:str):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.set_icon_name('starred-symbolic')
            local_dt = datetime.fromisoformat(starred).astimezone()
            self.star_el.set_tooltip_text(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.star_el.remove_css_class('accent')
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

    def update_stream_progress(self):
        if self.is_seeking:
            return True # don't update if seeking but keep the loop alive
        integration = get_current_integration()
        success, position = self.player.query_position(Gst.Format.TIME)
        if success:
            seconds = position / Gst.SECOND
            current_song = integration.loaded_models.get('currentSong')
            current_song.positionSeconds = seconds
            label_positive = str(timedelta(seconds=int(seconds))).removeprefix('0:')
            label_negative = str(timedelta(seconds=int(integration.loaded_models.get(current_song.songId).duration - seconds))).removeprefix('0:')
            self.positive_progress_el.set_label(label_positive)
            self.negative_progress_el.set_label('-{}'.format(label_negative))
        return True


# control_page.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject, Gst, Gio
from ...navidrome import get_current_integration
import threading, random, io, colorsys
from datetime import datetime, timedelta
from PIL import Image
from colorthief import ColorThief
from urllib.parse import urlparse
from .player import Player

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
        self.player = Player(self)
        GLib.idle_add(self.setup_sidebar_button_connection)

    def setup(self):
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'positionSeconds', self.update_position)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)

    def update_position(self, positionSeconds:int):
        integration = get_current_integration()
        current_song = integration.loaded_models.get('currentSong')
        if current_song:
            song = integration.loaded_models.get(current_song.get_property('songId'))
            if song:
                label_positive = str(timedelta(seconds=int(positionSeconds))).removeprefix('0:')
                label_negative = str(timedelta(seconds=int(song.get_property('duration') - positionSeconds))).removeprefix('0:')
                self.positive_progress_el.set_label(label_positive)
                self.negative_progress_el.set_label('-{}'.format(label_negative))
                self.progress_el.get_adjustment().set_value(positionSeconds)

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
            self.player.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.player.gst.set_state(Gst.State.PLAYING)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.player.gst.set_state(Gst.State.PAUSED)

    @Gtk.Template.Callback()
    def next_clicked(self, button):
        self.player.handle_song_change_request("next")

    @Gtk.Template.Callback()
    def previous_clicked(self, button):
        self.player.handle_song_change_request("previous")

    @Gtk.Template.Callback()
    def on_volume_changed(self, scale_el):
        value = round(scale_el.get_value(), 2)
        self.player.gst.set_property("volume", value)
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
        integration.loaded_models.get('currentSong').set_property('playbackMode', button.get_name())

    @Gtk.Template.Callback()
    def show_content_clicked(self, button):
        view = self.get_ancestor(Adw.NavigationSplitView)
        if view:
            view.set_show_content(True)

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
            self.player.gst.set_state(Gst.State.NULL)
        GLib.idle_add(self.change_bottom_sheet_state, bool(song_id))

        model = integration.loaded_models.get(song_id)
        if model:
            # Title
            self.title_el.set_label(model.get_property('title'))
            self.title_el.set_tooltip_text(model.get_property('title'))

            # HomePage (radio)
            if model.get_property('isRadio'):
                self.radio_homepage_el.get_child().set_label(urlparse(model.get_property('homePageUrl')).netloc.capitalize())
                self.radio_homepage_el.set_action_target_value(GLib.Variant.new_string(model.get_property('homePageUrl')))
                self.radio_homepage_el.set_tooltip_text(model.get_property('homePageUrl'))
            self.radio_homepage_el.set_visible(model.get_property('isRadio') and model.get_property('homePageUrl'))

            # Timestamp (radio)
            self.positive_progress_el.set_visible(not model.get_property('isRadio'))
            self.negative_progress_el.set_visible(not model.get_property('isRadio'))

            # Artist
            if len(model.get_property('artists')) > 0:
                self.artist_el.get_child().set_label(model.get_property('artists')[0].get('name'))
                self.artist_el.set_action_target_value(GLib.Variant.new_string(model.get_property('artists')[0].get('id')))
                self.artist_el.set_tooltip_text(model.get_property('artists')[0].get('name'))
            self.artist_el.set_visible(model.get_property('artists'))

            # Album
            self.album_el.get_child().set_label(model.get_property('album'))
            self.album_el.set_action_target_value(GLib.Variant.new_string(model.get_property('albumId')))
            self.album_el.set_tooltip_text(model.get_property('album'))
            self.album_el.set_visible(model.get_property('album'))

            # Progressbar
            self.progress_el.get_adjustment().set_upper(model.get_property('duration'))
            self.progress_el.set_visible(not model.get_property('isRadio'))
            integration.loaded_models.get('currentSong').set_property('positionSeconds', 0)

            # Star
            self.star_el.set_visible(not model.get_property('isRadio'))

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
        song_id = integration.loaded_models.get('currentSong').get_property('songId')
        if song_id:
            raw_bytes, paintable = integration.getCoverArtWithBytes(song_id)
            if raw_bytes and Gio.Settings(schema_id="com.jeffser.Nocturne").get_value("use-dynamic-background").unpack():
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
        self.player.gst.set_state(Gst.State.READY)
        songId = integration.loaded_models.get('currentSong').get_property('songId')
        if songId:
            stream_url = integration.get_stream_url(songId)
            self.player.gst.set_property('uri', stream_url)
            self.player.gst.set_state(Gst.State.PLAYING)



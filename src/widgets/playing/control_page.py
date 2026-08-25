# control_page.py

from gi.repository import Gtk, Adw, GLib, Gst, GObject
from ...integrations import get_current_integration
from ...constants import get_display_time
from urllib.parse import urlparse

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/control_page.ui')
class PlayingControlPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingControlPage'

    extra_widget = GObject.Property(type=Gtk.Widget)

    header_bar = Gtk.Template.Child()
    clamp = Gtk.Template.Child()
    main_container = Gtk.Template.Child()
    cover_art_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    radio_homepage_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    album_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    positive_progress_el = Gtk.Template.Child()
    negative_progress_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    show_sidebar_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    rating_button = Gtk.Template.Child()
    rating_container = Gtk.Template.Child()
    breakpoint_state = False

    def setup(self):
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'positionSeconds', self.update_position)
        integration.connect_to_model('currentSong', 'buttonState', self.state_stack_el.set_visible_child_name)
        integration.connect_to_model('currentSong', 'displaySongTitle', self.display_title_changed)
        integration.connect_to_model('currentSong', 'displaySongArtist', self.display_artist_changed)
        self.cover_art_el.setup()
        self.setup_sidebar_button_connection()
        if stack := self.get_ancestor(Gtk.Stack):
            stack.get_parent().set_overflow(Gtk.Overflow.HIDDEN)
            if stack2 := stack.get_parent().get_parent():
                stack2.get_parent().set_overflow(Gtk.Overflow.HIDDEN)
        if extra_widget := self.get_property('extra-widget'):
            self.main_container.prepend(extra_widget)

        # Connect to Current Song
        connections = {
            'id': lambda model_id: self.star_el.set_action_target_value(GLib.Variant('s', model_id or '')),
            'radioStreamUrl': self.update_radioStreamUrl,
            'artistId': self.update_artistId,
            'album': self.update_album,
            'albumId': self.update_albumId,
            'isExternalFile': self.update_isExternalFile,
            'duration': self.progress_el.get_adjustment().set_upper,
            'userRating': self.update_userRating,
            'starred': self.update_starred
        }
        for parameter, callback in connections.items():
            integration.connect_to_current_song(parameter, callback)

    def update_position(self, positionSeconds:int):
        integration = get_current_integration()
        current_song = integration.loaded_models.get('currentSong')
        if current_song:
            song = integration.loaded_models.get(current_song.get_property('songId'))
            if song:
                label_positive = get_display_time(positionSeconds)
                label_negative = get_display_time(song.get_property('duration') - positionSeconds)
                self.positive_progress_el.set_label(label_positive)
                self.negative_progress_el.set_label('-{}'.format(label_negative))
                if not integration.loaded_models.get('currentSong').get_property('seeking'):
                    self.progress_el.get_adjustment().set_value(positionSeconds)

    def breakpoint_toggled(self, active:bool):
        self.breakpoint_state = active
        if isinstance(self.get_parent(), Adw.NavigationView) and not self.get_parent().get_vhomogeneous():
            self.get_parent().set_vhomogeneous(True)

    def setup_sidebar_button_connection(self):
        if root := self.get_root():
            root.breakpoint_el.connect('apply', lambda *_: self.breakpoint_toggled(True))
            root.breakpoint_el.connect('unapply', lambda *_: self.breakpoint_toggled(False))
            if width := root.get_width():
                self.breakpoint_toggled(width <= 620)

    @Gtk.Template.Callback()
    def progress_bar_changed(self, scale_el, scroll_type, value):
        value = scale_el.get_adjustment().get_value()
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('seeking', True)
        def change_time(val):
            integration.loaded_models.get('currentSong').set_property('seeking', False)
            nanoseconds = int(val * Gst.SECOND)
            self.get_root().get_application().player.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )
        GLib.timeout_add(500, lambda v=value: change_time(v) if v == scale_el.get_adjustment().get_value() else None)

    @Gtk.Template.Callback()
    def show_content_clicked(self, button):
        if view := self.get_ancestor(Adw.NavigationSplitView):
            if self.breakpoint_state:
                view.set_show_content(True)
            else:
                view.set_collapsed(not view.get_collapsed())

    @Gtk.Template.Callback()
    def change_rating(self, button):
        integration = get_current_integration()
        target_value = GLib.Variant('a{sv}', {
            'model_id': GLib.Variant('s', integration.loaded_models.get('currentSong').get_property('songId')),
            'rating': GLib.Variant('i', int(button.get_name()))
        })
        self.get_root().activate_action("app.set_rating", target_value)

    def change_bottom_sheet_state(self, playing:bool):
        bottom_sheet = self.get_ancestor(Adw.BottomSheet)
        if bottom_sheet:
            bottom_sheet.set_can_open(playing)
            if not playing:
                bottom_sheet.set_open(False)
            bottom_sheet.set_reveal_bottom_bar(playing)

        if root := self.get_root():
            if application := root.get_application():
                if playing:
                    application.inhibit_suspend()
                else:
                    application.uninhibit_suspend()
                    if popout_window := application.popout_window:
                        popout_window.close()

    def update_radioStreamUrl(self, radioStreamUrl:str):
        self.radio_homepage_el.set_visible(radioStreamUrl)
        self.artist_el.set_can_target(not radioStreamUrl)
        self.artist_el.set_focusable(not radioStreamUrl)
        self.positive_progress_el.set_visible(not radioStreamUrl)
        self.negative_progress_el.set_visible(not radioStreamUrl)
        self.progress_el.set_visible(not radioStreamUrl)
        self.rating_button.set_visible(not radioStreamUrl)
        self.star_el.set_visible(not radioStreamUrl)

        homepage_url = ""
        if radioStreamUrl:
            stream_url = urlparse(radioStreamUrl)
            homepage_url = '{}://{}'.format(stream_url.scheme, stream_url.netloc)
        self.radio_homepage_el.set_tooltip_text(homepage_url)
        self.radio_homepage_el.set_action_target_value(GLib.Variant.new_string(homepage_url))
        self.radio_homepage_el.get_child().set_label(urlparse(radioStreamUrl).netloc)

    def update_artistId(self, artistId:str):
        if artistId:
            self.artist_el.set_action_target_value(GLib.Variant.new_string(artistId))
            self.artist_el.set_action_name("app.show_artist")

    def update_album(self, album:str):
        self.album_el.get_child().set_label(album)
        self.album_el.set_tooltip_text(album)
        self.album_el.set_visible(album)

    def update_albumId(self, albumId:str):
        if albumId:
            self.album_el.set_action_target_value(GLib.Variant.new_string(albumId))
            self.album_el.set_action_name("app.show_album")
            self.album_el.set_sensitive(True)
        else:
            self.album_el.set_action_name("")
            self.album_el.set_sensitive(False)

    def update_isExternalFile(self, isExternalFile:bool):
        self.album_el.get_ancestor(Adw.WrapBox).set_sensitive(not isExternalFile)
        self.rating_container.set_visible(self.rating_container.get_visible() and not isExternalFile)
        self.star_el.set_visible(self.star_el.get_visible() and not isExternalFile)

    def update_userRating(self, userRating:int):
        for i, el in enumerate(list(self.rating_container)):
            el.set_icon_name("starred-symbolic" if userRating >= i+1 else "non-starred-symbolic")
        self.rating_button.set_icon_name("starred-symbolic" if userRating > 0 else "non-starred-symbolic")

    def update_starred(self, starred:bool):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
            self.star_el.set_icon_name('heart-filled-symbolic')
            self.star_el.set_tooltip_text(_('Favorite'))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
            self.star_el.set_icon_name('heart-outline-thick-symbolic')
            self.star_el.set_tooltip_text(_('Not Favorite'))

    def display_title_changed(self, display_title:str):
        self.title_el.set_label(display_title)
        self.title_el.set_tooltip_text(display_title)

    def display_artist_changed(self, display_artist:str):
        self.artist_el.get_child().set_label(display_artist)
        self.artist_el.set_tooltip_text(display_artist)
        self.artist_el.set_visible(bool(display_artist))


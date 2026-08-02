# footer.py

from gi.repository import Gtk, GLib, GObject, Gst, Gio
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/footer.ui')
class PlayingFooter(Gtk.Overlay):
    __gtype_name__ = 'NocturnePlayingFooter'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    ro_progress_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    detail_container = Gtk.Template.Child()
    forceHugeMode = GObject.Property(type=bool, default=False)

    def setup(self):
        # Called after login
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', lambda song_id: self.update_progress_el_visibility())
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed)
        integration.connect_to_model('currentSong', 'buttonState', self.state_stack_el.set_visible_child_name)
        integration.connect_to_model('currentSong', 'displaySongTitle', self.display_title_changed)
        integration.connect_to_model('currentSong', 'displaySongArtist', self.display_artist_changed)
        self.settings.connect("changed::use-big-footer", self.big_mode_toggled)
        self.big_mode_toggled(self.settings, 'use-big-footer')

        connections = {
            'duration': self.progress_el.get_adjustment().set_upper,
            'gdkPaintable': self.update_coverArt
        }
        for parameter, callback in connections.items():
            integration.connect_to_current_song(parameter, callback)

    def big_mode_toggled(self, settings, key):
        if self.get_property('forceHugeMode'):
            big_mode = True
            size = 100
            self.cover_el.set_size_request(size, size)
            self.cover_el.set_pixel_size(size)
            self.title_el.set_wrap(True)
            self.title_el.set_lines(2)
            self.detail_container.set_spacing(10)
        else:
            big_mode = settings.get_value(key).unpack()
            size = 70 if big_mode else 48
            self.cover_el.set_size_request(size, size)
            self.cover_el.set_pixel_size(size)
            self.title_el.set_wrap(False)
            self.title_el.set_lines(1)
            self.detail_container.set_spacing(5)
        self.ro_progress_el.set_visible(not big_mode)
        self.update_progress_el_visibility()

    def update_progress_el_visibility(self):
        mode_status = self.settings.get_value('use-big-footer').unpack()
        force_status = self.get_property('forceHugeMode')
        integration = get_current_integration()
        songId = integration.loaded_models.get('currentSong').get_property('songId')
        isRadio = False
        if model := integration.loaded_models.get(songId):
            isRadio = bool(model.get_property('radioStreamUrl'))
        self.progress_el.set_visible(not isRadio and (mode_status or force_status))

    def display_title_changed(self, display_title:str):
        self.title_el.set_label(display_title)

    def display_artist_changed(self, display_artist:str):
        self.artist_el.set_label(display_artist)
        self.artist_el.set_visible(self.artist_el.get_label())

    def position_changed(self, positionSeconds:float):
        integration = get_current_integration()
        if not integration.loaded_models.get('currentSong').get_property('seeking'):
            duration = self.progress_el.get_adjustment().get_upper()
            self.ro_progress_el.set_fraction(0 if duration == 0 else positionSeconds / duration)
            self.progress_el.get_adjustment().set_value(positionSeconds)

    def update_coverArt(self, paintable):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
            self.cover_el.set_pixel_size(self.cover_el.get_size_request()[0])
        else:
            self.cover_el.set_from_icon_name('music-note-symbolic')
            self.cover_el.set_pixel_size(-1)

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


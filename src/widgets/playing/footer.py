# footer.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject
from ...integrations import get_current_integration
import threading
from urllib.parse import urlparse

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/footer.ui')
class PlayingFooter(Gtk.Overlay):
    __gtype_name__ = 'NocturnePlayingFooter'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    detail_container = Gtk.Template.Child()

    def setup(self):
        # Called after login
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed)
        integration.connect_to_model('currentSong', 'buttonState', self.state_stack_el.set_visible_child_name)

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        song = integration.loaded_models.get(song_id)
        if song:
            self.title_el.set_label(song.get_property('title'))
            artists = song.get_property('artists')
            if len(artists) > 0:
                self.artist_el.set_label(artists[0].get('name'))
            else:
                self.artist_el.set_label('')
            if song.get_property('isRadio'):
                if song.get_property('streamUrl'):
                    self.artist_el.set_label(urlparse(song.get_property('streamUrl')).netloc.capitalize())
                else:
                    self.artist_el.set_label("")
            self.artist_el.set_visible(self.artist_el.get_label())
            threading.Thread(target=self.update_cover_art).start()

    def position_changed(self, positionSeconds:float):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').get_property('songId')
        song = integration.loaded_models.get(song_id)
        if song:
            duration = song.get_property('duration')
            self.progress_el.set_fraction(0 if duration == 0 else positionSeconds / duration)

    def update_cover_art(self):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').get_property('songId')
        if song_id:
            gbytes, paintable = integration.getCoverArt(song_id)
            if paintable:
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
                GLib.idle_add(self.cover_el.set_pixel_size, self.cover_el.get_size_request()[0])
            else:
                GLib.idle_add(self.cover_el.set_from_icon_name, 'music-note-symbolic')
                GLib.idle_add(self.cover_el.set_pixel_size, -1)

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.get_root().playing_page.play_clicked(button)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.get_root().playing_page.pause_clicked(button)

    @Gtk.Template.Callback()
    def next_clicked(self, button):
        self.get_root().playing_page.next_clicked(button)

    @Gtk.Template.Callback()
    def previous_clicked(self, button):
        self.get_root().playing_page.previous_clicked(button)

# footer.py

from gi.repository import Gtk, Adw, Gdk, GLib, GObject
from ...navidrome import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/footer.ui')
class PlayingFooter(Gtk.Overlay):
    __gtype_name__ = 'NocturnePlayingFooter'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()

    def __init__(self):
        integration = get_current_integration()
        super().__init__()
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed)
        GLib.idle_add(self.connect_play_state)

    def connect_play_state(self):
        self.get_root().playing_navigationview.find_page('playing').state_stack_el.bind_property(
            "visible-child-name",
            self.state_stack_el,
            "visible-child-name",
            GObject.BindingFlags.SYNC_CREATE,
            None,
            None
        )

    def song_changed(self, song_id:str):
        integration = get_current_integration()
        song = integration.loaded_models.get(song_id)
        if song:
            self.title_el.set_label(song.title)
            self.artist_el.set_label(song.artists[0].get('name'))
            threading.Thread(target=self.update_cover_art).start()

    def position_changed(self, positionSeconds:float):
        integration = get_current_integration()
        song_id = integration.loaded_models.get('currentSong').songId
        song = integration.loaded_models.get(song_id)
        if song:
            self.progress_el.set_fraction(positionSeconds / song.duration)

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

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.get_root().playing_navigationview.find_page('playing').play_clicked(button)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.get_root().playing_navigationview.find_page('playing').pause_clicked(button)

    @Gtk.Template.Callback()
    def next_clicked(self, button):
        self.get_root().playing_navigationview.find_page('playing').next_clicked(button)

    @Gtk.Template.Callback()
    def previous_clicked(self, button):
        self.get_root().playing_navigationview.find_page('playing').previous_clicked(button)

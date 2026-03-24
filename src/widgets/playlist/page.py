# page.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from ...integrations import get_current_integration
from ...constants import CONTEXT_PLAYLIST, get_display_time
from ..containers import get_context_buttons_list
from ..song import SongRow
import threading, uuid

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/page.ui')
class PlaylistPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlaylistPage'

    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    song_count_el = Gtk.Template.Child()
    duration_el = Gtk.Template.Child()
    song_list_el = Gtk.Template.Child()

    context_wrap_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id, True)
        super().__init__(
            tag=str(uuid.uuid4())
        )
        self.song_list_el.set_header(_("Songs"), "music-note-symbolic")

        context_dict = CONTEXT_PLAYLIST.copy()
        del context_dict['edit']
        del context_dict['delete']
        context_buttons = get_context_buttons_list(context_dict, self.id)
        for btn in context_buttons:
            self.context_wrap_el.append(btn)

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
        integration.connect_to_model(self.id, 'duration', self.update_duration)
        integration.connect_to_model(self.id, 'entry', self.update_song_list)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

        self.song_list_el.playlist_id = self.id

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(self.id)
            if paintable:
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
                GLib.idle_add(self.cover_el.set_pixel_size, 240)
            else:
                GLib.idle_add(self.cover_el.set_from_icon_name, "playlist-symbolic")
                GLib.idle_add(self.cover_el.set_pixel_size, -1)
        if coverArt:
            threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.name_el.set_visible(name)
        self.set_title(name or _('Playlist'))

    def update_song_list(self, song_list:list):
        self.song_list_el.list_el.remove_all()
        for song_dict in song_list:
            self.song_list_el.list_el.append(
                SongRow(
                    song_dict.get('id'),
                    removable=True
                )
            )
        self.song_list_el.main_stack.set_visible_child_name('content' if len(song_list) > 0 else 'no-content')

    def update_song_count(self, songCount:int):
        if songCount == 1:
            self.song_count_el.set_label(_("1 Song"))
        else:
            self.song_count_el.set_label(_("{} Songs").format(songCount))

        self.song_count_el.set_visible(songCount)

    def update_duration(self, duration:int):
        self.duration_el.set_label(get_display_time(duration))
        self.duration_el.set_visible(duration)

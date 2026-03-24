# button.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...integrations import get_current_integration
from ...constants import CONTEXT_PLAYLIST
from ..containers import ContextContainer
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/button.ui')
class PlaylistButton(Gtk.Box):
    __gtype_name__ = 'NocturnePlaylistButton'

    play_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    name_label_el = Gtk.Template.Child()
    song_count_label_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id)
        super().__init__()

        self.play_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.name_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

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
        self.name_el.set_tooltip_text(name)
        self.name_label_el.set_label(name)
        self.set_name(name)

    def update_song_count(self, songCount:int):
        if songCount == 1:
            self.song_count_label_el.set_label(_("1 Song"))
        else:
            self.song_count_label_el.set_label(_("{} Songs").format(songCount))

        self.song_count_label_el.set_visible(songCount)

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=ContextContainer(CONTEXT_PLAYLIST, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()


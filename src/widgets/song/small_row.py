# small_row.py

from gi.repository import Gtk, Adw, Gdk, GLib
from ...navidrome import get_current_integration
from ..containers import ContextContainer
from ...constants import CONTEXT_SONG
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/small_row.ui')
class SongSmallRow(Gtk.Button):
    __gtype_name__ = 'NocturneSongSmallRow'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    subtitle_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifySong(self.id)
        super().__init__(
            action_target=GLib.Variant.new_string(self.id)
        )
        integration.connect_to_model(self.id, 'title', self.update_title)
        integration.connect_to_model(self.id, 'artists', self.update_artists)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(self.id)
            if paintable:
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
                GLib.idle_add(self.cover_el.set_pixel_size, 48)
            else:
                GLib.idle_add(self.cover_el.set_from_icon_name, "music-note-symbolic")
                GLib.idle_add(self.cover_el.set_pixel_size, -1)
        threading.Thread(target=update).start()

    def update_title(self, title:str):
        self.title_el.set_label(title)
        self.set_tooltip_text(title)

    def update_artists(self, artists:list):
        if len(artists) > 0:
            self.subtitle_el.set_label(artists[0].get('name'))
        else:
            self.subtitle_el.set_label("")

    def generate_context_menu(self) -> ContextContainer:
        context_dict = CONTEXT_SONG.copy()
        del context_dict["edit"]
        del context_dict["delete"]
        del context_dict["remove"]
        del context_dict["select"]
        return ContextContainer(context_dict, self.id)

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=self.generate_context_menu(),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()


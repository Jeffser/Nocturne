# row.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...navidrome import get_current_integration
from ...constants import CONTEXT_PLAYLIST
from ..containers import ContextContainer
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/row.ui')
class PlaylistRow(Adw.ActionRow):
    __gtype_name__ = 'NocturnePlaylistRow'

    cover_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id)
        super().__init__()
        self.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(self.id)
            if paintable:
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
                GLib.idle_add(self.cover_el.set_pixel_size, 48)
            else:
                GLib.idle_add(self.cover_el.set_from_icon_name, "playlist-symbolic")
                GLib.idle_add(self.cover_el.set_pixel_size, -1)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.set_title(GLib.markup_escape_text(name))
        self.set_name(GLib.markup_escape_text(name))

    def update_song_count(self, songCount:int):
        if songCount == 1:
            self.set_subtitle(_("1 Song"))
        else:
            self.set_subtitle(_("{} Songs").format(songCount))

    @Gtk.Template.Callback()
    def on_context_button_active(self, button, gparam):
        button.get_popover().set_child(ContextContainer(CONTEXT_PLAYLIST, self.id))

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



# row.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...navidrome import get_current_integration
from ...constants import CONTEXT_ARTIST
from ..containers import ContextContainer
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/row.ui')
class ArtistRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneArtistRow'

    avatar_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id)
        super().__init__()
        self.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)
        integration.connect_to_model(self.id, 'albumCount', self.update_album_count)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(self.id)
            if paintable:
                GLib.idle_add(self.avatar_el.set_custom_image, paintable)
            else:
                GLib.idle_add(self.avatar_el.set_custom_image, None)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.set_title(GLib.markup_escape_text(name))
        self.set_name(GLib.markup_escape_text(name))

    def update_album_count(self, albumCount:int):
        if albumCount == 1:
            self.set_subtitle(_("1 Album"))
        else:
            self.set_subtitle(_("{} Albums").format(albumCount))

    @Gtk.Template.Callback()
    def on_context_button_active(self, button, gparam):
        button.get_popover().set_child(ContextContainer(CONTEXT_ARTIST, self.id))

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=ContextContainer(CONTEXT_ARTIST, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()



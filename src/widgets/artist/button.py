# button.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...integrations import get_current_integration
from ...constants import CONTEXT_ARTIST
from ..containers import ContextContainer
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/button.ui')
class ArtistButton(Gtk.Button):
    __gtype_name__ = 'NocturneArtistButton'

    avatar_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    album_count_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id)
        super().__init__(
            action_target=GLib.Variant.new_string(self.id)
        )

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'albumCount', self.update_album_count)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(self.id)
            if paintable:
                GLib.idle_add(self.avatar_el.set_custom_image, paintable)
            else:
                GLib.idle_add(self.avatar_el.set_custom_image, None)
        if coverArt:
            threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.avatar_el.set_tooltip_text(name)
        self.set_tooltip_text(name)
        self.name_el.set_label(name)

    def update_album_count(self, albumCount:int):
        if albumCount == 1:
            self.album_count_el.set_label(_("1 Album"))
        else:
            self.album_count_el.set_label(_("{} Albums").format(albumCount))

        self.album_count_el.set_visible(albumCount)

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


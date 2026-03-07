# button.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...navidrome import get_current_integration
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
            paintable = integration.getCoverArt(coverArt, 480)
            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.avatar_el.set_custom_image, paintable)
            else:
                GLib.idle_add(self.avatar_el.set_custom_image, None)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.set_tooltip_text(name)
        self.name_el.set_label(name)

    def update_album_count(self, albumCount:int):
        if albumCount == 1:
            self.album_count_el.set_label(_("1 Album"))
        else:
            self.album_count_el.set_label(_("{} Albums").format(albumCount))

        self.album_count_el.set_visible(albumCount)

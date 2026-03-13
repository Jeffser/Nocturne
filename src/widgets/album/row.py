# row.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...navidrome import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/row.ui')
class AlbumRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneAlbumRow'

    cover_el = Gtk.Template.Child()
    play_el = Gtk.Template.Child()
    play_shuffle_el = Gtk.Template.Child()
    play_next_el = Gtk.Template.Child()
    play_later_el = Gtk.Template.Child()
    add_playlist_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id)
        super().__init__()
        self.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_shuffle_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_next_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_later_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.add_playlist_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'artist', self.update_artist)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(self.id, 480)
            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.cover_el.set_from_paintable, paintable)
            else:
                GLib.idle_add(self.cover_el.set_from_paintable, None)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.set_title(GLib.markup_escape_text(name))
        self.set_name(GLib.markup_escape_text(name))

    def update_artist(self, artist:str):
        self.set_subtitle(artist)

    @Gtk.Template.Callback()
    def option_selected(self, button):
        button.get_ancestor(Gtk.MenuButton).popdown()


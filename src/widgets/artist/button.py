# button.py

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration
from ...constants import CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/button.ui')
class ArtistButton(Gtk.Button):
    __gtype_name__ = 'NocturneArtistButton'

    avatar_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    album_count_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id, minimal=True)
        super().__init__(
            action_target=GLib.Variant.new_string(self.id)
        )

        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.connect("changed::button-size", lambda *_: self.update_size())

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'albumCount', self.update_album_count)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)

    def update_size(self):
        isBig = self.settings.get_value('button-size').unpack() == 'big'
        size = 240 if isBig else 180
        self.avatar_el.set_size(size)
        if isBig:
            self.name_el.remove_css_class('title-4')
            self.name_el.add_css_class('title-3')
        else:
            self.name_el.remove_css_class('title-3')
            self.name_el.add_css_class('title-4')

    def update_cover(self, paintable):
        if paintable:
            self.avatar_el.set_custom_image(paintable)
        elif isinstance(self.avatar_el.get_custom_image(), Adw.SpinnerPaintable):
            self.avatar_el.set_custom_image(None)
        self.update_size()

    def update_name(self, name:str):
        self.avatar_el.set_tooltip_text(name)
        self.set_tooltip_text(name)
        self.name_el.set_label(name)
        self.set_name(name)

    def update_album_count(self, albumCount:int):
        self.album_count_el.set_label(ngettext("{} Album", "{} Albums", albumCount).format(albumCount))
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


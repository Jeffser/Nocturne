# button.py

from gi.repository import GObject, Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/button.ui')
class ArtistButton(Gtk.Button):
    __gtype_name__ = 'NocturneArtistButton'

    model = GObject.Property(type=models.Artist)

    avatar_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    album_count_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id, minimal=True)
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.connect("changed::button-size", lambda *_: self.update_size())
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )

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

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_to_bool(self, obj, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def format_album_count_label(self, obj, albumCount:int) -> str:
        return ngettext("{} Album", "{} Albums", albumCount).format(albumCount)

    @Gtk.Template.Callback()
    def format_gdkPaintable(self, obj, paintable:Gdk.Paintable) -> Gdk.Paintable:
        GLib.idle_add(self.update_size)
        return paintable

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


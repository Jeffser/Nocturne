# row.py

from gi.repository import GObject, Gtk, Adw, GLib, Gio, Gdk
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ALBUM
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/row.ui')
class AlbumRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneAlbumRow'

    model = GObject.Property(type=models.Album)

    menu_button_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id, minimal=True)
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        settings.bind(
            "show-context-button",
            self.menu_button_el,
            "visible",
            Gio.SettingsBindFlags.DEFAULT
        )

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_cover_pixel_size(self, obj, paintable:Gdk.Paintable) -> int:
        return 48 if paintable else -1

    @Gtk.Template.Callback()
    def on_context_button_active(self, button, gparam):
        context = CONTEXT_ALBUM.copy()
        if 'no-downloads' in get_current_integration().limitations:
            del context['download']

        button.get_popover().set_child(ContextContainer(context, self.id))

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        context = CONTEXT_ALBUM.copy()
        if 'no-downloads' in get_current_integration().limitations:
            del context['download']

        popover = Gtk.Popover(
            child=ContextContainer(context, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()



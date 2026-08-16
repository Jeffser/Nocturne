# row.py

from gi.repository import GObject, Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/row.ui')
class ArtistRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneArtistRow'

    model = GObject.Property(type=models.Artist)

    avatar_el = Gtk.Template.Child()
    menu_button_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id, minimal=True)
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
    def format_album_count_label(self, obj, albumCount:int) -> str:
        return ngettext("{} Album", "{} Albums", albumCount).format(albumCount)

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



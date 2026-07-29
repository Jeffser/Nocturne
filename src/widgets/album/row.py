# row.py

from gi.repository import Gtk, Adw, GLib, Gio, Gdk
from ...integrations import get_current_integration
from ...constants import CONTEXT_ALBUM
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/row.ui')
class AlbumRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneAlbumRow'

    cover_el = Gtk.Template.Child()
    menu_button_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id)
        super().__init__()
        self.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'artist', self.update_artist)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)

        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        settings.bind(
            "show-context-button",
            self.menu_button_el,
            "visible",
            Gio.SettingsBindFlags.DEFAULT
        )

    def update_cover(self, paintable):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
            self.cover_el.set_pixel_size(48)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-queue-symbolic")
            self.cover_el.set_pixel_size(-1)

    def update_name(self, name:str):
        self.set_title(name)
        self.set_name(name)

    def update_artist(self, artist:str):
        self.set_subtitle(artist or "")

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



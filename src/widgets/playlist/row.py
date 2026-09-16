# row.py

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration
from ...constants import CONTEXT_PLAYLIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/row.ui')
class PlaylistRow(Adw.ActionRow):
    __gtype_name__ = 'NocturnePlaylistRow'

    cover_el = Gtk.Template.Child()
    menu_button_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id, minimal=True)
        super().__init__()
        self.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
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
            self.cover_el.set_from_icon_name("music-note-symbolic")
            self.cover_el.set_pixel_size(-1)

    def update_name(self, name:str):
        self.set_title(name)
        self.set_name(name)

    def update_song_count(self, songCount:int):
        self.set_subtitle(ngettext("{} Song", "{} Songs", songCount).format(songCount))

    @Gtk.Template.Callback()
    def on_context_button_active(self, button, gparam):
        context = CONTEXT_PLAYLIST.copy()
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

        context = CONTEXT_PLAYLIST.copy()
        if 'no-downloads' in get_current_integration().limitations:
            del context['download']

        popover = Gtk.Popover(
            child=ContextContainer(context, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()



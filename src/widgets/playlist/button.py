# button.py

from gi.repository import GObject, Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_PLAYLIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/button.ui')
class PlaylistButton(Gtk.Box):
    __gtype_name__ = 'NocturnePlaylistButton'

    model = GObject.Property(type=models.Playlist)

    play_el = Gtk.Template.Child()
    cover_button_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    name_label_el = Gtk.Template.Child()
    song_count_label_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id, minimal=True)
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )
        self.settings.connect("changed::button-size", lambda *_: self.update_size())

    def update_size(self):
        isBig = self.settings.get_value('button-size').unpack() == 'big'
        size = 240 if isBig else 180
        pixel_size = size if self.cover_el.get_paintable() is not None else -1
        self.cover_el.set_size_request(size, size)
        self.cover_el.set_pixel_size(pixel_size)
        if isBig:
            self.name_label_el.remove_css_class('title-4')
            self.name_label_el.add_css_class('title-3')
        else:
            self.name_label_el.remove_css_class('title-3')
            self.name_label_el.add_css_class('title-4')

    @Gtk.Template.Callback()
    def format_paintable(self, obj, paintable:Gdk.Paintable) -> Gdk.Paintable:
        GLib.idle_add(self.update_size)
        return paintable

    @Gtk.Template.Callback()
    def format_to_bool(self, obj, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def format_song_count(self, obj, songCount:int):
        return ngettext("{} Song", "{} Songs", songCount).format(songCount)

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        context = CONTEXT_PLAYLIST.copy()
        if root := self.get_root():
            if app := root.get_application():
                if integration := app.get_property('integration'):
                    if 'no-downloads' in integration.limitations:
                        del context['download']

        popover = Gtk.Popover(
            child=ContextContainer(context, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()


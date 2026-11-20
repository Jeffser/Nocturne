# selector_row.py

from gi.repository import GObject, Gtk, Adw, Gdk
from ...integrations import get_current_integration, models

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/selector_row.ui')
class PlaylistSelectorRow(Adw.ActionRow):
    __gtype_name__ = 'NocturnePlaylistSelectorRow'

    model = GObject.Property(type=models.Playlist)

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id)
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )

    @Gtk.Template.Callback()
    def format_tooltip_text(self, obj, name:str) -> str:
        return _("Add Songs to '{}'").format(name)

    @Gtk.Template.Callback()
    def format_song_count(self, obj, songCount:int):
        return ngettext("{} Song", "{} Songs", songCount).format(songCount)

    @Gtk.Template.Callback()
    def format_cover_paintable(self, obj, has_paintable:bool, model_id:str, size_key:str) -> Gdk.Paintable:
        if has_paintable:
            self.cover_el.remove_css_class('p12')
            return get_cover_art(model_id, size_key)
        else:
            self.cover_el.add_css_class('p12')
            return Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).lookup_icon(
                'playlist-symbolic',
                None,
                get_cover_size(size_key) / 2,
                1,
                Gtk.TextDirection.NONE,
                0
            )

    @Gtk.Template.Callback()
    def format_pixel_size(self, obj, has_paintable:bool, size_key:str) -> int:
        size = get_cover_size(size_key, dp=True)
        return size if has_paintable else size/2


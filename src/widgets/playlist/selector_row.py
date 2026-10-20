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
    def format_paintable_pixel_size(self, obj, paintable:Gdk.Paintable):
        return 48 if paintable else -1


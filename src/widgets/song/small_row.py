# small_row.py

from gi.repository import GObject, Gtk, Adw, Gdk, GLib
from ...integrations import get_current_integration, models
from ..containers import ContextContainer
from ...constants import CONTEXT_SONG

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/small_row.ui')
class SongSmallRow(Gtk.Button):
    __gtype_name__ = 'NocturneSongSmallRow'

    model = GObject.Property(type=models.Song)
    show_album_name = GObject.Property(type=bool, default=False)

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    subtitle_el = Gtk.Template.Child()

    def __init__(self, id:str, show_album_name:bool=False):
        self.id = id
        integration = get_current_integration()
        integration.verifySong(self.id, minimal=True)
        super().__init__(
            model=integration.loaded_models.get(self.id),
            show_album_name=show_album_name
        )
        integration.connect_to_model(self.id, 'deleted', self.delete_status_changed)

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_subtitle(self, obj, album:str, artist:str, show_album_name:bool) -> str:
        return album if show_album_name else artist

    @Gtk.Template.Callback()
    def format_pixel_size(self, obj, paintable:Gdk.Paintable) -> int:
        return 48 if paintable else -1

    def delete_status_changed(self, status:bool):
        if status:
            if wrapbox := self.get_ancestor(Adw.WrapBox):
                wrapbox.remove(self)

    def generate_context_menu(self) -> ContextContainer:
        integration = get_current_integration()
        context_dict = CONTEXT_SONG.copy()
        del context_dict["edit-radio"]
        del context_dict["delete-radio"]
        del context_dict["remove"]
        del context_dict["select"]

        context_dict['rating']['value'] = integration.loaded_models.get(self.id).get_property('userRating')

        context_dict["play-next"]["sensitive"] = integration.get_property('current-state').get_property('songId') != self.id
        context_dict["play-later"]["sensitive"] = integration.get_property('current-state').get_property('songId') != self.id

        if integration.__gtype_name__ == 'NocturneIntegrationOffline':
            context_dict["delete-download"]["sensitive"] = integration.get_property('current-state').get_property('songId') != self.id
        else:
            del context_dict["delete-download"]
        if 'no-downloads' in integration.limitations:
            del context_dict["download"]
        return ContextContainer(context_dict, self.id)

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=self.generate_context_menu(),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()


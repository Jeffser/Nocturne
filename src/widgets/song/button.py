# button.py

from gi.repository import GObject, Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_SONG, CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/button.ui')
class SongButton(Gtk.Box):
    __gtype_name__ = 'NocturneSongButton'

    model = GObject.Property(type=models.Song)

    cover_el = Gtk.Template.Child()
    cover_button_el = Gtk.Template.Child()
    play_indicator_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifySong(self.id, minimal=True)
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
            self.name_el.remove_css_class('title-4')
            self.name_el.add_css_class('title-3')
        else:
            self.name_el.remove_css_class('title-3')
            self.name_el.add_css_class('title-4')

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_cover_paintable(self, obj, paintable:Gdk.Paintable) -> Gdk.Paintable:
        GLib.idle_add(self.update_size)
        return paintable

    @Gtk.Template.Callback()
    def format_sensitive(self, obj, currentSongId:str) -> bool:
        if currentSongId == self.id:
            self.cover_button_el.add_css_class('accent')
            return False
        else:
            self.cover_button_el.remove_css_class('accent')
            return True

    def generate_context_menu(self) -> ContextContainer:
        integration = None
        if root := self.get_root():
            if app := root.get_application():
                integration = app.get_property('integration')
        context_dict = CONTEXT_SONG.copy()
        del context_dict["edit-radio"]
        del context_dict["delete-radio"]
        del context_dict["remove"]
        del context_dict["select"]

        currentSongId = ''
        if root := self.get_root():
            if app := root.get_application():
                if player := app.get_property('player'):
                    currentSongId = player.get_property('songId')

        context_dict["play-next"]["sensitive"] = currentSongId != self.id
        context_dict["play-later"]["sensitive"] = currentSongId != self.id

        if integration:
            context_dict['rating']['value'] = integration.loaded_models.get(self.id).get_property('userRating')

        if integration and integration.__gtype_name__ == 'NocturneIntegrationOffline':
            context_dict["delete-download"]["sensitive"] = currentSongId != self.id
        else:
            del context_dict["delete-download"]
        if not integration or 'no-downloads' in integration.limitations:
            del context_dict["download"]
        return ContextContainer(context_dict, self.id)

    @Gtk.Template.Callback()
    def show_popover_image(self, *args):
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

    @Gtk.Template.Callback()
    def show_popover_artist(self, *args):
        if root := self.get_root():
            if app := root.get_application():
                if integration := app.get_property('integration'):
                    if artist_id := integration.loaded_models.get(self.id).get_property('artistId'):
                        rect = Gdk.Rectangle()
                        if len(args) == 4:
                            rect.x, rect.y = args[2], args[3]
                        else:
                            rect.x, rect.y = args[1], args[2]

                        popover = Gtk.Popover(
                            child=ContextContainer(CONTEXT_ARTIST, artist_id),
                            pointing_to=rect,
                            has_arrow=False
                        )
                        popover.set_parent(self.artist_el)
                        popover.popup()

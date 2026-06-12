# button.py

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration
from ...constants import CONTEXT_SONG, CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/button.ui')
class SongButton(Gtk.Box):
    __gtype_name__ = 'NocturneSongButton'

    cover_el = Gtk.Template.Child()
    cover_button_el = Gtk.Template.Child()
    play_indicator_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifySong(self.id)
        super().__init__()

        self.cover_button_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.connect("changed::button-size", lambda *_: GLib.idle_add(self.update_size))

        integration.connect_to_model(self.id, 'title', self.update_name)
        integration.connect_to_model(self.id, 'artists', self.update_artists)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)
        integration.connect_to_model('currentSong', 'songId', self.current_song_changed)

        # Only fetch cover art once the widget is actually shown,
        # 'title' re-triggers in case metadata wasn't loaded yet at map time
        self.connect('map', self.request_cover)
        integration.connect_to_model(self.id, 'title', self.request_cover)

    def request_cover(self, *_):
        if self.get_mapped():
            get_current_integration().requestCoverArt(self.id)

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

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.cover_button_el.set_tooltip_text(name)
        self.set_name(name)

    def update_artists(self, artists:list):
        if artists:
            if artist_name := artists[0].get('name'):
                self.artist_el.get_child().set_label(artist_name)
                self.artist_el.set_tooltip_text(artist_name)
            if artist_id := artists[0].get('id'):
                self.artist_el.set_action_target_value(GLib.Variant('s', artist_id))
                self.artist_el.set_action_name('app.show_artist')
            return
        self.artist_el.get_child().set_label("")
        self.artist_el.set_tooltip_text("")

    def update_cover(self, paintable):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-queue-symbolic")
        self.update_size()

    def current_song_changed(self, songId):
        self.play_indicator_el.set_visible(self.id == songId)
        if self.id == songId:
            self.cover_button_el.set_action_name(None)
            self.cover_button_el.add_css_class('accent')
        else:
            self.cover_button_el.set_action_name("app.play_song")
            self.cover_button_el.remove_css_class('accent')

    def generate_context_menu(self) -> ContextContainer:
        integration = get_current_integration()
        context_dict = CONTEXT_SONG.copy()
        del context_dict["edit-radio"]
        del context_dict["delete-radio"]
        del context_dict["remove"]
        del context_dict["select"]

        context_dict["play-next"]["sensitive"] = integration.loaded_models.get('currentSong').get_property('songId') != self.id
        context_dict["play-later"]["sensitive"] = integration.loaded_models.get('currentSong').get_property('songId') != self.id

        context_dict['rating']['value'] = integration.loaded_models.get(self.id).get_property('userRating')

        if integration.__gtype_name__ == 'NocturneIntegrationOffline':
            context_dict["delete-download"]["sensitive"] = integration.loaded_models.get('currentSong').get_property('songId') != self.id
        else:
            del context_dict["delete-download"]
        if 'no-downloads' in integration.limitations:
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
        integration = get_current_integration()
        artist_id = integration.loaded_models.get(self.id).get_property('artistId')
        if artist_id:
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

# button.py

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration
from ...constants import CONTEXT_ALBUM, CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/button.ui')
class AlbumButton(Gtk.Box):
    __gtype_name__ = 'NocturneAlbumButton'

    play_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    cover_button_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_button_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    year_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()

    def __init__(self, id:str, show_year:bool=False):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id, minimal=True)
        super().__init__()

        self.play_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.cover_button_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.star_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.name_button_el.set_action_target_value(GLib.Variant.new_string(self.id))

        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.connect("changed::button-size", lambda *_: GLib.idle_add(self.update_size))

        self.show_year = show_year

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'artist', self.update_artist)
        integration.connect_to_model(self.id, 'artistId', self.update_artist_id)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)
        integration.connect_to_model(self.id, 'starred', self.update_starred)
        integration.connect_to_model(self.id, 'year', self.update_year)

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

    def update_cover(self, paintable:Gdk.Paintable=None):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-queue-symbolic")
        self.update_size()

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.name_button_el.set_tooltip_text(name)
        self.cover_button_el.set_tooltip_text(name)
        self.set_name(name)

    def update_artist(self, artist:str):
        self.artist_el.get_child().set_label(artist)
        self.artist_el.set_tooltip_text(artist)

    def update_year(self, year:int):
        if(year > 0):
            if self.show_year:
                self.year_el.set_label(str(year))
                self.year_el.set_visible(True)
        else:
            self.year_el.set_visible(False)

    def update_artist_id(self, artistId:str):
        if artistId:
            self.artist_el.set_action_target_value(GLib.Variant.new_string(artistId))
            self.artist_el.set_action_name("app.show_artist")
        else:
            self.artist_el.set_action_name("")

    def update_starred(self, starred:bool):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
            self.star_el.set_icon_name('heart-filled-symbolic')
            self.star_el.set_tooltip_text(_('Favorite'))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
            self.star_el.set_icon_name('heart-outline-thick-symbolic')
            self.star_el.set_tooltip_text(_('Not Favorite'))

    @Gtk.Template.Callback()
    def show_popover_image(self, *args):
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
        popover.set_parent(self.cover_button_el)
        popover.popup()

    @Gtk.Template.Callback()
    def show_popover_name(self, *args):
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
        popover.set_parent(self.name_button_el)
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

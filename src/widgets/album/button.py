# button.py

from gi.repository import Gtk, Adw, GLib, Gdk
from ...integrations import get_current_integration
from ...constants import CONTEXT_ALBUM, CONTEXT_ARTIST
from ..containers import ContextContainer
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/button.ui')
class AlbumButton(Gtk.Box):
    __gtype_name__ = 'NocturneAlbumButton'

    play_el = Gtk.Template.Child()
    favorite_el = Gtk.Template.Child()
    cover_button_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id)
        super().__init__()

        self.play_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.cover_button_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.favorite_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.name_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'artist', self.update_artist)
        integration.connect_to_model(self.id, 'artistId', self.update_artist_id)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)
        integration.connect_to_model(self.id, 'starred', self.update_starred)

    def update_cover(self, paintable:Gdk.Paintable=None):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
            self.cover_el.set_pixel_size(240)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-queue-symbolic")
            self.cover_el.set_pixel_size(-1)

    def update_name(self, name:str):
        self.name_el.get_child().set_label(name)
        self.name_el.set_tooltip_text(name)
        self.cover_button_el.set_tooltip_text(name)

    def update_artist(self, artist:str):
        self.artist_el.get_child().set_label(artist)
        self.artist_el.set_tooltip_text(artist)

    def update_artist_id(self, artistId:str):
        self.artist_el.set_action_target_value(GLib.Variant.new_string(artistId))

    def update_starred(self, starred:bool):
        if starred:
            self.favorite_el.add_css_class('accent')
            self.favorite_el.set_icon_name('heart-filled-symbolic')
            self.favorite_el.set_tooltip_text(_('Favorited'))
        else:
            self.favorite_el.remove_css_class('accent')
            self.favorite_el.set_icon_name('heart-outline-thick-symbolic')
            self.favorite_el.set_tooltip_text(_('Favorite'))

    @Gtk.Template.Callback()
    def show_popover_image(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=ContextContainer(CONTEXT_ALBUM, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self.play_el)
        popover.popup()

    @Gtk.Template.Callback()
    def show_popover_name(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=ContextContainer(CONTEXT_ALBUM, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self.name_el)
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

# button.py

from gi.repository import GObject, Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ALBUM, CONTEXT_ARTIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/button.ui')
class AlbumButton(Gtk.Box):
    __gtype_name__ = 'NocturneAlbumButton'

    model = GObject.Property(type=models.Album)
    show_year = GObject.Property(type=bool, default=False)

    artist_el = Gtk.Template.Child() # Used in artist page
    star_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()

    def __init__(self, id:str, show_year:bool=False):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id, minimal=True)
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.connect("changed::button-size", lambda *_: GLib.idle_add(self.update_size))
        super().__init__(
            model=integration.loaded_models.get(self.id),
            show_year=show_year
        )

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
    def format_starred_tooltip_text(self, obj, starred:bool) -> str:
        return _("Favorite") if starred else _("Not Favorite")

    @Gtk.Template.Callback()
    def format_starred_icon_name(self, obj, starred:bool) -> str:
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
        return "heart-filled-symbolic" if starred else "heart-outline-thick-symbolic"

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_year(self, obj, year:str, show_year:bool) -> str:
        return year if show_year else ''

    @Gtk.Template.Callback()
    def format_gdkPaintable(self, obj, paintable:Gdk.Paintable) -> Gdk.Paintable:
        GLib.idle_add(self.update_size)
        return paintable

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

        if model_id := self.get_property('model').get_property('id'):
            popover = Gtk.Popover(
                child=ContextContainer(context, model_id),
                pointing_to=rect,
                has_arrow=False
            )
            popover.set_parent(args[0].get_widget())
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

        if model_id := self.get_property('model').get_property('id'):
            popover = Gtk.Popover(
                child=ContextContainer(context, model_id),
                pointing_to=rect,
                has_arrow=False
            )
            popover.set_parent(args[0].get_widget())
            popover.popup()

    @Gtk.Template.Callback()
    def show_popover_artist(self, *args):
        integration = get_current_integration()
        if artist_id := self.get_property('model').get_property('artistId'):
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
            popover.set_parent(args[0].get_widget())
            popover.popup()

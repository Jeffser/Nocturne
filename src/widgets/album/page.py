# page.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from ..song import SongRow
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ALBUM
from ..containers import get_context_buttons_list
import threading, uuid, io
from colorthief import ColorThief

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/page.ui')
class AlbumPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneAlbumPage'

    clamp_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    song_list_el = Gtk.Template.Child()

    context_wrap_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id, True)
        super().__init__(
            tag=str(uuid.uuid4())
        )
        self.song_list_el.set_header(_("Songs"), "music-note-symbolic")

        self.star_el.set_action_target_value(GLib.Variant.new_string(self.id))
        context_buttons = get_context_buttons_list(CONTEXT_ALBUM, self.id)
        for btn in context_buttons:
            self.context_wrap_el.append(btn)

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'artist', self.update_artist)
        integration.connect_to_model(self.id, 'artistId', self.update_artist_id)
        integration.connect_to_model(self.id, 'starred', self.update_starred)
        integration.connect_to_model(self.id, 'song', self.update_song_list)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)
        integration.connect_to_model(self.id, 'gdkPaintableBytes', self.update_background)

    def update_cover(self, paintable:Gdk.Paintable=None):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
            self.cover_el.set_pixel_size(240)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-queue-symbolic")
            self.cover_el.set_pixel_size(-1)

    def update_background(self, gbytes:bytes):
        def run():
            if raw_bytes := gbytes.get_data():
                img_io = io.BytesIO(raw_bytes)
                color = ColorThief(img_io).get_color(quality=10)
                css = f"""
                clamp {{
                    transition: background .2s;
                    background: linear-gradient(180deg, color-mix(in srgb, rgb({','.join([str(c) for c in color])}) 50%, transparent), transparent 30%);
                    background-size: 100% 1000px;
                    background-repeat: no-repeat;
                }}
                """
                provider = Gtk.CssProvider()
                provider.load_from_data(css.encode())
                GLib.idle_add(self.clamp_el.get_style_context().add_provider,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        if gbytes:
            threading.Thread(target=run).start()

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.name_el.set_visible(name)
        self.set_title(name or _('Album'))

    def update_artist(self, artist:str):
        self.artist_el.set_label(artist)
        self.artist_el.set_visible(artist)
        self.artist_el.set_tooltip_text(artist)

    def update_artist_id(self, artistId:str):
        self.artist_el.set_action_target_value(GLib.Variant.new_string(artistId))

    def update_starred(self, starred:bool):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.set_icon_name('starred-symbolic')
            self.star_el.set_tooltip_text(_('Starred'))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.set_icon_name('non-starred-symbolic')
            self.star_el.set_tooltip_text(_('Star'))

    def update_song_list(self, song_list:list):
        self.song_list_el.list_el.remove_all()
        for song_dict in song_list:
            self.song_list_el.list_el.append(SongRow(song_dict.get('id')))
        self.song_list_el.main_stack.set_visible_child_name('content' if len(song_list) > 0 else 'no-content')
            

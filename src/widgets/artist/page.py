# page.py

from gi.repository import GObject, Gtk, Gdk, Adw, GLib, Pango
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ARTIST
from ..containers import get_context_buttons_list
from ..song import SongSmallRow
from ..album import AlbumButton
from .button import ArtistButton
import threading, io
from colorthief import ColorThief

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/page.ui')
class ArtistPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistPage'

    model = GObject.Property(type=models.Artist)

    clamp_el = Gtk.Template.Child()
    avatar_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    biography_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    top_songs_wrapbox = Gtk.Template.Child()
    album_wrapbox = Gtk.Template.Child()
    artist_carousel = Gtk.Template.Child()
    rating_container = Gtk.Template.Child()
    context_wrap_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id, True)
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )
        context_buttons = get_context_buttons_list(CONTEXT_ARTIST, self.id)
        for btn in context_buttons:
            self.context_wrap_el.append(btn)
        integration.connect_to_model(self.id, 'album', self.update_album_list)
        integration.connect_to_model(self.id, 'similarArtist', self.update_artist_list)
        self.top_songs_wrapbox.list_el.set_justify(Adw.JustifyMode.FILL)
        self.top_songs_wrapbox.list_el.set_justify_last_line(True)
        self.top_songs_wrapbox.list_el.set_child_spacing(5)
        self.top_songs_wrapbox.list_el.set_line_spacing(5)
        threading.Thread(target=self.update_top_songs, daemon=True).start()

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_to_bool(self, obj, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def format_rating_icon_name(self, obj, rating:int, index):
        return "starred-symbolic" if rating >= index else "non-starred-symbolic"

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
    def format_avatar_paintable(self, obj, paintable:Gdk.Paintable) -> Gdk.Paintable:
        if paintable:
            self.update_background(paintable.save_to_png_bytes().get_data())
        return paintable

    def update_top_songs(self):
        # call in different thread
        integration = get_current_integration()
        top_songs = integration.getTopSongs(self.id)
        self.top_songs_wrapbox.set_visible(len(top_songs) > 5)
        if len(top_songs) > 5:
            song_widgets = [SongSmallRow(song_id, show_album_name=True) for song_id in top_songs]
            self.top_songs_wrapbox.set_widgets(song_widgets)

    def update_background(self, raw_bytes:bytes):
        def run():
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
        if raw_bytes:
            threading.Thread(target=run, daemon=True).start()

    def update_album_list(self, album_list:list):
        if album_list:
            albums = [a.get('id') for a in album_list if isinstance(a, dict)]
            album_buttons = []
            for album in albums:
                button = AlbumButton(album)
                button.year_el.set_visible(True)
                button.artist_el.set_visible(False)
                button.set_halign(Gtk.Align.CENTER)
                button.name_el.remove_css_class('title-3')
                album_buttons.append(button)
            self.album_wrapbox.set_widgets(album_buttons)

    def update_artist_list(self, artist_list:list):
        artists = [a.get('id') for a in artist_list]
        self.artist_carousel.set_widgets([ArtistButton(id) for id in artists])

    # -- Callbacks --

    @Gtk.Template.Callback()
    def on_biography_clicked(self, button):
        if button.get_child().get_ellipsize() == Pango.EllipsizeMode.NONE:
            button.get_child().set_ellipsize(Pango.EllipsizeMode.END)
        else:
            button.get_child().set_ellipsize(Pango.EllipsizeMode.NONE)

    @Gtk.Template.Callback()
    def change_rating(self, button):
        integration = get_current_integration()
        target_value = GLib.Variant('a{sv}', {
            'model_id': GLib.Variant('s', self.id),
            'rating': GLib.Variant('i', int(button.get_name()))
        })
        self.get_root().activate_action("app.set_rating", target_value)

    def reload(self):
        pass

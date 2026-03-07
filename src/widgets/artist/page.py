# page.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from ...navidrome import get_current_integration
from ..album import AlbumButton
from .button import ArtistButton
import threading, uuid
from datetime import datetime

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/page.ui')
class ArtistPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistPage'

    avatar_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    biography_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    album_label_el = Gtk.Template.Child()
    album_list_el = Gtk.Template.Child()
    artist_label_el = Gtk.Template.Child()
    artist_list_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyArtist(self.id, True)
        super().__init__(
            tag=str(uuid.uuid4()),
        )

        self.star_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'biography', self.update_biography)
        integration.connect_to_model(self.id, 'starred', self.update_starred)
        integration.connect_to_model(self.id, 'album', self.update_album_list)
        integration.connect_to_model(self.id, 'similarArtist', self.update_artist_list)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(coverArt, 480)
            if isinstance(paintable, Gdk.MemoryTexture):
                GLib.idle_add(self.avatar_el.set_custom_image, paintable)
            else:
                GLib.idle_add(self.avatar_el.set_custom_image, None)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.name_el.set_visible(name)
        self.set_title(name or _('Author'))

    def update_biography(self, biography:str):
        self.biography_el.set_label(biography)
        self.biography_el.set_visible(biography)

    def update_starred(self, starred:str):
        if starred:
            self.star_el.add_css_class('suggested-action')
            self.star_el.set_icon_name('starred-symbolic')
            local_dt = datetime.fromisoformat(starred).astimezone()
            self.star_el.set_tooltip_text(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.star_el.remove_css_class('suggested-action')
            self.star_el.set_icon_name('non-starred-symbolic')
            self.star_el.set_tooltip_text(_('Star'))

    def update_album_list(self, album_list:list):
        for el in list(self.album_list_el):
            self.album_list_el.remove(el)

        for album_dict in album_list:
            button = AlbumButton(album_dict.get('id'))
            button.artist_el.set_visible(False)
            button.set_halign(Gtk.Align.CENTER)
            button.name_el.remove_css_class('title-3')
            self.album_list_el.prepend(button)

        self.album_label_el.set_visible(album_list)
        self.album_list_el.set_visible(album_list)

    def update_artist_list(self, artist_list:list):
        for i in range(self.artist_list_el.get_n_pages()):
            page = self.artist_list_el.get_nth_page(i)
            if page:
                self.artist_list_el.remove(page)

        for artist_dict in artist_list:
            self.artist_list_el.prepend(ArtistButton(artist_dict.get('id')))

        self.artist_label_el.set_visible(artist_list)
        self.artist_list_el.set_visible(artist_list)

    # -- Callbacks --

    @Gtk.Template.Callback()
    def on_biography_pressed(self, gesture, n_press, x, y):
        if n_press == 1:
            if self.biography_el.get_ellipsize() == Pango.EllipsizeMode.NONE:
                self.biography_el.set_ellipsize(Pango.EllipsizeMode.END)
            else:
                self.biography_el.set_ellipsize(Pango.EllipsizeMode.NONE)


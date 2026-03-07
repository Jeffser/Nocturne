# home.py

from gi.repository import Gtk, Adw
from ...navidrome import get_current_integration
from ..album import AlbumButton
from ..artist import ArtistButton
from ..playlist import PlaylistButton

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/home.ui')
class HomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneHomePage'

    album_list_el = Gtk.Template.Child()
    artist_list_el = Gtk.Template.Child()
    playlist_list_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.update_album_list()
        self.update_artist_list()
        self.update_playlist_list()

    def update_album_list(self):
        for i in range(self.album_list_el.get_n_pages()):
            page = self.album_list_el.get_nth_page(i)
            if page:
                self.album_list_el.remove(page)

        integration = get_current_integration()

        for album_id in integration.getAlbumList():
            self.album_list_el.append(AlbumButton(album_id))

    def update_artist_list(self):
        for i in range(self.artist_list_el.get_n_pages()):
            page = self.artist_list_el.get_nth_page(i)
            if page:
                self.artist_list_el.remove(page)

        integration = get_current_integration()

        for artist_id in integration.getArtists():
            self.artist_list_el.append(ArtistButton(artist_id))

    def update_playlist_list(self):
        for i in range(self.playlist_list_el.get_n_pages()):
            page = self.playlist_list_el.get_nth_page(i)
            if page:
                self.playlist_list_el.remove(page)

        integration = get_current_integration()

        for playlist_id in integration.getPlaylists():
            self.playlist_list_el.append(PlaylistButton(playlist_id))

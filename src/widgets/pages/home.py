# home.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio
from ...integrations import get_current_integration
from ..album import AlbumButton
from ..artist import ArtistButton
from ..playlist import PlaylistButton
from ..song import SongSmallRow

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/home.ui')
class HomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneHomePage'

    main_stack = Gtk.Template.Child()
    song_wrapbox = Gtk.Template.Child()
    album_carousel = Gtk.Template.Child()
    artist_carousel = Gtk.Template.Child()
    playlist_carousel = Gtk.Template.Child()

    def reload(self):
        # call in different thread
        integration = get_current_integration()
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        max_songs = settings.get_value('n-songs-home').unpack()
        max_albums = settings.get_value('n-albums-home').unpack()
        max_artists = settings.get_value('n-artists-home').unpack()
        max_playlists = settings.get_value('n-playlists-home').unpack()

        # -- Songs --
        self.song_wrapbox.set_header(
            label=_("Songs"),
            icon_name="music-note-symbolic",
            page_tag="songs"
        )
        self.song_wrapbox.list_el.set_margin_start(10)
        self.song_wrapbox.list_el.set_margin_end(10)
        self.song_wrapbox.list_el.set_justify(Adw.JustifyMode.FILL)
        self.song_wrapbox.list_el.set_justify_last_line(True)
        self.song_wrapbox.list_el.set_child_spacing(5)
        self.song_wrapbox.list_el.set_line_spacing(5)
        songs = integration.getRandomSongs(size=max_songs) if max_songs > 0 else []
        GLib.idle_add(self.song_wrapbox.set_widgets, [SongSmallRow(id) for id in songs])

        # -- Albums --
        self.album_carousel.set_header(
            label=_("Albums"),
            icon_name="music-queue-symbolic",
            page_tag="albums-all"
        )
        albums = integration.getAlbumList(size=max_albums) if max_albums > 0 else []
        GLib.idle_add(self.album_carousel.set_widgets, [AlbumButton(id) for id in albums])

        # -- Artists --
        self.artist_carousel.set_header(
            label=_("Artists"),
            icon_name="music-artist-symbolic",
            page_tag="artists"
        )
        artists = integration.getArtists(size=max_artists) if max_artists > 0 else []
        GLib.idle_add(self.artist_carousel.set_widgets, [ArtistButton(id) for id in artists])

        # -- Playlists --
        self.playlist_carousel.set_header(
            label=_("Playlists"),
            icon_name="playlist-symbolic",
            page_tag="playlists"
        )
        playlists = integration.getPlaylists()[:max_playlists]
        GLib.idle_add(self.playlist_carousel.set_widgets, [PlaylistButton(id) for id in playlists])

        n_elements = sum([len(s) for s in (songs, albums, artists, playlists)])
        self.main_stack.set_visible_child_name('content' if n_elements > 0 else 'no-content')

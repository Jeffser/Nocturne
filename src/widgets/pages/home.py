# home.py

from gi.repository import Gtk, Adw, GLib, Gio, Gdk
from ...integrations import get_current_integration
from ...constants import DATA_DIR
from ..album import AlbumButton
from ..artist import ArtistButton
from ..playlist import PlaylistButton
from ..song import SongSmallRow
import threading, os, io
from colorthief import ColorThief

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/home.ui')
class HomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneHomePage'

    header_bar = Gtk.Template.Child()
    search_toggle = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    main_clamp = Gtk.Template.Child()
    main_container = Gtk.Template.Child()
    frequent_album_carousel = Gtk.Template.Child()
    welcome_container = Gtk.Template.Child()
    welcome_avatar = Gtk.Template.Child()
    welcome_username_label = Gtk.Template.Child()
    song_wrapbox = Gtk.Template.Child()
    album_carousel = Gtk.Template.Child()
    artist_carousel = Gtk.Template.Child()
    playlist_carousel = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.css_provider = Gtk.CssProvider()
        self.main_clamp.get_style_context().add_provider(
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.max_frequent_albums = self.settings.get_value('n-frequent-albums-home').unpack()
        self.max_songs = self.settings.get_value('n-songs-home').unpack()
        self.max_albums = self.settings.get_value('n-albums-home').unpack()
        self.max_artists = self.settings.get_value('n-artists-home').unpack()
        self.max_playlists = self.settings.get_value('n-playlists-home').unpack()
        self.searching = False

        list(self.search_bar)[0].set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.song_wrapbox.list_el.set_margin_start(10)
        self.song_wrapbox.list_el.set_margin_end(10)
        self.song_wrapbox.list_el.set_justify(Adw.JustifyMode.FILL)
        self.song_wrapbox.list_el.set_justify_last_line(True)
        self.song_wrapbox.list_el.set_child_spacing(5)
        self.song_wrapbox.list_el.set_line_spacing(5)

    def get_default_results(self) -> dict:
        if integration := get_current_integration():
            frequent_albums = integration.getAlbumList(list_type="frequent", size=self.max_frequent_albums) if self.max_frequent_albums > 0 else []
            songs = integration.getRandomSongs(size=self.max_songs) if self.max_songs > 0 else []
            albums = integration.getAlbumList(list_type="random", size=self.max_albums) if self.max_albums > 0 else []
            artists = integration.getArtists(size=self.max_artists) if self.max_artists > 0 else []
            playlists = integration.getPlaylists()[:self.max_playlists]
            return {
                'frequent-album': frequent_albums,
                'song': songs,
                'album': albums,
                'artist': artists,
                'playlist': playlists
            }
        return {}

    def update_pfp_gradient(self, paintable):
        raw_bytes = paintable.save_to_png_bytes().get_data()
        if not raw_bytes:
            self.css_provider.load_from_data('clamp {background: none;}'.encode())
        img_io = io.BytesIO(raw_bytes)
        color = ColorThief(img_io).get_color(quality=10)
        css = f"""
        clamp {{
            transition: background .2s;
            background: linear-gradient(180deg, color-mix(in srgb, rgb({','.join([str(c) for c in color])}) 25%, transparent), transparent 30%);
            background-size: 100% 1000px;
            background-repeat: no-repeat;
        }}
        """
        self.css_provider.load_from_data(css.encode())

    def update_welcome_visibility(self):
        welcome_mode = self.settings.get_value("welcome-mode-home").unpack()
        welcome_username = self.settings.get_value("welcome-user-home").unpack()
        self.welcome_avatar.set_custom_image(None)
        self.css_provider.load_from_data('clamp {background: none;}'.encode())

        if welcome_mode and welcome_username:
            self.welcome_container.set_visible(True)
            try:
                pfp_destination_path = os.path.join(DATA_DIR, 'pfp')
                if os.path.isfile(pfp_destination_path):
                    if paintable := Gdk.Texture.new_from_filename(pfp_destination_path):
                        self.welcome_avatar.set_custom_image(paintable)
                        threading.Thread(target=self.update_pfp_gradient, args=(paintable,), daemon=True).start()
            except:
                self.welcome_avatar.set_custom_image(None)
            self.welcome_username_label.set_label(welcome_username)
        else:
            self.welcome_container.set_visible(False)

    def reload(self):
        self.max_frequent_albums = self.settings.get_value('n-frequent-albums-home').unpack()
        self.max_songs = self.settings.get_value('n-songs-home').unpack()
        self.max_albums = self.settings.get_value('n-albums-home').unpack()
        self.max_artists = self.settings.get_value('n-artists-home').unpack()
        self.max_playlists = self.settings.get_value('n-playlists-home').unpack()
        threading.Thread(target=self.search, daemon=True).start()
        GLib.idle_add(self.search_mode_toggled, self.search_toggle)
        GLib.idle_add(self.update_welcome_visibility)

    def reset(self):
        threading.Thread(target=self.frequent_album_carousel.set_widgets, args=([],), daemon=True).start()
        threading.Thread(target=self.song_wrapbox.set_widgets, args=([],), daemon=True).start()
        threading.Thread(target=self.album_carousel.set_widgets, args=([],), daemon=True).start()
        threading.Thread(target=self.artist_carousel.set_widgets, args=([],), daemon=True).start()
        threading.Thread(target=self.playlist_carousel.set_widgets, args=([],), daemon=True).start()

    def search(self):
        if self.searching:
            return
        self.searching = True
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        if integration := get_current_integration():
            if query := self.search_entry.get_text():
                search_results = integration.search(
                    query=query,
                    songCount=self.max_songs,
                    artistCount=self.max_artists,
                    albumCount=self.max_albums,
                    playlistCount=self.max_playlists
                )
                if self.settings.get_value('hide-singles').unpack():
                    if album_results := search_results.get('album'):
                        for albumId in album_results.copy():
                            if model := integration.loaded_models.get(albumId):
                                if model.get_property('songCount') <= 1:
                                    search_results['album'].remove(albumId)
            else:
                search_results = self.get_default_results()
            threading.Thread(
                target=self.frequent_album_carousel.set_widgets,
                args=([AlbumButton(id) for id in search_results.get('frequent-album') or []],),
                daemon=True
            ).start()
            threading.Thread(
                target=self.song_wrapbox.set_widgets,
                args=([SongSmallRow(id) for id in search_results.get('song') or []],),
                daemon=True
            ).start()
            threading.Thread(
                target=self.album_carousel.set_widgets,
                args=([AlbumButton(id) for id in search_results.get('album') or []],),
                daemon=True
            ).start()
            threading.Thread(
                target=self.artist_carousel.set_widgets,
                args=([ArtistButton(id) for id in search_results.get('artist') or []],),
                daemon=True
            ).start()
            threading.Thread(
                target=self.playlist_carousel.set_widgets,
                args=([PlaylistButton(id) for id in search_results.get('playlist') or []],),
                daemon=True
            ).start()
            has_results = any([len(search_results.get(key) or []) > 0 for key in list(search_results)])
        else:
            has_results = False
        GLib.idle_add(self.main_stack.set_visible_child_name, 'content' if has_results else 'no-content')
        self.searching = False

    @Gtk.Template.Callback()
    def search_mode_toggled(self, button):
        self.main_container.set_margin_top(0 if button.get_active() else self.header_bar.get_height() or 46)

    @Gtk.Template.Callback()
    def on_search(self, entry):
        threading.Thread(target=self.search, daemon=True).start()

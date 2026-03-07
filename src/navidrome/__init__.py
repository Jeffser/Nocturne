# __init__.py


from gi.repository import Gtk, GLib, GObject, Gdk
from . import secret, models
import requests, random, threading

class Navidrome(GObject.Object):
    __gtype_name__ = 'NocturneNavidrome'

    base_url = GObject.Property(type=str)
    username = GObject.Property(type=str)

    def __init__(self, base_url:str, username:str):
        super().__init__()
        self.base_url = base_url
        self.username = username
        self.loaded_models = {
            'currentSong': models.CurrentSong()
        }

    def get_base_params(self) -> dict:
        salt, token = secret.get_hashed_password(self.username, self.base_url)
        return {
            'u': self.username,
            't': token,
            's': salt,
            'v': '1.16.1',
            'c': 'Nocturne',
            'f': 'json'
        }

    def get_url(self, action:str) -> str:
        return '{}/rest/{}'.format(self.base_url.strip('/'), action)

    def make_request(self, action:str, params:dict={}) -> dict:
        params = {
            **self.get_base_params(),
            **params
        }
        response = requests.get(self.get_url(action), params=params)
        if response.status_code == 200:
            return response.json().get('subsonic-response', {})
        return {}

    # ----------- #

    def connect_to_model(self, id:str, parameter:str, callback:callable, use_gtk_thread:bool=True) -> str:
        # returns connection id so it can be disconnected if needed, mostly used by currentSong
        connection_id = ""
        if id in self.loaded_models:
            if use_gtk_thread:
                connection_id = self.loaded_models[id].connect(
                    'notify::{}'.format(parameter),
                    lambda *_, parameter=parameter, id=id: GLib.idle_add(callback, self.loaded_models[id].get_property(parameter))
                )
                GLib.idle_add(callback, self.loaded_models[id].get_property(parameter))
            else:
                connection_id = self.loaded_models[id].connect(
                    'notify::{}'.format(parameter),
                    lambda *_, parameter=parameter, id=id: callback(self.loaded_models[id].get_property(parameter))
                )
                callback(self.loaded_models[id].get_property(parameter))

        return connection_id

    def get_stream_url(self, song_id:str) -> str:
        # streams are handled by gst not requests
        params = self.get_base_params()
        params['id'] = song_id
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return '{}/rest/stream?{}'.format(self.base_url.strip('/'), query_string)

    def getCoverArtWithBytes(self, id:str=None, size:int=480) -> tuple:
        # returns bytes, Gdk.Paintable
        if id:
            params = {
                **self.get_base_params(),
                'id': id,
                'size': size
            }
            response = requests.get(self.get_url('getCoverArt'), params=params)
            response_bytes = response.content if response.status_code == 200 else b''

            if response_bytes and len(response_bytes) > 0:
                try:
                    return response_bytes, Gdk.Texture.new_from_bytes(GLib.Bytes.new(response_bytes))
                except Exception as e:
                    print('Texture error:', e)

        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        return b'', theme.lookup_icon(
            'image-missing-symbolic',
            None,
            size,
            1,
            Gtk.TextDirection.NONE,
            0
        )

    def getCoverArt(self, id:str=None, size:int=480) -> Gdk.Paintable:
        # Returns a paintable at the specified size, should be used directly in GTK without modifications
        # It also returns a pretty icon as a fallback if it fails for some reason
        return self.getCoverArtWithBytes(id, size)[1]

    def ping(self) -> bool:
        response = self.make_request('ping')
        return response.get('status') == 'ok'

    def getAlbumList(self, list_type:str="frequent", size:int=10, offset:int=0) -> list:
        # list_type = random, newest, frequent, recent, starred, alphabeticalByName, alphabeticalByArtist
        # returns a list of IDs
        params = {
            'type': list_type,
            'size': size,
            'offset': offset
        }
        response = self.make_request('getAlbumList2', params)

        album_ids = []
        for album_dict in response.get('albumList2', {}).get('album', []):
            new_id = album_dict.get('id')
            if new_id:
                album_ids.append(new_id)
                if new_id in self.loaded_models:
                    self.loaded_models.get(new_id).update_data(**album_dict)
                else:
                    self.loaded_models[new_id] = models.Album(**album_dict)

        return album_ids

    def getArtists(self, size:int=10) -> list:
        # if size == -1 then it will return every artist id in their names alphabetical order
        response = self.make_request('getArtists')

        artist_dicts = []
        for index in response.get('artists').get('index', []):
            artist_dicts.extend(index.get('artist', []))

        if size != -1:
            # randomize the dicts
            artist_dicts = random.sample(artist_dicts, size)

        artist_ids = []
        for artist_dict in artist_dicts:
            new_id = artist_dict.get('id')
            if new_id:
                artist_ids.append(new_id)
                if new_id in self.loaded_models:
                    self.loaded_models.get(new_id).update_data(**artist_dict)
                else:
                    self.loaded_models[new_id] = models.Artist(**artist_dict)
        return artist_ids

    def getPlaylists(self) -> list:
        # returns list of playlist ids
        response = self.make_request('getPlaylists')

        playlist_ids = []
        for playlist_dict in response.get('playlists', {}).get('playlist', []):
            new_id = playlist_dict.get('id')
            if new_id:
                playlist_ids.append(new_id)
                if new_id in self.loaded_models:
                    self.loaded_models.get(new_id).update_data(**playlist_dict)
                else:
                    self.loaded_models[new_id] = models.Playlist(**playlist_dict)
        return playlist_ids

    def verifyArtist(self, id:str, force_update:bool=False, update_callback:callable=None):
        def update():
            base_response = self.make_request('getArtist', {'id': id})
            base_artist = base_response.get('artist', {})
            detail_response = self.make_request('getArtistInfo2', {'id': id})
            detail_artist = detail_response.get('artistInfo2', {})
            artist_dict = {**base_artist, **detail_artist}
            self.loaded_models[id].update_data(**artist_dict)
            if update_callback:
                update_callback()

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Artist(id=id)
            threading.Thread(target=update).start()
        elif force_update:
            threading.Thread(target=update).start()

    def verifyAlbum(self, id:str, force_update:bool=False, update_callback:callable=None):
        def update():
            response = self.make_request('getAlbum', {'id': id})
            album_dict = response.get('album', {})
            self.loaded_models[id].update_data(**album_dict)
            if update_callback:
                update_callback()

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Album(id=id)
            threading.Thread(target=update).start()
        elif force_update:
            threading.Thread(target=update).start()

    def verifyPlaylist(self, id:str, force_update:bool=False, update_callback:callable=None):
        def update():
            response = self.make_request('getPlaylist', {'id': id})
            playlist_dict = response.get('playlist', {})
            self.loaded_models[id].update_data(**playlist_dict)
            if update_callback:
                update_callback()

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Playlist(id=id)
            threading.Thread(target=update).start()
        elif force_update:
            threading.Thread(target=update).start()

    def verifySong(self, id:str, force_update:bool=False, update_callback:callable=None):
        def update():
            response = self.make_request('getSong', {'id': id})
            song_dict = response.get('song', {})
            self.loaded_models[id].update_data(**song_dict)
            if update_callback:
                update_callback()

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Song(id=id)
            threading.Thread(target=update).start()
        elif force_update:
            threading.Thread(target=update).start()

    def star(self, id:str) -> bool:
        response = self.make_request('star', {'id': id})
        return response.get('status') == 'ok'

    def unstar(self, id:str) -> bool:
        response = self.make_request('unstar', {'id': id})
        return response.get('status') == 'ok'

integration = Navidrome('http://127.0.0.1:4533', 'tentri')
current_song = None

def get_current_integration():
    global integration
    return integration



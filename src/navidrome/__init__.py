# __init__.py


from gi.repository import Gtk, GLib, GObject, Gdk, Gio, GdkPixbuf
from . import secret, models
import requests, random, threading, favicon, io
from PIL import Image

class Integration(GObject.Object):
    __gtype_name__ = 'NocturneIntegration'

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
        salt, token = secret.get_hashed_password()
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
        try:
            response = requests.get(self.get_url(action), params=params)
            if response.status_code == 200:
                return response.json().get('subsonic-response', {})
        except Exception:
            pass
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
        model = self.loaded_models[song_id]
        if model.isRadio:
            return model.streamUrl
        params = self.get_base_params()
        params['id'] = song_id
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return '{}/rest/stream?{}'.format(self.base_url.strip('/'), query_string)

    def getRadioCoverArtWithBytes(self, id:str=None) -> tuple:
        # returns bytes, Gdk.Paintable or None, None
        if id:
            model = self.loaded_models[id]
            homepage_url = ""
            if model:
                if model.gdkPaintable:
                    return model.gdkPaintableBytes, model.gdkPaintable
                if model.homePageUrl:
                    icons = favicon.get(model.homePageUrl)
                    if len(icons) > 0:
                        try:
                            response = requests.get(icons[0].url, timeout=5)
                            response.raise_for_status()
                            response_bytes = response.content
                            stream = io.BytesIO(response_bytes)
                            png_bytes = b''
                            with Image.open(stream) as img:
                                img = img.convert("RGBA")
                                png_buffer = io.BytesIO()
                                img.save(png_buffer, format="PNG")
                                png_bytes = png_buffer.getvalue()
                            texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(png_bytes))
                            model.set_property('coverArtUrl', icons[0].url)
                            model.set_property('gdkPaintableBytes', png_bytes)
                            model.set_property('gdkPaintable', texture)
                            return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                        except Exception as e:
                            pass

        return None, None

    def getCoverArtWithBytes(self, id:str=None) -> tuple:
        # returns bytes, Gdk.Paintable or None, None
        if id:
            model = self.loaded_models[id]
            if isinstance(model, models.Song) and model.isRadio:
                return self.getRadioCoverArtWithBytes(id)
            coverArtId = ""
            if model:
                if model.gdkPaintable:
                    return model.gdkPaintableBytes, model.gdkPaintable
                coverArtId = model.coverArt

            params = {
                **self.get_base_params(),
                'id': coverArtId,
                'size': 480
            }
            response = requests.get(self.get_url('getCoverArt'), params=params)
            response_bytes = response.content if response.status_code == 200 else b''

            if response_bytes and len(response_bytes) > 0:
                try:
                    texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(response_bytes))
                    model.set_property('coverArtUrl', '{}?{}'.format(integration.get_url('getCoverArt'), "&".join([f"{k}={v}" for k, v in params.items()])))
                    model.set_property('gdkPaintableBytes', response_bytes)
                    model.set_property('gdkPaintable', texture)
                    return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                except Exception as e:
                    pass

        return None, None

    def getCoverArt(self, id:str=None) -> Gdk.Paintable:
        # Returns a paintable at the specified size, should be used directly in GTK without modifications
        # It also returns a pretty icon as a fallback if it fails for some reason
        return self.getCoverArtWithBytes(id)[1]

    def ping(self) -> bool:
        try:
            response = self.make_request('ping')
            return response.get('status') == 'ok'
        except Exception:
            return False

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
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
        for index in response.get('artists', {}).get('index', []):
            artist_dicts.extend(index.get('artist', []))

        if len(artist_dicts) == 0:
            return []

        if size != -1:
            # randomize the dicts
            artist_dicts = random.sample(artist_dicts, min(size, len(artist_dicts)))

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

    def getArtistsIndexes(self) -> dict:
        response = self.make_request('getArtists')
        indexes = {}
        for index in response.get('artists').get('index', []):
            indexes[index.get('name')] = [artist.get('id') for artist in index.get('artist', [])]
        return indexes

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

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            base_response = self.make_request('getArtist', {'id': id})
            base_artist = base_response.get('artist', {})
            detail_response = self.make_request('getArtistInfo2', {'id': id})
            detail_artist = detail_response.get('artistInfo2', {})
            artist_dict = {**base_artist, **detail_artist}
            self.loaded_models[id].update_data(**artist_dict)

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Artist(id=id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update).start()
            else:
                update()

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            response = self.make_request('getAlbum', {'id': id})
            album_dict = response.get('album', {})
            self.loaded_models[id].update_data(**album_dict)

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Album(id=id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update).start()
            else:
                update()

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            response = self.make_request('getPlaylist', {'id': id})
            playlist_dict = response.get('playlist', {})
            self.loaded_models[id].update_data(**playlist_dict)

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Playlist(id=id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update).start()
            else:
                update()

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            response = self.make_request('getSong', {'id': id})
            song_dict = response.get('song', {})
            self.loaded_models[id].update_data(**song_dict)

        if id not in self.loaded_models:
            self.loaded_models[id] = models.Song(id=id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update).start()
            else:
                update()

    def star(self, id:str) -> bool:
        response = self.make_request('star', {'id': id})
        return response.get('status') == 'ok'

    def unstar(self, id:str) -> bool:
        response = self.make_request('unstar', {'id': id})
        return response.get('status') == 'ok'

    def getPlayQueue(self) -> tuple:
        # used to retrieve sessions from other clients *at launch*
        # returns currentId and list for queue
        response = self.make_request('getPlayQueue')
        play_queue = response.get('playQueue', {})
        song_list = play_queue.get('entry', [])
        for song_dict in song_list:
            if song_dict.get('id') not in self.loaded_models:
                self.loaded_models[id] = models.Song(**song_dict)
            else:
                self.verifySong(self, force_update=True)

        return play_queue.get('current'), [s.get('id') for s in song_list]

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        # used to save session *on close* so that other clients can retrieve it
        # position is in ms
        # return true if ok
        response = self.make_request('savePlayQueue', {
            'id': id_list,
            'current': current,
            'position': position
        })
        return response.get('status') == 'ok'

    def getSimilarSongs(self, id:str, count:int=20) -> list:
        # Receives an artist id
        response = self.make_request('getSimilarSongs', {
            'id': id,
            'count': count
        })
        songs = response.get('similarSongs', {}).get('song', [])
        for song in songs:
            self.verifySong(song.get('id'))

        return [s.get('id') for s in songs if s.get('id')]

    def getRandomSongs(self, size:int=20) -> list:
        response = self.make_request('getRandomSongs', {
            'size': size
        })
        songs = response.get('randomSongs', {}).get('song', [])
        for song in songs:
            self.verifySong(song.get('id'))

        return [s.get('id') for s in songs if s.get('id')]

    def getLyrics(self, track_name:str, artist_name:str, album_name:str, duration:int) -> dict:
        # This uses the LRCLIB public API
        # Duration is in seconds
        response = requests.get('https://lrclib.net/api/get', params={
            'track_name': track_name,
            'artist_name': artist_name,
            'album_name': album_name,
            'duration': duration
        })
        return response.json()

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0) -> dict:
        response = self.make_request('search3', {
            'query': query,
            'artistCount': artistCount,
            'artistOffset': artistOffset,
            'albumCount': albumCount,
            'albumOffset': albumOffset,
            'songCount': songCount,
            'songOffset': songOffset
        })
        search_results = response.get('searchResult3')
        for model in search_results.get('artist', []):
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Artist(**model)
        for model in search_results.get('album', []):
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Album(**model)
        for model in search_results.get('song', []):
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Song(**model)

        return {
            'artist': [m.get('id') for m in search_results.get('artist', [])],
            'album': [m.get('id') for m in search_results.get('album', [])],
            'song': [m.get('id') for m in search_results.get('song', [])],
        }

    def getInternetRadioStations(self) -> list:
        response = self.make_request('getInternetRadioStations')
        radios = response.get('internetRadioStations', {}).get('internetRadioStation', [])
        for radio in radios:
            if radio.get('id') not in self.loaded_models:
                self.loaded_models[radio.get('id')] = models.Song(
                    id=radio.get('id'),
                    title=radio.get('name'),
                    streamUrl=radio.get('streamUrl'),
                    homePageUrl=radio.get('homePageUrl'),
                    duration=-1,
                    isRadio=True
                )
        return [radio.get('id') for radio in radios]

    def createInternetRadioStation(self, name:str, streamUrl:str, homepageUrl:str) -> bool:
        # returns true if ok
        response = self.make_request('createInternetRadioStation', {
            'name': name,
            'streamUrl': streamUrl,
            'homepageUrl': homepageUrl
        })
        return response.get('status') == 'ok'

    def updateInternetRadioStation(self, id:str, name:str, streamUrl:str, homepageUrl:str) -> bool:
        # returns true if ok
        response = self.make_request('updateInternetRadioStation', {
            'id': id,
            'name': name,
            'streamUrl': streamUrl,
            'homepageUrl': homepageUrl
        })
        return response.get('status') == 'ok'

    def deleteInternetRadioStation(self, id:str) -> bool:
        # returns true if ok
        response = self.make_request('deleteInternetRadioStation', {
            'id': id
        })
        return response.get('status') == 'ok'

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        # returns id
        # if playlistId is added then the name is updated
        response = self.make_request('createPlaylist', {
            'playlistId': playlistId,
            'name': name,
            'songId': songId
        })
        return response.get('playlist', {}).get('id')

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        # returns true if ok
        response = self.make_request('updatePlaylist', {
            'playlistId': playlistId,
            'songIdToAdd': songIdToAdd,
            'songIndexToRemove': songIndexToRemove
        })
        return response.get('status') == 'ok'

    def deletePlaylist(self, id:str) -> bool:
        # returns true if ok
        response = self.make_request('deletePlaylist', {
            'id': id
        })
        return response.get('status') == 'ok'

    def scrobble(self, id:str):
        # Registers the song as played, useful for keeping track of "most played" albums and the sorts
        self.make_request('scrobble', {
            'id': id
        })

integration = None

def ping_without_login(url:str) -> bool:
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('subsonic-response') is not None
    return False

def get_current_integration():
    global integration
    return integration

def set_current_integration(new_integration):
    global integration
    integration = new_integration

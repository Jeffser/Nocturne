# navidrome.py

from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Gio, GdkPixbuf
from . import secret, models, local
from ..constants import get_navidrome_path, check_if_navidrome_ready, get_navidrome_env, CONTEXT_MANAGED_NAVIDROME_SERVER, DOWNLOAD_QUEUE_DIR, DOWNLOADS_DIR, DOWNLOAD_MIME_MAP
from .base import Base
import requests, random, threading, io, subprocess, shutil, os
from PIL import Image
from urllib.parse import urlencode, urlparse

class Navidrome(Base):
    __gtype_name__ = 'NocturneIntegrationNavidrome'
    _use_apikey_auth = False

    login_page_metadata = {
        'icon-name': "network-server-symbolic",
        'title': "External Server",
        'description': _("Connect to an OpenSubsonic server like Navidrome."),
        'entries': ['url', 'user', 'password', 'trust-server']
    }
    button_metadata = {
        'title': _("External Server"),
        'subtitle': _("Use an existing OpenSubsonic / Navidrome instance")
    }

    url = GObject.Property(type=str, default="http://127.0.0.1:4533")

    def get_base_params(self) -> dict:
        params = {
            'v': '1.16.1',
            'c': 'Nocturne',
            'f': 'json'
        }
        if self._use_apikey_auth:
            params['apiKey'] = secret.get_plain_password()
        else:
            salt, token = secret.get_hashed_password()
            params['u'] = self.get_property('user')
            params['t'] = token
            params['s'] = salt
        return params

    def get_url(self, action:str) -> str:
        return '{}/rest/{}'.format(self.get_property('url').strip('/'), action)

    def send_request(self, action: str, params:dict={}) -> requests.Response:
        return requests.get(
            self.get_url(action),
            params={**self.get_base_params(), **params},
            verify=not self.get_property('trustServer')
        )

    def make_request(self, action:str, params:dict={}) -> dict:
        try:
            response = self.send_request(action, params)
            if response.status_code == 200:
                data = response.json().get('subsonic-response', {})
                if data.get('status') == 'failed' and data.get('error', {}).get('code') == 41:
                    self._use_apikey_auth = True
                    response = self.send_request(action, params)
                    if response.status_code == 200:
                        return response.json().get('subsonic-response', {})
                return data
        except Exception:
            pass
        return {}

    # ----------- #

    def get_stream_url(self, song_id:str) -> str:
        # streams are handled by gst not requests
        model = self.loaded_models.get(song_id)
        if not model or (model.get_property('artistId') and not model.get_property('artists')):
            self.verifySong(song_id, force_update=True, use_threading=False)
        model = self.loaded_models.get(song_id)

        if radioStreamUrl := model.get_property('radioStreamUrl'):
            return radioStreamUrl
        elif model.get_property('isExternalFile'):
            return 'file://{}'.format(model.get_property('path'))
        max_bitrate = Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('max-bitrate').unpack()
        params = self.get_base_params()
        params['id'] = song_id
        if max_bitrate != 0:
            params['maxBitRate'] = max_bitrate
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return '{}/rest/stream?{}'.format(self.get_property('url').strip('/'), query_string)

    def getCoverArt(self, model_id:str='', big:bool=False) -> Gdk.Paintable:
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('radioStreamUrl'):
                return None
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                return local.Local.getCoverArt(self, model_id, big=big)
            if not big and model.get_property('gdkPaintable'):
                return model.get_property('gdkPaintable')

            params = {
                **self.get_base_params(),
                'id': model.get_property('coverArt') or model.get_property('id'),
                'size': 720 if big else 240
            }
            response = requests.get(
                self.get_url('getCoverArt'),
                params=params,
                verify=not self.get_property('trustServer')
            )
            response_bytes = response.content if response.status_code == 200 else b''

            if response_bytes and len(response_bytes) > 0:
                try:
                    gbytes = GLib.Bytes.new(response_bytes)
                    texture = Gdk.Texture.new_from_bytes(gbytes)
                    if big:
                        return texture
                    model.set_property('gdkPaintable', texture)
                    return model.get_property('gdkPaintable')
                except Exception as e:
                    pass
        return None

    def getCoverArtUrl(self, model_id:str='', big:bool=False) -> str:
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and (model.get_property('radioStreamUrl') or model.get_property('isExternalFile')):
                return ""
            params = {
                **self.get_base_params(),
                'id': model.get_property('coverArt') or model.get_property('id'),
                'size': 720 if big else 240
            }
            return '{}?{}'.format(self.get_url('getCoverArt'), urlencode(params))
        return ""

    def ping(self) -> bool:
        try:
            response = self.make_request('ping')
            return response.get('status') == 'ok' and super().ping()
        except Exception:
            return False

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        # returns a list of IDs
        params = {
            'type': list_type,
            'size': size,
            'offset': offset
        }
        response = self.make_request('getAlbumList2', params)

        album_ids = []
        for album_dict in response.get('albumList2', {}).get('album', []):
            if new_id := str(album_dict.get('id', '')):
                album_dict['id'] = new_id
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
            if new_id := str(artist_dict.get('id', '')):
                artist_dict['id'] = new_id
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
            if new_id := str(playlist_dict.get('id', '')):
                playlist_dict['id'] = new_id
                playlist_ids.append(new_id)
                if new_id in self.loaded_models:
                    self.loaded_models.get(new_id).update_data(**playlist_dict)
                else:
                    self.loaded_models[new_id] = models.Playlist(**playlist_dict)
        return playlist_ids

    def getStarredSongs(self) -> list:
        songs = self.make_request('getStarred2').get('starred2', {}).get('song', [])
        return [song.get('id') for song in songs]

    def verifyArtist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            base_response = self.make_request('getArtist', {'id': model_id})
            base_artist = base_response.get('artist', {})
            detail_response = self.make_request('getArtistInfo2', {'id': model_id})
            detail_artist = detail_response.get('artistInfo2', {})
            if not isinstance(detail_artist, dict):
                detail_artist = {}
            artist_dict = {**base_artist, **detail_artist}
            if artist_dict.get('id'):
                self.loaded_models.get(model_id).update_data(**artist_dict)
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models:
            self.loaded_models[model_id] = models.Artist(id=model_id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update, daemon=True).start()
            else:
                update()

        threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def verifyAlbum(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            response = self.make_request('getAlbum', {'id': model_id})
            album_dict = response.get('album', {})
            if album_dict.get('id'):
                self.loaded_models.get(model_id).update_data(**album_dict)
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models:
            self.loaded_models[model_id] = models.Album(id=model_id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update, daemon=True).start()
            else:
                update()

        threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def verifyPlaylist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            response = self.make_request('getPlaylist', {'id': model_id})
            playlist_dict = response.get('playlist', {})
            if playlist_dict.get('id'):
                self.loaded_models.get(model_id).update_data(**playlist_dict)
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models:
            self.loaded_models[model_id] = models.Playlist(id=model_id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update, daemon=True).start()
            else:
                update()

        threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def verifySong(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def update():
            response = self.make_request('getSong', {'id': model_id})
            song_dict = response.get('song', {})
            if song_dict.get('id'):
                if 'artists' not in song_dict and song_dict.get('artistId'):
                    song_dict['artists'] = [{
                        'id': song_dict.get('artistId'),
                        'name': song_dict.get('artist')
                    }]
                gains = song_dict.get('replayGain') or {}
                self.loaded_models.get(model_id).update_data(**song_dict, albumGain=gains.get('albumGain', 0.0), trackGain=gains.get('trackGain', 0.0))
                threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()
            elif model_id in self.loaded_models:
                self.loaded_models.get(model_id).set_property('deleted', True)
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models:
            self.loaded_models[model_id] = models.Song(id=model_id)
            force_update = True

        if force_update:
            if use_threading:
                threading.Thread(target=update, daemon=True).start()
            else:
                update()
        else:
            threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def star(self, model_id:str) -> bool:
        response = self.make_request('star', {'id': model_id})
        return response.get('status') == 'ok'

    def unstar(self, model_id:str) -> bool:
        response = self.make_request('unstar', {'id': model_id})
        return response.get('status') == 'ok'

    def getPlayQueue(self) -> tuple:
        # used to retrieve sessions from other clients *at launch*
        # returns currentId and list for queue
        response = self.make_request('getPlayQueue')
        play_queue = response.get('playQueue', {})
        song_list = play_queue.get('entry', [])
        for song_dict in song_list:
            new_id = str(song_dict.get('id', ''))
            if new_id not in self.loaded_models:
                song_dict['id'] = new_id
                self.loaded_models[new_id] = models.Song(**song_dict)
            else:
                self.verifySong(song_dict.get('id'), force_update=True)

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

    def getSimilarSongs(self, model_id:str, count:int=20) -> list:
        # Receives an artist id
        response = self.make_request('getSimilarSongs', {
            'id': model_id,
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

    def getLyrics(self, songId:str) -> dict:
        lyrics_data = self.make_request('getLyricsBySongId', {'id': songId}).get('lyricsList') or {}
        lyrics = (lyrics_data.get('structuredLyrics') or [{}])[0]

        if lyrics.get('synced', False):
            lrc_lines = []
            for line in lyrics.get('line', []):
                lrc_lines.append({
                    'ms': line.get('start'),
                    'content': line.get('value')
                })
            return {
                'type': 'lrc',
                'content': lrc_lines
            }
        return {'type': 'not-found'}

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
            model['id'] = str(model.get('id', ''))
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Artist(**model)
        for model in search_results.get('album', []):
            model['id'] = str(model.get('id', ''))
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Album(**model)
        for model in search_results.get('song', []):
            model['id'] = str(model.get('id', ''))
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
            radio['id'] = str(radio.get('id', ''))
            if radio.get('id') not in self.loaded_models:
                self.loaded_models[radio.get('id')] = models.Song(
                    id=radio.get('id'),
                    title=radio.get('name'),
                    radioStreamUrl=radio.get('streamUrl'),
                    duration=-1
                )
        return [radio.get('id') for radio in radios]

    def createInternetRadioStation(self, name:str, radioStreamUrl:str) -> bool:
        # returns true if ok
        parsedStreamUrl = urlparse(radioStreamUrl)
        response = self.make_request('createInternetRadioStation', {
            'name': name,
            'streamUrl': radioStreamUrl,
            'homepageUrl': '{}://{}'.format(parsedStreamUrl.scheme, parsedStreamUrl.netloc)
        })
        return response.get('status') == 'ok'

    def updateInternetRadioStation(self, model_id:str, name:str, radioStreamUrl:str) -> bool:
        # returns true if ok
        parsedStreamUrl = urlparse(radioStreamUrl)
        response = self.make_request('updateInternetRadioStation', {
            'id': model_id,
            'name': name,
            'streamUrl': radioStreamUrl,
            'homepageUrl': '{}://{}'.format(parsedStreamUrl.scheme, parsedStreamUrl.netloc)
        })
        return response.get('status') == 'ok'

    def deleteInternetRadioStation(self, model_id:str) -> bool:
        # returns true if ok
        response = self.make_request('deleteInternetRadioStation', {
            'id': model_id
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

    def deletePlaylist(self, model_id:str) -> bool:
        # returns true if ok
        response = self.make_request('deletePlaylist', {
            'id': model_id
        })
        return response.get('status') == 'ok'

    def setRating(self, model_id:str, rating:int=0) -> bool:
        response = self.make_request('setRating', {
            'id': model_id,
            'rating': rating
        })
        if response.get('status') == 'ok':
            self.loaded_models.get(model_id).set_property('userRating', rating)
            return True
        return False

    def getTopSongs(self, artist_id:str, count:int=10) -> list:
        model = self.loaded_models.get(artist_id)
        if not model or not model.get_property('name'):
            self.verifyArtist(artist_id, force_update=True, use_threading=False)
        top_songs = self.make_request('getTopSongs', {
            'artist': model.get_property('name'),
            'count': count
        }).get('topSongs', {}).get('song', [])
        return [song.get('id') for song in top_songs if song.get('id')]

    def downloadSong(self, model_id:str, file_title:str, progress_callback:callable):
        params = {
            **self.get_base_params(),
            'id': model_id
        }
        try:
            with requests.get(self.get_url('download'), params=params, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                extension = DOWNLOAD_MIME_MAP.get(r.headers.get('Content-Type'), '.mp3')
                file_name = '{}{}'.format(file_title, extension)
                file_path = os.path.join(DOWNLOAD_QUEUE_DIR, file_name)

                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress_callback(downloaded_size / total_size)
                os.replace(file_path, os.path.join(DOWNLOADS_DIR, file_name))
        except:
            pass

    def scrobble(self, model_id:str, submission:bool = True):
        # Registers the song as played, useful for keeping track of "most played" albums and the sorts
        if model := self.loaded_models.get(model_id) :
            if not model.isExternalFile:
                self.make_request('scrobble', {
                    'id': model_id,
                    'submission': submission
                })
        super().scrobble(model_id, submission)

    def getSongDetails(self, model_id:str) -> models.SongDetails:
        song_dict = self.make_request('getSong', {
            'id': model_id,
        }).get('song', {})
        song_dict['trackGain'] = song_dict.get('replayGain', {}).get('trackGain') or 0.0
        song_dict['albumGain'] = song_dict.get('replayGain', {}).get('albumGain') or 0.0
        return models.SongDetails(**song_dict)

    def getServerInformation(self) -> dict:
        server_information = {
            'link': self.get_property('url').strip('/'),
            'username': self.get_property('user').title()
        }
        try:
            response = requests.get(
                self.get_url('ping'),
                params=self.get_base_params(),
                verify=not self.get_property('trustServer')
            )
            if response.status_code == 200:
                data = response.json().get('subsonic-response', {})
                server_information['title'] = "{} {}".format(data.get('type'), data.get('serverVersion')).title()
        except Exception:
            pass

        try:
            params = {
                **self.get_base_params(),
                'username': self.get_property('user')
            }
            response = requests.get(
                self.get_url('getAvatar'),
                params=params,
                verify=not self.get_property('trustServer')
            )
            response_bytes = response.content if response.status_code == 200 else b''
            if response_bytes and len(response_bytes) > 0:
                gbytes = GLib.Bytes.new(response_bytes)
                server_information['picture'] = Gdk.Texture.new_from_bytes(gbytes)
        except Exception:
            pass

        return server_information

class NavidromeIntegrated(Navidrome):
    __gtype_name__ = 'NocturneIntegrationNavidromeIntegrated'

    login_page_metadata = {
        'icon-name': "music-note-symbolic",
        'title': _("Managed Server"),
        'description': _("Connect to a Navidrome instance directly managed by Nocturne."),
        'entries': ['status', 'library-dir', 'user', 'password'],
        'extra-menu': {
            'title': _("Manage Server"),
            'context': CONTEXT_MANAGED_NAVIDROME_SERVER
        }
    }
    button_metadata = {
        'title': _("Managed Server"),
        'subtitle': _("Create and use a Navidrome instance")
    }

    url = GObject.Property(type=str, default="http://127.0.0.1:4534")
    serverRunning = GObject.Property(type=bool, default=False)
    process = None

    def check_if_ready(self, row) -> bool:
        if get_navidrome_path():
            return True
        else:
            row.get_root().main_stack.set_visible_child_name('setup')
            row.get_root().main_stack.get_child_by_name('setup').set_integration(self)
        return False

    def start_instance(self) -> bool:
        path = get_navidrome_path()
        env = get_navidrome_env()
        library_directory = self.get_property('libraryDir')
        if self.process:
            return True

        try:
            if path and env and library_directory:
                env["ND_MUSICFOLDER"] = library_directory
                self.process = subprocess.Popen([path], env=env)
                self.set_property('serverRunning', True)
                return True
            else:
                self.set_property('serverRunning', False)
                return False
        except Exception as e:
            self.set_property('serverRunning', False)
            return False

    def terminate_instance(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self.set_property('serverRunning', False)

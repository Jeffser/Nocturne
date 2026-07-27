# navidrome.py

from gi.repository import GLib, GObject, Gdk, Gio
from . import secret, models, local, sql_instance
from ..constants import get_navidrome_path, get_navidrome_env, CONTEXT_MANAGED_NAVIDROME_SERVER, DOWNLOAD_QUEUE_DIR, DOWNLOADS_DIR, DOWNLOAD_MIME_MAP
from .base import Base
import random, threading, subprocess, os, re, logging, time, uuid
from urllib.parse import urlencode, urlparse

logger = logging.getLogger(__name__)

class Navidrome(Base):
    __gtype_name__ = 'NocturneIntegrationNavidrome'
    _use_apikey_auth = False

    login_page_metadata = {
        'icon-name': "opensubsonic-symbolic",
        'title': "External Server",
        'description': _("Connect to an OpenSubsonic server like Navidrome."),
        'entries': ['url', 'user', 'password', 'trust-server']
    }
    button_metadata = {
        'title': _("External Server"),
        'subtitle': _("Use an existing OpenSubsonic instance")
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
        return '{}/rest/{}'.format(self.get_property('url').strip('/'), action) + ('.view' if self.__gtype_name__ == 'NocturneIntegrationBandcamp' else '')

    def send_request(self, action:str, params:dict={}):
        def request_job(url, parameters) -> tuple:
            with self.session as current_session:
                result = current_session.get(
                    url,
                    params={**self.get_base_params(), **parameters},
                    verify=not self.get_property('trustServer')
                )
                return result.status_code in (200, 201), result
        action_url = self.get_url(action)
        request_id = '{}?{}&apikey={}'.format(action_url, urlencode(params), self._use_apikey_auth)
        return self.cache_manager.get_result(request_id, request_job, action_url, params)

    def make_request(self, action:str, params:dict={}) -> dict:
        try:
            response = self.send_request(action, params)
            if response.status_code in (200, 201):
                data = response.json().get('subsonic-response', {})
                if data.get('status') == 'failed' and data.get('error', {}).get('code') in (41, 42):
                    self._use_apikey_auth = True
                    response = self.send_request(action, params)
                    if response.status_code in (200, 201):
                        return response.json().get('subsonic-response', {})
                return data
        except Exception as e:
            logger.error(f"action error {action}: {e}")
        return {}

    # ----------- #

    def get_stream_url(self, song_id:str) -> str:
        # streams are handled by gst not requests
        if model := self.loaded_models.get(song_id):
            if radioStreamUrl := model.get_property('radioStreamUrl'):
                try:
                    with self.session.get(radioStreamUrl, stream=True, timeout=10) as r:
                        r.raise_for_status()
                        content_type = r.headers.get('Content-Type', '').lower()
                        if 'mpegurl' in content_type or 'text/plain' in content_type or 'octet-stream' in content_type:
                            # It is a playlist text file, extract url
                            for line in r.iter_lines(decode_unicode=True):
                                line = line.decode('utf-8')
                                if line and not line.startswith('#'):
                                    return line.strip()
                except:
                    pass
                return radioStreamUrl
            elif model.get_property('isExternalFile'):
                return 'file://{}'.format(model.get_property('path'))
        max_bitrate = Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('max-bitrate').unpack()
        params = self.get_base_params()
        params['id'] = song_id
        if max_bitrate != 0:
            params['maxBitRate'] = max_bitrate
        query_string = urlencode(params)
        return '{}/rest/stream?{}'.format(self.get_property('url').strip('/'), query_string)

    def getCoverArtBytes(self, model_id:str, size:int) -> bytes:
        try:
            cover_id = model_id
            if model := self.loaded_models.get(model_id):
                cover_id = model.get_property('coverArt') or model_id
            params={
                'id': cover_id
            }
            if size != -1:
                params['size'] = size
            response = self.send_request(
                action='getCoverArt',
                params=params
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"can't get image from {model_id}: {e}")
        return b''

    def updateCoverArt(self, model_id:str):
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                local.Local.updateCoverArt(self, model_id)
                return

            sizes = {
                'gdkPaintableBig': 720,
                'gdkPaintable': 240
            }
            for property_name, size in sizes.items():
                if not model.get_property(property_name):
                    raw_bytes = self.get_cache_image(model_id, size)
                    save_cache = not raw_bytes
                    if not raw_bytes:
                        raw_bytes = self.getCoverArtBytes(model_id, size)
                        if not raw_bytes and isinstance(model, models.Song):
                            raw_bytes = self.getCoverArtBytes(model.get_property('albumId'), size)
                            if raw_bytes:
                                model.set_property('coverArt', model.get_property('albumId')) # For getCoverArtUrl
                    if raw_bytes:
                        try:
                            gbytes = GLib.Bytes.new(raw_bytes)
                            texture = Gdk.Texture.new_from_bytes(gbytes)
                            model.set_property(property_name, texture)
                            if save_cache:
                                self.save_cache_image(model_id, size, raw_bytes)
                        except Exception as e:
                            logger.error(f"can't convert image from {model_id} (size {size}): {e}")

    def getCoverArtUrl(self, model_id:str) -> str:
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                return ""
            params = {
                **self.get_base_params(),
                'id': model.get_property('coverArt') or model.get_property('id'),
                'size': 240
            }
            return '{}?{}'.format(self.get_url('getCoverArt'), urlencode(params))
        return ""

    def ping(self) -> dict:
        response = self.make_request('ping')
        if response.get('status') == 'ok':
            return super().ping()
        else:
            return {
                'status': 'error',
                'message': '{}\n"{}"'.format(_('Server returned an error'), response.get('error', {}).get('message', _('Unknown Error')))
            }

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
            if list_type != 'starred' or album_dict.get('starred'):
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

    def getStarred(self, item_type:str) -> list:
        items = self.make_request('getStarred2').get('starred2', {}).get(item_type, [])
        return [item.get('id') for item in items]

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
                self.threads.submit(update)
            else:
                update()

        self.threads.submit(self.updateCoverArt, model_id)

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
                self.threads.submit(update)
            else:
                update()

        self.threads.submit(self.updateCoverArt, model_id)

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
                self.threads.submit(update)
            else:
                update()

        self.threads.submit(self.updateCoverArt, model_id)

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
            elif model_id in self.loaded_models:
                self.loaded_models.get(model_id).set_property('deleted', True)
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models:
            self.loaded_models[model_id] = models.Song(id=model_id)
            force_update = True

        if force_update:
            if use_threading:
                self.threads.submit(update)
            else:
                update()

        self.threads.submit(self.updateCoverArt, model_id)

    def star(self, model_id:str) -> bool:
        response = None
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Album):
                response = self.make_request('star', {'albumId': model_id})
            elif isinstance(model, models.Artist):
                response = self.make_request('star', {'artistId': model_id})
        if not response:
            response = self.make_request('star', {'id': model_id})
        return response.get('status') == 'ok'

    def unstar(self, model_id:str) -> bool:
        response = None
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Album):
                response = self.make_request('unstar', {'albumId': model_id})
            elif isinstance(model, models.Artist):
                response = self.make_request('unstar', {'artistId': model_id})
        if not response:
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

    def getLyrics(self, songId:str, requestOnline:bool=False) -> tuple:
        # Initial Checks
        if songId not in self.loaded_models:
            return 'not-found', ''

        # 1. Database
        lyrics_type, content = super().getLyrics(songId)
        if lyrics_type != 'not-found':
            return lyrics_type, content

        # 2. Integration
        def job():
            lyrics_data = self.make_request('getLyricsBySongId', {'id': songId}).get('lyricsList') or {}
            lyrics = (lyrics_data.get('structuredLyrics') or [{}])[0]
            if lyrics.get('synced'):
                lrc_lines = []
                for line in lyrics.get('line', []):
                    ms = line.get('start')
                    minutes = ms // 60000
                    seconds = (ms % 60000) // 1000
                    centiseconds = (ms % 1000) // 10
                    timestamp = f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"
                    lrc_lines.append(f"{timestamp} {line.get('value').strip()}")
                if content := '\n'.join(lrc_lines):
                    return True, content
            return True, ''

        if content := self.cache_manager.get_result(f'IntegrationLyrics:{songId}', job):
            self.saveLyrics(songId, content, 'lrc')
            return 'lrc', content

        # 3. Online
        if requestOnline:
            return super().getLyrics(songId, requestOnline)
        return 'not-found-locally', ''

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0, playlistCount:int=0, playlistOffset:int=0) -> dict:
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
        for model in search_results.get('artist') or []:
            model['id'] = str(model.get('id', ''))
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Artist(**model)
        for model in search_results.get('album') or []:
            model['id'] = str(model.get('id', ''))
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Album(**model)
        for model in search_results.get('song') or []:
            model['id'] = str(model.get('id', ''))
            if model.get('id') not in self.loaded_models:
                self.loaded_models[model.get('id')] = models.Song(**model)

        # Playlists
        playlist_ids = []
        for playlistId in self.getPlaylists():
            if playlist := self.loaded_models.get(playlistId):
                if re.search(query, playlist.get_property('name'), re.IGNORECASE):
                    playlist_ids.append(playlistId)

        return {
            'artist': [m.get('id') for m in search_results.get('artist') or []],
            'album': [m.get('id') for m in search_results.get('album') or []],
            'song': [m.get('id') for m in search_results.get('song') or []],
            'playlist': playlist_ids[playlistOffset:playlistCount+playlistOffset]
        }

    def systemSearch(self, query:str) -> dict:
        results = {}
        response = self.make_request('search3', {
            'query': query,
            'artistCount': 5,
            'albumCount': 5,
            'songCount': 5,
        }).get('searchResult3', {})

        # Artists
        for artist in response.get('artist', []):
            icon_bytes = self.getCoverArtBytes(artist.get('id'), 128)
            results[artist.get('id')] = {
                'display': GLib.Variant('s', artist.get('name')),
                'type': GLib.Variant('s', 'artist'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Albums
        for album in response.get('album', []):
            display_name = album.get('name')
            try:
                if artists := album.get('artists'):
                    if len(artists) > 0:
                        if artist := artists[0].get('name'):
                            display_name = '{} • {}'.format(album.get('name'), artist)
            except:
                display_name = album.get('name')
            icon_bytes = self.getCoverArtBytes(album.get('id'), 128)
            results[album.get('id')] = {
                'display': GLib.Variant('s', display_name),
                'type': GLib.Variant('s', 'album'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Songs
        for song in response.get('song', []):
            display_name = song.get('title')
            try:
                if artists := song.get('artists'):
                    if len(artists) > 0:
                        if artist := artists[0].get('name'):
                            display_name = '{} • {}'.format(song.get('title'), artist)
            except:
                display_name = song.get('title')
            icon_bytes = self.getCoverArtBytes(song.get('id'), 128)
            results[song.get('id')] = {
                'display': GLib.Variant('s', display_name),
                'type': GLib.Variant('s', 'song'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Playlists
        for playlistId in self.getPlaylists():
            if playlist := self.loaded_models.get(playlistId):
                if re.search(query, playlist.get_property('name'), re.IGNORECASE):
                    icon_bytes = self.getCoverArtBytes(playlistId, 128)
                    results[playlistId] = {
                        'display': GLib.Variant('s', playlist.get_property('name')),
                        'type': GLib.Variant('s', 'playlist'),
                        'icon': GLib.Variant('ay', bytearray(icon_bytes))
                    }
        return results

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
        if playlistId:
            response = self.make_request('updatePlaylist', {
                'playlistId': playlistId,
                'name': name
            })
            if response.get('status') == 'ok':
                return playlistId
        else:
            response = self.make_request('createPlaylist', {
                'name': name,
                'songId': songId
            })
            return response.get('playlist', {}).get('id')
        return ''

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
            with self.session.get(self.get_url('download'), params=params, stream=True) as r:
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
            response = self.send_request('ping')
            if response.status_code in (200, 201):
                data = response.json().get('subsonic-response', {})
                server_information['title'] = "{} {}".format(data.get('type'), data.get('serverVersion')).title()
        except Exception as e:
            logger.error(f"can't get server information: {e}")

        try:
            response = self.send_request(
                action='getAvatar',
                params={
                    'username': self.get_property('user')
                }
            )
            response_bytes = response.content if response.status_code in (200, 201) else b''
            if response_bytes and len(response_bytes) > 0:
                gbytes = GLib.Bytes.new(response_bytes)
                server_information['picture'] = Gdk.Texture.new_from_bytes(gbytes)
        except Exception as e:
            logger.error(f"can't get profile picture: {e}")

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

    def ping(self) -> dict:
        gio_file = Gio.File.new_for_path(self.get_property('libraryDir'))
        if new_path := gio_file.get_path():
            self.set_property('libraryDir', new_path)
            if self.start_instance():
                return super().ping()
        return {
            'status': 'error',
            'message': _('Could not locate path, try again')
        }

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
            logger.error(f"can't start server: {e}")
            self.set_property('serverRunning', False)
            return False

    def terminate_instance(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self.set_property('serverRunning', False)

class Bandcamp(Navidrome):
    __gtype_name__ = 'NocturneIntegrationBandcamp'

    login_page_metadata = {
        'icon-name': "bandcamp-symbolic",
        'title': "Bandcamp",
        'description': _("Important: Use your Subsonic login information."),
        'entries': ['user', 'password'],
        'additional-link': {
            'label': _("Bandcamp User Settings"),
            'url': 'https://bandcamp.com/settings?pane=fan'
        }
    }
    button_metadata = {
        'title': "Bandcamp (Beta)",
        'subtitle': _("Explore your online library")
    }

    url = GObject.Property(type=str, default="https://bandcamp.com/api/subsonic")

    sqlSchema = {
        'radios': {
            'id': 'TEXT PRIMARY KEY',
            'name': 'TEXT NOT NULL',
            'stream_url': 'TEXT NOT NULL'
        },
        'ratings': {
            'id': 'TEXT PRIMARY KEY',
            'rating': 'INTEGER DEFAULT 1'
        },
        'scrobble': {
            'id': 'TEXT PRIMARY KEY',
            'plays': 'INTEGER DEFAULT 1',
            'last_play': 'INTEGER DEFAULT 0',
            'album_id': 'TEXT NOT NULL',
            'artist_id': 'TEXT NOT NULL'
        }
    }

    def getServerInformation(self) -> dict:
        server_info = super().getServerInformation()
        server_info['link'] = 'https://bandcamp.com'
        return server_info

    # Implementation of Radios ---------

    def getInternetRadioStations(self) -> list:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT id, name, stream_url FROM radios")
        radio_ids = []
        for radio in cursor.fetchall():
            radio_ids.append(radio[0])
            self.loaded_models[radio[0]] = models.Song(
                id=radio[0],
                title=radio[1],
                radioStreamUrl=radio[2],
                duration=-1
            )
        conn.close()
        return radio_ids

    def createInternetRadioStation(self, name:str, radioStreamUrl:str) -> bool:
        radio_id = 'RADIO:{}'.format(str(uuid.uuid4()))
        return self.updateInternetRadioStation(radio_id, name, radioStreamUrl)

    def updateInternetRadioStation(self, model_id:str, name:str, radioStreamUrl:str) -> bool:
        conn, cursor = sql_instance.get_connection(self)
        query = """
        INSERT INTO radios (id, name, stream_url)
        VALUES (?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            name = excluded.name,
            stream_url = excluded.stream_url
        """
        cursor.execute(query, (model_id, name, radioStreamUrl))
        conn.commit()
        conn.close()
        return True

    def deleteInternetRadioStation(self, model_id:str) -> bool:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("DELETE FROM radios WHERE id = ?", (model_id,))
        conn.commit()
        conn.close()
        return True

    def getRandomSongs(self, size:int=20) -> list:
        song_ids = []
        albums = self.make_request('getAlbumList2', {
            'type': 'random',
            'size': 20
        }).get('albumList2', {}).get('album', [])
        for album in albums:
            album_detail = self.make_request('getAlbum', {
                'id': album.get('id')
            }).get('album', {})
            song_ids.extend([s.get('id') for s in album_detail.get('song')])
        song_ids = random.sample(song_ids, size)
        for song_id in song_ids:
            self.verifySong(song_id)
        return song_ids

    # Implementation of Ratings ---------

    def get_rating(self, model_id) -> int: # For internal use
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT rating FROM ratings WHERE id = ?", (model_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def setRating(self, model_id:str, rating:int=0) -> bool:
        conn, cursor = sql_instance.get_connection(self)
        if rating == 0:
            cursor.execute("DELETE FROM ratings WHERE id = ?", (model_id,))
        else:
            query = """
            INSERT INTO ratings (id, rating)
            VALUES (?, ?)
            ON CONFLICT (id) DO UPDATE SET
                rating = excluded.rating
            """
            cursor.execute(query, (model_id, rating))
        conn.commit()
        conn.close()
        return True

    def verifyArtist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        super().verifyArtist(model_id, force_update, use_threading)
        if model := self.loaded_models.get(model_id):
            model.set_property('userRating', self.get_rating(model_id))

    def verifyAlbum(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        super().verifyAlbum(model_id, force_update, use_threading)
        if model := self.loaded_models.get(model_id):
            model.set_property('userRating', self.get_rating(model_id))

    def verifySong(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        super().verifySong(model_id, force_update, use_threading)
        if model := self.loaded_models.get(model_id):
            model.set_property('userRating', self.get_rating(model_id))

    # Implementation of Play Queue ---------

    def getPlayQueue(self) -> tuple:
        queue_dict = self.open_json('queue.json')

        song_list = [model_id for model_id in queue_dict.get('id', []) if model_id in self.loaded_models]
        current = queue_dict.get('current', "")
        if current not in song_list:
            if len(song_list) > 0:
                current = song_list[0]
            else:
                current = ""

        return current, song_list

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        final_id_list = []
        for model_id in id_list:
            if model := self.loaded_models.get(model_id):
                if not model.get_property('isExternalFile'):
                    final_id_list.append(model_id)

        if current not in final_id_list:
            if len(final_id_list) > 0:
                current = final_id_list[0]
            else:
                current = ""

        queue_dict = {
            'id': final_id_list,
            'current': current,
            'position': position
        }

        self.save_json('queue.json', queue_dict)
        return True

    # Implementation of Scrobble / album pages

    def scrobble(self, model_id:str, submission:bool = True):
        if not model_id:
            return
        if model := self.loaded_models.get(model_id):
            if model.get_property('isExternalFile') or model.get_property('radioStreamUrl'):
                return

            if submission:
                conn, cursor = sql_instance.get_connection(self)
                query = """
                INSERT INTO scrobble (id, plays, last_play, album_id, artist_id)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    plays = plays + 1,
                    last_play = excluded.last_play,
                    album_id = excluded.album_id,
                    artist_id = excluded.artist_id
                """
                cursor.execute(query, (model_id, int(time.time()), model.get_property('albumId'), model.get_property('artistId')))
                conn.commit()
                conn.close()
        super().scrobble(model_id, submission)

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        if list_type in ("frequent", "recent"):
            album_views = {}
            conn, cursor = sql_instance.get_connection(self)
            cursor.execute("SELECT album_id, plays, last_play FROM scrobble")
            for row in cursor.fetchall():
                album_id = row[0]
                plays = row[1]
                last_play = row[2]

                if album_id in album_views:
                    album_views[album_id]['plays'] += plays
                    album_views[album_id]['last_play'] = max(album_views.get(album_id).get('last_play'), last_play)
                else:
                    album_views[album_id] = {
                        'plays': plays,
                        'last_play': last_play
                    }
            conn.close()
            if list_type == "frequent":
                album_list = sorted(album_views, key=lambda x: album_views.get(x).get('plays'), reverse=True)
            else:
                album_list = sorted(album_views, key=lambda x: album_views.get(x).get('last_play'), reverse=True)
            return [model_id for model_id in album_list if model_id in self.loaded_models][offset:size+offset]
        else:
            return super().getAlbumList(list_type, size, offset)

    def downloadSong(self, model_id:str, file_title:str, progress_callback:callable):
        params = {
            **self.get_base_params(),
            'id': model_id,
            'maxBitRate': 0,
            'format': 'raw'
        }
        try:
            with self.session.get(self.get_url('stream'), params=params, stream=True) as r:
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

# local.py

from gi.repository import Gtk, GLib, GObject, Gdk, Gio, GdkPixbuf
from . import secret, models
from .base import Base
from datetime import datetime, timezone
import requests, random, threading, favicon, io, pathlib, re, json, os, time, uuid, pwd, getpass, time
from PIL import Image
from mutagen import File
from ..constants import LOCAL_DATA_DIR, get_song_info_from_file

class Local(Base):
    __gtype_name__ = 'NocturneIntegrationLocal'

    login_page_metadata = {
        'icon-name': "music-note-symbolic",
        'title': _("Local Files"),
        'entries': ['library-dir'],
        'login-label': _("Continue"),
        'default-page': 'songs-all'
    }
    button_metadata = {
        'title': _("Local Files"),
        'subtitle': _("Limited functionality")
    }
    library_dir = GObject.Property(type=str)

    def open_json(self, filename:str, is_list:bool=False) -> dict | list:
        try:
            with open(os.path.join(LOCAL_DATA_DIR, filename), 'r') as f:
                result = json.load(f)
                if is_list:
                    if not isinstance(result, list):
                        return []
                else:
                    if not isinstance(result, dict):
                        return {}
                return result
        except Exception:
            return [] if is_list else {}

    def on_login(self):
        # Goes through the whole directory retrieving all the metadata
        audio_data_list = []
        path_obj = pathlib.Path(self.get_property('library_dir'))

        def load_songs():
            # load songs, albums, artists
            threads = []
            self.set_property('loadingMessage', _("Loading Songs"))
            for file_path in path_obj.rglob("*"):
                if file_path.suffix.lower() in ('.mp3', '.flac', '.m4a', '.ogg', '.wav'):
                    song_id = 'SONG:{}'.format(file_path)
                    self.loaded_models[song_id] = models.Song(id=song_id, path=file_path)
                    threads.append(threading.Thread(target=self.verifySong, args=(song_id,)))
                    threads[-1].start()
            for t in threads:
                t.join()
            self.set_property('loadingMessage', "")
        threading.Thread(target=load_songs).start()

        # Load radios
        radio_dict = self.open_json('radios.json')

        for radio_id, radio in radio_dict.items():
            self.loaded_models[radio_id] = models.Song(
                id=radio_id,
                title=radio.get('name'),
                streamUrl=radio.get('streamUrl'),
                duration=-1,
                isRadio=True
            )

        self.load_playlists()

    def load_playlists(self):
        # Load playlists
        playlist_dict = self.open_json('playlists.json')

        for playlist_id, playlist in playlist_dict.items():
            if playlist_id not in self.loaded_models:
                path_str = ""
                if len(playlist.get('songId', [])) > 0:
                    if model := self.loaded_models.get(playlist.get('songId')[0]):
                        path_str = model.path

                self.loaded_models[playlist_id] = models.Playlist(
                    id=playlist_id,
                    name=playlist.get('name'),
                    songCount=len(playlist.get('songId', [])),
                    entry=[{'id': id} for id in playlist.get('songId', [])],
                    path = path_str
                )

    # ----------- #

    def get_stream_url(self, song_id:str) -> str:
        model = self.loaded_models.get(song_id)
        if model.isRadio:
            return model.streamUrl
        return 'file://{}'.format(model.path)

    def getCoverArt(self, id:str=None) -> tuple:
        # returns bytes, Gdk.Paintable or None, None
        if id:
            if model := self.loaded_models.get(id):
                if isinstance(model, models.Song) and model.isRadio:
                    return self.getRadioCoverArt(id)
                if not isinstance(model, models.Playlist) and model.gdkPaintable:
                    return model.gdkPaintableBytes, model.gdkPaintable

                if not model.path:
                    return None, None

                audio_file = File(model.path)
                if audio_file is None:
                    return None, None

                raw_data = None
                if 'APIC:' in audio_file:
                    raw_data = audio_file.get('APIC:').data
                elif hasattr(audio_file, 'pictures') and audio_file.pictures:
                    raw_data = audio_file.pictures[0].data
                elif 'covr' in audio_file:
                    raw_data = audio_file.get('covr')[0]

                if not raw_data:
                    return None, None

                try:
                    gbytes = GLib.Bytes.new(raw_data)
                    texture = Gdk.Texture.new_from_bytes(gbytes)
                    model.set_property('gdkPaintableBytes', gbytes)
                    model.set_property('gdkPaintable', texture)
                    return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                except Exception as e:
                    pass
        return None, None

    def ping(self) -> bool:
        # Always true, it checks it at login
        return True

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        album_list = []
        if list_type == "random":
            album_list = [model_id for model_id in list(self.loaded_models) if model_id.startswith('ALBUM:')]
            random.shuffle(album_list)
        elif list_type == "newest":
            albums = {} # id : creation_time
            for model in [self.loaded_models.get(model_id) for model_id in list(self.loaded_models) if model_id.startswith('ALBUM:')]:
                albums[model.id] = pathlib.Path(model.path).stat().st_ctime
            album_list = sorted(albums, key=lambda x: albums.get(x), reverse=True)
        elif list_type in ("frequent", "recent"):
            try:
                with open(os.path.join(LOCAL_DATA_DIR, 'scrobble.json'), 'r') as f:
                    scrobble_dict = json.load(f)
                if not isinstance(scrobble_dict, dict):
                    return []
            except Exception:
                return []

            album_views = {}
            for data in scrobble_dict.values():
                if data.get('album') in album_views:
                    album_views[data.get('album')]['plays'] += data.get('plays')
                    album_views[data.get('album')]['last_play'] = max(data.get('last_play'), album_views.get(data.get('album')).get('last_play'))
                else:
                    album_views[data.get('album')] = {
                        'plays': data.get('plays'),
                        'last_play': data.get('last_play')
                    }

            if list_type == "frequent":
                album_list = sorted(album_views, key=lambda x: album_views.get(x).get('plays'), reverse=True)
            elif list_type == "recent":
                album_list = sorted(album_views, key=lambda x: album_views.get(x).get('last_play'), reverse=True)
        elif list_type == "starred":
            album_list = [model_id for model_id, model in self.loaded_models.items() if model_id.startswith('ALBUM:') and model.starred]
        else:
            album_list = [model_id for model_id in list(self.loaded_models) if model_id.startswith('ALBUM:')]
        return [model_id for model_id in album_list if model_id in self.loaded_models][offset:offset+size]

    def getArtists(self, size:int=10) -> list:
        return [model_id for model_id in list(self.loaded_models) if model_id.startswith('ARTIST:')][:size]

    def getPlaylists(self) -> list:
        self.load_playlists()
        return [model_id for model_id in list(self.loaded_models) if model_id.startswith('PLAYLIST:')]

    def getStarredSongs(self) -> list:
        star_dict = self.open_json('stars.json')
        return [song_id for song_id in star_dict if song_id.startswith("SONG:") and song_id in self.loaded_models]

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            # load star_dict
            star_dict = self.open_json('stars.json')

            # Updating Song Model
            song = get_song_info_from_file(self.loaded_models.get(id).get_property("path"), star_dict=star_dict)
            if not song:
                return
            song["id"] = id
            song["starred"] = song.get("id") in star_dict
            self.loaded_models.get(id).update_data(**song)

            # Making Album Model
            album_id = song.get('albumId')
            if not album_id:
                album_id = 'ALBUM:NO_ALBUM:{}'.format(song.get('artists')[0].get('id'))

            if album_id:
                if album_id in self.loaded_models:
                    if {'id': id} not in self.loaded_models.get(album_id).get_property('song'):
                        self.loaded_models.get(album_id).song.append({'id': id})
                else:
                    album = {
                        'id': album_id,
                        'path': song.get('path'),
                        'name': song.get('album') or _("No Album"),
                        'artist': song.get('artist'),
                        'artistId': song.get('artistId'),
                        'song': [{'id': id}],
                        'starred': album_id in star_dict
                    }
                    self.loaded_models[album.get('id')] = models.Album(**album)

            # Making Artist Model
            for a_dict in song.get('artists', []):
                if a_dict.get('id'):
                    if a_dict.get('id') not in self.loaded_models:
                        artist = {
                            'id': a_dict.get('id'),
                            'path': song.get('path'),
                            'name': a_dict.get('name'),
                            'album': [],
                            'albumCount': 0,
                            'starred': a_dict.get('id') in star_dict
                        }
                        self.loaded_models[artist.get('id')] = models.Artist(**artist)

                    # Add album
                    album_list = self.loaded_models.get(a_dict.get('id')).album
                    if album_id and not any([album.get('id') == album_id for album in album_list]):
                        self.loaded_models.get(a_dict.get('id')).album.append({'id': album_id})
                        self.loaded_models.get(a_dict.get('id')).albumCount += 1

        if force_update or not self.loaded_models.get(id).get_property('title'):
            if use_threading:
                threading.Thread(target=run).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def star(self, id:str) -> bool:
        star_dict = self.open_json('stars.json')

        current_time = datetime.now(timezone.utc).isoformat(timespec='microseconds').replace("+00:00", "Z")
        star_dict[id] = current_time

        with open(os.path.join(LOCAL_DATA_DIR, 'stars.json'), 'w') as f:
            json.dump(star_dict, f, ensure_ascii=False)

        return True

    def unstar(self, id:str) -> bool:
        star_dict = self.open_json('stars.json')

        if id in star_dict:
            del star_dict[id]

        with open(os.path.join(LOCAL_DATA_DIR, 'stars.json'), 'w') as f:
            json.dump(star_dict, f, ensure_ascii=False)

        return True

    def getPlayQueue(self) -> tuple:
        queue_dict = self.open_json('queue.json')

        song_list = [id for id in queue_dict.get('id', []) if id in self.loaded_models]
        current = queue_dict.get('current', "")
        if current not in song_list:
            if len(song_list) > 0:
                current = song_list[0]
            else:
                current = ""

        return current, song_list

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        final_id_list = []
        for id in id_list:
            if model := self.loaded_models.get(id):
                if not model.isExternalFile:
                    final_id_list.append(id)

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

        with open(os.path.join(LOCAL_DATA_DIR, 'queue.json'), 'w') as f:
            json.dump(queue_dict, f, ensure_ascii=False)

        return True

    def getSimilarSongs(self, id:str, count:int=20) -> list:
        # out of the scope of Local
        return self.getRandomSongs(count)

    def getRandomSongs(self, size:int=20) -> list:
        songs = [song_id for song_id in list(self.loaded_models) if song_id.startswith('SONG:')]
        return random.sample(songs, k=min(size, len(songs)))

    def getLyrics(self, songId:str) -> dict:
        if model := self.loaded_models.get(songId):
            audio = File(model.path)
            if not audio:
                return {'type': 'not-found'}

            if model.path.split('.')[-1].lower == 'mp3':
                if synced_lyrics := audio.get("SYLT"):
                    if len(synced_lyrics) > 0 and synced_lyrics[0].lyrics:
                        lines = []
                        for content, ms in synced_lyrics[0].lyrics:
                            lines.append({
                                'ms': ms,
                                'content': content
                            })
                        if lines:
                            return {
                                'type': 'lrc',
                                'content': lines
                            }
                if plain_lyrics := audio_file.get("USLT"):
                    if content := plain_lyrics[0].text:
                        return {
                            'type': 'plain',
                            'content': content
                        }
            else:
                if lyrics := audio.get('LYRICS') or audio.get('UNSYNCEDLYRICS'):
                    if lyrics.startwith('['):
                        return {'type': 'lrc', 'content': lyrics}
                    else:
                        return {'type': 'plain', 'content': lyrics}
        return {'type': 'not-found'}

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0) -> dict:
        all_artists = [model for model_id, model in self.loaded_models.items() if model_id.startswith('ARTIST:')]
        all_albums = [model for model_id, model in self.loaded_models.items() if model_id.startswith('ALBUM:')]
        all_songs = [model for model_id, model in self.loaded_models.items() if model_id.startswith('SONG:')]

        return {
            'artist': [model.id for model in all_artists if re.search(query, model.name, re.IGNORECASE)][artistOffset:artistCount],
            'album': [model.id for model in all_albums if re.search(query, model.name, re.IGNORECASE) or re.search(query, model.artist, re.IGNORECASE)][albumOffset:albumCount],
            'song': [model.id for model in all_songs if re.search(query, model.title, re.IGNORECASE) or re.search(query, model.album, re.IGNORECASE) or re.search(query, model.artist, re.IGNORECASE)][songOffset:songCount]
        }

    def getInternetRadioStations(self) -> list:
        return [model_id for model_id in list(self.loaded_models) if model_id.startswith('RADIO:')]

    def createInternetRadioStation(self, name:str, streamUrl:str) -> bool:
        radio_dict = self.open_json('radios.json')

        radio_id = str(uuid.uuid4())
        radio_dict[radio_id] = {
            'name': name,
            'streamUrl': streamUrl
        }

        self.loaded_models[radio_id] = models.Song(
            id=radio_id,
            title=name,
            streamUrl=streamUrl,
            duration=-1,
            isRadio=True
        )

        with open(os.path.join(LOCAL_DATA_DIR, 'radios.json'), 'w') as f:
            json.dump(radio_dict, f, ensure_ascii=False)

        return True

    def updateInternetRadioStation(self, id:str, name:str, streamUrl:str) -> bool:
        radio_dict = self.open_json('radios.json')

        radio_dict[id] = {
            'name': name,
            'streamUrl': streamUrl
        }
        if model := self.loaded_models.get(id):
            model.set_property('title', name)
            model.set_property('streamUrl', streamUrl)

        with open(os.path.join(LOCAL_DATA_DIR, 'radios.json'), 'w') as f:
            json.dump(radio_dict, f, ensure_ascii=False)

        return True

    def deleteInternetRadioStation(self, id:str) -> bool:
        radio_dict = self.open_json('radios.json')

        if id in radio_dict:
            del radio_dict[id]

        with open(os.path.join(LOCAL_DATA_DIR, 'radios.json'), 'w') as f:
            json.dump(radio_dict, f, ensure_ascii=False)

        return True

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        playlist_dict = self.open_json('playlists.json')

        playlistId = playlistId or 'PLAYLIST:{}'.format(str(uuid.uuid4()))

        playlist_dict[playlistId] = {
            'name': name,
            'songId': songId
        }

        path_str = ""
        if len(songId) > 0:
            if model := self.loaded_models.get(songId[0]):
                path_str = model.path

        self.loaded_models[playlistId] = models.Playlist(
            id=playlistId,
            name=name,
            songCount=len(songId),
            entry=[{'id': id} for id in songId],
            path = path_str
        )

        with open(os.path.join(LOCAL_DATA_DIR, 'playlists.json'), 'w') as f:
            json.dump(playlist_dict, f, ensure_ascii=False)

        return playlistId

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        playlist_dict = self.open_json('playlists.json')

        if playlistId in playlist_dict:
            songs = playlist_dict.get(playlistId).get('songId')
            for index in songIndexToRemove:
                songs.pop(int(index))
            songs.extend(songIdToAdd)
            playlist_dict[playlistId]['songId'] = songs

            if model := self.loaded_models.get(playlistId):
                songId = playlist_dict.get(playlistId).get('songId')
                model.set_property('songCount', len(songId))
                model.set_property('entry', [{'id': id} for id in songId])
                path_str = ""
                if len(songId) > 0:
                    if model := self.loaded_models.get(songId[0]):
                        path_str = model.path
                model.set_property('path', path_str)

        with open(os.path.join(LOCAL_DATA_DIR, 'playlists.json'), 'w') as f:
            json.dump(playlist_dict, f, ensure_ascii=False)

        return True

    def deletePlaylist(self, id:str) -> bool:
        playlist_dict = self.open_json('playlists.json')
        if id in playlist_dict:
            del playlist_dict[id]
        with open(os.path.join(LOCAL_DATA_DIR, 'playlists.json'), 'w') as f:
            json.dump(playlist_dict, f, ensure_ascii=False)

        return True

    def scrobble(self, id:str):
        if not id:
            return
        if model := self.loaded_models.get(id):
            if model.get_property('isExternalFile') or model.get_property('isRadio'):
                return
            scrobble_dict = self.open_json('scrobble.json')

            if id in scrobble_dict:
                scrobble_dict[id]['plays'] += 1
                scrobble_dict[id]['last_play'] = int(time.time())
                scrobble_dict[id]['album'] = model.albumId
            else:
                scrobble_dict[id] = {
                    'plays': 1,
                    'last_play': int(time.time()),
                    'album': model.get_property('albumId')
                }

            with open(os.path.join(LOCAL_DATA_DIR, 'scrobble.json'), 'w') as f:
                json.dump(scrobble_dict, f, ensure_ascii=False)

    def setRating(self, id:str, rating:int=0) -> bool:
        ratings = self.open_json('ratings.json')
        ratings[id] = rating
        self.loaded_models.get(id).set_property('userRating', rating)
        with open(os.path.join(LOCAL_DATA_DIR, 'ratings.json'), 'w') as f:
            json.dump(ratings, f, ensure_ascii=False)
        return True

    def getServerInformation(self) -> dict:
        server_information = {
            'link': 'file://{}'.format(self.get_property('library_dir')),
            'title': _("Local Files")
        }
        try:
            gecos_temp = pwd.getpwnam(getpass.getuser()).pw_gecos.split(',')
            if len(gecos_temp) > 0:
                server_information["username"] = pwd.getpwnam(getpass.getuser()).pw_gecos.split(',')[0].title()
        except Exception:
            pass

        return server_information

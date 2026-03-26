# local.py

from gi.repository import Gtk, GLib, GObject, Gdk, Gio, GdkPixbuf
from . import secret, models
from .base import Base
from datetime import datetime, timezone
import requests, random, threading, favicon, io, pathlib, re, json, os, time, uuid
from PIL import Image
from mutagen import File
from ..constants import MUSIC_DIR, LOCAL_DATA_DIR, get_song_info_from_file

class Local(Base):
    __gtype_name__ = 'NocturneIntegrationLocal'

    music_dir = GObject.Property(type=str, default=MUSIC_DIR)
    supported_extensions = ('.mp3', '.flac', '.m4a', '.ogg', '.wav')

    def __init__(self):
        super().__init__()
        self.update_loaded_models()

    def update_loaded_models(self):
        # Goes through the whole directory retrieving all the metadata
        audio_data_list = []
        path_obj = pathlib.Path(self.music_dir)

        # load star_dict
        STARFILE = os.path.join(LOCAL_DATA_DIR, 'stars.json')
        try:
            with open(STARFILE, 'r') as f:
                star_dict = json.load(f)
            if not isinstance(star_dict, dict):
                star_dict = {}
        except Exception:
            star_dict = {}

        # load songs, albums, artists
        for file_path in path_obj.rglob("*"):
            if file_path.suffix.lower() in self.supported_extensions:
                try:
                    # Making Song Model
                    song = get_song_info_from_file(file_path, star_dict)
                    if not song:
                        continue
                    self.loaded_models[song.get('id')] = models.Song(**song)

                    # Making Album Model
                    if song.get('albumId'):
                        if song.get('albumId') in self.loaded_models:
                            self.loaded_models.get(song.get('albumId')).song.append({'id': song.get('id')})
                        else:
                            album = {
                                'id': song.get('albumId'),
                                'path': song.get('path'),
                                'name': song.get('album'),
                                'artist': song.get('artist'),
                                'artistId': song.get('artistId'),
                                'song': [{'id': song.get('id')}],
                                'starred': star_dict.get(song.get('albumId'))
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
                                    'starred': star_dict.get(a_dict.get('id'))
                                }
                                self.loaded_models[artist.get('id')] = models.Artist(**artist)

                            # Add album
                            album_list = self.loaded_models.get(a_dict.get('id')).album
                            if not any([album.get('id') == song.get('albumId') for album in album_list]):
                                self.loaded_models.get(a_dict.get('id')).album.append({'id': song.get('albumId')})
                                self.loaded_models.get(a_dict.get('id')).albumCount += 1

                except Exception as e:
                    print('Error loading items:', e)

        # Load radios
        RADIOFILE = os.path.join(LOCAL_DATA_DIR, 'radios.json')
        try:
            with open(RADIOFILE, 'r') as f:
                radio_dict = json.load(f)
            if not isinstance(radio_dict, dict):
                radio_dict = {}
        except Exception:
            radio_dict = {}

        for radio_id, radio in radio_dict.items():
            self.loaded_models[radio_id] = models.Song(
                id=radio_id,
                title=radio.get('name'),
                streamUrl=radio.get('streamUrl'),
                homePageUrl=radio.get('homePageUrl'),
                duration=-1,
                isRadio=True
            )

        # Load playlists
        PLAYLISTFILE = os.path.join(LOCAL_DATA_DIR, 'playlists.json')
        try:
            with open(PLAYLISTFILE, 'r') as f:
                playlist_dict = json.load(f)
            if not isinstance(playlist_dict, dict):
                playlist_dict = {}
        except Exception:
            playlist_dict = {}

        for playlist_id, playlist in playlist_dict.items():
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

    def connect_to_model(self, id:str, parameter:str, callback:callable, use_gtk_thread:bool=True) -> str:
        connection_id = super().connect_to_model(id, parameter, callback, use_gtk_thread)
        if parameter == "coverArt":
            self.getCoverArt(id)
        return connection_id

    def get_stream_url(self, song_id:str) -> str:
        model = self.loaded_models.get(song_id)
        if model.isRadio:
            return model.streamUrl
        return 'file://{}'.format(model.path)

    def getRadioCoverArtWithBytes(self, id:str=None) -> tuple:
        # returns bytes, Gdk.Paintable or None, None
        if id:
            if model := self.loaded_models.get(id):
                homepage_url = ""
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
                            model.set_property('gdkPaintableBytes', png_bytes)
                            model.set_property('gdkPaintable', texture)
                            return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                        except Exception as e:
                            pass

        return None, None

    def getCoverArtWithBytes(self, id:str=None) -> tuple:
        # returns bytes, Gdk.Paintable or None, None
        if id:
            if model := self.loaded_models.get(id):
                if isinstance(model, models.Song) and model.isRadio:
                    return self.getRadioCoverArtWithBytes(id)
                if not isinstance(model, models.Playlist) and model.gdkPaintable:
                    return model.gdkPaintableBytes, model.gdkPaintable

                if not model.get_property('coverArt'):
                    model.set_property('coverArt', str(random.randint(1,1000)))

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
                    model.set_property('gdkPaintableBytes', raw_data)
                    model.set_property('gdkPaintable', texture)
                    return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                except Exception as e:
                    pass
        return None, None

    def getCoverArt(self, id:str=None) -> Gdk.Paintable:
        # Returns a paintable at the specified size, should be used directly in GTK without modifications
        return self.getCoverArtWithBytes(id)[1]

    def ping(self) -> bool:
        # Implemented from Navidrome, just a check
        return True

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        # list_type is not implemented yet
        album_list = []
        if list_type == "random":
            album_list = [id for id in list(self.loaded_models) if id.startswith('ALBUM:')]
            random.shuffle(album_list)
        elif list_type == "newest":
            albums = {} # id : creation_time
            for model in [self.loaded_models.get(id) for id in list(self.loaded_models) if id.startswith('ALBUM:')]:
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
            album_list = [id for id, model in self.loaded_models.items() if id.startswith('ALBUM:') and model.starred]
        else:
            album_list = [id for id in list(self.loaded_models) if id.startswith('ALBUM:')]
        return [id for id in album_list if id in self.loaded_models][offset:size]

    def getArtists(self, size:int=10) -> list:
        return [id for id in list(self.loaded_models) if id.startswith('ARTIST:')][:size]

    def getPlaylists(self) -> list:
        return [id for id in list(self.loaded_models) if id.startswith('PLAYLIST:')]

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        # no need
        return

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        # no need
        return

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        # no need
        return

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        # no need
        return

    def star(self, id:str) -> bool:
        STARFILE = os.path.join(LOCAL_DATA_DIR, 'stars.json')

        try:
            with open(STARFILE, 'r') as f:
                star_dict = json.load(f)
            if not isinstance(star_dict, dict):
                star_dict = {}
        except Exception:
            star_dict = {}

        current_time = datetime.now(timezone.utc).isoformat(timespec='microseconds').replace("+00:00", "Z")
        star_dict[id] = current_time

        with open(STARFILE, 'w') as f:
            json.dump(star_dict, f, ensure_ascii=False)

        return True

    def unstar(self, id:str) -> bool:
        STARFILE = os.path.join(LOCAL_DATA_DIR, 'stars.json')

        try:
            with open(STARFILE, 'r') as f:
                star_dict = json.load(f)
            if not isinstance(star_dict, list):
                star_dict = {}
        except Exception:
            star_dict = {}

        if id in star_dict:
            del star_dict[id]

        with open(STARFILE, 'w') as f:
            json.dump(star_dict, f, ensure_ascii=False)

        return True

    def getPlayQueue(self) -> tuple:
        QUEUEFILE = os.path.join(LOCAL_DATA_DIR, 'queue.json')

        try:
            with open(QUEUEFILE, 'r') as f:
                queue_dict = json.load(f)
            if not isinstance(queue_dict, dict):
                queue_dict = {}
        except Exception:
            queue_dict = {}

        song_list = [id for id in queue_dict.get('id', []) if id in self.loaded_models]
        current = queue_dict.get('current', "")
        if current not in song_list:
            if len(song_list) > 0:
                current = song_list[0]
            else:
                current = ""

        return current, song_list

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        QUEUEFILE = os.path.join(LOCAL_DATA_DIR, 'queue.json')

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

        with open(QUEUEFILE, 'w') as f:
            json.dump(queue_dict, f, ensure_ascii=False)

        return True

    def getSimilarSongs(self, id:str, count:int=20) -> list:
        # out of the scope of Local
        return self.getRandomSongs(count)

    def getRandomSongs(self, size:int=20) -> list:
        songs = [id for id in list(self.loaded_models) if id.startswith('SONG:')]
        return random.sample(songs, k=min(size, len(songs)))

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
        all_artists = [model for id, model in self.loaded_models.items() if id.startswith('ARTIST:')]
        all_albums = [model for id, model in self.loaded_models.items() if id.startswith('ALBUM:')]
        all_songs = [model for id, model in self.loaded_models.items() if id.startswith('SONG:')]

        return {
            'artist': [model.id for model in all_artists if re.search(query, model.name, re.IGNORECASE)][artistOffset:artistCount],
            'album': [model.id for model in all_albums if re.search(query, model.name, re.IGNORECASE) or re.search(query, model.artist, re.IGNORECASE)][albumOffset:albumCount],
            'song': [model.id for model in all_songs if re.search(query, model.title, re.IGNORECASE) or re.search(query, model.album, re.IGNORECASE) or re.search(query, model.artist, re.IGNORECASE)][songOffset:songCount]
        }

    def getInternetRadioStations(self) -> list:
        return [id for id in list(self.loaded_models) if id.startswith('RADIO:')]

    def createInternetRadioStation(self, name:str, streamUrl:str, homePageUrl:str) -> bool:
        RADIOFILE = os.path.join(LOCAL_DATA_DIR, 'radios.json')
        try:
            with open(RADIOFILE, 'r') as f:
                radio_dict = json.load(f)
            if not isinstance(radio_dict, dict):
                radio_dict = {}
        except Exception:
            radio_dict = {}

        radio_id = str(uuid.uuid4())
        radio_dict[radio_id] = {
            'name': name,
            'streamUrl': streamUrl,
            'homePageUrl': homePageUrl
        }

        self.loaded_models[radio_id] = models.Song(
            id=radio_id,
            title=name,
            streamUrl=streamUrl,
            homePageUrl=homePageUrl,
            duration=-1,
            isRadio=True
        )

        with open(RADIOFILE, 'w') as f:
            json.dump(radio_dict, f, ensure_ascii=False)

        return True

    def updateInternetRadioStation(self, id:str, name:str, streamUrl:str, homePageUrl:str) -> bool:
        RADIOFILE = os.path.join(LOCAL_DATA_DIR, 'radios.json')
        try:
            with open(RADIOFILE, 'r') as f:
                radio_dict = json.load(f)
            if not isinstance(radio_dict, dict):
                radio_dict = {}
        except Exception:
            radio_dict = {}

        radio_dict[id] = {
            'name': name,
            'streamUrl': streamUrl,
            'homePageUrl': homePageUrl
        }
        if model := self.loaded_models.get(id):
            model.set_property('name', name)
            model.set_property('streamUrl', streamUrl)
            model.set_property('homePageUrl', homePageUrl)
            model.set_property('coverArt', str(random.randint(1,1000)))

        with open(RADIOFILE, 'w') as f:
            json.dump(radio_dict, f, ensure_ascii=False)

        return True

    def deleteInternetRadioStation(self, id:str) -> bool:
        RADIOFILE = os.path.join(LOCAL_DATA_DIR, 'radios.json')
        try:
            with open(RADIOFILE, 'r') as f:
                radio_dict = json.load(f)
            if not isinstance(radio_dict, dict):
                radio_dict = {}
        except Exception:
            radio_dict = {}

        if id in radio_dict:
            del radio_dict[id]

        with open(RADIOFILE, 'w') as f:
            json.dump(radio_dict, f, ensure_ascii=False)

        return True

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        PLAYLISTFILE = os.path.join(LOCAL_DATA_DIR, 'playlists.json')
        try:
            with open(PLAYLISTFILE, 'r') as f:
                playlist_dict = json.load(f)
            if not isinstance(playlist_dict, dict):
                playlist_dict = {}
        except Exception:
            playlist_dict = {}

        playlistId = playlistId or str(uuid.uuid4())

        playlist_dict[playlistId] = {
            'name': name,
            'songId': songId
        }

        path_str = ""
        if len(songId) > 0:
            if model := self.loaded_models.get(songId[0]):
                path_str = model.path
        print('CREATE', path_str)

        self.loaded_models[playlistId] = models.Playlist(
            id=playlistId,
            name=name,
            songCount=len(songId),
            entry=[{'id': id} for id in songId],
            path = path_str
        )

        with open(PLAYLISTFILE, 'w') as f:
            json.dump(playlist_dict, f, ensure_ascii=False)

        return playlistId

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        PLAYLISTFILE = os.path.join(LOCAL_DATA_DIR, 'playlists.json')
        try:
            with open(PLAYLISTFILE, 'r') as f:
                playlist_dict = json.load(f)
            if not isinstance(playlist_dict, dict):
                playlist_dict = {}
        except Exception:
            playlist_dict = {}

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
                print('UPDATE', path_str)
                model.set_property('path', path_str)
                model.set_property('coverArt', str(random.randint(1,1000)))

        with open(PLAYLISTFILE, 'w') as f:
            json.dump(playlist_dict, f, ensure_ascii=False)

        return True

    def deletePlaylist(self, id:str) -> bool:
        PLAYLISTFILE = os.path.join(LOCAL_DATA_DIR, 'playlists.json')
        try:
            with open(PLAYLISTFILE, 'r') as f:
                playlist_dict = json.load(f)
            if not isinstance(playlist_dict, dict):
                playlist_dict = {}
        except Exception:
            playlist_dict = {}

        if id in playlist_dict:
            del playlist_dict[id]

        with open(PLAYLISTFILE, 'w') as f:
            json.dump(playlist_dict, f, ensure_ascii=False)

        return True

    def scrobble(self, id:str):
        if not id:
            return
        if model := self.loaded_models.get(id):
            if model.isExternalFile:
                return
            SCROBBLEFILE = os.path.join(LOCAL_DATA_DIR, 'scrobble.json')
            try:
                with open(SCROBBLEFILE, 'r') as f:
                    scrobble_dict = json.load(f)
                if not isinstance(scrobble_dict, dict):
                    scrobble_dict = {}
            except Exception:
                scrobble_dict = {}

            if id in scrobble_dict:
                scrobble_dict[id]['plays'] += 1
                scrobble_dict[id]['last_play'] = int(time.time())
                scrobble_dict[id]['album'] = model.albumId
            else:
                scrobble_dict[id] = {
                    'plays': 1,
                    'last_play': int(time.time()),
                    'album': model.albumId
                }

            with open(SCROBBLEFILE, 'w') as f:
                json.dump(scrobble_dict, f, ensure_ascii=False)


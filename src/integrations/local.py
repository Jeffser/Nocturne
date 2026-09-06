# local.py

from gi.repository import GLib, GObject, Gdk, Gio
from . import models, sql_instance
from .base import Base
import random, threading, io, pathlib, re, os, time, uuid, pwd, getpass, shutil, logging
from PIL import Image
from tinytag import TinyTag
from ..constants import DOWNLOADS_DIR, COMPATIBLE_EXTENSIONS, get_song_info_from_file
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class Local(Base):
    __gtype_name__ = 'NocturneIntegrationLocal'
    album_artist_ids = set()

    login_page_metadata = {
        'icon-name': "folder-open-symbolic",
        'title': _("Local Files"),
        'description': _("Let Nocturne load your local files directly, for big libraries it is recommended to use a dedicated server."),
        'entries': ['library-dir'],
        'login-label': _("Continue")
    }
    button_metadata = {
        'title': _("Local Files"),
        'subtitle': _("Limited functionality")
    }
    limitations = ('no-max-bitrate',)

    sqlSchema = {
        'stars': {
            'id': 'TEXT PRIMARY KEY'
        },
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

    def get_rating(self, model_id) -> int:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT rating FROM ratings WHERE id = ?", (model_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def on_login(self):
        # Goes through the whole directory retrieving all the metadata
        audio_data_list = []
        path_obj = pathlib.Path(self.get_property('libraryDir'))
        self.album_artist_ids = set()

        def load_songs():
            # load songs, albums, artists
            self.set_property('loadingMessage', _("Loading Songs"))

            futures = {}
            with ThreadPoolExecutor() as executor:
                for file_path in path_obj.rglob("*"):
                    # Exclude any hidden files/folders within the library path
                    if any(part.startswith(".") for part in file_path.relative_to(path_obj).parts):
                        continue
                    if file_path.suffix.lower() in COMPATIBLE_EXTENSIONS.get('audio') + COMPATIBLE_EXTENSIONS.get('video'):
                        song_id = 'SONG:{}'.format(file_path)
                        self.loaded_models[song_id] = models.Song(
                            id=song_id,
                            path=file_path,
                            coverArt=file_path,
                            userRating=self.get_rating(song_id)
                        )
                        futures[executor.submit(self.verifySong, model_id=song_id, use_threading=False)] = song_id
                
                for future in as_completed(futures):
                    song_id = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"can't load song {song_id}: {e}")
    
            self.set_property('loadingMessage', "")

        threading.Thread(target=load_songs, daemon=True).start()

        # Load radios
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT id, name, stream_url FROM radios")
        for radio in cursor.fetchall():
            self.loaded_models[radio[0]] = models.Song(
                id=radio[0],
                title=radio[1],
                radioStreamUrl=radio[2],
                duration=-1
            )
        conn.close()
        self.load_playlists()

    def load_playlists(self):
        # Load playlists
        playlist_dict = self.open_json('playlists.json')

        for playlist_id, playlist in playlist_dict.items():
            if playlist_id not in self.loaded_models:
                path_str = ""
                if len(playlist.get('songId', [])) > 0:
                    if model := self.loaded_models.get(playlist.get('songId')[0]):
                        path_str = model.get_property('path')

                self.loaded_models[playlist_id] = models.Playlist(
                    id=playlist_id,
                    name=playlist.get('name'),
                    songCount=len(playlist.get('songId', [])),
                    entry=[{'id': model_id} for model_id in playlist.get('songId', [])],
                    coverArt = path_str
                )

    # ----------- #

    def ping(self) -> dict:
        gio_file = Gio.File.new_for_path(self.get_property('libraryDir'))
        if new_path := gio_file.get_path():
            self.set_property('libraryDir', new_path)
            return super().ping()
        return {
            'status': 'error',
            'message': _('Could not locate path, try again')
        }

    def get_stream_url(self, song_id:str) -> str:
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
            return 'file://{}'.format(model.get_property('path'))
        return ""

    def getCoverArtBytes(self, model_id:str, size:int) -> bytes:
        try:
            coverArtPath = None
            if model := self.loaded_models.get(model_id):
                coverArtPath = model.get_property('coverArt')
            if not coverArtPath:
                return b''

            tag = TinyTag.get(coverArtPath, image=True)
            if tag is None:
                return b''

            image_data = tag.get_image()
            if not image_data:
                return b''

            img = Image.open(io.BytesIO(image_data))
            w_percent = (size / float(img.size[0]))
            height = int((float(img.size[1]) * float(w_percent)))
            resized_img = img.resize((size, height), Image.LANCZOS)
            buffer = io.BytesIO()
            resized_img.save(buffer, format="JPEG", quality=85)
            raw_data = buffer.getvalue()
            return raw_data
        except Exception as e:
            logger.error(f"can't get image from {model_id}: {e}")
        return b''

    def updateCoverArt(self, model_id:str):
        if model := self.loaded_models.get(model_id):
            sizes = {
                'gdkPaintableBig': 720,
                'gdkPaintable': 240
            }
            for property_name, size in sizes.items():
                if not model.get_property(property_name):
                    try:
                        if response_bytes := self.getCoverArtBytes(model_id, size):
                            gbytes = GLib.Bytes.new(response_bytes)
                            texture = Gdk.Texture.new_from_bytes(gbytes)
                            model.set_property(property_name, texture)
                    except Exception as e:
                        logger.error(f"can't get image from {model_id} (size {720 if big else 240}): {e}")

    def getCoverArtUrl(self, model_id:str) -> str:
        if model := self.loaded_models.get(model_id):
            directory = os.path.join(self.getIntegrationDir(), 'covers')
            file_name = '{} - {}.png'.format(model.get_property('title'), model.get_property('artist')).replace('/', '-')
            path = os.path.join(directory, file_name)
            if os.path.isfile(path):
                return "file://{}".format(path)
            try:
                shutil.rmtree(directory, ignore_errors=True)
                os.makedirs(directory, exist_ok=True)

                paintable = model.get_property('gdkPaintable')
                if not paintable:
                    self.updateCoverArt(model_id)
                    paintable = model.get_property('gdkPaintable')

                if paintable:
                    paintable.save_to_png(path)
                    return "file://{}".format(path)
            except Exception as e:
                logger.error(f"can't get image url from {model_id}: {e}")
                pass
        return ""

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        album_list = []
        if list_type == "random":
            album_list = [model_id for model_id in list(self.loaded_models) if model_id.startswith('ALBUM:')]
            random.shuffle(album_list)
        elif list_type == "newest":
            albums = {} # id : creation_time
            for model in [self.loaded_models.get(model_id) for model_id in list(self.loaded_models) if model_id.startswith('ALBUM:')]:
                albums[model.get_property('id')] = pathlib.Path(model.get_property('coverArt')).stat().st_ctime
            album_list = sorted(albums, key=lambda x: albums.get(x), reverse=True)
        elif list_type in ("frequent", "recent"):
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
            elif list_type == "recent":
                album_list = sorted(album_views, key=lambda x: album_views.get(x).get('last_play'), reverse=True)
        elif list_type == "starred":
            album_list = [model_id for model_id, model in self.loaded_models.items() if model_id.startswith('ALBUM:') and model.starred]
        else:
            album_list = [model_id for model_id in list(self.loaded_models) if model_id.startswith('ALBUM:')]
        return [model_id for model_id in album_list if model_id in self.loaded_models][offset:size+offset]

    def getArtists(self, size:int=10) -> list:
        return [model_id for model_id in list(self.loaded_models) if model_id in self.album_artist_ids][:size]

    def getPlaylists(self) -> list:
        self.load_playlists()
        return [model_id for model_id in list(self.loaded_models) if model_id.startswith('PLAYLIST:')]

    def getStarred(self, item_type:str) -> list:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT id FROM stars")
        star_list = [str(r[0]) for r in cursor.fetchall()]
        conn.close()
        query = f"{item_type.upper()}:"
        return [item_id for item_id in star_list if item_id.startswith(query) and item_id in self.loaded_models]

    def verifyArtist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        threading.Thread(target=self.updateCoverArt, args=(model_id,), daemon=True).start()

    def verifyAlbum(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        threading.Thread(target=self.updateCoverArt, args=(model_id,), daemon=True).start()

    def verifyPlaylist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        threading.Thread(target=self.updateCoverArt, args=(model_id,), daemon=True).start()

    def verifySong(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            conn, cursor = sql_instance.get_connection(self)
            cursor.execute("SELECT id FROM stars")
            star_list = [str(r[0]) for r in cursor.fetchall()]
            conn.close()

            # Updating Song Model
            song = get_song_info_from_file(self.loaded_models.get(model_id).get_property("path"), star_list=star_list)
            if not song:
                return
            song["id"] = model_id
            song["starred"] = song.get("id") in star_list
            self.loaded_models.get(model_id).update_data(**song)

            # Making Album Model
            album_id = song.get('albumId')
            if not album_id:
                album_id = 'ALBUM:NO_ALBUM:{}'.format(song.get('artists')[0].get('id'))

            if album_id:
                if album_id in self.loaded_models:
                    if {'id': model_id} not in self.loaded_models.get(album_id).get_property('song'):
                        self.loaded_models.get(album_id).song.append({'id': model_id})
                else:
                    album = {
                        'id': album_id,
                        'coverArt': song.get('path'),
                        'name': song.get('album') or _("No Album"),
                        'artist': song.get('artist'),
                        'artistId': song.get('artistId'),
                        'song': [{'id': model_id}],
                        'year':int(song.get('year') or "0"),
                        'starred': album_id in star_list,
                        'userRating': self.get_rating(album_id)
                    }
                    self.loaded_models[album.get('id')] = models.Album(**album)

            # Making Artist Model
            def update_artist(artist_id:str, artist_name:str):
                if artist_id not in self.loaded_models:
                    self.loaded_models[artist_id] = models.Artist(
                        id=artist_id,
                        coverArt=song.get('path'),
                        name=artist_name,
                        album=[],
                        albumCount=0,
                        starred=artist_id in star_list,
                        userRating=self.get_rating(artist_id)
                    )

                album_list = self.loaded_models.get(artist_id).album
                if album_id and not any(album.get('id') == album_id for album in album_list):
                    self.loaded_models.get(artist_id).album.append({'id': album_id})
                    self.loaded_models.get(artist_id).albumCount += 1

            artist_id = song.get('artistId')
            if artist_id:
                self.album_artist_ids.add(artist_id)
                update_artist(artist_id, song.get('artist'))

            for artist in song.get('artists', []):
                if artist.get('id'):
                    update_artist(artist.get('id'), artist.get('name'))

            self.updateCoverArt(model_id)

        # safe check before loading
        song = self.loaded_models.get(model_id)
        if force_update or (song and not song.get_property('title')):
            if use_threading:
                threading.Thread(target=run, daemon=True).start()
            else:
                run()

    def star(self, model_id:str) -> bool:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("INSERT OR IGNORE INTO stars (id) VALUES (?)", (model_id,))
        conn.commit()
        conn.close()
        return True

    def unstar(self, model_id:str) -> bool:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("DELETE FROM stars WHERE id=?", (model_id,))
        conn.commit()
        conn.close()
        return True

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

    def getSimilarSongs(self, model_id:str, count:int=20) -> list:
        # out of the scope of Local
        return self.getRandomSongs(count)

    def getRandomSongs(self, size:int=20) -> list:
        songs = [song_id for song_id in list(self.loaded_models) if song_id.startswith('SONG:')]
        return random.sample(songs, k=min(size, len(songs)))

    def getLyrics(self, songId:str, requestOnline:bool=False) -> dict:
        # Initial Checks
        if songId not in self.loaded_models:
            return 'not-found', ''

        # 1. Database
        lyrics_type, content = super().getLyrics(songId)
        if lyrics_type != 'not-found':
            return lyrics_type, content

        # 2. Integration
        def job():
            if model := self.loaded_models.get(songId):
                tag = TinyTag.get(model.get_property('path'))
                if lyrics_str := tag.extra.get('lyrics'):
                    if lyrics_str.startswith('['):
                        return True, {'type': 'lrc', 'content': lyrics_str}
                    else:
                        return True, {'type': 'plain', 'content': lyrics_str}
            return True, {}

        if content_dict := self.cache_manager.get_result(f'IntegrationLyrics:{songId}', job):
            if content := content_dict.get('content'):
                if lyrics_type := content_dict.get('type'):
                    if lyrics_type in ('lrc', 'plain'):
                        self.saveLyrics(songId, content, lyrics_type)
                        return lyrics_type, content

        # 3. Online
        if requestOnline:
            return super().getLyrics(songId, requestOnline)
        return 'not-found-locally', ''

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0, playlistCount:int=0, playlistOffset:int=0) -> dict:
        all_artists = [model for model_id, model in self.loaded_models.items() if model_id in self.album_artist_ids]
        all_albums = [model for model_id, model in self.loaded_models.items() if model_id.startswith('ALBUM:')]
        all_songs = [model for model_id, model in self.loaded_models.items() if model_id.startswith('SONG:')]
        all_playlists = [self.loaded_models.get(playlistId) for playlistId in self.getPlaylists() if playlistId in self.loaded_models]

        return {
            'artist': [model.id for model in all_artists if re.search(query, model.name, re.IGNORECASE)][artistOffset:artistCount+artistOffset],
            'album': [model.id for model in all_albums if re.search(query, ' '.join([model.name, model.artist]), re.IGNORECASE)][albumOffset:albumCount+albumOffset],
            'song': [model.id for model in all_songs if re.search(query, ' '.join([model.title, model.artist, model.album]), re.IGNORECASE)][songOffset:songCount+songOffset],
            'playlist': [model.id for model in all_playlists if re.search(query, model.name, re.IGNORECASE)][playlistOffset:playlistCount+playlistOffset]
        }

    def systemSearch(self, query:str) -> dict:
        results = {}

        all_artists = [model for model_id, model in self.loaded_models.items() if model_id in self.album_artist_ids]
        all_albums = [model for model_id, model in self.loaded_models.items() if model_id.startswith('ALBUM:')]
        all_songs = [model for model_id, model in self.loaded_models.items() if model_id.startswith('SONG:')]
        all_playlists = [self.loaded_models.get(playlistId) for playlistId in self.getPlaylists() if playlistId in self.loaded_models]

        # Artists
        for artist in [model for model in all_artists if re.search(query, model.name, re.IGNORECASE)][:5]:
            icon_bytes = self.getCoverArtBytes(artist.id, 128)
            results[artist.id] = {
                'display': GLib.Variant('s', artist.name),
                'type': GLib.Variant('s', 'artist'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Albums
        for album in [model for model in all_albums if re.search(query, ' '.join([model.name, model.artist]), re.IGNORECASE)][:5]:
            icon_bytes = self.getCoverArtBytes(album.id, 128)
            results[album.id] = {
                'display': GLib.Variant('s', album.name),
                'type': GLib.Variant('s', 'album'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Songs
        for song in [model for model in all_songs if re.search(query, ' '.join([model.title, model.artist, model.album]), re.IGNORECASE)][:5]:
            icon_bytes = self.getCoverArtBytes(song.id, 128)
            results[song.id] = {
                'display': GLib.Variant('s', song.title),
                'type': GLib.Variant('s', 'song'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Playlists
        for playlist in [model for model in all_playlists if re.search(query, model.name, re.IGNORECASE)][:5]:
            icon_bytes = self.getCoverArtBytes(playlist.id, 128)
            results[playlist.id] = {
                'display': GLib.Variant('s', playlist.name),
                'type': GLib.Variant('s', 'playlist'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }
        return results

    def getInternetRadioStations(self) -> list:
        return [model_id for model_id in list(self.loaded_models) if model_id.startswith('RADIO:')]

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
                path_str = model.get_property('path')

        self.loaded_models[playlistId] = models.Playlist(
            id=playlistId,
            name=name,
            songCount=len(songId),
            entry=[{'id': model_id} for model_id in songId],
            coverArt = path_str
        )
        self.save_json('playlists.json', playlist_dict)
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
                model.set_property('entry', [{'id': model_id} for model_id in songId])
                path_str = ""
                if len(songId) > 0:
                    if model := self.loaded_models.get(songId[0]):
                        path_str = model.get_property('path')
                model.set_property('coverArt', path_str)

        self.save_json('playlists.json', playlist_dict)
        return True

    def deletePlaylist(self, model_id:str) -> bool:
        playlist_dict = self.open_json('playlists.json')
        if model_id in playlist_dict:
            del playlist_dict[model_id]
        self.save_json('playlists.json', playlist_dict)
        return True

    def getTopSongs(self, artist_id:str, count:int=10) -> list:
        artist_scrobbles = {}
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT id, plays, artist_id FROM scrobble")
        for song in cursor.fetchall():
            song_id = song[0]
            plays = song[1]
            artist = song[2]
            if not artist:
                if model := self.loaded_models.get(song_id):
                    artist = model.get_property('artistId')
            if artist == artist_id:
                artist_scrobbles[song_id] = plays
        conn.close()
        return sorted(artist_scrobbles, key=artist_scrobbles.get, reverse=True)[:count]

    def downloadSong(self, model_id:str, file_title:str, progress_callback:callable):
        if model := self.loaded_models.get(model_id):
            source_path = model.get_property('path')
            extension = pathlib.Path(source_path).suffix
            shutil.copy2(source_path, os.path.join(DOWNLOADS_DIR, '{}{}'.format(file_title, extension)))
            progress_callback(1)

    def scrobble(self, model_id:str, submission:bool=True):
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
        super().scrobble(model_id, submission=submission)

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

    def getSongDetails(self, model_id:str) -> models.SongDetails:
        if model := self.loaded_models.get(model_id):
            tag = TinyTag.get(model.get_property('path'))

            # Limitations:
            # - no bitDepth
            # - no bpm
            # - no trackGain
            # - no albumGain
            return models.SongDetails(
                id=model_id,
                title=tag.title,
                album=tag.album,
                albumId=model.get_property('albumId'),
                artist=tag.artist,
                artistId=model.get_property('artistId'),
                track=tag.track or 0,
                year=int(tag.year or "0"),
                size=tag.filesize,
                suffix=os.path.splitext(model.get_property('path'))[1].replace('.',  ''),
                starred=model.get_property('starred'),
                duration=tag.duration,
                bitRate=int(tag.bitrate or "0"),
                samplingRate=int(tag.samplerate or "0"),
                path=model.get_property('path'),
                discNumber=tag.disc or 0,
                genres=[{'name': tag.genre}] if tag.genre else [],
                artists=model.get_property('artists')
            )
        return models.SongDetails()

    def getServerInformation(self) -> dict:
        server_information = {
            'link': 'file://{}'.format(self.get_property('libraryDir')),
            'title': _("Local Files"),
            'username': os.getlogin()
        }
        return server_information

class Offline(Local):
    __gtype_name__ = 'NocturneIntegrationOffline'

    login_page_metadata = {
        'icon-name': 'network-offline-symbolic'
    }
    button_metadata = {
        'title': _("Offline Mode"),
        'subtitle': _("Access your downloads")
    }
    limitations = ('no-downloads', 'no-max-bitrate')

    libraryDir = GObject.Property(type=str, default=DOWNLOADS_DIR)

    def getServerInformation(self) -> dict:
        server_information = {
            'title': _("Offline Mode"),
            'username': os.getlogin()
        }
        return server_information



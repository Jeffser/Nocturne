# jellyfin.py

from gi.repository import GLib, GObject, Gdk, Gio
from . import secret, models, local, sql_instance
from .base import Base
from ..constants import DOWNLOAD_QUEUE_DIR, DOWNLOADS_DIR, DOWNLOAD_MIME_MAP, COVER_SIZE, get_nocturne_version, get_device_id
import os, platform, logging, io
from urllib.parse import urlencode
from concurrent.futures import wait
import threading
from enum import StrEnum
from PIL import Image

logger = logging.getLogger(__name__)

class MediaType(StrEnum):
    ALBUM = "MusicAlbum"
    ARTIST = "MusicArtist"
    SONG = "Audio"
    PLAYLIST = "Playlist"

class Jellyfin(Base):
    __gtype_name__ = 'NocturneIntegrationJellyfin'

    login_page_metadata = {
        'icon-name': "jellyfin-symbolic",
        'title': "Jellyfin",
        'description': _("Connect to a Jellyfin server."),
        'entries': ["url", "user", "password", "trust-server"],
    }
    button_metadata = {
        'title': _("Jellyfin"),
        'subtitle': _("Use an existing Jellyfin instance")
    }
    limitations = ('no-edit-radio',)
    cache_actions = {
        'deleted-radios': []
    }

    sqlSchema = {
        'ratings': {
            'id': 'TEXT PRIMARY KEY',
            'rating': 'INTEGER DEFAULT 1'
        }
    }

    url = GObject.Property(type=str, default="http://127.0.0.1:8096")

    # Loaded by API
    accessToken = GObject.Property(type=str)
    userId = GObject.Property(type=str)

    @property
    def libraryId(self) -> str:
        stored_id = ""
        if self.library_ids and self.library_ids[0] != "All":
            stored_id = self.library_ids[0]
        return stored_id

    #requests tracker
    #holds model_id as the key and whether the request was minimal as the value
    ongoing_requests = {}

    @property
    def AUTH_HEADER(self) -> str:
        return 'MediaBrowser Client="Nocturne", Device="{}", DeviceId="{}", Version="{}"'.format(platform.node(), get_device_id(), get_nocturne_version())

    def get_base_header(self) -> dict:
        headers = {
            "Authorization": self.AUTH_HEADER,
            "Accept": "application/json"
        }
        if token := self.get_property('accessToken'):
            headers["Authorization"] += ', Token="{}"'.format(token)
        return headers

    def get_url(self, action:str, **keys) -> str:
        action = action.format(userId=self.get_property('userId'), **keys)
        return '{}/{}'.format(self.get_property('url').strip('/'), action)

    def make_request(self, action:str, json:dict={}, params:dict={}, mode:str="GET", action_keys:dict={}) -> dict:
        def request_job(url):
            try:
                with self.session as current_session:
                    if mode == 'GET':
                        response = current_session.get(
                            url,
                            params=params,
                            json=json,
                            headers=self.get_base_header(),
                            verify=not self.get_property('trustServer'),
                            timeout=(3.05, 10)
                        )
                    elif mode == 'POST':
                        response = current_session.post(
                            url,
                            params=params,
                            json=json,
                            headers=self.get_base_header(),
                            verify=not self.get_property('trustServer'),
                            timeout=(3.05, 20)
                        )
                    elif mode == 'DELETE':
                        response = current_session.delete(
                            url,
                            params=params,
                            json=json,
                            headers=self.get_base_header(),
                            verify=not self.get_property('trustServer'),
                            timeout=(3.05, 10)
                        )
                    elif mode == 'RAWGET':
                        # Get without calling json()
                        response = current_session.get(
                            self.get_url(action, **action_keys),
                            params=params,
                            json=json,
                            headers=self.get_base_header(),
                            verify=not self.get_property('trustServer'),
                            timeout=(3.05, 10)
                        )
                        return response.status_code in (200, 201), response
                if response.status_code in (200, 201):
                    return True, response.json()
                elif response.status_code == 204:
                    return True, {'state': 'ok'}
            except Exception as e:
                logger.error(f"action error {action}: {e}")
            return False, {}
        action_url = self.get_url(action, **action_keys)
        request_id = '({}) {}?{}'.format(mode, action_url, urlencode(params))
        return self.cache_manager.get_result(request_id, request_job, action_url)

    def get_rating(self, model_id) -> int:
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT rating FROM ratings WHERE id = ?", (model_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def start_instance(self) -> bool:
        return True

    def terminate_instance(self):
        pass

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
            elif model.get_property('isExternalFile'):
                return 'file://{}'.format(model.get_property('path'))
        base_url = self.get_url('Audio/{}/stream'.format(song_id))
        max_bitrate = self.settings.get_value('max-bitrate').unpack()
        if max_bitrate == 0:
            return '{}?static=true&api_key={}'.format(
                base_url,
                self.get_property('accessToken')
            )
        else:
            return '{}?static=true&audioBitrate={}&api_key={}'.format(
                base_url,
                max_bitrate*1000,
                self.get_property('accessToken')
            )

    def initiateQuickConnect(self) -> dict:
        return self.make_request(
            action='QuickConnect/Initiate',
            mode='POST',
        )

    def checkQuickConnect(self, secret_str:str) -> bool:
        response = self.make_request(
            action='QuickConnect/Connect',
            params={'secret': secret_str}
        )
        if response.get('Authenticated'):
            secret.store_password(response.get("Secret"))
            return True
        return False

    def getLibraries(self) -> tuple[bool, list]:
        libraries = self.make_request(
            action='Users/{userId}/Views',
            mode='GET'
        ).get("Items", [])

        library_list = [{"id": library.get("Id"), "name": library.get("Name")} for library in libraries if library.get("CollectionType") == "music"]
        if len(library_list) > 1: #Add All button if multiple libraries present
            library_list.insert(0, {"name":_("All"), "id": "All"})
        return library_list, False

    def getCoverArtBytes(self, model_id:str, size:int) -> bytes:
        try:
            if not model_id:
                return b''
            url = 'Items/{id}/Images/Primary'
            if model := self.loaded_models.get(model_id):
                if image_url := self.loaded_models.get(model_id).get_property('coverArt'):
                    url = image_url
                else:
                    return b'' #will otherwise return a 404 error

            response = self.make_request(
                action=url,
                action_keys={'id': model_id},
                params={
                    'maxWidth': size,
                    'quality': 90
                },
                mode="RAWGET"
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"can't get image from {model_id}: {e}")
        return b''

    def getCachedCoverArt(self, model_id:str=''):
        sizes = {
            'gdkPaintableBig': COVER_SIZE["big"],
            'gdkPaintable': COVER_SIZE["small"]
        }
        for property_name, size in sizes.items():
            covers = {}
            raw_bytes = self.get_cache_image(model_id, size)
            if raw_bytes:
                try:
                    gbytes = GLib.Bytes.new(raw_bytes)
                    texture = Gdk.Texture.new_from_bytes(gbytes)
                    covers.update({property_name: texture})
                except Exception as e:
                    logger.error(f"can't convert image from {model_id} (size {size}): {e}")
        return covers

    def updateCoverArt(self, model_id:str=''):
        def resize_image(image_bytes:b'', size):
            in_stream = io.BytesIO(image_bytes)
            image = Image.open(in_stream)
            image_format = image.format
            image.thumbnail((size, size))
            out_stream = io.BytesIO()
            image.save(out_stream, format=image_format)
            return out_stream.getvalue()

        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                local.Local.updateCoverArt(self, model_id)
                return

            size = COVER_SIZE
            if not model.get_property('gdkPaintableBig') or not model.get_property('gdkPaintable'):
                gdkPaintable_bytes = self.get_cache_image(model_id, size["small"])
                gdkPaintableBig_bytes = self.get_cache_image(model_id, size["big"])
                save_cache_small = not gdkPaintable_bytes
                save_cache_big = not gdkPaintableBig_bytes
                if not gdkPaintableBig_bytes:
                    if model.get_property('coverArt'):
                        gdkPaintableBig_bytes = self.getCoverArtBytes(model_id, size["big"])
                    elif isinstance(model, models.Song) and not model.get_property("albumArtCheck"):
                        gdkPaintableBig_bytes = self.getCoverArtBytes(model.get_property('albumId'), size["big"])
                if gdkPaintableBig_bytes:
                    if not gdkPaintable_bytes:
                        gdkPaintable_bytes = resize_image(gdkPaintableBig_bytes, size["small"])
                    try:
                        gbytes_small = GLib.Bytes.new(gdkPaintable_bytes)
                        gdkPaintable = Gdk.Texture.new_from_bytes(gbytes_small)
                        if save_cache_small:
                            self.save_cache_image(model_id, size["small"], gdkPaintable_bytes)
                        gbytes_big = GLib.Bytes.new(gdkPaintableBig_bytes)
                        gdkPaintableBig = Gdk.Texture.new_from_bytes(gbytes_big)
                        if save_cache_big:
                            self.save_cache_image(model_id, size["big"], gdkPaintableBig_bytes)
                        self.__write_to_model(model_id, dict(gdkPaintable=gdkPaintable, gdkPaintableBig=gdkPaintableBig))
                    except Exception as e:
                        logger.error(f"can't convert image from {model_id}: {e}")


    def getCoverArtUrl(self, model_id) -> str:
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                return ""
            params = {
                'maxWidth': 240,
                'quality': 90
            }
            if token := self.get_property('accessToken'):
                params['api_key'] = token

            if model.get_property('coverArt'):
                url = self.get_url(model.get_property('coverArt'))
            else:
                url = self.get_url('Items/{id}/Images/Primary', id=model_id)

            return '{}?{}'.format(url, urlencode(params))
        return ""

    def ping(self) -> dict:
        self.set_property('accessToken', "")
        self.set_property('userId', "")
        response = self.make_request(
            action='Users/AuthenticateWithQuickConnect',
            json={
                "Secret": secret.get_plain_password()
            },
            mode='POST'
        )
        self.set_property('accessToken', response.get('AccessToken'))
        self.set_property('userId', response.get('User', {}).get('Id'))
        if self.get_property("accessToken") and self.get_property("userId"):
            self.set_property("user", response.get('User', {}).get('Name'))
        else:
            response = self.make_request(
                action='Users/AuthenticateByName',
                json={
                    'Username': self.get_property('user'),
                    'Pw': secret.get_plain_password()
                },
                mode='POST'
            )
            self.set_property('accessToken', response.get('AccessToken'))
            self.set_property('userId', response.get('User', {}).get('Id'))
        if self.get_property('accessToken') and self.get_property('userId'):
            if not self.library_ids:
                libraries, _ = self.getLibraries()
                if libraries:
                    self.settings.set_strv("library-ids", [libraries[0].get("id")])
            return super().ping()
        return {
            'status': 'error',
            'message': _('Could not log in')
        }

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        params = {
            "IncludeItemTypes": MediaType.ALBUM,
            "Recursive": "true",
            "Limit": size,
            "StartIndex": offset,
            "Fields": "ArtistItems,IsFavorite",
            "ParentId": self.libraryId
        }
        if list_type == "random":
            params["SortBy"] = "Random"
        elif list_type == "newest":
            params["SortBy"] = "DateCreated"
            params["SortOrder"] = "Descending"
        elif list_type == "frequent":
            params["SortBy"] = "PlayCount"
            params["SortOrder"] = "Descending"
        elif list_type == "recent":
            params["SortBy"] = "DatePlayed"
            params["SortOrder"] = "Descending"
        elif list_type == "starred":
            params["Filters"] = "IsFavorite"

        albums = self.make_request(
            action='Users/{userId}/Items',
            mode='GET',
            params=params
        ).get('Items', [])
        self.__bulk_compile(MediaType.ALBUM, albums)
        return [album.get("Id") for album in albums]

    def getArtists(self, size:int=10) -> list:
        artists = self.make_request(
            action='Artists/AlbumArtists',
            mode='GET',
            params={
                "Limit": size,
                "Recursive": "true",
                "Fields": "Overview,SimilarItems,UserData",
                "SortBy": "Random",
                "SortOrder": "Ascending",
                "ParentId": self.libraryId
            }
        ).get('Items', [])
        self.__bulk_compile("MusicArtist", artists)
        return [artist.get("Id") for artist in artists]

    def getPlaylists(self) -> list:
        playlists = self.make_request(
            action='Users/{userId}/Items',
            mode='GET',
            params={
                "IncludeItemTypes": MediaType.PLAYLIST,
                "Recursive": "true",
                "Fields": "None"
            }
        ).get('Items', [])
        id_list = []
        self.__bulk_compile(MediaType.PLAYLIST, playlists)
        return [playlist.get("Id") for playlist in playlists]

    def getStarred(self, item_type:str) -> list:
        check = {
            "artist": MediaType.ARTIST,
            "album": MediaType.ALBUM,
            "song": MediaType.SONG,
            "playlist": MediaType.PLAYLIST
        }
        if item_type == 'artist':
            items = self.make_request(
                action='Artists/AlbumArtists',
                mode="GET",
                params={
                    "userId": self.get_property("userId"),
                    "parentId": self.libraryId,
                    "Recursive": "true",
                    "Filters": "isFavorite"
                }
            ).get('Items', [])
        else:
            params = {
                "IncludeItemTypes": check[item_type],
                "Recursive": "true",
                "Fields": "Id",
                "Filters": "IsFavorite"
            }
            if item_type != 'playlist':
                params["ParentId"] = self.libraryId

            items = self.make_request(
                action="Users/{userId}/Items",
                mode="GET",
                params=params
            ).get("Items", [])

        self.__bulk_compile(check[item_type], items)
        return [item.get("Id") for item in items]


    def verifyArtist(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        def fetch_artist():
            artist = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode="GET"
            )
            if artist.get("Id"):
                artist_dict = self.__compile_response_json(artist, MediaType.ARTIST)
                self.__write_to_model(model_id, artist_dict, wait=True) #wait to ensure model is present for other fetch functions
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        def fetch_albums():
            params={
                "AlbumArtistIds": [model_id],
                "IncludeItemTypes": MediaType.ALBUM,
                "Recursive": "true",
                "SortBy": "PremiereDate"
            }
            if minimal:
                params["Limit"]=0 #Prevents complex db query
                params["Fields"]=None
                params["EnableImages"]="false"
                params["EnableUserData"]="false"
                del params["SortBy"]

            albums_request = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params=params
            )
            if total := albums_request.get("TotalRecordCount", 0):
                albums = albums_request.get("Items", [])
                if not minimal: self.__bulk_compile(MediaType.ALBUM, albums)
                self.__write_to_model(model_id, {
                    "albumCount": albums_request.get("TotalRecordCount"),
                    "album": [{"id": alb.get("Id"), "name": alb.get("Name")} for alb in albums]
                },
                wait=not use_threading)

        def fetch_similar():
            similar_request = self.make_request(
                action='/Items/{id}/Similar?userId={userId}',
                action_keys={"id": model_id},
                params={"limit": 12},
                mode="GET"
            )
            if similar := similar_request.get("Items", []):
                self.__bulk_compile(MediaType.ARTIST, similar)
                self.__write_to_model(model_id, {
                    "similarArtist":[{"id": sim.get("Id"), "name": sim.get("Name")} for sim in similar]
                },
                wait = not use_threading)

        def fetch_all():
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Artist(id=model_id)
                fetch_artist()
            if model_id in self.loaded_models:
                futures = []
                model = self.loaded_models[model_id]
                if not model.get_property("album"):
                    if use_threading: futures.append(self.threads.submit(fetch_albums))
                    else: fetch_albums()
                if (not model.get_property("gdkPaintable") or not model.get_property("gdkPaintableBig")) and model.get_property("coverArt"):
                    if use_threading: futures.append(self.threads.submit(self.updateCoverArt(model_id)))
                    else: self.updateCoverArt(model_id)
                if not model.get_property("similarArtist") and not minimal:
                    if use_threading: futures.append(self.threads.submit(fetch_similar))
                    else: fetch_similar()
                wait(futures)
            if self.ongoing_requests[model_id] == minimal:
                del self.ongoing_requests[model_id]


        #Pre-check for argument validation and current active requests
        if not model_id or not model_id.strip():
            logger.debug("Empty Artist model_id, aborting.")
            return
        if model_id in self.ongoing_requests:
            if minimal or (not minimal and self.ongoing_requests[model_id] == False):
                return #return if ongoing request is present or not minimal
        self.ongoing_requests[model_id] = minimal

        if use_threading:
            threading.Thread(target=fetch_all, daemon=True).start()
        else:
            fetch_all()

    def verifyAlbum(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        def fetch_album():
            album = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode="GET"
            )

            if album.get("Id"):
                album_dict = self.__compile_response_json(album, MediaType.ALBUM)
                self.__write_to_model(model_id, album_dict, wait=True) #wait to ensure model is present for other fetch functions
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        def fetch_songs():
            songs_request = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params={
                    "ParentId": model_id,
                    "IncludeItemTypes": MediaType.SONG,
                    "Recursive": "true",
                    "Fields": "RunTimeTicks,IndexNumber,ParentIndexNumber,ProductionYear",
                    "SortBy": "ParentIndexNumber,IndexNumber",
                    "SortOrder": "Ascending"
                }
            )

            if total := songs_request.get("TotalRecordCount", 0):
                songs = songs_request.get("Items", [])
                duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)
                if total > 0: self.__bulk_compile(MediaType.SONG, songs)
                self.__write_to_model(model_id, {
                    "songCount": total,
                    "duration": duration,
                    "song": [{"id": song.get("Id"), "name": song.get("Name")} for song in songs]
                },
                wait=not use_threading) #ensure songs are there for app actions

        def fetch_all():
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Album(id=model_id)
                fetch_album()
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                futures = []
                if not model.get_property("song") and not minimal:
                    if use_threading: futures.append(self.threads.submit(fetch_songs))
                    else: fetch_songs()
                if (not model.get_property("gdkPaintable") or not model.get_property("gdkPaintableBig")) and model.get_property("coverArt"):
                    if use_threading: futures.append(self.threads.submit(self.updateCoverArt(model_id)))
                    else: self.updateCoverArt(model_id)
                wait(futures)
            if self.ongoing_requests[model_id] == minimal:
                del self.ongoing_requests[model_id]


        #Pre-check for argument validation and current active requests
        if not model_id or not model_id.strip():
            logger.debug("Empty Album model_id, aborting.")
            return
        if model_id in self.ongoing_requests:
            if minimal or (not minimal and self.ongoing_requests[model_id] == False):
                return #return if ongoing request is present or not minimal
        self.ongoing_requests[model_id] = minimal

        if use_threading:
            threading.Thread(target=fetch_all, daemon=True).start()
        else:
            fetch_all()

    def verifyPlaylist(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        def fetch_playlist():
            playlist = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode="GET"
            )
            if playlist.get("Id"):
                playlist_dict = self.__compile_response_json(playlist, MediaType.PLAYLIST)
                self.__write_to_model(model_id, playlist_dict, wait=True) #wait to ensure model is present for other fetch functions
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        def get_songs():
            params = {
                "UserId": self.get_property("userId"),
                "Fields": "RunTimeTicks"
            }
            if minimal:
                params["Limit"]=0
                params["Fields"]=None
                params["EnableImages"]="false"
                params["EnableUserData"]="false"

            songs_response = self.make_request(
                action='Playlists/{id}/Items',
                action_keys={"id": model_id},
                mode="GET",
                params=params
            )
            if total := songs_response.get("TotalRecordCount"):
                songs = songs_response.get("Items", [])
                duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)
                self.__bulk_compile(MediaType.SONG, songs)
                self.__write_to_model(model_id, {
                    "songCount": total,
                    "duration": duration,
                    "entry": [{"id": song.get("Id"), "name": song.get("Name")} for song in songs]
                },
                wait=not use_threading) #ensure songs are there for app actions

        def fetch_all():
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Playlist(id=model_id)
                fetch_playlist()
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                futures = []
                if not model.get_property("entry"):
                    if use_threading: futures.append(self.threads.submit(get_songs))
                    else: get_songs()
                if (not model.get_property("gdkPaintable") or not model.get_property("gdkPaintableBig")) and model.get_property("coverArt"):
                    if use_threading: futures.append(self.threads.submit(self.updateCoverArt(model_id)))
                    else: self.updateCoverArt(model_id)
                wait(futures)
            if self.ongoing_requests[model_id] == minimal:
                del self.ongoing_requests[model_id]


        #Pre-check for argument validation and current active requests
        if not model_id or not model_id.strip():
            logger.debug("Empty Playlist model_id, aborting.")
            return
        if model_id in self.ongoing_requests:
            if minimal or (not minimal and self.ongoing_requests[model_id] == False):
                return #return if ongoing request is present or not minimal
        self.ongoing_requests[model_id] = minimal

        if use_threading:
            threading.Thread(target=fetch_all, daemon=True).start()
        else:
            fetch_all()

    def verifySong(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        def fetch_song():
            params = {
                "Fields": "ArtistItems,AlbumId,RunTimeTicks,UserData,IndexNumber,ParentIndexNumber"
            }
            song = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode='GET',
                params=params
            )
            if song.get("Id"):
                song_dict = self.__compile_response_json(song, MediaType.SONG)
                self.__write_to_model(model_id, song_dict, wait=True) #wait to ensure model is present for other fetch functions
            elif model_id in self.loaded_models:
                self.loaded_models.get(model_id).set_property('deleted', True)
                del self.loaded_models[model_id]

        def fetch_cover():
            model = self.loaded_models[model_id]
            cover_art = model.get_property("coverArt")
            covers = {}
            if not cover_art:
                cover_art = ""
                if model.get_property("albumId"): #check for loaded model
                    if model.get_property("albumId") in self.loaded_models:
                        if album_art := self.loaded_models[model.get_property("albumId")].get_property("coverArt"):
                            cover_art = album_art
                    else: #call API
                        album = self.make_request(
                            action='Users/{userId}/Items/{id}',
                            action_keys={"id": model.get_property("albumId")},
                            mode="GET"
                        )
                        if primary_tag := album.get('ImageTags', {}).get('Primary', ''):
                            cover_art = f"Items/{model.get_property('albumId')}/Images/Primary?={primary_tag}"
                self.__write_to_model(model_id, {"coverArt" : cover_art, "albumArtCheck": True}, wait=True)
            if cover_art:
                self.updateCoverArt(model_id)

        def fetch_all():
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Song(id=model_id)
                fetch_song()
            if model_id in self.loaded_models:
                model = self.loaded_models[model_id]
                if (not model.get_property("gdkPaintable") or not model.get_property("gdkPaintableBig")) and (model.get_property("coverArt") or not model.get_property("albumArtCheck")):
                    fetch_cover()
            if self.ongoing_requests[model_id] == minimal:
                del self.ongoing_requests[model_id]

        #Pre-check for argument validation and current active requests
        if not model_id or not model_id.strip():
            logger.debug("Empty Song model_id, aborting.")
            return
        if model_id in self.ongoing_requests:
            if minimal or (not minimal and self.ongoing_requests[model_id] == False):
                return #return if ongoing request is present or not minimal
        self.ongoing_requests[model_id] = minimal

        if use_threading:
            self.threads.submit(fetch_all)
        else:
            fetch_all()

    def star(self, model_id:str) -> bool:
        response = self.make_request(
            action='Users/{userId}/FavoriteItems/{id}',
            action_keys={"id": model_id},
            mode='POST'
        )
        return response.get('IsFavorite', False)

    def unstar(self, model_id:str) -> bool:
        response = self.make_request(
            action='Users/{userId}/FavoriteItems/{id}',
            action_keys={"id": model_id},
            mode='DELETE'
        )
        return not response.get('IsFavorite', False)

    def getPlayQueue(self) -> tuple:
        queue_dict = self.open_json('queue.json')
        song_list = [model_id for model_id in queue_dict.get('id', [])]
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
                if not model.isExternalFile:
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
        artist_songs = self.make_request(
            action='Users/{userId}/Items',
            mode="GET",
            params={
                "ArtistIds": model_id,
                "IncludeItemTypes": MediaType.SONG,
                "Recursive": "true",
                "Limit": 1,
            }
        ).get('Items', [])

        if len(artist_songs) == 0:
            return []

        songs = self.make_request(
            action='Items/{id}/Similar',
            action_keys={"id": artist_songs[0].get("Id")},
            mode='GET',
            params={
                "UserId": self.get_property("userId"),
                "Limit": count,
                "IncludeItemTypes": MediaType.SONG,
                "Fields": "ArtistItems,RunTimeTicks,UserData"
            }
        ).get("Items", [])

        self.__bulk_compile(MediaType.SONG, songs)
        return [song.get("Id") for song in songs]

    def getRandomSongs(self, size:int=20) -> list:
        songs = self.make_request(
            action='Users/{userId}/Items',
            mode="GET",
            params={
                "IncludeItemTypes": MediaType.SONG,
                "Recursive": "true",
                "Fields": "RunTimeTicks,UserData,ArtistItems",
                "Limit": size,
                "SortBy": "Random",
                "MediaTypes": MediaType.SONG,
                "ParentId":self.libraryId
            }
        ).get('Items', [])

        self.__bulk_compile(MediaType.SONG, songs)
        return [song.get("Id") for song in songs]

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
            result = self.make_request(
                action='Audio/{id}/Lyrics',
                action_keys={'id': songId},
                mode='GET'
            )
            if result.get('Lyrics', [{}])[0].get('Start'): # is lrc
                lines = []
                for line in result.get('Lyrics', []):
                    ms = line.get('Start') / 10000
                    minutes = int(ms // 60000)
                    seconds = int((ms % 60000) // 1000)
                    centiseconds = int((ms % 1000) // 10)
                    timestamp = f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"
                    lines.append(f"{timestamp} {line.get('Text').strip()}")
                if content := '\n'.join(lines):
                    return True, {
                        'type': 'lrc',
                        'content': content
                    }
            else:
                text = '\n'.join([line.get('Text') for line in result.get('Lyrics', [])])
                if text:
                    return True, {
                        'type': 'plain',
                        'content': text
                    }
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

    def __fetch_type(self, item_type:MediaType, query:str, limit:int=5, offset:int=0, fields:str="", verify:bool=False):
        if limit == 0:
            return []
        # Method exclusive to Jellyfin, helper for searches
        items = []
        if item_type == MediaType.ARTIST:
            items = self.make_request(
                action='Artists/AlbumArtists',
                mode="GET",
                params={
                    "userId": self.get_property("userId"),
                    "parentId": self.libraryId,
                    "SearchTerm": query,
                    "Recursive": "true",
                    "Limit": limit,
                    "StartIndex": offset,
                    "Fields": fields
                }
            ).get('Items', [])
        else:
            params = {
                "SearchTerm": query,
                "IncludeItemTypes": item_type,
                "Recursive": "true",
                "Limit": limit,
                "StartIndex": offset,
                "Fields": fields
            }
            if item_type != "Playlist":
                params["ParentId"] = self.libraryId
            items = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params=params
            ).get('Items', [])

        if verify:
            self.__bulk_compile(item_type, items)
        return items

    def __bulk_compile(self, item_type:MediaType, items:list, wait=True):
        # Pre-compiles a list of response objects into the Models
        compiled = []
        for item in items:
            cover = self.getCachedCoverArt(item.get("Id"))
            compiled.append(self.__compile_response_json(item, item_type) | cover)

        #Write to models
        lock = threading.Event()
        def run():
            for item in compiled:
                model_id = item.get("id")
                if model_id not in self.loaded_models:
                    if item_type == MediaType.ARTIST:
                        self.loaded_models[model_id] = models.Artist(id=model_id)
                    elif item_type == MediaType.ALBUM:
                        self.loaded_models[model_id] = models.Album(id=model_id)
                    elif item_type == MediaType.SONG:
                        self.loaded_models[model_id] = models.Song(id=model_id)
                    elif item_type == MediaType.PLAYLIST:
                        self.loaded_models[model_id] = models.Playlist(id=model_id)
                self.loaded_models.get(model_id).update_data(**item)
            lock.set()

        GLib.idle_add(run)
        if wait: lock.wait()

    def __write_to_model(self, model_id:str, data:dict, wait:bool=False):
        # Method to safely write data to GObject models on main thread
        # wait determines whether the function waits for the main thread write to finish
        #   true - calls main thread and locks background thread until main thread finishes
        #   false - calls main thread and immediately returns
        lock = threading.Event()
        def run():
            self.loaded_models.get(model_id).update_data(**data)
            lock.set()

        GLib.idle_add(run)
        if wait: lock.wait() #pause thread until main thread dispatch finishes

    def __compile_response_json(self, item:dict, model_type:MediaType):
        # Compiles the response for the basic MediaType responses
        # NOTE: Not meant for anything but the base Jellyfin response object
        # Mainly used for pre-fetching content
        primary_tag = item.get('ImageTags', {}).get('Primary', '')
        cover_art = f"Items/{item.get("Id")}/Images/Primary?={primary_tag}" if primary_tag else ""

        if model_type == MediaType.ARTIST:
            return {
                "id": item.get("Id"),
                "name": item.get("Name"),
                "coverArt": cover_art,
                "starred": item.get("UserData", {}).get("IsFavorite", False),
                "biography": item.get("Overview", ""),
                "userRating": self.get_rating(item.get("Id"))
            }
        elif model_type == MediaType.ALBUM:
            artists = item.get("ArtistItems", [])
            if not artists:
                artists = item.get("AlbumArtists", [])

            return {
                "id": item.get("Id"),
                "name": item.get("Name"),
                "artist": item.get("AlbumArtist"),
                "artistId": artists[0].get("Id") if artists else None,
                "coverArt": cover_art,
                "artists": [{"id": art.get("Id"), "name": art.get("Name")} for art in artists],
                "starred": item.get("UserData", {}).get("IsFavorite", False),
                "userRating": self.get_rating(item.get("Id")),
                "year": item.get("ProductionYear", 0)
            }
        elif model_type == MediaType.PLAYLIST:
            return {
                "id": item.get("Id"),
                "name": item.get("Name"),
                "coverArt": cover_art
            }
        elif model_type == MediaType.SONG:
            duration = int(item.get("RunTimeTicks", 0) / 10000000)

            artists = item.get("ArtistItems", [])
            if not artists:
                artists = item.get("AlbumArtists", [])

            return {
                "id": item.get("Id"),
                "title": item.get("Name"),
                "album": item.get("Album"),
                "albumId": item.get("AlbumId"),
                "artist": item.get("AlbumArtist"),
                "artistId": (artists or [{}])[0].get("Id"),
                "coverArt": cover_art,
                "duration": duration,
                "artists": [{"id": art.get("Id"), "name": art.get("Name")} for art in artists],
                "starred": item.get("UserData", {}).get("IsFavorite", False),
                "track": item.get("IndexNumber") or 0,
                "discNumber": item.get("ParentIndexNumber") or 0,
                "albumGain": item.get("AlbumNormalizationGain", item.get("NormalizationGain")) or 0.0,
                "trackGain": item.get("NormalizationGain") or 0.0,
                "userRating": self.get_rating(item.get("Id"))
            }

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0, playlistCount:int=0, playlistOffset:int=0) -> dict:
        return {
            'artist': [item.get("Id") for item in self.__fetch_type(MediaType.ARTIST, query, artistCount, artistOffset, verify=True)],
            'album': [item.get("Id") for item in self.__fetch_type(MediaType.ALBUM, query, albumCount, albumOffset, verify=True)],
            'song': [item.get("Id") for item in self.__fetch_type(MediaType.SONG, query, songCount, songOffset, verify=True)],
            'playlist': [item.get("Id") for item in self.__fetch_type(MediaType.PLAYLIST, query, playlistCount, playlistOffset, verify=True)]
        }

    def systemSearch(self, query:str) -> dict:
        results = {}

        # Artists
        for artist in self.__fetch_type(MediaType.ARTIST, query):
            icon_bytes = self.getCoverArtBytes(artist.get('Id'), 128)
            results[artist.get('Id')] = {
                'display': GLib.Variant('s', artist.get('Name')),
                'type': GLib.Variant('s', 'artist'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Albums
        for album in self.__fetch_type(MediaType.ALBUM, query):
            if artist := album.get('AlbumArtist'):
                display_name = '{} • {}'.format(album.get('Name'), artist)
            else:
                display_name = album.get('Name')
            icon_bytes = self.getCoverArtBytes(album.get('Id'), 128)
            results[album.get('Id')] = {
                'display': GLib.Variant('s', display_name),
                'type': GLib.Variant('s', 'album'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Songs
        for song in self.__fetch_type('Audio', query):
            if artist := song.get('AlbumArtist'):
                display_name = '{} • {}'.format(song.get('Name'), artist)
            else:
                display_name = song.get('Name')
            cover_id = song.get('Id')
            if not song.get('ImageTags', {}).get('Primary', ''):
                if album_id := song.get('AlbumId', ''):
                    cover_id = album_id
            icon_bytes = self.getCoverArtBytes(cover_id, 128)
            results[song.get('Id')] = {
                'display': GLib.Variant('s', display_name),
                'type': GLib.Variant('s', 'song'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        # Playlist
        for playlist in self.__fetch_type('Playlist', query):
            icon_bytes = self.getCoverArtBytes(playlist.get('Id'), 128)
            results[playlist.get('Id')] = {
                'display': GLib.Variant('s', playlist.get('Name')),
                'type': GLib.Variant('s', 'playlist'),
                'icon': GLib.Variant('ay', bytearray(icon_bytes))
            }

        return results

    def getInternetRadioStations(self) -> list:
        radios = self.make_request(
            action='LiveTv/Channels',
            mode='GET',
            params={
                "userId": self.get_property("userId"),
                "type": "Radio"
            }
        ).get('Items', [])

        id_list = []
        for radio in radios:
            if radio.get("Id") not in self.cache_actions.get('deleted-radios'):
                primary_tag = radio.get('ImageTags', {}).get('Primary', '')
                cover_art = f"Items/{radio.get('Id')}/Images/Primary?={primary_tag}" if primary_tag else ""
                radio_id = radio.get("Id")

                self.loaded_models[radio_id] = models.Song(id=radio_id)

                radio_dict = {
                    "id": radio_id,
                    "title": radio.get("Name"),
                    "duration": -1,
                    "coverArt": cover_art
                }

                raw_url = None
                radio_metadata = test_radio = self.make_request(
                    action='Items/{id}/PlaybackInfo',
                    action_keys={'id': radio.get('Id')},
                    params={
                        "fields": "Path",
                        "userId": self.get_property("userId")
                    }
                ).get('MediaSources', [])
                if len(radio_metadata) > 0:
                    raw_url = radio_metadata[0].get('Path')
                if not raw_url:
                    raw_url = self.get_stream_url(radio_id)
                radio_dict.update({"radioStreamUrl": raw_url})

                id_list.append(radio_id)
                self.__write_to_model(radio_id, radio_dict)

        return id_list

    def createInternetRadioStation(self, name:str, radioStreamUrl:str) -> bool:
        radio = self.make_request(
            action='LiveTv/TunerHosts',
            mode='POST',
            json={
                "Url": radioStreamUrl,
                "Type": "M3U",
                "FriendlyName": name
            }
        )
        if radio.get('Id'):
            self.loaded_models[radio.get("Id")] = models.Song(
                id=radio.get("Id"),
                title=radio.get("FriendlyName"),
                duration=-1,
                radioStreamUrl=radioStreamUrl
            )
            return True
        return False

    def deleteInternetRadioStation(self, model_id:str) -> bool:
        response = self.make_request(
            action='LiveTv/TunerHosts',
            mode='DELETE',
            params={
                "id": model_id
            }
        )
        if response.get('state') == 'ok':
            self.cache_actions['deleted-radios'].append(model_id)
            return True
        return False

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        if playlistId:
            #TODO update name
            if self.updatePlaylist(playlistId=playlistId, songIdToAdd=songId):
                return playlistId
            else:
                return ''
        response = self.make_request(
            action='Playlists',
            mode="POST",
            params={
                "UserId": self.get_property("userId"),
                "MediaType": MediaType.SONG
            },
            json={
                "Name": name,
                "Ids": ",".join(songId)
            }
        )
        return response.get("Id", "")

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        if songIndexToRemove:
            current_items = self.make_request(
                action='Playlists/{id}/Items',
                action_keys={"id": playlistId},
                mode="GET",
                params={
                    "UserId": self.get_property("userId")
                }
            ).get("Items", [])

            entry_ids_to_remove = []
            for index in songIndexToRemove:
                index = int(index)
                if 0 <= index < len(current_items):
                    entry_ids_to_remove.append(current_items[index].get("PlaylistItemId"))

            if entry_ids_to_remove:
                self.make_request(
                    action='Playlists/{id}/Items',
                    action_keys={"id": playlistId},
                    mode="DELETE",
                    params={
                        "EntryIds": ",".join(entry_ids_to_remove)
                    }
                )

        if songIdToAdd:
            self.make_request(
                action="Playlists/{id}/Items",
                action_keys={"id": playlistId},
                mode="POST",
                params={
                    "Ids": ",".join(songIdToAdd),
                    "UserId": self.get_property("userId")
                }
            )

        return True

    def deletePlaylist(self, model_id:str) -> bool:
        response = self.make_request(
            action='Items/{id}',
            action_keys={'id': model_id},
            mode="DELETE"
        )
        return response.get("state") == "ok"

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

    def getTopSongs(self, artist_id:str, count:int=10) -> list:
        songs = self.make_request(
            action='Users/{userId}/Items',
            mode='GET',
            params={
                'ArtistIds': artist_id,
                'IncludeItemTypes': 'Audio',
                'SortBy': 'PlayCount',
                'SortOrder': 'Descending',
                'Limit': count,
                'Recursive': 'true',
                'ParentId': self.libraryId
            }
        ).get('Items', [])
        self.__bulk_compile(MediaType.SONG, songs)
        return [song.get('Id') for song in songs if song.get('Id')]

    def downloadSong(self, model_id:str, file_title:str, progress_callback:callable):
        try:
            with self.session.get(self.get_url('Items/{id}/Download', id=model_id), headers=self.get_base_header(), stream=True) as r:
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
        except Exception as e:
            logger.error(f"can't download song {model_id}: {e}")

    def getSongDetails(self, model_id:str) -> models.SongDetails:
        song = self.make_request(
            action='Users/{userId}/Items/{id}',
            action_keys={'id': model_id},
            mode='GET',
            params={
                'fields': 'MediaSources,Genres,ArtistItems,Path,ProductionYear,Taglines'
            }
        )
        # Limitations:
        # - no bpm
        return models.SongDetails(
            id=model_id,
            title=song.get('Name'),
            album=song.get('Album'),
            albumId=song.get('AlbumId'),
            artist=song.get('Artists')[0] if song.get('Artists') else "",
            artistId=song.get('ArtistItems')[0].get('Id', '') if song.get('ArtistItems') else "",
            musicBrainzId=song.get("ProviderIds", {}).get("MusicBrainzTrack") or "",
            track=song.get('IndexNumber', 0),
            year=song.get('ProductionYear', 0),
            size=song.get('MediaSources', [{}])[0].get('Size', 0),
            suffix=song.get('MediaSources', [{}])[0].get('Container', _("Unknown")),
            starred=song.get('UserData', {}).get('IsFavorite', False),
            duration=song.get('RunTimeTicks', 1) / 10_000_000,
            bitRate=song.get('MediaSources', [{}])[0].get('Bitrate', 1) / 1000,
            bitDepth=song.get('MediaSources', [{}])[0].get('MediaStreams', [{}])[0].get('BitDepth', 0),
            samplingRate=song.get('MediaSources', [{}])[0].get('MediaStreams', [{}])[0].get('SampleRate', 1),
            path=song.get('Path'),
            discNumber=song.get('ParentIndexNumber', 0),
            genres=[{'name': genre} for genre in song.get('Genres', [])],
            artists=[{'name': art.get('Name'), 'id': art.get('Id')} for art in song.get('ArtistItems', [])],
            trackGain=song.get('NormalizationGain', 0.0),
            albumGain=song.get('NormalizationGain', 0.0)
        )


    def getServerInformation(self) -> dict:
        server_information = {
            'link': self.get_property('url').strip('/'),
            'username': self.get_property('user').title()
        }
        try:
            response = self.make_request(
                action='Users/{userId}/Images/Primary',
                params={
                    "maxWidth": 240,
                    "quality": 90
                },
                mode='RAWGET'
            )
            response_bytes = response.content if response.status_code in (200, 201) else b''
            if response_bytes and len(response_bytes) > 0:
                gbytes = GLib.Bytes.new(response_bytes)
                server_information['picture'] = Gdk.Texture.new_from_bytes(gbytes)
        except Exception as e:
            logger.error(f"can't get server information: {e}")

        try:
            info = self.make_request(
                action="System/Info",
                mode="GET"
            )
            server_information["title"] = "{} {}".format(info.get("ServerName"), info.get("Version"))
        except Exception as e:
            logger.error(f"can't get server information: {e}")

        return server_information

# jellyfin.py

from gi.repository import GLib, GObject, Gdk, Gio
from . import secret, models, local, sql_instance
from .base import Base
from ..constants import DOWNLOAD_QUEUE_DIR, DOWNLOADS_DIR, DOWNLOAD_MIME_MAP
import threading, os, platform, logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class Jellyfin(Base):
    __gtype_name__ = 'NocturneIntegrationJellyfin'

    login_page_metadata = {
        'icon-name': "network-server-symbolic",
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

    AUTH_HEADER = 'MediaBrowser Client="Nocturne", Device="{}", DeviceId="{}", Version="1.0.0"'.format(platform.node(), str(abs(hash(platform.node()))))

    url = GObject.Property(type=str, default="http://127.0.0.1:8096")

    # Loaded by API
    accessToken = GObject.Property(type=str)
    userId = GObject.Property(type=str)

    def get_base_header(self) -> dict:
        headers = {
            "Authorization": self.AUTH_HEADER
        }
        if token := self.get_property('accessToken'):
            headers["Authorization"] += ', Token="{}"'.format(token)
        return headers

    def get_url(self, action:str, **keys) -> str:
        action = action.format(userId=self.get_property('userId'), **keys)
        return '{}/{}'.format(self.get_property('url').strip('/'), action)

    def make_request(self, action:str, json:dict={}, params:dict={}, mode:str="GET", action_keys:dict={}) -> dict:
        params = {
            **params
        }
        headers = {
            **self.get_base_header(),
            "Accept": "application/json"
        }
        try:
            if mode == 'GET':
                response = self.session.get(
                    self.get_url(action, **action_keys),
                    params=params,
                    json=json,
                    headers=headers,
                    verify=not self.get_property('trustServer')
                )
            elif mode == 'POST':
                response = self.session.post(
                    self.get_url(action, **action_keys),
                    params=params,
                    json=json,
                    headers=headers,
                    verify=not self.get_property('trustServer')
                )
            elif mode == 'DELETE':
                response = self.session.delete(
                    self.get_url(action, **action_keys),
                    params=params,
                    json=json,
                    headers=headers,
                    verify=not self.get_property('trustServer')
                )
            if response.status_code in (200, 201):
                return response.json()
            elif response.status_code == 204:
                return {'state': 'ok'}
        except Exception as e:
            logger.error(f"action error {action}: {e}")
        return {}

    # ----------- #

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
        model = self.loaded_models.get(song_id)
        if radioStreamUrl := model.get_property('radioStreamUrl'):
            return radioStreamUrl
        elif model.get_property('isExternalFile'):
            return 'file://{}'.format(model.get_property('path'))
        base_url = self.get_url('Audio/{}/stream'.format(song_id))
        max_bitrate = Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('max-bitrate').unpack()
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

    def getCoverArt(self, model_id:str='', big:bool=False) -> Gdk.Paintable:
        if not model_id:
            return None
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                return local.Local.getCoverArt(self, model_id, big=big)
            if not big and model.get_property('gdkPaintable') is not None:
                return model.get_property('gdkPaintable')

            with self.cover_art_semaphore:
                # Re-check, another thread might have loaded it while waiting
                if not big and model.get_property('gdkPaintable') is not None:
                    return model.get_property('gdkPaintable')

                params = {
                    'maxWidth': 720 if big else 240,
                    'quality': 90
                }
                try:
                    response = self.session.get(
                        self.get_url('Items/{id}/Images/Primary', id=model_id),
                        headers=self.get_base_header(),
                        params=params,
                        verify=not self.get_property('trustServer'),
                        timeout=10
                    )
                    # Treat non-200 responses as empty content to avoid
                    # propagating network-related exceptions up and into the UI thread
                    response.raise_for_status()
                    response_bytes = response.content
                except Exception as e:
                    response_bytes = b''
                    logger.error(f"can't get image from {model_id}: {e}")

                if response_bytes and len(response_bytes) > 0:
                    try:
                        gbytes = GLib.Bytes.new(response_bytes)
                        texture = Gdk.Texture.new_from_bytes(gbytes)
                        if big:
                            return texture
                        model.set_property('gdkPaintable', texture)
                        return model.get_property('gdkPaintable')
                    except Exception as e:
                        logger.error(f"can't convert image from {model_id}: {e}")
        return None

    def getCoverArtUrl(self, model_id:str='', big:bool=False) -> str:
        if model := self.loaded_models.get(model_id):
            if isinstance(model, models.Song) and model.get_property('isExternalFile'):
                return ""
            params = {
                'maxWidth': 720 if big else 240,
                'quality': 90
            }
            if token := self.get_property('accessToken'):
                params['api_key'] = token
            return '{}?{}'.format(self.get_url('Items/{id}/Images/Primary', id=model_id), urlencode(params))
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
            return super().ping()
        return {
            'status': 'error',
            'message': _('Could not log in')
        }

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        params = {
            "IncludeItemTypes": "MusicAlbum",
            "Recursive": "true",
            "Limit": size,
            "StartIndex": offset,
            "Fields": "ArtistItems,IsFavorite",
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
        id_list = []
        for album in albums:
            artists = album.get("ArtistItems", [])
            songs = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params={
                    "ParentId": album.get("Id"),
                    "IncludeItemTypes": "Audio",
                    "Fields": "RunTimeTicks"
                }
            ).get("Items", [])

            duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)

            album_model = models.Album(
                id=album.get("Id"),
                name=album.get("Name"),
                artist=artists[0].get("Name") if artists else "Unknown",
                artistId=artists[0].get("Id") if artists else "",
                songCount=len(songs),
                duration=duration,
                artists=[{"id": art.get("Id"), "name": art.get("Name")} for art in artists],
                song=[{"id": song.get("Id"), "name": song.get("Name")} for song in songs],
                starred=album.get("UserData", {}).get("IsFavorite", False),
                userRating=self.get_rating(album.get("Id"))
            )
            self.loaded_models[album.get("Id")] = album_model
            id_list.append(album.get("Id"))
        return id_list

    def getArtists(self, size:int=10) -> list:
        params = {
            "Limit": size,
            "Recursive": "true",
            "Fields": "Overview,SimilarItems,UserData",
            "SortBy": "SortName",
            "SortOrder": "Ascending"
        }
        response = self.make_request(
            action='Artists',
            mode='GET',
            params=params
        )
        id_list = []
        for artist in response.get('Items', []):
            albums = self.make_request(
                action="Users/{userId}/Items",
                mode="GET",
                params={
                    "ArtistIds": artist.get("Id"),
                    "IncludeItemTypes": "MusicAlbum",
                    "Recursive": "true"
                }
            ).get("Items", [])

            artist_model = models.Artist(
                id=artist.get('Id'),
                name=artist.get('Name'),
                albumCount=len(albums),
                album=[{'id': alb.get("Id"), 'name': alb.get("Name")} for alb in albums],
                starred=artist.get("UserData", {}).get("IsFavorite", False),
                biography=artist.get("Overview", ""),
                similarArtist=[{'id': art.get("Id"), 'name': art.get("Name")} for art in artist.get("SimilarItems", [])],
                userRating=self.get_rating(artist.get("Id"))
            )
            self.loaded_models[artist.get("Id")] = artist_model
            id_list.append(artist.get("Id"))
        return id_list

    def getPlaylists(self) -> list:
        params = {
            "IncludeItemTypes": "Playlist",
            "Recursive": "true",
            "Fields": "None"
        }
        response = self.make_request(
            action='Users/{userId}/Items',
            mode='GET',
            params=params
        )
        id_list = []
        for playlist in response.get('Items', []):
            songs = self.make_request(
                action='Playlists/{id}/Items',
                action_keys={"id": playlist.get("Id")},
                mode="GET",
                params={
                    "Fields": "RunTimeTicks",
                    "UserId": self.get_property("userId")
                }
            ).get("Items", [])

            duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)

            playlist_model = models.Playlist(
                id=playlist.get("Id"),
                name=playlist.get("Name"),
                songCount=len(songs),
                duration=duration,
                entry=[{"id": song.get("Id"), "name": song.get("Name")} for song in songs]
            )
            self.loaded_models[playlist.get("Id")] = playlist_model
            id_list.append(playlist.get("Id"))
        return id_list

    def getStarredSongs(self) -> list:
        # The list request already returns full metadata for every song,
        # load it into the models so searching and displaying doesn't need
        # per song requests
        songs = self.make_request(
            action="Users/{userId}/Items",
            mode="GET",
            params={
                "IncludeItemTypes": "Audio",
                "Recursive": "true",
                "Fields": "ArtistItems,AlbumId,RunTimeTicks,UserData,IndexNumber,ParentIndexNumber",
                "Filters": "IsFavorite"
            }
        ).get("Items", [])

        return [song_id for song in songs if (song_id := self.load_song_dict(song))]

    def verifyArtist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            artist = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode="GET"
            )

            if artist.get("Id"):
                albums = self.make_request(
                    action='Users/{userId}/Items',
                    mode="GET",
                    params={
                        "ParentId": model_id,
                        "IncludeItemTypes": "MusicAlbum",
                        "Recursive": "true",
                        "Fields": "ItemCounts",
                        "SortBy": "PremiereDate"
                    }
                ).get("Items", [])

                self.loaded_models.get(model_id).update_data(
                    id=artist.get("Id"),
                    name=artist.get("Name"),
                    albumCount=len(albums),
                    album=[{"id": alb.get("Id"), "name": alb.get("Name")} for alb in albums],
                    starred=artist.get("UserData", {}).get("IsFavorite", False),
                    biography=artist.get("Overview", ""),
                    similarArtists=[{"id": art.get("Id"), "name": art.get("Name")} for art in artist.get("SimilarItems", [])],
                    userRating=self.get_rating(artist.get("Id"))
                )
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models or force_update:
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Artist(id=model_id)
            if use_threading:
                threading.Thread(target=run, daemon=True).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def verifyAlbum(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            album = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode="GET"
            )

            if album.get("Id"):
                songs = self.make_request(
                    action='Users/{userId}/Items',
                    mode="GET",
                    params={
                        "ParentId": model_id,
                        "IncludeItemTypes": "Audio",
                        "Recursive": "true",
                        "Fields": "RunTimeTicks,IndexNumber,ParentIndexNumber,ProductionYear",
                        "SortBy": "ParentIndexNumber,IndexNumber",
                        "SortOrder": "Ascending"
                    }
                ).get("Items", [])

                duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)

                for i, song in enumerate(songs):
                    if model := self.loaded_models.get(song.get("Id")):
                        model.update_data(track=song.get("IndexNumber") or i)

                self.loaded_models.get(model_id).update_data(
                    id=album.get("Id"),
                    name=album.get("Name"),
                    artist=album.get("AlbumArtist"),
                    artistId=album.get("ArtistItems", [{}])[0].get("Id") if album.get("ArtistItems") else None,
                    songCount=len(songs),
                    duration=duration,
                    artists=[{"id": art.get("Id"), "name": art.get("Name")} for art in album.get("ArtistItems", [])],
                    song=[{"id": song.get("Id"), "name": song.get("Name")} for song in songs],
                    starred=album.get("UserData", {}).get("IsFavorite", False),
                    userRating=self.get_rating(album.get("Id")),
                    year=album.get("ProductionYear", 0)
                )
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models or force_update:
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Album(id=model_id)
            if use_threading:
                threading.Thread(target=run, daemon=True).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def verifyPlaylist(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            playlist = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": model_id},
                mode="GET"
            )

            if playlist.get("Id"):
                songs = self.make_request(
                    action='Users/{userId}/Items',
                    mode="GET",
                    params={
                        "ParentId": model_id,
                        "IncludeItemTypes": "Audio",
                        "Recursive": "true",
                        "Fields": "RunTimeTicks"
                    }
                ).get("Items", [])

                duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)

                self.loaded_models.get(model_id).update_data(
                    id=playlist.get("Id"),
                    name=playlist.get("Name"),
                    songCount=len(songs),
                    duration=duration,
                    entry=[{"id": song.get("Id"), "name": song.get("Name")} for song in songs]
                )
            elif model_id in self.loaded_models:
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models or force_update:
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Playlist(id=model_id)
            if use_threading:
                threading.Thread(target=run, daemon=True).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(model_id,), daemon=True).start()

    def load_song_dict(self, song:dict) -> str:
        # Creates or updates a Song model from an API item dict, returns the model id
        model_id = song.get("Id", "")
        if not model_id:
            return ''
        data = dict(
            id=model_id,
            title=song.get("Name"),
            album=song.get("Album"),
            albumId=song.get("AlbumId"),
            artist=song.get("AlbumArtist"),
            artistId=(song.get("ArtistItems") or [{}])[0].get("Id"),
            duration=int(song.get("RunTimeTicks", 0) / 10000000),
            artists=[{"id": art.get("Id"), "name": art.get("Name")} for art in song.get("ArtistItems", [])],
            starred=song.get("UserData", {}).get("IsFavorite", False),
            track=song.get("IndexNumber") or 0,
            discNumber=song.get("ParentIndexNumber") or 0,
            albumGain=song.get("AlbumNormalizationGain", song.get("NormalizationGain")) or 0.0,
            trackGain=song.get("NormalizationGain") or 0.0,
            userRating=self.get_rating(model_id)
        )
        if model_id in self.loaded_models:
            self.loaded_models.get(model_id).update_data(**data)
        else:
            self.loaded_models[model_id] = models.Song(**data)
        return model_id

    def verifySong(self, model_id:str, force_update:bool=False, use_threading:bool=True):
        def run():
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
                self.load_song_dict(song)
            elif model_id in self.loaded_models:
                self.loaded_models.get(model_id).set_property('deleted', True)
                del self.loaded_models[model_id]

        if model_id not in self.loaded_models or force_update:
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = models.Song(id=model_id)
            if use_threading:
                threading.Thread(target=run, daemon=True).start()
            else:
                run()

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
                "IncludeItemTypes": "Audio",
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
                "IncludeItemTypes": "Audio",
                "Fields": "ArtistItems,RunTimeTicks,UserData"
            }
        ).get("Items", [])

        id_list = []
        for song in songs:
            if song.get("Id"):
                duration = int(song.get("RunTimeTicks", 0) / 10000000)
                properties = {
                    "id": song.get("Id"),
                    "title": song.get("Name"),
                    "album": song.get("Album"),
                    "albumId": song.get("AlbumId"),
                    "artist": song.get("AlbumArtist"),
                    "artistId": (song.get("ArtistItems") or [{}])[0].get("Id"),
                    "duration": duration,
                    "artists": [{"id": art.get("Id"), "name": art.get("Name")} for art in song.get("ArtistItems", [])],
                    "starred": song.get("UserData", {}).get("IsFavorite", False),
                    "userRating": self.get_rating(song.get("Id"))
                }
                if song.get("Id") in self.loaded_models:
                    self.loaded_models.get(song.get("Id")).update_data(**properties)
                else:
                    self.loaded_models[song.get("Id")] = models.Song(**properties)
                id_list.append(song.get("Id"))
        return id_list

    def getRandomSongs(self, size:int=20) -> list:
        songs = self.make_request(
            action='Users/{userId}/Items',
            mode="GET",
            params={
                "IncludeItemTypes": "Audio",
                "Recursive": "true",
                "Fields": "RunTimeTicks,UserData,ArtistItems",
                "Limit": size,
                "SortBy": "Random",
                "MediaTypes": "Audio"
            }
        ).get('Items', [])

        id_list = []
        for song in songs:
            if song.get("Id"):
                duration = int(song.get("RunTimeTicks", 0) / 10000000)
                properties = {
                    "id": song.get("Id"),
                    "title": song.get("Name"),
                    "album": song.get("Album"),
                    "albumId": song.get("AlbumId"),
                    "artist": song.get("AlbumArtist"),
                    "artistId": (song.get("ArtistItems") or [{}])[0].get("Id"),
                    "duration": duration,
                    "artists": [{"id": art.get("Id"), "name": art.get("Name")} for art in song.get("ArtistItems", [])],
                    "starred": song.get("UserData", {}).get("IsFavorite", False),
                    "userRating": self.get_rating(song.get("Id"))
                }
                if song.get("Id") in self.loaded_models:
                    self.loaded_models.get(song.get("Id")).update_data(**properties)
                else:
                    self.loaded_models[song.get("Id")] = models.Song(**properties)
            id_list.append(song.get("Id"))
        return id_list

    def getLyrics(self, songId:str) -> dict:
        result = self.make_request(
            action='Audio/{id}/Lyrics',
            action_keys={'id': songId},
            mode='GET'
        )
        isSynced = bool(result.get('Lyrics', [{}])[0].get('Start'))
        if isSynced:
            lines = []
            for line in result.get('Lyrics', []):
                lines.append({
                    'content': line.get('Text'),
                    'ms': line.get('Start') / 10000
                })
            return {
                'type': 'lrc',
                'content': lines
            }
        else:
            text = '\n'.join([line.get('Text') for line in result.get('Lyrics', [])])
            if text:
                return {
                    'type': 'plain',
                    'content': text
                }
        return {'type': 'not-found'}

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0, playlistCount:int=0, playlistOffset:int=0) -> dict:
        def fetch_type(item_type:str, limit:int, offset:int, fields:str=""):
            return self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params={
                    "SearchTerm": query,
                    "IncludeItemTypes": item_type,
                    "Recursive": "true",
                    "Limit": limit,
                    "StartIndex": offset,
                    "Fields": fields
                }
            ).get('Items', [])

        return {
            'artist': [item.get("Id") for item in fetch_type("MusicArtist", artistCount, artistOffset)],
            'album': [item.get("Id") for item in fetch_type("MusicAlbum", albumCount, albumOffset)],
            'song': [item.get("Id") for item in fetch_type("Audio", songCount, songOffset)],
            'playlist': [item.get("Id") for item in fetch_type("Playlist", playlistCount, playlistOffset)]
        }

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
                radio_model = models.Song(
                    id=radio.get("Id"),
                    title=radio.get("Name"),
                    duration=-1
                )
                self.loaded_models[radio.get("Id")] = radio_model

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
                    raw_url = self.get_stream_url(radio.get("Id"))
                self.loaded_models.get(radio.get("Id")).set_property("radioStreamUrl", raw_url)

                id_list.append(radio.get("Id"))
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
            return self.updatePlaylist(
                playlistId=playlistId,
                songIdToAdd=songId
            )

        response = self.make_request(
            action='Playlists',
            mode="POST",
            params={
                "UserId": self.get_property("userId"),
                "MediaType": "Audio"
            },
            json={
                "Name": name,
                "Ids": ",".join(songId)
            }
        )
        return response.get("Id")

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
                'Recursive': 'true'
            }
        ).get('Items', [])
        return [song.get('Id') for song in songs if song.get('Id')]

    def downloadSong(self, model_id:str, file_title:str, progress_callback:callable):
        headers = {
            **self.get_base_header(),
            "Accept": "application/json"
        }
        try:
            with self.session.get(self.get_url('Items/{id}/Download', id=model_id), headers=headers, stream=True) as r:
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
            params = {
                "maxWidth": 240,
                "quality": 90
            }
            response = self.session.get(
                self.get_url('Users/{userId}/Images/Primary'),
                params=params,
                verify=not self.get_property('trustServer')
            )
            response_bytes = response.content if response.status_code == 200 else b''
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


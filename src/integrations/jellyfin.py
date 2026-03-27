# jellyfin.py

from gi.repository import Gtk, GLib, GObject, Gdk, Gio, GdkPixbuf
from . import secret, models, local
from ..constants import get_pc_name
from .base import Base
import requests, subprocess, random, threading

class Jellyfin(Base):
    __gtype_name__ = 'NocturneIntegrationJellyfin'

    login_page_metadata = {
        'icon-name': "music-note-symbolic",
        'title': "Jellyfin",
        'entries': ["url", "user", "password"]
    }
    button_metadata = {
        'title': "Jellyfin",
        'subtitle': _("Use an existing Jellyfin instance")
    }
    url = GObject.Property(type=str)
    user = GObject.Property(type=str)

    AUTH_HEADER = 'MediaBrowser Client="Nocturne", Device="{}", DeviceId="{}", Version="1.0.0"'.format(get_pc_name(), str(random.randint(1000, 9999)))

    # Loaded by API
    accessToken = GObject.Property(type=str)
    userId = GObject.Property(type=str)

    def get_base_params(self) -> dict:
        #TODO
        return {}

    def get_base_header(self) -> dict:
        headers = {
            "X-Emby-Authorization": self.AUTH_HEADER
        }
        if token := self.get_property('accessToken'):
            headers["X-Emby-Authorization"] += ', Token="{}"'.format(token)
        return headers

    def get_url(self, action:str, **keys) -> str:
        action = action.format(userId=self.get_property('userId'), **keys)
        return '{}/{}'.format(self.get_property('url').strip('/'), action)

    def make_request(self, action:str, json:dict={}, params:dict={}, mode:str="GET", action_keys:dict={}) -> dict:
        params = {
            **self.get_base_params(),
            **params
        }
        headers = {
            **self.get_base_header(),
            "Accept": "application/json"
        }
        try:
            if mode == 'GET':
                response = requests.get(
                    self.get_url(action, **action_keys),
                    params=params,
                    json=json,
                    headers=headers
                )
            elif mode == 'POST':
                response = requests.post(
                    self.get_url(action, **action_keys),
                    params=params,
                    json=json,
                    headers=headers
                )
            elif mode == 'DELETE':
                response = requests.delete(
                    self.get_url(action, **action_keys),
                    params=params,
                    json=json,
                    headers=headers
                )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            pass
        return {}

    # ----------- #

    def start_instance(self) -> bool:
        return True

    def terminate_instance(self):
        pass

    def on_login(self):
        pass

    def get_stream_url(self, song_id:str) -> str:
        base_url = self.get_url('Audio/{}/stream'.format(song_id))
        url = '{}?static=true&api_key={}'.format(base_url, self.get_property('accessToken'))
        return url

    def getCoverArt(self, id:str=None) -> tuple:
        if id:
            if model := self.loaded_models.get(id):
                if isinstance(model, models.Song) and model.isRadio:
                    return self.getRadioCoverArt(id)
                if isinstance(model, models.Song) and model.isExternalFile:
                    return local.Local.getCoverArt(self, id)
                if model.get_property('gdkPaintable') is not None:
                    return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')

                params = {
                    **self.get_base_params(),
                    'maxWidth': 480,
                    'quality': 90
                }
                response = requests.get(
                    self.get_url('Items/{id}/Images/Primary', id=id),
                    headers=self.get_base_header(),
                    params=params
                )
                response_bytes = response.content if response.status_code == 200 else b''

                if response_bytes and len(response_bytes) > 0:
                    try:
                        gbytes = GLib.Bytes.new(response_bytes)
                        texture = Gdk.Texture.new_from_bytes(gbytes)
                        model.set_property('gdkPaintableBytes', gbytes)
                        model.set_property('gdkPaintable', texture)
                        return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                    except Exception as e:
                        pass

        return None, None

    def ping(self) -> bool:
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
        return self.get_property('accessToken') and self.get_property('userId')

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
            params["Filters"] = "IsPlayed"
        elif list_type == "starred":
            params["Filters"] = "IsFavorite"

        response = self.make_request(
            action='Users/{userId}/Items',
            mode='GET',
            params=params
        )
        id_list = []
        for album in response.get('Items'):
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
                starred=album.get("UserData", {}).get("IsFavorite", False)
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
                similarArtist=[{'id': art.get("Id"), 'name': art.get("Name")} for art in artist.get("SimilarItems", [])]
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

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            artist = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": id},
                mode="GET"
            )

            albums = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params={
                    "ParentId": id,
                    "IncludeItemTypes": "MusicAlbum",
                    "Recursive": "true",
                    "Fields": "ItemCounts"
                }
            ).get("Items", [])

            self.loaded_models.get(id).update_data(
                id=artist.get("Id"),
                name=artist.get("Name"),
                albumCount=len(albums),
                album=[{"id": alb.get("Id"), "name": alb.get("Name")} for alb in albums],
                starred=artist.get("UserData", {}).get("IsFavorite", False),
                biography=artist.get("Overview", ""),
                similarArtists=[{"id": art.get("Id"), "name": art.get("Name")} for art in artist.get("SimilarItems", [])]
            )

        if id not in self.loaded_models or force_update:
            if id not in self.loaded_models:
                self.loaded_models[id] = models.Artist(id=id)
            if use_threading:
                threading.Thread(target=run).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            album = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": id},
                mode="GET"
            )

            songs = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params={
                    "ParentId": id,
                    "IncludeItemTypes": "Audio",
                    "Recursive": "true",
                    "Fields": "RunTimeTicks"
                }
            ).get("Items", [])

            duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)

            self.loaded_models.get(id).update_data(
                id=album.get("Id"),
                name=album.get("Name"),
                artist=album.get("AlbumArtist"),
                artistId=album.get("ArtistItems", [{}])[0].get("Id") if album.get("ArtistItems") else None,
                songCount=len(songs),
                duration=duration,
                artists=[{"id": art.get("Id"), "name": art.get("Name")} for art in album.get("ArtistItems", [])],
                song=[{"id": song.get("Id"), "name": song.get("Name")} for song in songs],
                starred=album.get("UserData", {}).get("IsFavorite", False)
            )

        if id not in self.loaded_models or force_update:
            if id not in self.loaded_models:
                self.loaded_models[id] = models.Album(id=id)
            if use_threading:
                threading.Thread(target=run).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            playlist = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": id},
                mode="GET"
            )

            songs = self.make_request(
                action='Users/{userId}/Items',
                mode="GET",
                params={
                    "ParentId": id,
                    "IncludeItemTypes": "Audio",
                    "Recursive": "true",
                    "Fields": "RunTimeTicks"
                }
            ).get("Items", [])

            duration = int(sum(song.get("RunTimeTicks", 0) for song in songs) / 10000000)

            self.loaded_models.get(id).update_data(
                id=playlist.get("Id"),
                name=playlist.get("Name"),
                songCount=len(songs),
                duration=duration,
                entry=[{"id": song.get("Id"), "name": song.get("Name")} for song in songs]
            )

        if id not in self.loaded_models or force_update:
            if id not in self.loaded_models:
                self.loaded_models[id] = models.Playlist(id=id)
            if use_threading:
                threading.Thread(target=run).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        def run():
            params = {
                "Fields": "ArtistItems,AlbumId,RunTimeTicks,UserData"
            }
            song = self.make_request(
                action='Users/{userId}/Items/{id}',
                action_keys={"id": id},
                mode='GET',
                params=params
            )

            duration = int(song.get("RunTimeTicks", 0) / 10000000)

            self.loaded_models.get(id).update_data(
                id=song.get("Id"),
                title=song.get("Name"),
                album=song.get("Album"),
                albumId=song.get("AlbumId"),
                artist=song.get("AlbumArtist"),
                artistId=song.get("ArtistItems", [{}])[0].get("Id"),
                duration=duration,
                artists=[{"id": art.get("Id"), "name": art.get("Name")} for art in song.get("ArtistItems", [])],
                starred=song.get("UserData", {}).get("IsFavorite", False)
            )

        if id not in self.loaded_models or force_update:
            if id not in self.loaded_models:
                self.loaded_models[id] = models.Song(id=id)
            if use_threading:
                threading.Thread(target=run).start()
            else:
                run()

        threading.Thread(target=self.getCoverArt, args=(id,)).start()

    def star(self, id:str) -> bool:
        response = self.make_request(
            action='Users/{userId}/FavoriteItems/{id}',
            action_keys={"id": id},
            mode='POST'
        )
        return response.get('IsFavorite', False)

    def unstar(self, id:str) -> bool:
        response = self.make_request(
            action='Users/{userId}/FavoriteItems/{id}',
            action_keys={"id": id},
            mode='DELETE'
        )
        return not response.get('IsFavorite', False)

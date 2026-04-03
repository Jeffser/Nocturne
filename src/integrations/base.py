# base.py

from gi.repository import Gtk, GLib, GObject, Gdk
from . import models
import requests, favicon, io, urllib3
from PIL import Image
from urllib.parse import urlparse

# Just so that the logs don't get cluttered with warnings if trust-server = True
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# DO NOT USE DIRECTLY
class Base(GObject.Object):
    __gtype_name__ = 'NocturneIntegrationBase'

    # For how to fill these checkout navidrome.py and local.py
    login_page_metadata = {}
    button_metadata = {}
    limitations = ()

    # Always have a currentSong inside loaded_models
    loaded_models = {'currentSong': models.CurrentSong()}

    def check_if_ready(self, row) -> bool:
        # gets called to see if it is ready to show login page
        return True

    def connect_to_model(self, id:str, parameter:str, callback:callable) -> str:
        # do not modify this function, it works as is in any instance
        connection_id = ""
        if id in self.loaded_models:
            connection_id = self.loaded_models.get(id).connect(
                'notify::{}'.format(parameter),
                lambda *_, parameter=parameter, id=id: GLib.idle_add(callback, self.loaded_models.get(id).get_property(parameter))
            )
            GLib.idle_add(callback, self.loaded_models.get(id).get_property(parameter))
        return connection_id

    def start_instance(self) -> bool:
        # always called in different thread, because it might take a couple of seconds to get started
        print('WARNING', 'start_instance', 'not implemented')
        return False

    def terminate_instance(self):
        # called when the instance is no longer used
        print('WARNING', 'terminate_instance', 'not implemented')

    def on_login(self):
        # gets called in different thread when the login is successful
        print('WARNING', 'on_login', 'not implemented')

    def get_stream_url(self, song_id:str) -> str:
        # should return a valid url for a gst stream
        print('WARNING', 'get_stream_url', 'not implemented')
        return ""

    def getRadioCoverArt(self, id:str=None) -> tuple:
        # returns bytes, Gdk.Paintable or None, None
        if id:
            if model := self.loaded_models.get(id):
                if model.gdkPaintable:
                    return model.gdkPaintableBytes, model.gdkPaintable
                if streamUrl := urlparse(model.get_property('streamUrl')):
                    icons = favicon.get('{}://{}'.format(streamUrl.scheme, streamUrl.netloc))
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
                            gbytes = GLib.Bytes.new(png_bytes)
                            texture = Gdk.Texture.new_from_bytes(gbytes)
                            model.set_property('gdkPaintableBytes', gbytes)
                            model.set_property('gdkPaintable', texture)
                            return model.get_property('gdkPaintableBytes'), model.get_property('gdkPaintable')
                        except Exception as e:
                            pass
        return None, None

    def getCoverArt(self, id:str=None) -> tuple:
        # should set GdkPaintable and gdkPaintableBytes from Model
        # should return GLib.Bytes, Gdk.Paintable (texture)
        print('WARNING', 'getCoverArt', 'not implemented')
        return None, None

    def ping(self) -> bool:
        # return True if logged in and connection is successful
        print('WARNING', 'ping', 'not implemented')
        return False

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        print('WARNING', 'getAlbumList', 'not implemented')
        return []

    def getArtists(self, size:int=10) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        print('WARNING', 'getArtists', 'not implemented')
        return []

    def getPlaylists(self) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        print('WARNING', 'getPlaylists', 'not implemented')
        return []

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt
        print('WARNING', 'verifyArtist', 'not implemented')

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt
        print('WARNING', 'verifyAlbum', 'not implemented')

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt
        print('WARNING', 'verifyPlaylist', 'not implemented')

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        # verifies that element is fully loaded with all it's metadata, should also call for getCoverArt or getRadioCoverArt
        print('WARNING', 'verifySong', 'not implemented')

    def favorite(self, id:str) -> bool:
        # stars an element, should return True if change is done
        print('WARNING', 'star', 'not implemented')
        return False

    def unfavorite(self, id:str) -> bool:
        # unfavorites an element, should return True if change is done
        print('WARNING', 'unfavorite', 'not implemented')
        return False

    def getPlayQueue(self) -> tuple:
        # returns the song ID to be played and a list of IDs
        print('WARNING', 'getPlayQueue', 'not implemented')
        return "", []

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        # save the play queue for retrieving later, called on close, return True if ok
        print('WARNING', 'savePlayQueue', 'not implemented')
        return False

    def getSimilarSongs(self, id:str, count:int=20) -> list:
        # returns list of IDs of similar songs to id, if it can not be implemented just return the result of getRandomSongs
        print('WARNING', 'getSimilarSongs', 'not implemented')
        return []

    def getRandomSongs(self, size:int=20) -> list:
        # returns a list of song IDs
        print('WARNING', 'getRandomSongs', 'not implemented')
        return []

    def getLyrics(self, songId:str) -> dict:
        # returns same dicts as lyrics -> helpers -> get_lyrics
        return {'type': 'not-found'}

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0) -> dict:
        # returns a dict with results trucated with the count and offset, the dict has keys for album, artist and song, the values are lists of IDs
        # for an example view local.py
        print('WARNING', 'search', 'not implemented')
        return {'artist': {}, 'album': {}, 'song': {}}

    def getInternetRadioStations(self) -> list:
        # returns a list of Song IDs with the property isRadio=True
        # make sure the id also exists in self.loaded_models, no need to be verified
        print('WARNING', 'getInternetRadioStations', 'not implemented')
        return []

    def createInternetRadioStation(self, name:str, streamUrl:str) -> bool:
        # returns True if created successfully
        print('WARNING', 'createInternetRadioStation', 'not implemented')
        return False

    def updateInternetRadioStation(self, id:str, name:str, streamUrl:str) -> bool:
        # returns True if updated successfully
        print('WARNING', 'updateInternetRadioStation', 'not implemented')
        return False

    def deleteInternetRadioStation(self, id:str) -> bool:
        # returns True if deleted successfully
        print('WARNING', 'deleteInternetRadioStation', 'not implemented')
        return False

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        # returns id if created successfully
        print('WARNING', 'createPlaylist', 'not implemented')
        return ""

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        # returns True if updated successfully
        print('WARNING', 'updatePlaylist', 'not implemented')
        return False

    def deletePlaylist(self, id:str) -> bool:
        # returns True if deleted successfully
        print('WARNING', 'deletePlaylist', 'not implemented')
        return False

    def scrobble(self, id:str):
        # the id is for a Song, this is how views are stored
        # called when a song is played
        print('WARNING', 'scrobble', 'not implemented')
    
    def getServerInformation(self) -> dict:
        # should return these keys:
        # picture : gdk.Paintable
        # username : str
        # title : str
        # link : str
        print('WARNING', 'getServerInformation', 'not implemented')
        return {}

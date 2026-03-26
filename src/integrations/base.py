# base.py

from gi.repository import Gtk, GLib, GObject, Gdk
from . import models

class Base(GObject.Object):
    __gtype_name__ = 'NocturneIntegrationBase'

    loaded_models = {'currentSong': models.CurrentSong()}

    def connect_to_model(self, id:str, parameter:str, callback:callable, use_gtk_thread:bool=True) -> str:
        use_gtk_thread = True
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
        print('WARNING', 'get_stream_url', 'not implemented')
        return ""

    def getRadioCoverArtWithBytes(self, id:str=None) -> tuple:
        print('WARNING', 'getRadioCoverArtWithBytes', 'not implemented')
        return None, None

    def getCoverArtWithBytes(self, id:str=None) -> tuple:
        print('WARNING', 'getCoverArtWithBytes', 'not implemented')
        return None, None

    def getCoverArt(self, id:str=None) -> Gdk.Paintable | None:
        print('WARNING', 'getCoverArt', 'not implemented')
        return None

    def ping(self) -> bool:
        print('WARNING', 'ping', 'not implemented')
        return False

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        print('WARNING', 'getAlbumList', 'not implemented')
        return []

    def getArtists(self, size:int=10) -> list:
        print('WARNING', 'getArtists', 'not implemented')
        return []

    def getPlaylists(self) -> list:
        print('WARNING', 'getPlaylists', 'not implemented')
        return []

    def verifyArtist(self, id:str, force_update:bool=False, use_threading:bool=True):
        print('WARNING', 'verifyArtist', 'not implemented')

    def verifyAlbum(self, id:str, force_update:bool=False, use_threading:bool=True):
        print('WARNING', 'verifyAlbum', 'not implemented')

    def verifyPlaylist(self, id:str, force_update:bool=False, use_threading:bool=True):
        print('WARNING', 'verifyPlaylist', 'not implemented')

    def verifySong(self, id:str, force_update:bool=False, use_threading:bool=True):
        print('WARNING', 'verifySong', 'not implemented')

    def star(self, id:str) -> bool:
        print('WARNING', 'star', 'not implemented')
        return False

    def unstar(self, id:str) -> bool:
        print('WARNING', 'unstar', 'not implemented')
        return False

    def getPlayQueue(self) -> tuple:
        print('WARNING', 'getPlayQueue', 'not implemented')
        return "", []

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        print('WARNING', 'savePlayQueue', 'not implemented')
        return False

    def getSimilarSongs(self, id:str, count:int=20) -> list:
        print('WARNING', 'getSimilarSongs', 'not implemented')
        return []

    def getRandomSongs(self, size:int=20) -> list:
        print('WARNING', 'getRandomSongs', 'not implemented')
        return []

    def getLyrics(self, track_name:str, artist_name:str, album_name:str, duration:int) -> dict:
        print('WARNING', 'getLyrics', 'not implemented')
        return {}

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0) -> dict:
        print('WARNING', 'search', 'not implemented')
        return {}

    def getInternetRadioStations(self) -> list:
        print('WARNING', 'getInternetRadioStations', 'not implemented')
        return []

    def createInternetRadioStation(self, name:str, streamUrl:str, homePageUrl:str) -> bool:
        print('WARNING', 'createInternetRadioStation', 'not implemented')
        return False

    def updateInternetRadioStation(self, id:str, name:str, streamUrl:str, homePageUrl:str) -> bool:
        print('WARNING', 'updateInternetRadioStation', 'not implemented')
        return False

    def deleteInternetRadioStation(self, id:str) -> bool:
        print('WARNING', 'deleteInternetRadioStation', 'not implemented')
        return False

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        print('WARNING', 'createPlaylist', 'not implemented')
        return ""

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        print('WARNING', 'updatePlaylist', 'not implemented')
        return False

    def deletePlaylist(self, id:str) -> bool:
        print('WARNING', 'deletePlaylist', 'not implemented')
        return False

    def scrobble(self, id:str):
        print('WARNING', 'scrobble', 'not implemented')
    

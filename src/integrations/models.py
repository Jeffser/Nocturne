# models.py

from gi.repository import GObject, Gdk, GLib

class Album(GObject.Object):
    __gtype_name__ = 'NocturneModelAlbum'

    id = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBytes = GObject.Property(type=GLib.Bytes)
    name = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    artistId = GObject.Property(type=str)
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    song = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    starred = GObject.Property(type=bool, default=False)
    path = GObject.Property(type=str) # For use in Local

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Artist(GObject.Object):
    __gtype_name__ = 'NocturneModelArtist'

    id = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable) #Gdk.Paintable
    gdkPaintableBytes = GObject.Property(type=GLib.Bytes)
    name = GObject.Property(type=str)
    albumCount = GObject.Property(type=int)
    album = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    starred = GObject.Property(type=bool, default=False)
    biography = GObject.Property(type=str)
    similarArtist = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    path = GObject.Property(type=str) # For use in Local

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Playlist(GObject.Object):
    __gtype_name__ = 'NocturneModelPlaylist'

    id = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable) #Gdk.Paintable
    gdkPaintableBytes = GObject.Property(type=GLib.Bytes)
    name = GObject.Property(type=str)
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    readonly = GObject.Property(type=bool, default=False)
    entry = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    path = GObject.Property(type=str) # For use in Local

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Song(GObject.Object):
    __gtype_name__ = 'NocturneModelSong'

    id = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable) #Gdk.Paintable
    gdkPaintableBytes = GObject.Property(type=GLib.Bytes)
    title = GObject.Property(type=str)
    album = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    duration = GObject.Property(type=int)
    albumId = GObject.Property(type=str)
    artistId = GObject.Property(type=str)
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    starred = GObject.Property(type=bool, default=False)
    isExternalFile = GObject.Property(type=bool, default=False)

    # --RADIO--
    isRadio = GObject.Property(type=bool, default=False)
    streamUrl = GObject.Property(type=str)
    # ---------

    path = GObject.Property(type=str) # For use in Local

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class CurrentSong(GObject.Object):
    __gtype_name__ = 'NocturneModelCurrentSong'

    songId = GObject.Property(type=str)
    positionSeconds = GObject.Property(type=float, default=0.0)
    playbackMode = GObject.Property(type=str, default="consecutive") # consecutive, # repeat-one # repeat-all
    buttonState = GObject.Property(type=str, default="play") # play, pause (for use in state stacks)

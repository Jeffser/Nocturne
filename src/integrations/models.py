# models.py

from gi.repository import GObject, Gtk, Gdk, Gio

class Album(GObject.Object):
    __gtype_name__ = 'NocturneModelAlbum'

    id = GObject.Property(type=str, default="")
    coverArt = GObject.Property(type=str, default="")
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    name = GObject.Property(type=str, default="")
    artist = GObject.Property(type=str, default="")
    artistId = GObject.Property(type=str, default="")
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    song = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    starred = GObject.Property(type=bool, default=False)
    userRating = GObject.Property(type=int)
    year = GObject.Property(type=int)

    verified = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                if self.get_property(prop.get_name()) != kwargs.get(prop.get_name()):
                    self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Artist(GObject.Object):
    __gtype_name__ = 'NocturneModelArtist'

    id = GObject.Property(type=str, default="")
    coverArt = GObject.Property(type=str, default="")
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    name = GObject.Property(type=str, default="")
    albumCount = GObject.Property(type=int, default=-1)
    album = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    guestAlbum = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    guestAlbumCount = GObject.Property(type=int, default=-1)
    starred = GObject.Property(type=bool, default=False)
    biography = GObject.Property(type=str, default="")
    similarArtist = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    userRating = GObject.Property(type=int)

    verified = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                if self.get_property(prop.get_name()) != kwargs.get(prop.get_name()):
                    self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Playlist(GObject.Object):
    __gtype_name__ = 'NocturneModelPlaylist'

    id = GObject.Property(type=str, default="")
    coverArt = GObject.Property(type=str, default="")
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    name = GObject.Property(type=str, default="")
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    readonly = GObject.Property(type=bool, default=False)
    entry = GObject.Property(type=GObject.TYPE_PYOBJECT) #list

    verified = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                if self.get_property(prop.get_name()) != kwargs.get(prop.get_name()):
                    self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Song(GObject.Object):
    __gtype_name__ = 'NocturneModelSong'

    id = GObject.Property(type=str, default="")
    coverArt = GObject.Property(type=str, default="")
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    title = GObject.Property(type=str, default="")
    album = GObject.Property(type=str, default="")
    artist = GObject.Property(type=str, default="")
    duration = GObject.Property(type=int)
    albumId = GObject.Property(type=str, default="")
    discNumber = GObject.Property(type=int)
    albumGain = GObject.Property(type=float)
    trackGain = GObject.Property(type=float)
    artistId = GObject.Property(type=str, default="")
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    starred = GObject.Property(type=bool, default=False)
    track = GObject.Property(type=int) #Track N in album
    isExternalFile = GObject.Property(type=bool, default=False)
    userRating = GObject.Property(type=int)
    deleted = GObject.Property(type=bool, default=False)
    radioStreamUrl = GObject.Property(type=str, default="")
    container = GObject.Property(type=str, default="")
    codec = GObject.Property(type=str, default="")

    verified = GObject.Property(type=bool, default=False)

    path = GObject.Property(type=str, default="") # For use in Local

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                if self.get_property(prop.get_name()) != kwargs.get(prop.get_name()):
                    self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class SongDetails(GObject.Object):
    __gtype_name__ = 'NocturneSongDetails'

    id = GObject.Property(type=str, default="")
    title = GObject.Property(type=str, default="")
    album = GObject.Property(type=str, nick=_("Album"))
    albumId = GObject.Property(type=str, default="")
    artist = GObject.Property(type=str, nick=_("Display Artist"))
    artistId = GObject.Property(type=str, default="")
    musicBrainzId = GObject.Property(type=str, nick=_("MusicBrainz ID"))
    track = GObject.Property(type=int, nick=_("Track Number"))
    year = GObject.Property(type=int, nick=_("Year"))
    size = GObject.Property(type=int, nick=_("Size"))
    suffix = GObject.Property(type=str, nick=_("Suffix"))
    starred = GObject.Property(type=bool, default=False, nick=_("Favorite"))
    duration = GObject.Property(type=int, nick=_("Duration"))

    bitRate = GObject.Property(type=int, nick=_("Bit Rate"))
    bitDepth = GObject.Property(type=int, nick=_("Bit Depth"))
    samplingRate = GObject.Property(type=int, nick=_("Sampling Rate"))
    channelCount = GObject.Property(type=int, nick=_("Channel Count"))

    path = GObject.Property(type=str, nick=_("Path"))
    discNumber = GObject.Property(type=int, nick=_("Disc Number"))
    bpm = GObject.Property(type=int, nick=_("BPM"))
    genres = GObject.Property(type=GObject.TYPE_PYOBJECT, nick=_("Genres")) # list
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT, nick=_("Artists")) # list
    trackGain = GObject.Property(type=float, nick=_("Track Gain"))
    albumGain = GObject.Property(type=float, nick=_("Album Gain"))

    verified = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                if self.get_property(prop.get_name()) != kwargs.get(prop.get_name()):
                    self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            elif self.get_property(prop.get_name()) is None:
                if prop.value_type.name == 'PyObject': #LIST
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class SongDownload(GObject.Object):
    __gtype_name__ = 'NocturneSongDownload'

    songId = GObject.Property(type=str, default="")
    progress = GObject.Property(type=float, default=0.0) # 0-1


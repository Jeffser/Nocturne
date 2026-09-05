# models.py

from gi.repository import GObject, Gtk, Gdk, Gio

class Album(GObject.Object):
    __gtype_name__ = 'NocturneModelAlbum'

    id = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    name = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    artistId = GObject.Property(type=str)
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    song = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    starred = GObject.Property(type=bool, default=False)
    userRating = GObject.Property(type=int)
    year = GObject.Property(type=int)

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

    id = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    name = GObject.Property(type=str)
    albumCount = GObject.Property(type=int)
    album = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    starred = GObject.Property(type=bool, default=False)
    biography = GObject.Property(type=str)
    similarArtist = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    userRating = GObject.Property(type=int)

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

    id = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    name = GObject.Property(type=str)
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    readonly = GObject.Property(type=bool, default=False)
    entry = GObject.Property(type=GObject.TYPE_PYOBJECT) #list

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

    id = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    albumArtCheck = GObject.Property(type=bool, default=False)
    gdkPaintable = GObject.Property(type=Gdk.Paintable)
    gdkPaintableBig = GObject.Property(type=Gdk.Paintable)
    title = GObject.Property(type=str)
    album = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    duration = GObject.Property(type=int)
    albumId = GObject.Property(type=str)
    discNumber = GObject.Property(type=int)
    albumGain = GObject.Property(type=float)
    trackGain = GObject.Property(type=float)
    artistId = GObject.Property(type=str)
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    starred = GObject.Property(type=bool, default=False)
    track = GObject.Property(type=int) #Track N in album
    isExternalFile = GObject.Property(type=bool, default=False)
    userRating = GObject.Property(type=int)
    deleted = GObject.Property(type=bool, default=False)
    radioStreamUrl = GObject.Property(type=str)

    path = GObject.Property(type=str) # For use in Local

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

    id = GObject.Property(type=str)
    title = GObject.Property(type=str)
    album = GObject.Property(type=str, nick=_("Album"))
    albumId = GObject.Property(type=str)
    artist = GObject.Property(type=str, nick=_("Display Artist"))
    artistId = GObject.Property(type=str)
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

    songId = GObject.Property(type=str)
    progress = GObject.Property(type=float, default=0.0) # 0-1

class CurrentSong(GObject.Object):
    __gtype_name__ = 'NocturneModelCurrentSong'
    # Not really currentSong, more like currentState at this point

    songId = GObject.Property(type=str)
    videoId = GObject.Property(type=str) # Should check if videoId == songId to see if the current song has video
    positionSeconds = GObject.Property(type=float, default=0.0)
    buttonState = GObject.Property(type=str, default="play") # play, pause (for use in state stacks)
    magnitudes = GObject.Property(type=GObject.TYPE_PYOBJECT) # dict
    seeking = GObject.Property(type=bool, default=False)
    queueOrigin = GObject.Property(type=str, default="") # set to the id of playlist / album where the queue originated from
    queueModel = GObject.Property(type=Gio.ListStore, default=Gio.ListStore.new(item_type=Gtk.StringObject))
    generatedQueue = GObject.Property(type=Gio.ListStore, default=Gio.ListStore.new(item_type=Gtk.StringObject))
    generatingQueue = GObject.Property(type=bool, default=False)
    downloadQueueModel = GObject.Property(type=Gio.ListStore, default=Gio.ListStore.new(item_type=SongDownload))
    displaySongTitle = GObject.Property(type=str)
    displaySongArtist = GObject.Property(type=str)
    accentColor = GObject.Property(type=GObject.TYPE_PYOBJECT) # list [r,g,b] for use in spectrum, set in player

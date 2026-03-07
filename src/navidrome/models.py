# models.py

from gi.repository import GObject

class Album(GObject.Object):
    __gtype_name__ = 'NocturneModelAlbum'

    id = GObject.Property(type=str)
    name = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    artistId = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    playCount = GObject.Property(type=int)
    created = GObject.Property(type=str)
    played = GObject.Property(type=str)
    userRating = GObject.Property(type=int)
    genres = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    musicBrainzId = GObject.Property(type=str)
    isCompilation = GObject.Property(type=bool, default=False)
    sortName = GObject.Property(type=str)
    discTitles = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    releaseTypes = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    recordLabels = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    moods = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    song = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    displayArtist = GObject.Property(type=str)
    explicitStatus = GObject.Property(type=str)
    version = GObject.Property(type=str)
    starred = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        LISTS = ('genres', 'discTitles', 'releaseTypes', 'recordLabels', 'moods', 'artists', 'song')

        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            else:
                if prop.get_name() in LISTS: # is list
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())


class Artist(GObject.Object):
    __gtype_name__ = 'NocturneModelArtist'

    id = GObject.Property(type=str)
    name = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    albumCount = GObject.Property(type=int)
    artistImageUrl = GObject.Property(type=str)
    musicBrainzId = GObject.Property(type=str)
    sortName = GObject.Property(type=str)
    roles = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    album = GObject.Property(type=GObject.TYPE_PYOBJECT) #list
    starred = GObject.Property(type=str)
    biography = GObject.Property(type=str)
    lastFmUrl = GObject.Property(type=str)
    similarArtist = GObject.Property(type=GObject.TYPE_PYOBJECT) #list

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        LISTS = ('roles', 'album', 'similarArtist')

        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            else:
                if prop.get_name() in LISTS: # is list
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Playlist(GObject.Object):
    __gtype_name__ = 'NocturneModelPlaylist'

    id = GObject.Property(type=str)
    name = GObject.Property(type=str)
    songCount = GObject.Property(type=int)
    duration = GObject.Property(type=int)
    owner = GObject.Property(type=str)
    created = GObject.Property(type=str)
    changed = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    readonly = GObject.Property(type=bool, default=False)
    entry = GObject.Property(type=GObject.TYPE_PYOBJECT) #list

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        LISTS = ('entry',)

        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            else:
                if prop.get_name() in LISTS: # is list
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class Song(GObject.Object):
    __gtype_name__ = 'NocturneModelSong'

    id = GObject.Property(type=str)
    parent = GObject.Property(type=str)
    isDir = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str)
    album = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    coverArt = GObject.Property(type=str)
    size = GObject.Property(type=int)
    contentType = GObject.Property(type=str)
    suffix = GObject.Property(type=str)
    duration = GObject.Property(type=int)
    bitRate = GObject.Property(type=int)
    path = GObject.Property(type=str)
    created = GObject.Property(type=str)
    albumId = GObject.Property(type=str)
    artistId = GObject.Property(type=str)
    type = GObject.Property(type=str)
    bpm = GObject.Property(type=int)
    comment = GObject.Property(type=str)
    sortName = GObject.Property(type=str)
    mediaType = GObject.Property(type=str)
    musicBrainzId = GObject.Property(type=str)
    isrc = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    genres = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    channelCount = GObject.Property(type=int)
    samplingRate = GObject.Property(type=int)
    bitDepth = GObject.Property(type=int)
    displayArtist = GObject.Property(type=str)
    displayAlbumArtist = GObject.Property(type=str)
    displayComposer = GObject.Property(type=str)
    explicitStatus = GObject.Property(type=str)
    moods = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    artists = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    albumArtists = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    contributors = GObject.Property(type=GObject.TYPE_PYOBJECT) # list
    starred = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__()
        self.update_data(**kwargs)

    def update_data(self, **kwargs):
        LISTS = ('isrc', 'genres', 'moods', 'artists', 'albumArtists', 'contributors')

        for prop in self.list_properties():
            if prop.get_name() in kwargs:
                self.set_property(prop.get_name(), kwargs.get(prop.get_name()))
            else:
                if prop.get_name() in LISTS: # is list
                    self.set_property(prop.get_name(), [])
                else:
                    self.set_property(prop.get_name(), prop.get_default_value())

class CurrentSong(GObject.Object):
    __gtype_name__ = 'NocturneModelCurrentSong'

    songId = GObject.Property(type=str)
    positionSeconds = GObject.Property(type=float, default=0.0)


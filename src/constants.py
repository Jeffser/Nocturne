# constants.py

import os, subprocess, json, shutil, uuid
from tinytag import TinyTag

CLI_ARGUMENTS = {
    "Play Control": {
        '--player-next': {
            'message': 'skip to the next song',
            'action-name': 'player_next'
        },
        '--player-previous': {
            'message': 'skip to the previous song',
            'action-name': 'player_previous'
        },
        '--player-pause': {
            'message': 'pauses the current song',
            'action-name': 'player_pause'
        },
        '--player-play': {
            'message': 'plays the current song',
            'action-name': 'player_play'
        },
        '--player-toggle': {
            'message': 'toggles between playing and pausing the current song',
            'action-name': 'player_toggle'
        },
        '--player-raise-volume': {
            'message': 'raises volume',
            'action-name': 'player_raise_volume'
        },
        '--player-lower-volume': {
            'message': 'lowers volume',
            'action-name': 'player_lower_volume'
        }
    },
    "Songs": {
        '--song-show': {
            'message': 'show details of the specified song',
            'action-name': 'show_song_details',
            'metavar': 'SONG_ID'
        },
        '--song-play': {
            'message': 'play the specified song',
            'action-name': 'play_song',
            'metavar': 'SONG_ID'
        },
        '--play-song-later': {
            'message': 'play the specified song later',
            'action-name': 'play_song_later',
            'metavar': 'SONG_ID'
        },
        '--play-song-next': {
            'message': 'play the specified song next',
            'action-name': 'play_song_next',
            'metavar': 'SONG_ID'
        }
    },
    "Albums": {
        '--album-show': {
            'message': 'show the specified album',
            'action-name': 'show_album',
            'metavar': 'ALBUM_ID'
        },
        '--album-show-from-song': {
            'message': 'show the album of the specified song',
            'action-name': 'show_album_from_song',
            'metavar': 'SONG_ID'
        },
        '--album-play': {
            'message': 'play the specified album',
            'action-name': 'play_album',
            'metavar': 'ALBUM_ID'
        },
        '--album-play-later': {
            'message': 'play the specified album later',
            'action-name': 'play_album_later',
            'metavar': 'ALBUM_ID'
        },
        '--album-play-next': {
            'message': 'play the specified album next',
            'action-name': 'play_album_next',
            'metavar': 'ALBUM_ID'
        },
        '--album-play-shuffle': {
            'message': 'shuffle and play the specified album',
            'action-name': 'play_album_shuffle',
            'metavar': 'ALBUM_ID'
        },
    },
    "Artists": {
        '--artist-show': {
            'message': 'show the specified artist',
            'action-name': 'show_artist',
            'metavar': 'ARTIST_ID'
        },
        '--artist-show-from-album': {
            'message': 'show the artist of the specified album',
            'action-name': 'show_artist_from_album',
            'metavar': 'ALBUM_ID'
        },
        '--artist-show-from-song': {
            'message': 'show the artist of the specified song',
            'action-name': 'show_artist_from_song',
            'metavar': 'SONG_ID'
        },
        '--artist-play-shuffle': {
            'message': 'shuffle and play music from the specified artist',
            'action-name': 'play_shuffle_artist',
            'metavar': 'ARTIST_ID'
        },
        '--artist-play-radio': {
            'message': 'start a radio based on music from the specified artist',
            'action-name': 'play_radio_artist',
            'metavar': 'ARTIST_ID'
        },
    },
    "Playlists": {
        '--playlist-show': {
            'message': 'show the specified playlist',
            'action-name': 'show_playlist',
            'metavar': 'PLAYLIST_ID'
        },
        '--playlist-play': {
            'message': 'play the specified playlist',
            'action-name': 'play_playlist',
            'metavar': 'PLAYLIST_ID'
        },
        '--playlist-play-later': {
            'message': 'play the specified playlist later',
            'action-name': 'play_playlist_later',
            'metavar': 'PLAYLIST_ID'
        },
        '--playlist-play-next': {
            'message': 'play the specified playlist next',
            'action-name': 'play_playlist_next',
            'metavar': 'PLAYLIST_ID'
        },
        '--playlist-play-shuffle': {
            'message': 'shuffle and play the specified playlist',
            'action-name': 'play_playlist_shuffle',
            'metavar': 'PLAYLIST_ID'
        }
    },
    "Miscellaneous": {
        '--toggle-fullscreen': {
            'message': 'toggle the fullscreen mode',
            'action-name': 'toggle_fullscreen'
        },
        '--logout': {
            'message': 'logout from the current instance',
            'action-name': 'logout'
        },
        '--search': {
            'message': 'get top results based on query (JSON)',
            'action-name': 'search',
            'metavar': 'QUERY'
        }
    }
}

DISCORD_APP_ID = "1504946005764739092"

IN_FLATPAK = bool(os.getenv("FLATPAK_ID"))

COPYRIGHT_NOTICE = """Nocturne © 2026 Jeffry Samuel, Jeffser

Nocturne is an independent application and is not affiliated with, endorsed, or sponsored by OpenSubsonic, Bandcamp, or Jellyfin. All logos and illustrative assets used within the app are the property of their respective owners. All rights are reserved by their respective holders, and will be taken down if requested.

Nocturne functions strictly as a client application. All network connections and data transfers are performed exclusively at the request and authorization of the server owner. Nocturne does not independently access or host any content.

Nocturne does not facilitate, encourage, or provide mechanisms for music piracy. Users are responsible for ensuring they have the legal right to access and stream the content hosted on the servers they connect to."""

def get_xdg_home(env: str, default: str) -> str:
    base = os.getenv(env) or os.path.expanduser(default)
    if IN_FLATPAK:
        return base
    path = os.path.join(base, "com.jeffser.Nocturne")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

COMPATIBLE_EXTENSIONS = {
    'audio': ['.mp3', '.flac', '.m4a', '.oga', '.ogg', '.opus', '.wav'],
    'video': ['.mp4', '.mov', '.m4v', '.avi', '.webm', '.mkv']
}
DATA_DIR = get_xdg_home("XDG_DATA_HOME", "~/.local/share")
CONFIG_DIR = get_xdg_home("XDG_CONFIG_HOME", "~/.config")
CACHE_DIR = get_xdg_home("XDG_CACHE_HOME", "~/.cache")

INTEGRATIONS_DIR = os.path.join(DATA_DIR, "integrations")
os.makedirs(INTEGRATIONS_DIR, exist_ok=True)
# DEPRECATED DONT USE THESE VARIABLES
OLD_JELLYFIN_DATA_DIR = os.path.join(DATA_DIR, "jellyfin")
if os.path.isdir(OLD_JELLYFIN_DATA_DIR) and not os.path.isdir(os.path.join(INTEGRATIONS_DIR, 'NocturneIntegrationJellyfin')):
    os.rename(OLD_JELLYFIN_DATA_DIR, os.path.join(INTEGRATIONS_DIR, 'NocturneIntegrationJellyfin'))

OLD_LOCAL_DATA_DIR = os.path.join(DATA_DIR, "local")
if os.path.isdir(OLD_LOCAL_DATA_DIR) and not os.path.isdir(os.path.join(INTEGRATIONS_DIR, 'NocturneIntegrationLocal')):
    os.rename(OLD_LOCAL_DATA_DIR, os.path.join(INTEGRATIONS_DIR, 'NocturneIntegrationLocal'))
# ----------

DOWNLOAD_QUEUE_DIR = os.path.join(DATA_DIR, 'downloading')
if os.path.isdir(DOWNLOAD_QUEUE_DIR):
    shutil.rmtree(DOWNLOAD_QUEUE_DIR)
os.makedirs(DOWNLOAD_QUEUE_DIR, exist_ok=True)
DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
DOWNLOAD_MIME_MAP = {
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a"
}

# Fallback only used if the system does not have a keyring
FALLBACK_PASSWORD_PATH = os.path.join(CONFIG_DIR, 'pass.txt')

# Retrieves device ID or generates a UUID if device ID not found
# Used for Jellyfin session tracking
def get_device_id():
    device_id = None
    if IN_FLATPAK:
        try:
            from pydbus import SessionBus
            bus = SessionBus()
            flatpak_portal = bus.get("org.freedesktop.portal.Flatpak", "/org/freedesktop/portal/Flatpak")
            device_id = flatpak_portal.GetMachineId().strip()
        except Exception as e:
            pass
    else:
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    device_id = f.read().strip()
    if not device_id: #generate UUID as fallback
        fallback_path = os.path.join(CONFIG_DIR, "device_id")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r") as f:
                device_id = f.read().strip()
        else:
            device_id = str(uuid.uuid4())
            with open(fallback_path, "w") as f:
                f.write(device_id)
    return device_id

BASE_NAVIDROME_DIR = os.path.join(DATA_DIR, "navidrome")
os.makedirs(BASE_NAVIDROME_DIR, exist_ok=True)
NAVIDROME_ENV = {
    "ND_DATAFOLDER": BASE_NAVIDROME_DIR,
    "ND_PORT": "4534",
    "ND_LOGLEVEL": "ERROR",
    "ND_ENABLEINSIGHTSCOLLECTOR": "false"
}

def get_navidrome_path() -> str | None:
    NAVIDROME_PATH = os.path.join(BASE_NAVIDROME_DIR, 'navidrome')
    if os.path.isfile(NAVIDROME_PATH):
        return NAVIDROME_PATH

def get_navidrome_env() -> dict:
    return {
        **os.environ.copy(),
        **NAVIDROME_ENV
    }

def check_if_navidrome_ready() -> bool:
    # checks if admin has already been created
    navidrome_path = get_navidrome_path()
    if navidrome_path:
        try:
            output = subprocess.check_output([navidrome_path, "user", "list", "-f", "json", "-n", "--loglevel", "error"], stderr=subprocess.STDOUT, env=get_navidrome_env()).strip()
            output_json = json.loads(output)
            return len(output_json) > 0
        except Exception as e:
            pass
    return False

NOCTURNE_VERSION = ""
def get_nocturne_version() -> str:
    global NOCTURNE_VERSION
    return NOCTURNE_VERSION
def set_version(version_str:str):
    global NOCTURNE_VERSION
    NOCTURNE_VERSION = version_str

def get_display_time(seconds:float, show_ms:bool=False) -> str:
    if not show_ms:
        total_seconds = round(max(0, seconds))
    else:
        total_seconds = max(0, seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if show_ms:
        seconds_str = f"{seconds:05.2f}"
    else:
        seconds_str = f"{int(seconds):02d}"

    if hours > 0:
        # Format H:MM:SS.ms
        return f"{int(hours)}:{int(minutes):02d}:{seconds_str}"
    else:
        # Format MM:SS.ms
        return f"{int(minutes):02d}:{seconds_str}"

def _normalize_artists(values:list[str]) -> list[str]:
    artists = []
    for value in values:
        for artist_name in value.split(';'):
            artist_name = artist_name.strip()
            if artist_name and artist_name not in artists:
                artists.append(artist_name)
    return artists

def get_song_info_from_file(file_path:str, star_list:list=[], is_external_file:bool=False) -> dict | None:
    tag = TinyTag.get(file_path)
    if not tag:
        return None

    artists = _normalize_artists(tag.as_dict().get('artist', []))
    album_artists = _normalize_artists([tag.albumartist or ""])
    album_artist = album_artists[0] if album_artists else (artists[0] if artists else "")

    song = {
        'path': file_path,
        'coverArt': file_path,
        'duration': tag.duration or 0,
        'title': tag.title or os.path.basename(file_path),
        'album': tag.album or "",
        'artist': album_artist,
        'artists': [{
            'id': "ARTIST:{}".format(artist_name),
            'name': artist_name,
            'starred': "ARTIST:{}".format(artist_name) in star_list
        } for artist_name in artists],
        'track': tag.track or 0,
        'isExternalFile': is_external_file,
        'discNumber': tag.disc or 0,
        'year':tag.year or 0,
        'albumGain': tag.extra.get('replaygain_album_gain') or tag.extra.get('REPLAYGAIN_ALBUM_GAIN') or 1,
        'trackGain': tag.extra.get('replaygain_track_gain') or tag.extra.get('REPLAYGAIN_TRACK_GAIN') or 1
    }

    if not is_external_file:
        song["artistId"] = "ARTIST:{}".format(album_artist) if album_artist else ""
        song["albumId"] = "ALBUM:{}".format(song.get("album")) if song.get('album') else ""

    return song

TRANSLATORS = [
    "Jeffry Samuel (Spanish) https://jeffser.com",
    "Jordi Bultó (Catalan) https://github.com/formajestically",
    "Ibai Oihanguren Sala (Basque) https://ibaios.eus",
    "Martin Prokoph (German) https://github.com/Motschen",
    "Aleksandr Shamaraev (Russian) https://github.com/AlexanderShad",
    "gttn-84 (Russian) https://github.com/gttn-84",
    "Saul Gman (Simplified Chinese) https://github.com/Ja4e",
    "Muhammed Emin Akalan (Turkish) https://github.com/muhammedeminakalan",
    "Yuan Chiu (Traditional Chinese) https://yuaner.tw",
    "Milo Ivir (Croatian) https://github.com/milotype",
    "Aryan Karamtoth (Telugu) https://github.com/spaciouskarter78",
    "Rikelry Souza (Brazilian Portuguese) https://github.com/Rikelry"
]

PLAYBACK_MODES = {
    'consecutive': {
        'icon-name': 'media-playlist-consecutive-symbolic',
        'display-name': _("Consecutive")
    },
    'repeat-all': {
        'icon-name': 'media-playlist-repeat-symbolic',
        'display-name': _("Repeat All")
    },
    'repeat-one': {
        'icon-name': 'media-playlist-repeat-song-symbolic',
        'display-name': _("Repeat One")
    }
}

BITRATE_OPTIONS = {
    _("Low ({})"): 64,
    _("Medium ({})"): 128,
    _("High ({})"): 192,
    _("Ultra ({})"): 320,
    _("Original File"): 0
}

SIDEBAR_MENU = [
    { # Section
        'items': [
            { # Item
                'title': _("Home"),
                'icon-name': "user-home-symbolic",
                'page-tag': 'home'
            },
            { # Item
                'title': _("Artists"),
                'icon-name': "music-artist-symbolic",
                'page-tag': 'artists'
            }
        ]
    },
    { # Section
        'title': _("Albums"),
        'items': [
            { # Item
                'title': _("All"),
                'icon-name': "music-queue-symbolic",
                'page-tag': 'albums-all'
            },
            { # Item
                'title': _("Random"),
                'icon-name': "playlist-shuffle-symbolic",
                'page-tag': 'albums-random'
            },
            { # Item
                'title': _("Favorites"),
                'icon-name': "heart-filled-symbolic",
                'page-tag': 'albums-starred'
            },
            { # Item
                'title': _("Recently Added"),
                'icon-name': "list-add-symbolic",
                'page-tag': 'albums-newest'
            },
            { # Item
                'title': _("Recently Played"),
                'icon-name': "media-playback-start-symbolic",
                'page-tag': 'albums-recent'
            },
            { # Item
                'title': _("Most Played"),
                'icon-name': "media-playlist-repeat-symbolic",
                'page-tag': 'albums-frequent'
            }
        ]
    },
    { # Section
        'title': _("Songs"),
        'items': [
            { # Item
                'title': _("All"),
                'icon-name': "music-note-symbolic",
                'page-tag': 'songs-all'
            },
            { # Item
                'title': _("Favorites"),
                'icon-name': "heart-filled-symbolic",
                'page-tag': 'songs-starred'
            },
            { # Item
                'title': _("Radios"),
                'icon-name': "sound-wave-symbolic",
                'page-tag': 'radios'
            }
        ]
    },
    { # Section
        'title': _("Playlists"),
        'items': [
            { # Item
                'title': _("All"),
                'icon-name': "playlist-symbolic",
                'page-tag': "playlists"
            }
        ]
    }
]

CONTEXT_ALBUM = {
    "play": {
        "name": _("Play"),
        "icon-name": "media-playback-start-symbolic",
        "action-name": "app.play_album"
    },
    "shuffle": {
        "name": _("Shuffle"),
        "icon-name": "playlist-shuffle-symbolic",
        "action-name": "app.play_album_shuffle"
    },
    "play-next": {
        "name": _("Play Next"),
        "icon-name": "list-high-priority-symbolic",
        "action-name": "app.play_album_next"
    },
    "play-later": {
        "name": _("Play Later"),
        "icon-name": "list-low-priority-symbolic",
        "action-name": "app.play_album_later"
    },
    "add-to-playlist": {
        "name": _("Add To Playlist"),
        "icon-name": "playlist-symbolic",
        "action-name": "app.prompt_add_album_to_playlist"
    },
    "download": {
        "name": _("Download"),
        "icon-name": "folder-download-symbolic",
        "action-name": "app.download_album"
    },
    "show-artist": {
        "name": _("Show Artist"),
        "icon-name": "music-artist-symbolic",
        "action-name": "app.show_artist_from_album"
    }
}

CONTEXT_ARTIST = {
    "shuffle": {
        "name": _("Shuffle"),
        "icon-name": "playlist-shuffle-symbolic",
        "action-name": "app.play_shuffle_artist"
    },
    "radio": {
        "name": _("Radio"),
        "icon-name": "sound-symbolic",
        "action-name": "app.play_radio_artist"
    }
}

CONTEXT_PLAYLIST = {
    "play": {
        "name": _("Play"),
        "icon-name": "media-playback-start-symbolic",
        "action-name": "app.play_playlist"
    },
    "resume": {
        "name": _("Resume"),
        "icon-name": "playback-options-symbolic",
        "action-name": "app.resume_playlist"
    },
    "shuffle": {
        "name": _("Shuffle"),
        "icon-name": "media-playlist-shuffle-symbolic",
        "action-name": "app.play_playlist_shuffle"
    },
    "play-next": {
        "name": _("Play Next"),
        "icon-name": "list-high-priority-symbolic",
        "action-name": "app.play_playlist_next"
    },
    "play-later": {
        "name": _("Play Later"),
        "icon-name": "list-low-priority-symbolic",
        "action-name": "app.play_playlist_later"
    },
    "download": {
        "name": _("Download"),
        "icon-name": "folder-download-symbolic",
        "action-name": "app.download_playlist"
    },
    "edit": {
        "name": _("Edit"),
        "icon-name": "document-edit-symbolic",
        "action-name": "app.update_playlist"
    },
    "delete": {
        "name": _("Delete"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic",
        "action-name": "app.delete_playlist"
    }
}

CONTEXT_SONG = {
    "select": {
        "name": _("Select"),
        "icon-name": "object-select-symbolic"
    },
    "play-next": {
        "name": _("Play Next"),
        "icon-name": "list-high-priority-symbolic",
        "action-name": "app.play_song_next"
    },
    "play-later": {
        "name": _("Play Later"),
        "icon-name": "list-low-priority-symbolic",
        "action-name": "app.play_song_later"
    },
    "edit-radio": {
        "name": _("Edit"),
        "icon-name": "document-edit-symbolic",
        "action-name": "app.update_radio"
    },
    "add-to-playlist": {
        "name": _("Add To Playlist"),
        "icon-name": "playlist-symbolic",
        "action-name": "app.prompt_add_song_to_playlist"
    },
    "download": {
        "name": _("Download"),
        "icon-name": "folder-download-symbolic",
        "action-name": "app.download_song"
    },
    "show-album": {
        "name": _("Show Album"),
        "icon-name": "music-queue-symbolic",
        "action-name": "app.show_album_from_song"
    },
    "show-artist": {
        "name": _("Show Artist"),
        "icon-name": "music-artist-symbolic",
        "action-name": "app.show_artist_from_song"
    },
    "delete-radio": {
        "name": _("Delete"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic",
        "action-name": "app.delete_radio"
    },
    "remove": {
        "name": _("Remove"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic"
    },
    "delete-download": {
        "name": _("Delete Download"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic",
        "action-name": "app.delete_download"
    },
    "details": {
        "name": _("Show Details"),
        "icon-name": "info-outline-symbolic",
        "action-name": "app.show_song_details"
    },
    "rating": {
        "special": "song-rating"
    }
}

CONTEXT_MANAGED_NAVIDROME_SERVER = {
    "visit": {
        "name": _("Visit Webpage"),
        "icon-name": "globe-symbolic",
        "action-name": "app.visit_url",
        "action-target": "http://127.0.0.1:4534"
    },
    "update": {
        "name": _("Update Server"),
        "icon-name": "update-symbolic",
        "action-name": "app.update_navidrome_server"
    },
    "delete": {
        "name": _("Delete Server"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic",
        "action-name": "app.delete_navidrome_server"
    }
}

CONTEXT_LYRICS = {
    "edit": {
        "name": _("Edit Lyrics"),
        "icon-name": "document-edit-symbolic",
        "action-name": "app.edit_lyrics"
    },
    "remove": {
        "name": _("Remove Lyrics"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic",
    }
}

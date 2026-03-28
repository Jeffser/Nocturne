# constants.py

import os, subprocess, json
from mutagen import File

IN_FLATPAK = bool(os.getenv("FLATPAK_ID"))
IN_SNAP = bool(os.getenv("FLATPAK_ID"))

def get_xdg_home(env, default):
    if IN_FLATPAK:
        return os.getenv(env)
    base = os.getenv(env) or os.path.expanduser(default)
    path = os.path.join(base, "com.jeffser.Nocturne")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

DATA_DIR = get_xdg_home("XDG_DATA_HOME", "~/.local/share")
CONFIG_DIR = get_xdg_home("XDG_CONFIG_HOME", "~/.config")
CACHE_DIR = get_xdg_home("XDG_CACHE_HOME", "~/.cache")
DEFAULT_MUSIC_DIR = subprocess.check_output(["xdg-user-dir", "MUSIC"], text=True).strip() or os.path.expanduser("~/Music")
JELLYFIN_DATA_DIR = os.path.join(DATA_DIR, "jellyfin")
os.makedirs(JELLYFIN_DATA_DIR, exist_ok=True)
LOCAL_DATA_DIR = os.path.join(DATA_DIR, "local")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
MPRIS_COVER_PATH = os.path.join(CACHE_DIR, 'cover.png')

# Fallback only used if the system does not have a keyring
FALLBACK_PASSWORD_PATH = os.path.join(CONFIG_DIR, 'pass.txt')

BASE_NAVIDROME_DIR = os.path.join(DATA_DIR, "navidrome")
os.makedirs(BASE_NAVIDROME_DIR, exist_ok=True)
NAVIDROME_ENV = {
    "ND_MUSICFOLDER": DEFAULT_MUSIC_DIR,
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

def get_display_time(seconds:float, show_ms:bool=False) -> str:
    total_seconds = max(0, seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if show_ms:
        seconds_str = f"{seconds:05.2f}"
    else:
        seconds_str = f"{seconds:02.0f}"

    if hours > 0:
        # Format H:MM:SS.ms
        return f"{hours:01.0f}:{minutes:02.0f}:{seconds_str}"
    else:
        # Format MM:SS.ms
        return f"{minutes:02.0f}:{seconds_str}"

def get_song_info_from_file(file_path:str, star_dict:dict={}, is_external_file:bool=False) -> dict | None:
    audio = File(file_path)
    if audio is None:
        return None

    song = {
        'id': "SONG:{}-{}".format(file_path.name.removesuffix(file_path.suffix), audio.info.length if hasattr(audio, 'info') else 0),
        'path': file_path,
        'duration': audio.info.length if hasattr(audio, 'info') else 0,
        'title': "",
        'album': "",
        'artist': "",
        'artists': [],
        'isExternalFile': is_external_file
    }

    if file_path.suffix.lower() == '.mp3':
        # ID3 Mapping
        song['title'] = audio.get('TIT2', file_path.name.removesuffix(file_path.suffix))
        song['album'] = str(audio.get('TALB') or '')
        artists = [artist.strip() for artist in str(audio.get('TPE1') or '').split(';')]
        if len(artists) > 0:
            song['artist'] = artists[0]
            for artist in artists:
                artist_id = "ARTIST:{}".format(artist)
                song['artists'].append({
                    'id': artist_id,
                    'name': artist,
                    'starred': star_dict.get(artist_id)
                })
    else:
        # Vorbis/FLAC/MP4 Mapping
        if 'title' in audio:
            song["title"] = audio.get('title', [file_path.name.removesuffix(file_path.suffix)])[0]
        else:
            song["title"] = audio.get('©nam', [file_path.name.removesuffix(file_path.suffix)])[0]

        if 'album' in audio:
            song["album"] = audio.get('album', [""])[0]
        else:
            song["album"] = audio.get('©alb', [""])[0]


        if 'artist' in audio:
            artist_list = audio.get('artist', [])
        else:
            artist_list = audio.get('©ART', [])

        artists = [artist.strip() for artist in artist_list[1:] + (artist_list[0].split(';') if len(artist_list) > 0 else [])]
        if len(artists) > 0:
            song['artist'] = artists[0]
            for artist in artists:
                artist_id = "ARTIST:{}".format(artist)
                song['artists'].append({
                    'id': artist_id,
                    'name': artist,
                    'starred': star_dict.get(artist_id)
                })

    if not is_external_file:
        song["artistId"] = "ARTIST:{}".format(song.get("artist")) if song.get('artist') else ""
        song["albumId"] = "ALBUM:{}".format(song.get("album")) if song.get('album') else ""

    song["starred"] = star_dict.get(song.get('id'))

    return song

TRANSLATORS = [
    "Jeffry Samuel (Spanish) https://jeffser.com"
]

SIDEBAR_MENU = [
    { # Section
        'items': [
            { # Item
                'title': _("Home"),
                'icon-name': "user-home-symbolic",
                'page-tag': 'home'
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
                'page-tag': 'albums',
                'page-type': 'random'
            },
            { # Item
                'title': _("Starred"),
                'icon-name': "starred-symbolic",
                'page-tag': 'albums',
                'page-type': 'starred'
            },
            { # Item
                'title': _("Recently Added"),
                'icon-name': "list-add-symbolic",
                'page-tag': 'albums',
                'page-type': 'newest'
            },
            { # Item
                'title': _("Recently Played"),
                'icon-name': "media-playback-start-symbolic",
                'page-tag': 'albums',
                'page-type': 'recent'
            },
            { # Item
                'title': _("Most Played"),
                'icon-name': "media-playlist-repeat-symbolic",
                'page-tag': 'albums',
                'page-type': 'frequent'
            }
        ]
    },
    {
        'items': [
            { # Item
                'title': _("Artists"),
                'icon-name': "music-artist-symbolic",
                'page-tag': 'artists'
            },
            { # Item
                'title': _("Songs"),
                'icon-name': "music-note-symbolic",
                'page-tag': 'songs'
            },
            { # Item
                'title': _("Radios"),
                'icon-name': "sound-wave-symbolic",
                'page-tag': 'radios'
            },
            { # Item
                'title': _("Playlists"),
                'icon-name': "playlist-symbolic",
                'page-tag': 'playlists'
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
    "edit": {
        "name": _("Edit"),
        "icon-name": "document-edit-symbolic",
        "action-name": "app.update_radio"
    },
    "edit-lyrics": {
        "name": _("Edit Lyrics"),
        "icon-name": "text-justify-center-symbolic",
        "action-name": "app.edit_lyrics"
    },
    "delete": {
        "name": _("Delete"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic",
        "action-name": "app.delete_radio"
    },
    "add-to-playlist": {
        "name": _("Add To Playlist"),
        "icon-name": "playlist-symbolic",
        "action-name": "app.prompt_add_song_to_playlist"
    },
    "remove": {
        "name": _("Remove"),
        "css": ["error"],
        "icon-name": "user-trash-symbolic"
    }
}

CONTEXT_SERVER = {
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

# constants.py

import os, subprocess, json

IN_FLATPAK = bool(os.getenv("FLATPAK_ID"))
IN_SNAP = bool(os.getenv("FLATPAK_ID"))

def get_xdg_home(env, default):
    if IN_FLATPAK:
        return os.getenv(env)
    base = os.getenv(env) or os.path.expanduser(default)
    path = os.path.join(base, "com.jeffser.Alpaca")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

DATA_DIR = get_xdg_home("XDG_DATA_HOME", "~/.local/share")
CONFIG_DIR = get_xdg_home("XDG_CONFIG_HOME", "~/.config")
CACHE_DIR = get_xdg_home("XDG_CACHE_HOME", "~/.cache")

BASE_NAVIDROME_DIR = os.path.join(DATA_DIR, "navidrome")
os.makedirs(BASE_NAVIDROME_DIR, exist_ok=True)
NAVIDROME_ENV = {
    "ND_MUSICFOLDER": subprocess.check_output(["xdg-user-dir", "MUSIC"], text=True).strip() or os.path.expanduser("~/Music"),
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

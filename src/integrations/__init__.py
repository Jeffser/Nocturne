# __init__.py

from .navidrome import Navidrome
from .local import Local
from . import models, secret
from ..constants import DATA_DIR
import os, requests

integration = None

def ping_without_login(url:str) -> bool:
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('subsonic-response') is not None
    return False

def get_current_integration():
    global integration
    return integration

def set_current_integration(new_integration):
    global integration
    integration = new_integration


def prepare_lrc(lrc_str:str) -> list:
        lrc_lines = []
        for line in lrc_str.split('\n'):
            if line.startswith('['):
                timestamp, content = line[1:].split(']')[:2]
                minutes_str, rest = timestamp.split(':')
                seconds_str, ms_str = rest.split('.')
                minutes = int(minutes_str)
                seconds = int(seconds_str)
                ms = int(ms_str)
                if len(ms_str) == 2:
                    ms *= 10
                timing = (minutes * 60000) + (seconds * 1000) + ms
                lrc_lines.append({'ms': timing, 'content': content.strip()})
        return lrc_lines

def get_lyrics(song_id:str, download:bool) -> dict:
    # returns these keys:
    # type (instrumental, lrc, plain, not-found, not-found-locally, radio)
    # content (none (instrumental/not-found/not-found-locally/radio), list (lrc), str (plain))

    integration = get_current_integration()
    model = integration.loaded_models.get(song_id)

    if not model:
        return {'type': 'not-found', 'content': None}

    if model.get_property('isRadio'):
        return {'type': 'radio', 'content': None}

    lyrics_dir = os.path.join(DATA_DIR, 'lyrics')
    os.makedirs(lyrics_dir, exist_ok=True)

    file_name_without_ext = '{}|{}|{}|{}'.format(
        model.get_property('title'),
        model.get_property('artist'),
        model.get_property('album') or model.get_property('title'),
        model.get_property('duration')
    )
    lrc_path = os.path.join(lyrics_dir, file_name_without_ext+'.lrc')
    plain_lyrics_path = os.path.join(lyrics_dir, file_name_without_ext+'.txt')

    if os.path.isfile(lrc_path):
        with open(lrc_path, 'r') as f:
            return {'type': 'lrc', 'content': prepare_lrc(f.read())}

    if os.path.isfile(plain_lyrics_path):
        with open(plain_lyrics_path, 'r') as f:
            content = f.read()
            if content == '[instrumental]':
                return {'type': 'instrumental', 'content': None}
            else:
                return {'type': 'plain', 'content': content}

    if not download:
        return {'type': 'not-found-locally', 'content': None}

    lyrics = integration.getLyrics(
        track_name=model.get_property('title'),
        artist_name=model.get_property('artist'),
        album_name=model.get_property('album') or model.get_property('title'),
        duration=model.get_property('duration')
    )

    if lyrics.get('statusCode') == '404':
        return {'type': 'not-found', 'content': None}

    if lyrics.get('instrumental'):
        with open(plain_lyrics_path, 'w+') as f:
            f.write('[instrumental]')
        return {'type': 'instrumental', 'content': None}

    if lyrics.get('syncedLyrics'):
        with open(lrc_path, 'w+') as f:
            f.write(lyrics.get('syncedLyrics'))
        return {'type': 'lrc', 'content': prepare_lrc(lyrics.get('syncedLyrics'))}

    if lyrics.get('plainLyrics'):
        with open(plain_lyrics_path, 'w+') as f:
            f.write(lyrics.get('plainLyrics'))
        return {'type': 'plain', 'content': lyrics.get('plainLyrics')}

    return {'type': 'not-found', 'content': None}

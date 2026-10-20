# discord_rpc.py

import json, os, socket, struct, threading, time, uuid, requests, ipaddress
from urllib.parse import urlparse
from gi.repository import GLib, Gst, Gio

from ..constants import DISCORD_APP_ID


class DiscordRPC:
    MAX_FIELD_LENGTH = 127

    def __init__(self, player):
        self.player = player
        self.socket = None
        self.state_lock = threading.Lock()
        self.socket_lock = threading.Lock()
        self.pending = None
        self.worker_running = False
        self.generation = 0
        self.update_source_id = None

    def close(self):
        with self.state_lock:
            self.generation += 1
            self.pending = None
            if self.update_source_id:
                GLib.source_remove(self.update_source_id)
                self.update_source_id = None
        with self.socket_lock:
            self._clear()
            if self.socket:
                try:
                    self.socket.close()
                except OSError:
                    pass
                self.socket = None

    def update(self):
        if not self.player.settings.get_value("discord-rpc-enabled").unpack():
            self.close()
            return

        with self.state_lock:
            if self.update_source_id:
                GLib.source_remove(self.update_source_id)
            self.update_source_id = GLib.timeout_add(500, self._queue_update)

    def _queue_update(self):
        activity = self._get_activity()
        with self.state_lock:
            self.update_source_id = None
            self.generation += 1
            self.pending = (self.generation, activity)
            if self.worker_running:
                return GLib.SOURCE_REMOVE
            self.worker_running = True
        threading.Thread(target=self._run, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def _run(self):
        while True:
            with self.state_lock:
                if not self.pending:
                    self.worker_running = False
                    return
                generation, activity = self.pending
                success, state, pending = self.player.gst.get_state(0)
                if state == Gst.State.PLAYING:
                    if song_id := self.player.get_property("songId"):
                        activity["assets"]["large_image"] = self._get_cover_art(song_id) or "logo"
                self.pending = None

            with self.socket_lock:
                with self.state_lock:
                    if generation != self.generation:
                        continue
                if not self.socket and not self._connect():
                    continue
                with self.state_lock:
                    if self.pending or generation != self.generation:
                        continue
                if not self._set_activity(activity):
                    self._disconnect()

    def _set_activity(self, activity):
        return self._send(1, {
            "cmd": "SET_ACTIVITY",
            "args": {
                "pid": os.getpid(),
                "activity": activity
            },
            "nonce": uuid.uuid4().hex
        })

    def _get_cover_art(self, song_id) -> str:
        # Returns public URL for cover art or empty string
        if not song_id or not integration:
            return ""

        if Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('discord-instance-art-share').unpack():
            # Check if getCoverArtUrl provides a public endpoint
            if url_str := integration.getCoverArtUrl(song_id):
                parsed_url = urlparse(url_str)
                scheme = parsed_url.scheme.lower()
                if scheme in ('http', 'https'):
                    hostname = parsed_url.hostname
                    is_domain = False
                    try:
                        ipaddress.ip_address(hostname)
                    except ValueError:
                        is_domain = True
                    if is_domain:
                        return url_str

        mbid = ""

        if song_details := integration.getSongDetails(song_id):
            mbid = song_details.get_property('musicBrainzId')

        if not mbid:
            if song_model := integration.loaded_models.get(song_id):
                # Get MusicBrainz ID
                headers = {
                    "User-Agent": "Nocturne/1.0 ( https://jeffser.com/nocturne )"
                }
                search_url = "https://musicbrainz.org/ws/2/release"
                artist_name = song_model.get_property("artist")
                if artists := song_model.get_property("artists"):
                    if len(artists) > 0:
                        artist_name = artists[0].get('name') or artist_name
                params = {
                    "query": f'release:"{song_model.get_property("album")}" AND artist:"{artist_name}"',
                    "fmt": "json"
                }
                try:
                    response = requests.get(search_url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    if not data.get("releases"):
                        return ""
                    mbid = data.get("releases")[0].get("id")
                except requests.exceptions.RequestException as e:
                    return ""

        if mbid:
            caa_url = f"https://coverartarchive.org/release/{mbid}/front-500"
            image_response = requests.get(caa_url, headers=headers, allow_redirects=True)
            if image_response.status_code == 200:
                return image_response.url or ""
        return ""

    def _get_activity(self):
        song = self.player.get_property("currentSong")
        if not song:
            return None

        success, state, pending = self.player.gst.get_state(0)
        if self.player.get_property("buttonState") == "play" and pending != Gst.State.PLAYING:
            return {
                "details": _("Browsing"),
                "type": 0,
                "assets": {
                    "large_image": "logo",
                    "large_text": "Nocturne"
                }
            }

        if song and song.get_property("radioStreamUrl"):
            title = self.player.get_property("displaySongTitle") or song.get_property("title")
            artist = self.player.get_property("displaySongArtist") or song.get_property("artist")
        else:
            title = song.get_property("title") if song else self.player.get_property("displaySongTitle")
            if song and song.get_property("artists"):
                artist = ", ".join([a.get("name") for a in song.get_property("artists")])
            else:
                artist = song.get_property("artist") if song else self.player.get_property("displaySongArtist")
        activity = {
            "details": self._truncate(title or _("Listening to music")),
            "state": self._truncate(artist) if artist else None,
            "type": 2,
            "assets": {
                "large_text": self._truncate(song.get_property("album") if song else "Nocturne")
            }
        }
        activity["assets"]["large_image"] = "logo"

        if song and song.get_property("duration") > 0:
            position = max(self.player.get_property("positionSeconds"), 0)
            started_at = int(time.time() - position)
            activity["timestamps"] = {
                "start": started_at,
                "end": started_at + song.get_property("duration")
            }

        return activity

    def _connect(self):
        for path in self._get_socket_paths():
            try:
                rpc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                rpc_socket.settimeout(2)
                rpc_socket.connect(path)
                self.socket = rpc_socket
                if self._send(0, {"v": 1, "client_id": DISCORD_APP_ID}):
                    self._receive()
                    return True
            except OSError:
                self._disconnect()
        return False

    def _get_socket_paths(self):
        dirs = [
            os.environ.get("XDG_RUNTIME_DIR"),
            os.environ.get("TMPDIR"),
            "/tmp"
        ]
        return [
            os.path.join(directory, "discord-ipc-{}".format(index))
            for directory in dirs
            if directory and os.path.isdir(directory)
            for index in range(10)
        ]

    def _truncate(self, field):
        return field if len(field) <= self.MAX_FIELD_LENGTH else field[:self.MAX_FIELD_LENGTH - 1] + "..."

    def _send(self, op, payload):
        try:
            data = json.dumps(payload).encode("utf-8")
            self.socket.sendall(struct.pack("<II", op, len(data)) + data)
            return True
        except OSError:
            return False

    def _receive(self):
        try:
            header = self.socket.recv(8)
            if len(header) != 8:
                return None
            op, length = struct.unpack("<II", header)
            return json.loads(self.socket.recv(length).decode("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _clear(self):
        if self.socket:
            self._set_activity(None)

    def _disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None

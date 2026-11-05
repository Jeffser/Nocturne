# base.py

from gi.repository import GObject, GLib, Gdk, Gtk, Gio
from . import models, secret, sql_instance
from ..constants import get_nocturne_version, INTEGRATIONS_DIR, DATA_DIR
import requests, urllib3, time, os, json, threading, logging
from datetime import datetime
from requests.adapters import HTTPAdapter, Retry
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Just so that the logs don't get cluttered with warnings if trust-server = True
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BaseReportManager():
    def __init__(self, integration):
        self.integration = integration

    def start(self, song_id:str, paused:bool=False, position:float=0.0):
        # Start song playback when no song was playing
        # If changing songs use change_song() function
        #   position - the positionSeconds the song will start at for resuming playback
        #   paused - whether the song was started paused, used by Jellyfin
        # Call super().start() to preserve local scrobbling and ListenBrainz reporting
        self.integration.scrobble(song_id, submission=False)

    def stop(self, song_id:str, position:float=0.0, playtime:int=0, duration:int=0):
        # Stop song playback when no song is remaining in queue
        # If changing songs use change_song() function
        #   position - the positionSeconds the playback ended at, used by Jellyfin
        #   playtime - the seconds the user actively listened, used by ListenBrainz
        #   duration - the duration of the track, used by ListenBrainz
        # Call super().stop() to preserve local scrobbling and ListenBrainz reporting
        if (playtime >= 240) or (playtime >= duration / 2):
            self.integration.scrobble(song_id, playtime=playtime, submission=True)

    def change_song(self, starting_id:str, finished_id:str, start_position:float=0.0, finish_position:float=0.0, playtime:int=0, duration:int=0):
        # Reports when one song has ended and another one is starting
        #   starting_id - the model_id for the incoming track
        #   finished_id - the model_id for the finished track
        #   start_position - the positionSeconds the song will start at for resuming playback
        #   finish_position - the positionSeconds the playback ended at, used by Jellyfin
        #   playtime - the seconds the user actively listened, used by ListenBrainz
        #   duration - the duration of the track, used by ListenBrainz
        # Call super().stop() to preserve local scrobbling and ListenBrainz reporting
        if (playtime >= 240) or (playtime >= duration / 2):
            self.integration.scrobble(finished_id, playtime=playtime, submission=True)
            time.sleep(1.2) #prevent API flood protection
        self.integration.scrobble(starting_id, submission=False)

    def playing(self, song_id:str, paused:bool, position:float):
        # Reports playback state - play/pause status and the position
        # Meant to be used for keep-alive pulses
        #   position - the positionSeconds the playback ended at, used by Jellyfin
        #   paused - whether the song is currently paused, used by Jellyfin
        # Currently only used by jellyfin.py
        pass

    def quit(self, song_id:str, position:float=0.0, playtime:int=0, duration:int=0):
        # Report that the application is closing
        #   position - the positionSeconds the playback ended at, used by Jellyfin
        #   playtime - the seconds the user actively listened, used by ListenBrainz
        #   duration - the duration of the track, used by ListenBrainz
        # Call super().quit() to preserve local scrobbling and ListenBrainz reporting
        if (playtime >= 240) or (playtime >= duration / 2):
            self.integration.scrobble(song_id, playtime=playtime, submission=True)

class CacheManager(GObject.Object):
    __gtype_name__ = 'NocturneCacheManager'

    # Completely thread safe

    timeout = GObject.Property(type=int, default=20) # Max time waiting for origin thread to finish (seconds)
    permanence = GObject.Property(type=int, default=5) # How long will the cache object last (seconds)

    results = {}
    events = {}
    lock = threading.Lock()

    def delete_result(self, cache_id:str):
        with self.lock:
            if cache_id in self.results:
                del self.results[cache_id]

    def insert_result(self, cache_id:str, result:object):
        with self.lock:
            self.results[cache_id] = result
            GLib.timeout_add(self.get_property('permanence') * 1000, self.delete_result, cache_id)

    def get_result(self, cache_id:str, job:callable, *job_args) -> object:
        # Will either pull result from cache or do the job (callable)
        # Call this in a different thread, job will be done in that thread
        # Job should return a tuple: state, object.
        # Where state dictates if it should be saved in cache and object is what is returned
        result = None
        is_origin = False
        with self.lock:
            if result := self.results.get(cache_id):
                # Case 1: Result is in cache
                return result

            if self.events.get(cache_id) is not None:
                # Case 2: Pending
                event = self.events.get(cache_id)
                is_origin = False
            else:
                # Case 3: First request, create event
                if job is None:
                    return None
                event = threading.Event()
                self.events[cache_id] = event
                is_origin = True

        if is_origin:
            try:
                state, result = job(*job_args)
                if state:
                    self.insert_result(cache_id, result)
            finally:
                event.set()
                with self.lock:
                    del self.events[cache_id]
        else:
            event.wait(timeout=self.get_property('timeout'))
            result = self.results.get(cache_id)
            if result:
                logger.debug(f'(Cache) Job Skipped : {cache_id}')
            else:
                # No result, just do the job at this point
                state, result = job(*job_args)

        return result

# DO NOT USE DIRECTLY
class Base(GObject.Object):
    __gtype_name__ = 'NocturneIntegrationBase'

    # For how to fill these checkout navidrome.py and local.py
    login_page_metadata = {}
    button_metadata = {}
    limitations = ()

    loaded_models = {}

    url = GObject.Property(type=str)
    trustServer = GObject.Property(type=bool, default=False)
    user = GObject.Property(type=str)
    libraryDir = GObject.Property(type=str)

    # Show spinner in sidebar with message as tooltip text if set
    loadingMessage = GObject.Property(type=str)

    # See example in get_sql_schema
    sqlSchema = {}

    # Set up thread executor
    threads = ThreadPoolExecutor(max_workers=30)

    # Re-usable session_adapter for shared connection pool
    _session_adapter = HTTPAdapter(
        pool_connections=5,
        pool_maxsize=35,
        pool_block=True,
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
    )

    # Playback reporting class
    report_manager_class = BaseReportManager

    @property
    def session(self):
        session = requests.Session()
        session.mount("http://", self._session_adapter)
        session.mount("https://", self._session_adapter)
        return session

    # Epic custom lightweight cache manager
    cache_manager = CacheManager()

    # List of library IDs to retrieve from
    library_ids = []

    def __init__(self, *args, **kwargs):
        # do not change
        super().__init__(*args, **kwargs)
        self.loaded_models = {}
        self.report = self.report_manager_class(self)

        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.library_ids = self.settings.get_strv("library-ids")
        self.settings.connect("changed::library-ids", self.changeLibrary)

    def open_json(self, filename:str, fallback={}) -> dict:
        # please use sql when possible
        try:
            with open(os.path.join(self.getIntegrationDir(), filename), 'r') as f:
                return json.load(f)
        except:
            pass
        return fallback

    def save_json(self, filename:str, data:dict):
        # save JSON to instance specific file
        try:
            with open(os.path.join(self.getIntegrationDir(), filename), 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def get_sql_schema(self) -> dict:
        return {
            'playlist_resume': {
                'id': 'TEXT PRIMARY KEY',
                'song_id': 'TEXT NOT NULL',
                'timestamp': 'FLOAT DEFAULT 0'
            },
            'playback_scrobble': {
                'month': 'TEXT NOT NULL',
                'song_id': 'TEXT NOT NULL',
                'amount': 'INTEGER DEFAULT 1',
                'UNIQUE': '(month, song_id)'
            },
            'lyrics': {
                'id': 'TEXT PRIMARY KEY',
                'type': 'TEXT NOT NULL',
                'content': 'TEXT NOT NULL'
            },
            **self.sqlSchema
        }

    def check_if_ready(self, row) -> bool:
        # gets called to see if it is ready to show login page
        return True

    def connect_to_model(self, model_id:str, parameter:str, callback:callable) -> str:
        connection_id = ""
        if model_id in self.loaded_models:
            model = self.loaded_models.get(model_id)
            connection_id = model.connect(
                'notify::{}'.format(parameter),
                lambda *_, p=parameter, mid=model_id, cb=callback: (
                    self._dispatch_model_callback(cb, self.loaded_models.get(mid).get_property(p))
                    if threading.current_thread() == threading.main_thread()
                    else GLib.idle_add(self._dispatch_model_callback, cb, self.loaded_models.get(mid).get_property(p))
                )
            )
            if threading.current_thread() == threading.main_thread():
                self._dispatch_model_callback(callback, self.loaded_models.get(model_id).get_property(parameter))
            else:
                GLib.idle_add(self._dispatch_model_callback, callback, self.loaded_models.get(model_id).get_property(parameter))
            self._auto_disconnect_on_unroot(callback, model, connection_id)
        return connection_id

    def _dispatch_model_callback(self, cb, *args):
        # Drops updates already queued for widgets removed from the tree before they ran.
        widget = getattr(cb, '__self__', None)
        if isinstance(widget, Gtk.Widget) and getattr(widget, '_nocturne_removed_from_tree', False):
            return
        cb(*args)

    def _auto_disconnect_on_unroot(self, callback:callable, model:GObject.Object, connection_id:int):
        # Row/button widgets connect to shared, long-lived models here. Without disconnecting
        # when the widget is removed from the tree (eg. via list_el.remove_all() on page
        # reset/reload), the model's signal connection keeps the orphaned widget alive forever,
        # so it keeps receiving updates and mutating its children with no allocation - which
        # crashes GTK's next snapshot pass.
        widget = getattr(callback, '__self__', None)
        if not isinstance(widget, Gtk.Widget):
            return
        pending = getattr(widget, '_nocturne_model_connections', None)
        if pending is None:
            pending = []
            widget._nocturne_model_connections = pending
            # Gtk.Widget has no connectable 'unroot' signal; 'parent' becoming None is the
            # observable equivalent for widgets removed via list_el.remove()/remove_all().
            widget.connect('notify::parent', self._disconnect_widget_model_connections)
        pending.append((model, connection_id))

    def _disconnect_widget_model_connections(self, widget, pspec):
        if widget.get_parent() is not None:
            return
        for model, connection_id in widget._nocturne_model_connections:
            if model.handler_is_connected(connection_id):
                model.disconnect(connection_id)
        widget._nocturne_model_connections = []
        widget._nocturne_removed_from_tree = True

    def save_cache_image(self, model_id:str, size:int, image_data:bytes):
        # do not modify this function, it works as is in any instance
        # should be called in updateCoverArt
        conn, cursor = sql_instance.get_cache_connection()
        cursor.execute(
            "INSERT OR IGNORE INTO images (integration, model, size, image) values (?, ?, ?, ?)",
            (self.__gtype_name__, model_id, size, image_data)
        )
        conn.commit()
        conn.close()

    def get_cache_image(self, model_id:str, size:int) -> bytes:
        # do not modify this function, it works as is in any instance
        # should be called in updateCoverArt
        conn, cursor = sql_instance.get_cache_connection()
        cursor.execute(
            "SELECT image from images WHERE integration=? AND model=? AND size=?",
            (self.__gtype_name__, model_id, size)
        )
        result = b''
        if row := cursor.fetchone():
            result = row[0] or b''
        conn.commit()
        conn.close()
        return result

    def start_instance(self) -> bool:
        # always called in different thread, because it might take a couple of seconds to get started
        logger.warning('method not implemented')
        return False

    def terminate_instance(self):
        # called when the instance is no longer used
        logger.warning('method not implemented')

    def on_login(self):
        # gets called in different thread when the login is successful
        # optional
        pass

    def get_stream_url(self, song_id:str) -> str:
        # should return a valid url for a gst stream
        logger.warning('method not implemented')
        return ""

    def getIntegrationDir(self) -> str:
        # do not modify this function
        directory = os.path.join(INTEGRATIONS_DIR, self.__gtype_name__)
        os.makedirs(directory, exist_ok=True)
        return directory

    def getLibraries(self) -> tuple[list, bool]:
        # Used to retrieve a list of dicts containing the names and IDs for the available music libraries
        # Returns a list of libraries and whether multiple libraries can be selected at once
        return [], False

    def changeLibrary(self, settings, key):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.library_ids = settings.get_strv(key)

        #reset models
        self.loaded_models = {}

    def getCoverArtBytes(self, model_id:str, size:int) -> bytes:
        # Used to send bytes to different parts of the codebase instead of full paintables, also called by getCoverArt
        logger.warning('method not implemented')
        return b''

    def updateCoverArt(self, model_id:str):
        # update both gdkPaintable and gdkPaintableBig
        logger.warning('method not implemented')

    def getCoverArtUrl(self, model_id:str) -> str:
        # Returns URL that can be used to get coverArt directly by external services
        # Returns empty string when a url is not available
        logger.warning('method not implemented')
        return ""

    def ping(self) -> dict:
        # return True if logged in and connection is successful
        # when implementing also do super().ping() to prepare SQL
        try:
            sql_instance.ensure_schema(self)
            sql_instance.ensure_cache_schema()
            return {'status': 'ok'}
        except:
            return {
                'status': 'error',
                'message': _('Could not generate SQL database')
            }

    def getAlbumList(self, list_type:str="recent", size:int=10, offset:int=0) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        # list_type = random, newest, frequent, recent, starred
        logger.warning('method not implemented')
        return []

    def getArtists(self, size:int=10) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        logger.warning('method not implemented')
        return []

    def getPlaylists(self) -> list:
        # add non existing elements to self.loaded_models, returns lists of IDs, nothing more
        logger.warning('method not implemented')
        return []

    def getStarred(self, item_type:str) -> list:
        # returns a list of IDs of items of a given type
        logger.warning('method not implemented')
        return []

    def verifyArtist(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        # verifies that element is fully loaded with all it's metadata, should also call for updateCoverArt
        logger.warning('method not implemented')

    def verifyAlbum(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        # verifies that element is fully loaded with all it's metadata, should also call for updateCoverArt
        logger.warning('method not implemented')

    def verifyPlaylist(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        # verifies that element is fully loaded with all it's metadata, should also call for updateCoverArt
        logger.warning('method not implemented')

    def verifySong(self, model_id:str, force_update:bool=False, use_threading:bool=True, minimal:bool=False):
        # verifies that element is fully loaded with all it's metadata, should also call for updateCoverArt
        logger.warning('method not implemented')

    def star(self, model_id:str) -> bool:
        # stars an element, should return True if change is done
        logger.warning('method not implemented')
        return False

    def unstar(self, model_id:str) -> bool:
        # unstars an element, should return True if change is done
        logger.warning('method not implemented')
        return False

    def getPlayQueue(self) -> tuple:
        # returns the song ID to be played and a list of IDs
        logger.warning('method not implemented')
        return "", []

    def savePlayQueue(self, id_list:list, current:str, position:int) -> bool:
        # save the play queue for retrieving later, called on close, return True if ok
        logger.warning('method not implemented')
        return False

    def getSimilarSongs(self, model_id:str, count:int=20) -> list:
        # returns list of IDs of similar songs to id, if it can not be implemented just return the result of getRandomSongs
        logger.warning('method not implemented')
        return []

    def getRandomSongs(self, size:int=20) -> list:
        # returns a list of song IDs
        logger.warning('method not implemented')
        return []

    def saveLyrics(self, songId:str, content:str, lyrics_type:str):
        # Do not modify, works as is
        conn, cursor = sql_instance.get_connection(self)
        query = """
        INSERT INTO lyrics (id, type, content)
        VALUES (?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            type = excluded.type,
            content = excluded.content
        """
        cursor.execute(query, (songId, lyrics_type, content))
        conn.commit()
        conn.close()

    def deleteLyrics(self, songId:str):
        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("DELETE FROM lyrics WHERE id = ?", (songId,))
        conn.commit()
        conn.close()
        # Do not modify, works as is

    def getLyrics(self, songId:str, requestOnline:bool=False) -> tuple:
        # call this function first super().getLyrics(args)
        # it loads lyrics from db, as a last resource

        if model := self.loaded_models.get(songId):
            # Radio
            if model.get_property('radioStreamUrl'):
                return 'radio', ''

            # Online
            if requestOnline:
                def job(track_name, artist_name, album_name, duration):
                    params = {
                        'track_name': track_name,
                        'artist_name': artist_name
                    }
                    if album_name: #optional
                        params['album_name'] = album_name
                    #if duration: #optional
                        #params['duration'] = duration
                    response = requests.get(
                        'https://lrclib.net/api/get',
                        params=params,
                        headers={"User-Agent": "Nocturne (https://jeffser.com/nocturne)"}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return True, data.get("syncedLyrics", "")
                    return True, ''
                if content := self.cache_manager.get_result(f'OnlineLyrics:{songId}', job, model.get_property('title'), model.get_property('artist'), model.get_property('album'), model.get_property('duration')):
                    self.saveLyrics(songId, content, 'lrc')
                    return 'lrc', content
                else:
                    return 'not-found', ''

            # Legacy: Move existing lrc files to DB
            file_name_without_ext = '{}|{}|{}|{}'.format(
                model.get_property('title'),
                model.get_property('artist'),
                model.get_property('album') or model.get_property('title'),
                model.get_property('duration')
            )
            lrc_path = os.path.join(DATA_DIR, 'lyrics', file_name_without_ext+'.lrc')
            plain_path = os.path.join(DATA_DIR, 'lyrics', file_name_without_ext+'.txt')
            if os.path.isfile(lrc_path):
                with open(lrc_path, 'r') as f:
                    if content := f.read():
                        self.saveLyrics(songId, content, 'lrc')
                try:
                    os.remove(lrc_path)
                except:
                    pass
            if os.path.isfile(plain_path):
                try:
                    os.remove(plain_path)
                except:
                    pass
        else:
            return 'not-found', ''

        conn, cursor = sql_instance.get_connection(self)
        cursor.execute("SELECT type, content FROM lyrics WHERE id = ?", (songId,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0] in ('plain', 'lrc') and row[1]:
            return row[0], row[1]
        return 'not-found', ''

    def search(self, query:str, artistCount:int=0, artistOffset:int=0, albumCount:int=0, albumOffset:int=0, songCount:int=0, songOffset:int=0, playlistCount:int=0, playlistOffset:int=0) -> dict:
        # returns a dict with results trucated with the count and offset, the dict has keys for album, artist and song, the values are lists of IDs
        # for an example view local.py
        logger.warning('method not implemented')
        return {'artist': [], 'album': [], 'song': [], 'playlist': []}

    def systemSearch(self, query:str):
        # similar to 'search' but it will always just return the top 5 results for each category
        # and instead of separating categories it is a dict of other dicts like this
        # {'ID': {'display': VARIANT, 'type': VARIANT, 'icon': VARIANT}}
        # The values for display, type and icon should be GVariants, see Jellyfin for example
        logger.warning('method not implemented')
        return {}

    def getInternetRadioStations(self) -> list:
        # returns a list of Song IDs with the property radioStreamUrl set
        # make sure the id also exists in self.loaded_models, no need to be verified
        logger.warning('method not implemented')
        return []

    def createInternetRadioStation(self, name:str, radioStreamUrl:str) -> bool:
        # returns True if created successfully
        logger.warning('method not implemented')
        return False

    def updateInternetRadioStation(self, model_id:str, name:str, radioStreamUrl:str) -> bool:
        # returns True if updated successfully
        logger.warning('method not implemented')
        return False

    def deleteInternetRadioStation(self, model_id:str) -> bool:
        # returns True if deleted successfully
        logger.warning('method not implemented')
        return False

    def createPlaylist(self, name:str=None, playlistId:str=None, songId:list=[]) -> str:
        # returns id if created successfully
        logger.warning('method not implemented')
        return ""

    def updatePlaylist(self, playlistId:str, songIdToAdd:list=[], songIndexToRemove:list=[]) -> bool:
        # returns True if updated successfully
        logger.warning('method not implemented')
        return False

    def deletePlaylist(self, model_id:str) -> bool:
        # returns True if deleted successfully
        logger.warning('method not implemented')
        return False

    def setRating(self, model_id:str, rating:int=0) -> bool:
        # returns True if rated successfully
        logger.warning('method not implemented')
        return False

    def getTopSongs(self, artist_id:str, count:int=10) -> list:
        # returns list of ids
        logger.warning('method not implemented')
        return []

    def downloadSong(self, model_id:str, file_title:str, progress_callback:callable):
        # from constants.py
        # file_title does NOT include extension (.mp3, .flac, etc)
        # download into DOWNLOAD_QUEUE_DIR
        # on finish move file to DOWNLOADS_DIR
        # see navidrome.py for example
        logger.warning('method not implemented')

    def scrobble(self, model_id:str, playtime:int=0, submission:bool=True):
        if submission and not playtime:
            logger.warning("Invalid scrobble, submissions must include the playtime for ListenBrainz")
            return

        # the id is for a Song, this is how views are stored
        # called when a song is played
        # if you need to inherit this, also call super().scrobble(id) so that listenbrainz can also get the scrobble

        # TODO IMPORTANT: current-state is no longer available at an integration-level
        # the values requested should be parsed to scrobble (also affects other integrations functions)

        # Playback (monthly scrobble)
        date_formated = datetime.now().strftime("%m-%Y")
        conn, cursor = sql_instance.get_connection(self)
        query = """
        INSERT INTO playback_scrobble (month, song_id)
        VALUES (?, ?)
        ON CONFLICT(month, song_id) DO UPDATE SET
            amount = amount + 1;
        """
        cursor.execute(query, (date_formated, model_id))
        conn.commit()
        conn.close()

        # ListenBrainz
        if model := self.loaded_models.get(model_id):
            if token := secret.get_plain_password("listenbrainz"):
                listen_payload = {
                    "track_metadata": {
                        "artist_name": model.get_property("artist"),
                        "track_name": model.get_property("title"),
                        "release_name": model.get_property("album"),
                        "additional_info": {
                            "submission_client": "com.jeffser.Nocturne",
                            "submission_client_version": get_nocturne_version(),
                            "media_player": "Nocturne"
                        }
                    }
                }
                
                if submission:
                    listen_payload["listened_at"] = int(time.time() - playtime)

                payload = {
                    "listen_type": "single" if submission else "playing_now",
                    "payload": [listen_payload]
                }
                headers = {
                    "Authorization": f"Token {token}",
                    "User-Agent": f"com.jeffser.Nocturne/{get_nocturne_version()} ( https://jeffser.com/nocturne/ )",
                    "Content-Type": "application/json"
                }
                try:
                    response = requests.post("https://api.listenbrainz.org/1/submit-listens", json=payload, headers=headers)
                except:
                    pass

        return
        # Playlist Resume
        queue_origin_id = self.get_property('current-state').get_property('queueOrigin')
        current_timestamp = self.get_property('current-state').get_property('positionSeconds')
        if model := self.loaded_models.get(queue_origin_id):
            if isinstance(model, models.Playlist):
                conn, cursor = sql_instance.get_connection(self)
                query = """
                INSERT INTO playlist_resume (id, song_id, timestamp)
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    song_id = excluded.song_id,
                    timestamp = excluded.timestamp;
                """
                cursor.execute(query, (queue_origin_id, model_id, current_timestamp))
                conn.commit()
                conn.close()

    def getPlaylistResume(self, model_id:str) -> tuple:
        # Works as is, no need to modify
        # Returns song_id, timestamp (seconds float)
        if playlist := self.loaded_models.get(model_id):
            conn, cursor = sql_instance.get_connection(self)
            cursor.execute(
                "SELECT song_id, timestamp FROM playlist_resume WHERE id=?",
                (playlist.get_property('id'),)
            )
            result = cursor.fetchone()
            conn.close()
            if result:
                return result[0], result[1]
        return "", 0

    def savePlaylistResume(self, queue_origin_id:str, song_id:str, current_timestamp:float):
        # Works as is, no need to modify
        if model := self.loaded_models.get(queue_origin_id):
            if isinstance(model, models.Playlist):
                conn, cursor = sql_instance.get_connection(self)
                query = """
                INSERT INTO playlist_resume (id, song_id, timestamp)
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    song_id = excluded.song_id,
                    timestamp = excluded.timestamp;
                """
                cursor.execute(query, (queue_origin_id, song_id, current_timestamp))
                conn.commit()
                conn.close()

    def getSongDetails(self, model_id:str) -> models.SongDetails:
        # Fill and return songDetails
        # Do NOT add it to loaded_models
        return models.SongDetails()
    
    def getPlaybackScrobble(self, month:str, top:int=50) -> list:
        # Works as is, no need to modify
        # Month in format %m-%Y
        # Returns list of tuples (song_id, amount)
        conn, cursor = sql_instance.get_connection(self)
        query = """
        SELECT song_id, amount FROM playback_scrobble
        WHERE month = ? ORDER BY amount DESC LIMIT ?;
        """
        cursor.execute(query, (month, top))
        results = cursor.fetchall()
        conn.close()
        return results

    def getServerInformation(self) -> dict:
        # should return these keys:
        # picture : gdk.Paintable
        # username : str
        # title : str
        # link : str
        logger.warning('method not implemented')
        return {}



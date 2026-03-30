# queue_page.py

from gi.repository import Gtk, Adw, GObject, GLib, Gio
from ..song import SongRow
from ...integrations import models, get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/queue_page.ui')
class PlayingQueuePage(Gtk.ScrolledWindow):
    __gtype_name__ = 'NocturnePlayingQueuePage'

    song_list_el = Gtk.Template.Child()
    autoplay_row_el = Gtk.Template.Child()
    autoplay_spinner_el = Gtk.Template.Child()
    list_bin_el = Gtk.Template.Child()
    generated_queue = [] # Preload the next queue for auto-play

    def __init__(self):
        super().__init__()

        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        settings.bind('auto-play', self.autoplay_row_el, 'active', Gio.SettingsBindFlags.DEFAULT)

    def replace_list_element(self, list_el:Gtk.Widget):
        if self.get_root().__gtype_name__ != 'NocturnePopoutWindow':
            if parent := self.song_list_el.get_parent():
                parent.set_child(None)
            self.list_bin_el.set_child(self.song_list_el)
        else:
            if parent := list_el.get_parent():
                parent.set_child(None)
            self.list_bin_el.set_child(list_el)

    def replace_queue(self, songs:list, current_id:str=None):
        integration = get_current_integration()
        for row in list(self.song_list_el.list_el):
            GLib.idle_add(self.song_list_el.list_el.remove, row)
        if len(songs) > 0:
            if current_id is None:
                current_id = songs[0]

            for song_id in songs:
                integration.verifySong(song_id, use_threading=False)
                GLib.idle_add(self.song_list_el.list_el.append,
                    SongRow(
                        song_id,
                        draggable=True,
                        removable=True
                    )
                )
        GLib.idle_add(integration.loaded_models.get('currentSong').set_property, 'songId', current_id)
        if Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('auto-play').unpack():
            threading.Thread(target=self.generate_auto_play_queue).start()

    def play_next(self, songs:list):
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        if len(list(self.song_list_el.list_el)) == 0 or not current_song_id:
            self.replace_queue(songs)
        else:
            for row in list(self.song_list_el.list_el):
                if row.id in songs and row.id != current_song_id:
                    GLib.idle_add(self.song_list_el.list_el.remove, row)
            current_song_index = -1
            for i, row in enumerate(list(self.song_list_el.list_el)):
                if row.id == current_song_id:
                    current_song_index = i + 1
            songs.reverse()
            for song_id in [s for s in songs if s != current_song_id]:
                integration.verifySong(song_id, use_threading=False)
                GLib.idle_add(self.song_list_el.list_el.insert,
                    SongRow(
                        song_id,
                        draggable=True,
                        removable=True
                    ),
                    current_song_index
                )

    def play_later(self, songs:list):
        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        if len(list(self.song_list_el.list_el)) == 0:
            self.replace_queue(songs)
        else:
            for row in list(self.song_list_el.list_el):
                if row.id in songs and row.id != current_song_id:
                    GLib.idle_add(self.song_list_el.list_el.remove, row)
            for song_id in [s for s in songs if s != current_song_id]:
                integration.verifySong(song_id, use_threading=False)
                GLib.idle_add(self.song_list_el.list_el.append,
                    SongRow(
                        song_id,
                        draggable=True,
                        removable=True
                    )
                )

    def generate_auto_play_queue(self):
        self.generated_queue = []
        GLib.idle_add(self.autoplay_spinner_el.set_visible, True)
        integration = get_current_integration()

        if len(list(self.song_list_el.list_el)) > 0:
            artists = []
            for row in list(self.song_list_el.list_el):
                if model := integration.loaded_models.get(row.id):
                    artists.append(model.artistId)
            if len(artists) > 0:
                main_artist = max(set(artists), key=artists.count)
                self.generated_queue = integration.getSimilarSongs(main_artist)

        # Remove repeated songs, if it ends up being less than 5 then just generate a random queue
        self.generated_queue = [s for s in self.generated_queue if s not in self.song_list_el.get_all_ids()]
        if len(self.generated_queue) < 5:
            self.generated_queue = integration.getRandomSongs()

        GLib.idle_add(self.autoplay_spinner_el.set_visible, False)


# queue_page.py

from gi.repository import Gtk, Adw, GObject, GLib
from ..song import SongRow
from ...navidrome import models, get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/queue_page.ui')
class PlayingQueuePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingQueuePage'

    song_list_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.song_list_el.set_mode(True)

    def replace_queue(self, songs:list, current_id:str=None):
        integration = get_current_integration()
        #for row in list(self.song_list_el.list_el):
            #self.song_list_el.list_el.remove(row)

        if len(songs) > 0:
            if current_id is None:
                current_id = songs[0]

            for song_id in songs:
                self.song_list_el.list_el.append(SongRow(song_id, draggable=True))

        integration.loaded_models['currentSong'].songId = current_id


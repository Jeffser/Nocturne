# queue_page.py

from gi.repository import Gtk, Gio
from ..song import SongRow
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/queue_page.ui')
class PlayingQueuePage(Gtk.ScrolledWindow):
    __gtype_name__ = 'NocturnePlayingQueuePage'

    song_list_el = Gtk.Template.Child()
    autoplay_row_el = Gtk.Template.Child()
    autoplay_spinner_el = Gtk.Template.Child()
    list_bin_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        Gio.Settings(schema_id="com.jeffser.Nocturne").bind(
            'auto-play',
            self.autoplay_row_el,
            'active',
            Gio.SettingsBindFlags.DEFAULT
        )
        self.song_list_el.main_stack.set_visible_child_name('content')

    def setup(self):
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'generatingQueue', self.autoplay_spinner_el.get_parent().set_visible)
        global_queue = integration.loaded_models.get('currentSong').get_property('queueModel')
        if len(list(self.song_list_el.list_el)) == 0:
            self.queue_changed(global_queue, 0, 0, global_queue.get_property('n-items'))
        global_queue.connect('items-changed', self.queue_changed)

    def queue_changed(self, global_queue, position:int, removed:int, added:int):
        for _ in range(removed):
            if row := self.song_list_el.list_el.get_row_at_index(position):
                self.song_list_el.list_el.remove(row)

        for i in range(added):
            if item := global_queue.get_item(position + i):
                row = SongRow(
                    item.get_string(),
                    draggable=True,
                    removable=True
                )
                self.song_list_el.list_el.insert(row, position + i)

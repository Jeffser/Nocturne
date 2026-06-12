# songs_starred.py

from gi.repository import Gtk, Adw, GLib
from ...integrations import get_current_integration
from ..song import SongRow, SongButton
import threading
import re

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/songs_starred.ui')
class SongsStarredPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneSongsStarredPage'

    search_entry = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    wrapbox_el = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    end_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    offset = 0
    loading = False
    generation = 0
    song_ids = []
    filtered_ids = []

    def __init__(self):
        super().__init__()
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size() and self.end_stack.get_visible_child_name() == 'loading':
            threading.Thread(target=self.load_songs, daemon=True).start()

    def reload(self):
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        integration = get_current_integration()
        self.song_ids = integration.getStarredSongs()
        GLib.idle_add(self.apply_search)

    def reset(self):
        self.list_el.list_el.remove_all()
        for el in list(self.wrapbox_el):
            self.wrapbox_el.remove(el)

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        self.apply_search()

    def apply_search(self):
        # Filters by title using the metadata loaded by getStarredSongs,
        # widgets are only created for songs that match
        query = self.search_entry.get_text()
        pattern = None
        if query:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error:
                pattern = re.compile(re.escape(query), re.IGNORECASE)
        integration = get_current_integration()
        filtered = []
        for song_id in self.song_ids:
            if model := integration.loaded_models.get(song_id):
                if not pattern or pattern.search(model.get_property('title') or ''):
                    filtered.append(song_id)

        self.generation += 1
        self.filtered_ids = filtered
        self.offset = 0
        self.reset()
        self.end_stack.set_visible_child_name('loading')
        threading.Thread(target=self.load_songs, daemon=True).start()

    def load_songs(self, count=30):
        if self.loading:
            return
        self.loading = True
        generation = self.generation
        chunk = [(SongRow(song_id), SongButton(song_id)) for song_id in self.filtered_ids[self.offset:self.offset + count]]

        def add_chunk():
            if generation == self.generation:
                for row, button in chunk:
                    self.list_el.list_el.append(row)
                    self.wrapbox_el.append(button)
                self.offset += len(chunk)
                self.end_stack.set_visible_child_name('end' if self.offset >= len(self.filtered_ids) else 'loading')
                self.update_visibility()
            self.loading = False
        GLib.idle_add(add_chunk)

    @Gtk.Template.Callback()
    def scroll_edge_reached(self, scrolledwindow, pos):
        if pos == Gtk.PositionType.BOTTOM and self.end_stack.get_visible_child_name() == 'loading':
            threading.Thread(target=self.load_songs, daemon=True).start()

    def update_visibility(self):
        for row in list(self.list_el.list_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')

# artist.py

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from ...integrations import get_current_integration, models
from ..artist import ArtistRow
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/artists.ui')
class ArtistsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistsPage'

    search_entry = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    end_stack = Gtk.Template.Child()
    offset = 0
    searching = False

    def reload(self):
        if len(list(self.list_el)) == 0:
            GLib.idle_add(self.on_search, self.search_entry)

    def search(self):
        if self.searching:
            return
        self.searching = True
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        query = self.search_entry.get_text()
        integration = get_current_integration()
        search_results = integration.search(
            query=query,
            artistCount=30,
            artistOffset=self.offset
        )
        for artist_id in search_results.get('artist'):
            results = [row for row in list(self.list_el) if row.id == artist_id]
            if len(results) > 0:
                GLib.idle_add(results[0].set_visible, True)
            else:
                row = ArtistRow(artist_id)
                GLib.idle_add(self.list_el.append, row)
        self.end_stack.set_visible_child_name('end' if max(self.offset, 30) > len([row for row in list(self.list_el) if row.get_visible()]) else 'loading')
        self.offset += 30
        self.searching = False
        GLib.idle_add(self.update_visibility)

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        self.offset = 0
        for row in list(self.list_el):
            row.set_visible(False)
        threading.Thread(target=self.search).start()
            
    @Gtk.Template.Callback()
    def scroll_edge_reached(self, scrolledwindow, pos):
        if pos == Gtk.PositionType.BOTTOM and self.end_stack.get_visible_child_name() == 'loading':
            threading.Thread(target=self.search).start()

    def update_visibility(self):
        for row in list(self.list_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')

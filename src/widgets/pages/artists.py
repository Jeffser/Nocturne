# artist.py

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration
from ..artist import ArtistRow, ArtistButton
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/artists.ui')
class ArtistsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistsPage'

    toggle_group_el = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    wrapbox_el = Gtk.Template.Child()
    end_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    offset = 0
    searching = False

    def __init__(self):
        super().__init__()
        Gio.Settings(schema_id="com.jeffser.Nocturne").bind(
            "default-view-mode-artists",
            self.toggle_group_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size():
            threading.Thread(target=self.search, daemon=True).start()

    def reload(self):
        if len(list(self.list_el)) + len(list(self.wrapbox_el)) == 0:
            GLib.idle_add(self.on_search, self.search_entry)

    def reset(self):
        self.list_el.remove_all()
        for el in list(self.wrapbox_el):
            self.wrapbox_el.remove(el)

    def search(self):
        if self.searching:
            return
        self.searching = True
        integration = get_current_integration()

        query = ""
        while query != self.search_entry.get_text(): # In case query changes whilst calling integration
            query = self.search_entry.get_text()
            search_results = integration.search(query=query, artistCount=30, artistOffset=self.offset)

        for artist_id in search_results.get('artist'):
            results_list = [row for row in list(self.list_el) if row.id == artist_id]
            if len(results_list) > 0:
                GLib.idle_add(results_list[0].set_visible, True)
            else:
                row = ArtistRow(artist_id)
                GLib.idle_add(self.list_el.append, row)

            results_wrapbox = [button for button in list(self.wrapbox_el) if button.id == artist_id]
            if len(results_wrapbox) > 0:
                GLib.idle_add(results_wrapbox[0].set_visible, True)
            else:
                button = ArtistButton(artist_id)
                GLib.idle_add(self.wrapbox_el.append, button)

        GLib.idle_add(self.end_stack.set_visible_child_name, 'end' if len(search_results.get('artist')) < 30 else 'loading')
        self.offset += 30
        self.searching = False
        GLib.idle_add(self.update_visibility)

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        self.offset = 0
        for row in list(self.list_el) + list(self.wrapbox_el):
            row.set_visible(False)
        threading.Thread(target=self.search, daemon=True).start()
            
    @Gtk.Template.Callback()
    def scroll_edge_reached(self, scrolledwindow, pos):
        if pos == Gtk.PositionType.BOTTOM and self.end_stack.get_visible_child_name() == 'loading':
            threading.Thread(target=self.search, daemon=True).start()

    def update_visibility(self):
        for row in list(self.list_el) + list(self.wrapbox_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')

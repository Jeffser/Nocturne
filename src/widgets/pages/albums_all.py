# albums_all.py

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration
from ..album import AlbumRow, AlbumButton
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/albums_all.ui')
class AlbumsAllPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneAlbumsAllPage'

    toggle_group_el = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    wrapbox_el = Gtk.Template.Child()
    end_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    offset = 0
    searching = False
    skipped_albums = 0

    def __init__(self):
        super().__init__()
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.bind(
            "default-view-mode-albums",
            self.toggle_group_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size():
            threading.Thread(target=self.search, daemon=True).start()

    def reload(self):
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
        hide_singles = self.settings.get_value('hide-singles').unpack()
        self.skipped_albums = 0

        query = None
        while query != self.search_entry.get_text(): # In case query changes whilst calling integration
            query = self.search_entry.get_text()
            search_results = integration.search(query=query, albumCount=30, albumOffset=self.offset)

        for album_id in search_results.get('album'):
            should_skip = False
            if hide_singles:
                if model := integration.loaded_models.get(album_id):
                    if model.get_property('songCount') <= 1:
                        self.skipped_albums += 1
                        should_skip = True
            results_list = [row for row in list(self.list_el) if row.id == album_id]
            if len(results_list) > 0:
                GLib.idle_add(results_list[0].set_visible, not should_skip)
            elif not should_skip:
                row = AlbumRow(album_id)
                GLib.idle_add(self.list_el.append, row)

            results_wrapbox = [button for button in list(self.wrapbox_el) if button.id == album_id]
            if len(results_wrapbox) > 0:
                GLib.idle_add(results_wrapbox[0].set_visible, not should_skip)
            elif not should_skip:
                button = AlbumButton(album_id)
                GLib.idle_add(self.wrapbox_el.append, button)

        GLib.idle_add(self.end_stack.set_visible_child_name, 'end' if len(search_results.get('album')) - self.skipped_albums < 30 else 'loading')
        self.offset += 30
        self.searching = False
        if len(search_results.get('album')) >= 30 and self.skipped_albums:
            self.search()
        else:
            GLib.idle_add(self.update_visibility)

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        self.offset = 0
        self.searching = False
        print('on_search')
        for widget in list(self.list_el) + list(self.wrapbox_el):
            widget.set_visible(False)
        self.end_stack.set_visible_child_name('loading')
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

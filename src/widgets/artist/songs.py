# starred.py
# handles both starred artists and songs

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration
from ..song import SongRow
import re, threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/songs.ui')
class ArtistSongsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistSongsPage'

    list_el = Gtk.Template.Child()
    search_entry_el = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    failed_status_el = Gtk.Template.Child()
    heart_toggle = Gtk.Template.Child()
    item_ids = []
    offset = 0
    searching = False

    def __init__(self, model_id:str):
        super().__init__()
        self.id = model_id
        integration = get_current_integration()
        model = integration.loaded_models.get(self.id)
        self.item_ids = model.get_property("topSongs")
        self.list_el.list_el.set_filter_func(self.filter_favorites, None)
        self.reload()
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))

    def filter_favorites(self, row, _):
        integration = get_current_integration()
        favorited = integration.loaded_models.get(row.id).get_property('starred')
        if self.heart_toggle.get_active():
            return favorited
        return True

    def search(self):
        def append_widget(item_id:str):
            row = SongRow(item_id)
            row.set_action_name(None)
            row.set_action_target_value(GLib.Variant('a{sv}', {
                'songId': GLib.Variant('s', item_id),
                'songs': GLib.Variant('as', self.item_ids),
                'originId': GLib.Variant('s', self.id)
            }))
            row.set_action_name('app.play_song_from_list')
            self.list_el.list_el.append(row)

        if self.searching:
            return
        self.searching = True
        integration = get_current_integration()
        ids_to_show = []
        if query := self.search_entry_el.get_text():
            for item_id in self.item_ids:
                if model := integration.loaded_models.get(item_id):
                    checker = model.get_property('title') + model.get_property('artist')
                    if re.search(query, checker, re.IGNORECASE):
                        ids_to_show.append(item_id)
        else:
            ids_to_show = self.item_ids

        ids_to_show = ids_to_show[:self.offset+30]
        missing_ids = ids_to_show.copy()

        for widget in list(self.list_el.list_el):
            GLib.idle_add(widget.set_visible, widget.id in ids_to_show)
            if widget.id in missing_ids:
                missing_ids.remove(widget.id)

        for item_id in missing_ids:
            GLib.idle_add(append_widget, item_id)
        self.offset += 30
        GLib.idle_add(self.update_visibility)
        self.searching = False

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size():
            threading.Thread(target=self.search).start()

    def reset(self):
        self.offset = 0
        GLib.idle_add(self.list_el.list_el.remove_all)
        integration = get_current_integration()
        model = integration.loaded_models.get(self.id)
        if model.get_property("topSongs"):
            self.item_ids = model.get_property("topSongs")
        else:
            #TODO add Top Songs fetch
            #self.item_ids = integration.getStarred((self.get_tag().split('-')[0]).removesuffix("s"))
            pass

    def load(self):
        self.reload()

    def reload(self):
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')

        def run():
            self.reset()
            self.search()
        threading.Thread(target=run, daemon=True).start()

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        self.offset = 0
        threading.Thread(target=self.search, daemon=True).start()

    @Gtk.Template.Callback()
    def scroll_edge_reached(self, scrolledwindow, pos):
        if pos == Gtk.PositionType.BOTTOM and self.offset < len(self.item_ids):
            threading.Thread(target=self.search, daemon=True).start()

    def update_visibility(self):
        for row in list(self.list_el.list_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                self.list_el.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')
        self.list_el.main_stack.set_visible_child_name('no-content')

    @Gtk.Template.Callback()
    def favorites_mode_toggled(self, button):
        self.list_el.list_el.invalidate_filter()
        threading.Thread(target=self.search, daemon=True).start()

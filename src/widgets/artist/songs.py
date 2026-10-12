# starred.py
# handles both starred artists and songs

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration
from ..song import SongRow
import re, threading, locale, random

@Gtk.Template(resource_path='/com/jeffser/Nocturne/artist/songs.ui')
class ArtistSongsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneArtistSongsPage'

    list_el = Gtk.Template.Child()
    search_entry_el = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    failed_status_el = Gtk.Template.Child()
    offset = 0
    searching = False
    reorder = True
    song_list = []

    def __init__(self, model_id:str):
        super().__init__()
        self.id = model_id

        #Create popover actions
        self.action_group = Gio.SimpleActionGroup.new()
        favorites_check = Gio.SimpleAction.new_stateful(
            "favorites-only", None, GLib.Variant.new_boolean(False)
        )
        favorites_check.connect("activate", self.on_favorites_toggled)
        self.action_group.add_action(favorites_check)
        sort_radios = Gio.SimpleAction.new_stateful(
            "sort-order",
            GLib.VariantType.new('s'),
            GLib.Variant.new_string("playCount")
        )
        sort_radios.connect("activate", self.on_sort_changed)
        self.action_group.add_action(sort_radios)
        self.insert_action_group("sort", self.action_group)

        threading.Thread(target=self.fetch_songs, daemon=True).start()
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))

    def fetch_songs(self):
        integration = get_current_integration()
        self.song_list = integration.getArtistSongs(self.id)
        self.search()

    def search(self):
        def append_widgets(ids_to_add:list):
            for item_id in ids_to_add:
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
        if self.reorder:
            self.sort_list()

        self.searching = True
        integration = get_current_integration()
        ids_to_show = []
        query = ""
        if query := self.search_entry_el.get_text():
            current_artist = integration.loaded_models.get(self.id).get_property("name")
            for item_id in self.item_ids:
                if model := integration.loaded_models.get(item_id):
                    artists = " ".join([
                        artist["name"] for artist in model.get_property("artists")
                        if artist["name"] != current_artist
                    ])
                    checker = model.get_property('title') + artists
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

        GLib.idle_add(append_widgets, missing_ids)
        self.offset += 30
        GLib.idle_add(self.update_visibility)
        self.searching = False

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size():
            threading.Thread(target=self.search).start()

    def reset(self):
        self.offset = 0
        GLib.idle_add(self.list_el.list_el.remove_all)

    def reset_list(self):
        self.offset = 0
        self.list_el.list_el.remove_all()
        self.main_stack.set_visible_child_name('loading')
        threading.Thread(target=self.search).start()

    def load(self):
        self.reload()

    def reload(self):
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')

        def run():
            self.reset()
            self.search()
        threading.Thread(target=run, daemon=True).start()

    def sort_list(self):
        #Get popover menu item states
        sort_order = self.action_group.lookup_action("sort-order").get_state().get_string()
        favorites_only = self.action_group.lookup_action("favorites-only").get_state().get_boolean()

        integration = get_current_integration()
        if favorites_only:
            filtered_list = [
                song for song in self.song_list
                if (model := integration.loaded_models.get(song)) and model.get_property("starred")
            ]
        else:
            filtered_list = self.song_list

        if sort_order == "random":
            random.shuffle(self.item_ids)
        else:
            self.item_ids = sorted(
                filtered_list,
                key=lambda item_id: (
                    locale.strxfrm(result) if isinstance((result := integration.loaded_models.get(item_id).get_property(sort_order)), str)
                    else result
                ),
                reverse=(sort_order == "playCount")
            )
        self.reorder = False

    def on_favorites_toggled(self, action, parameter):
        self.reorder = True
        current_state = action.get_state().get_boolean()
        action.set_state(GLib.Variant.new_boolean(not current_state))
        GLib.idle_add(self.reset_list)

    def on_sort_changed(self, action, parameter):
        self.reorder = True
        requested_choice = parameter.get_string()
        action.set_state(parameter)
        GLib.idle_add(self.reset_list)

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        if not self.search_entry_el.get_text():
            self.reset_list()
        else:
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

# starred.py
# handles both starred artists and songs

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration
from ..song import SongRow, SongButton
from ..artist import ArtistRow, ArtistButton
import re, threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/starred.ui')
class StarredPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneStarredPage'

    list_el = Gtk.Template.Child()
    wrapbox_el = Gtk.Template.Child()
    search_entry_el = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    toggle_group_el = Gtk.Template.Child()
    failed_status_el = Gtk.Template.Child()
    item_ids = []
    offset = 0
    searching = False

    def __init__(self):
        super().__init__()
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))
        self.connect("notify::tag", self.on_tag_assigned)

    def on_tag_assigned(self, obj, pspec):
        pref_string = f"default-view-mode-{self.get_tag().split('-')[0]}"
        Gio.Settings(schema_id="com.jeffser.Nocturne").bind(
            pref_string,
            self.toggle_group_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )

        if self.get_tag() == 'favorite-artists':
            GLib.idle_add(self.search_entry_el.update_property(
                [Gtk.AccessibleProperty.LABEL],
                [_("Search favorite artists")]
            ))
            GLib.idle_add(self.failed_status_el.set_title(_("No Artists Found")))

    def search(self):
        if self.searching:
            return
        self.searching = True
        integration = get_current_integration()
        ids_to_show = []
        if query := self.search_entry_el.get_text():
            for item_id in self.item_ids:
                if model := integration.loaded_models.get(item_id):
                    if 'songs' in self.get_tag():
                        checker = model.get_property('title') + model.get_property('artist')
                    elif 'artists' in self.get_tag():
                        checker = model.get_property('name')
                    if re.search(query, checker, re.IGNORECASE):
                        ids_to_show.append(item_id)
        else:
            ids_to_show = self.item_ids

        ids_to_show = ids_to_show[:self.offset+30]
        missing_ids = ids_to_show.copy()

        for widget in list(self.list_el.list_el) + list(self.wrapbox_el):
            GLib.idle_add(widget.set_visible, widget.id in ids_to_show)
            if widget.id in missing_ids:
                missing_ids.remove(widget.id)

        for item_id in missing_ids:
            if 'songs' in self.get_tag():
                GLib.idle_add(self.list_el.list_el.append, SongRow(item_id))
                GLib.idle_add(self.wrapbox_el.append, SongButton(item_id))
            elif 'artists' in self.get_tag():
                GLib.idle_add(self.list_el.list_el.append, ArtistRow(item_id))
                GLib.idle_add(self.wrapbox_el.append, ArtistButton(item_id))
        self.offset += 30
        GLib.idle_add(self.update_visibility)
        self.searching = False

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size():
            threading.Thread(target=self.search).start()

    def reset(self):
        self.offset = 0
        GLib.idle_add(self.list_el.list_el.remove_all)
        for el in list(self.wrapbox_el):
            GLib.idle_add(self.wrapbox_el.remove, el)
        integration = get_current_integration()
        self.item_ids = integration.getStarred((self.get_tag().split('-')[0]).removesuffix("s"))

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

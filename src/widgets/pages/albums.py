# albums.py

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration
from ..album import AlbumButton
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/albums.ui')
class AlbumsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneAlbumsPage'

    list_el = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    end_stack = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    offset = 0
    loading = False
    skipped_albums = 0
    lazy_reload = False

    def __init__(self):
        super().__init__()
        self.scrolledwindow.get_vadjustment().connect('notify::upper', lambda va, ud: GLib.timeout_add(1000, self.check_scrollbar, va))

    def check_scrollbar(self, adjustment):
        if adjustment.get_upper() <= adjustment.get_page_size():
            threading.Thread(target=self.load_albums, daemon=True).start()

    def load(self):
        if len(list(self.list_el.list_el)) <= 1:
            GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
            self.offset = 0
            self.loading = False
            self.lazy_reload = False
            GLib.idle_add(self.reset)
            GLib.idle_add(self.end_stack.set_visible_child_name, 'loading')
            threading.Thread(target=self.load_albums, daemon=True).start()

    def reload(self):
        self.reset()
        self.load()

    def do_showing(self):
        if self.lazy_reload:
            self.reload()

    def reset(self):
        GLib.idle_add(self.list_el.remove_all)

    def load_albums(self):
        if self.loading:
            return

        self.loading = True
        integration = get_current_integration()
        hide_singles = Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('hide-singles').unpack()
        self.skipped_albums = 0
        
        albums = integration.getAlbumList(
            list_type=self.get_tag().split('-')[1],
            size=20,
            offset=self.offset
        )

        for album_id in albums:
            should_skip = False
            if hide_singles:
                if model := integration.loaded_models.get(album_id):
                    if model.get_property('songCount') <= 1:
                        self.skipped_albums += 1
                        should_skip = True
            results = [button for button in list(self.list_el.list_el) if getattr(button, 'id', None) == album_id]
            if len(results) > 0:
                GLib.idle_add(results[0].set_visible, not should_skip)
            elif not should_skip:
                button = AlbumButton(album_id)
                GLib.idle_add(self.list_el.list_el.append, button)

        GLib.idle_add(self.end_stack.set_visible_child_name, 'end' if len(albums) - self.skipped_albums < 20 else 'loading')
        self.offset += 20
        self.loading = False
        GLib.idle_add(self.update_visibility)

    @Gtk.Template.Callback()
    def scroll_edge_reached(self, scrolledwindow, pos):
        if pos == Gtk.PositionType.BOTTOM and self.end_stack.get_visible_child_name() == 'loading':
            threading.Thread(target=self.load_albums, daemon=True).start()

    def update_visibility(self):
        for row in list(self.list_el.list_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')


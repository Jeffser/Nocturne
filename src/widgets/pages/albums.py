# albums.py

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from ...integrations import get_current_integration, models
from ..album import AlbumButton

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/albums.ui')
class AlbumsPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneAlbumsPage'

    list_el = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    page_type = GObject.Property(type=str)

    def reload(self):
        # call in different thread
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        integration = get_current_integration()

        albums = integration.getAlbumList(
            list_type=self.page_type,
            size=20
        )
        self.list_el.set_widgets([AlbumButton(id) for id in albums])
        GLib.idle_add(self.update_visibility)

    def update_visibility(self):
        for row in list(self.list_el.list_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')


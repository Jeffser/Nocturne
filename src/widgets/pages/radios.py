# radios.py

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from ...integrations import get_current_integration, models
from ..song import SongRow
import re

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/radios.ui')
class RadiosPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneRadiosPage'

    main_stack = Gtk.Template.Child()
    list_el = Gtk.Template.Child()

    def reload(self):
        # call in different thread
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        integration = get_current_integration()
        radios = integration.getInternetRadioStations()
        for row in list(self.list_el):
            GLib.idle_add(self.list_el.remove, row)
        for id in radios:
            GLib.idle_add(self.list_el.append, SongRow(id))
        GLib.idle_add(self.update_visibility)

    @Gtk.Template.Callback()
    def on_search(self, search_entry):
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        query = search_entry.get_text()
        for child in list(self.list_el):
            child.set_visible(child.get_name() != 'GtkListBoxRow' and re.search(query, child.get_name(), re.IGNORECASE))
        GLib.idle_add(self.update_visibility)

    def update_visibility(self):
        for row in list(self.list_el):
            if row.get_visible():
                self.main_stack.set_visible_child_name('content')
                return
        self.main_stack.set_visible_child_name('no-content')

# dialog.py

from gi.repository import Gtk, Adw, GLib
from .selector_row import PlaylistSelectorRow
from ...integrations import get_current_integration
import re

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/dialog.ui')
class PlaylistDialog(Adw.Dialog):
    __gtype_name__ = 'NocturnePlaylistDialog'

    search_entry_el = Gtk.Template.Child()
    preferences_group_el = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    add_button_el = Gtk.Template.Child()

    def __init__(self, song_list:list):
        self.song_list = song_list
        integration = get_current_integration()
        super().__init__()
        for id in integration.getPlaylists():
            row = PlaylistSelectorRow(id)
            target_value = GLib.Variant('a{sv}', {
                'playlist': GLib.Variant('s', id),
                'songs': GLib.Variant('as', self.song_list)
            })
            row.set_action_target_value(target_value)
            self.list_el.append(row)

        if len(self.song_list) > 1:
            self.preferences_group_el.set_description(_("{} Songs").format(len(self.song_list)))
        else:
            integration.verifySong(self.song_list[0], force_update=True, use_threading=False)
            self.preferences_group_el.set_description(integration.loaded_models.get(self.song_list[0]).get_property('title'))
        self.search_changed(self.search_entry_el)

    @Gtk.Template.Callback()
    def search_changed(self, entry):
        query = entry.get_text()
        rows = list(self.list_el)[1:]
        exact_match = False

        for child in rows:
            child.set_visible(re.search(query, child.get_name(), re.IGNORECASE))
            if child.get_name().lower() == query.lower():
                exact_match = True

        self.add_button_el.set_visible((not exact_match and query) or len(rows) == 0)
        target_value = GLib.Variant('a{sv}', {
            'new_playlist': GLib.Variant('s', query),
            'songs': GLib.Variant('as', self.song_list)
        })
        self.add_button_el.set_action_target_value(target_value)
        self.add_button_el.set_action_name('app.add_songs_to_playlist')
        self.add_button_el.set_title(query or _("New Playlist"))


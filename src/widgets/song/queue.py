# queue.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from ...navidrome import get_current_integration
import threading, uuid
from datetime import timedelta

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/queue.ui')
class SongQueue(Gtk.Box):
    __gtype_name__ = 'NocturneSongQueue'

    toolbar_revealer_el = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    remove_el = Gtk.Template.Child()
    play_el = Gtk.Template.Child()
    play_next_el = Gtk.Template.Child()
    play_later_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

    def set_mode(self, playing:bool=False):
        self.remove_el.set_visible(playing)
        self.play_el.set_visible(not playing)
        self.play_next_el.set_visible(not playing)
        self.play_later_el.set_visible(not playing)

    def set_selected_mode(self, select:bool=False, selected_row:Gtk.Widget=None):
        integration = get_current_integration()
        for row in list(self.list_el):
            row.suffixes_stack_el.set_visible_child_name('select' if select else 'normal')
            row.check_el.set_active(row == selected_row)
            row.set_activatable(not select and row.id != integration.loaded_models.get('currentSong').songId)

        if select:
            self.remove_el.set_visible(selected_row.removable)
            self.play_el.set_visible(not selected_row.draggable)
            self.play_next_el.set_visible(not selected_row.draggable)
            self.play_later_el.set_visible(not selected_row.draggable)
        self.toolbar_revealer_el.set_reveal_child(select)


    def get_selected_rows(self) -> list:
        return [row for row in list(self.list_el) if row.check_el.get_active()]

    def get_all_ids(self) -> list:
        return [row.id for row in list(self.list_el)]

    @Gtk.Template.Callback()
    def close_selector(self, button):
        self.set_selected_mode()

    @Gtk.Template.Callback()
    def remove_selected(self, button):
        ''

    @Gtk.Template.Callback()
    def play_selected(self, button):
        ''

    @Gtk.Template.Callback()
    def play_next_selected(self, button):
        ''

    @Gtk.Template.Callback()
    def play_later_selected(self, button):
        ''

    @Gtk.Template.Callback()
    def add_to_playlist_selected(self, button):
        ''

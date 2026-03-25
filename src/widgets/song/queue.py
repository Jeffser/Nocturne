# queue.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from ...integrations import get_current_integration
import threading, uuid

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/queue.ui')
class SongQueue(Gtk.Box):
    __gtype_name__ = 'NocturneSongQueue'

    header_button = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    toolbar_revealer_el = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    remove_el = Gtk.Template.Child()
    play_el = Gtk.Template.Child()
    play_next_el = Gtk.Template.Child()
    play_later_el = Gtk.Template.Child()
    playlist_id:str = ""

    def set_header(self, label:str, icon_name:str, page_tag:str=None):
        self.header_button.set_tooltip_text(label)
        self.header_button.get_child().set_label(label)
        self.header_button.get_child().set_icon_name(icon_name)
        self.header_button.set_visible(True)
        if page_tag:
            self.header_button.set_action_target_value(GLib.Variant.new_string(page_tag))
            self.header_button.set_action_name('app.replace_root_page')

    def set_selected_mode(self, select:bool=False, selected_row:Gtk.Widget=None):
        integration = get_current_integration()
        for row in list(self.list_el):
            row.suffixes_stack_el.set_visible_child_name('select' if select else 'normal')
            row.check_el.set_active(row == selected_row)
            row.set_activatable(not select and row.id != integration.loaded_models.get('currentSong').get_property('songId'))

        if select:
            self.remove_el.set_visible(selected_row.removable)
            self.play_el.set_visible(not selected_row.draggable)
            self.play_next_el.set_visible(not selected_row.draggable)
            self.play_later_el.set_visible(not selected_row.draggable)
        self.toolbar_revealer_el.set_reveal_child(select)

    def get_selected_rows(self) -> list:
        return [row for row in list(self.list_el) if row.check_el.get_active()]

    def get_selected_indexes(self) -> list:
        return [i for i, row in enumerate(list(self.list_el)) if row.check_el.get_active()]

    def get_all_ids(self) -> list:
        return [row.id for row in list(self.list_el)]

    @Gtk.Template.Callback()
    def close_selector(self, button=None):
        self.set_selected_mode()

    @Gtk.Template.Callback()
    def remove_selected(self, button):
        if self.playlist_id: # is playlist
            indexes = self.get_selected_indexes()
            target_value = GLib.Variant('a{sv}', {
                'playlist': GLib.Variant('s', self.playlist_id),
                'indexes': GLib.Variant('as', [str(i) for i in indexes])
            })
            self.get_root().activate_action("app.remove_songs_from_playlist", target_value)
            for index in indexes:
                GLib.idle_add(self.list_el.remove, list(self.list_el)[index])
            def verify_visibility():
                self.main_stack.set_visible_child_name('content' if len(list(self.list_el)) > 0 else 'no-content')
            GLib.idle_add(verify_visibility)
        else:
            integration = get_current_integration()
            all_ids = self.get_all_ids()
            selected_rows = self.get_selected_rows()
            selected_ids = [r.id for r in selected_rows]
            current_id = integration.loaded_models.get('currentSong').get_property('songId')

            if current_id in selected_ids: # handle changing song
                if len(selected_rows) == len(all_ids):
                    new_id = None
                else:
                    new_id = [s for s in all_ids if s not in selected_ids][0]
                integration.loaded_models.get('currentSong').set_property('songId', new_id)
            for row in selected_rows:
                GLib.idle_add(self.list_el.remove, row)
        self.close_selector()

    @Gtk.Template.Callback()
    def play_selected(self, button):
        selected_rows = self.get_selected_rows()
        selected_ids = [r.id for r in selected_rows]
        target_value = GLib.Variant('as', selected_ids)
        self.get_root().activate_action("app.play_songs", target_value)
        self.close_selector()

    @Gtk.Template.Callback()
    def play_next_selected(self, button):
        selected_rows = self.get_selected_rows()
        selected_ids = [r.id for r in selected_rows]
        target_value = GLib.Variant('as', selected_ids)
        self.get_root().activate_action("app.play_songs_next", target_value)
        self.close_selector()

    @Gtk.Template.Callback()
    def play_later_selected(self, button):
        selected_rows = self.get_selected_rows()
        selected_ids = [r.id for r in selected_rows]
        target_value = GLib.Variant('as', selected_ids)
        self.get_root().activate_action("app.play_songs_later", target_value)
        self.close_selector()

    @Gtk.Template.Callback()
    def add_to_playlist_selected(self, button):
        selected_rows = self.get_selected_rows()
        target_value = GLib.Variant('as', [r.id for r in selected_rows])
        self.get_root().activate_action("app.prompt_add_songs_to_playlist", target_value)
        self.close_selector()

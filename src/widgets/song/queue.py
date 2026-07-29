# queue.py

from gi.repository import GObject, Gtk, GLib
from ...integrations import get_current_integration

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
    download_el = Gtk.Template.Child()
    delete_download_el = Gtk.Template.Child()
    playlist_id:str = ""
    header_label = GObject.Property(type=str, default="")
    header_icon_name = GObject.Property(type=str, default="")
    header_page_tag = GObject.Property(type=str, default="")

    def set_selected_mode(self, select:bool=False, selected_row:Gtk.Widget=None):
        integration = get_current_integration()
        for row in list(self.list_el):
            if row.__gtype_name__ != 'NocturneDiscIndicator':
                row.suffixes_stack_el.set_visible_child_name('select' if select else 'normal')
                row.check_el.set_active(row == selected_row)
                row.set_activatable(not select and row.id != integration.loaded_models.get('currentSong').get_property('songId'))

        if select:
            self.remove_el.set_visible(selected_row.removable)
            self.play_el.set_visible(not selected_row.draggable)
            self.play_next_el.set_visible(not selected_row.draggable)
            self.play_later_el.set_visible(not selected_row.draggable)
            self.delete_download_el.set_visible(integration.__gtype_name__ == 'NocturneIntegrationOffline')
            self.download_el.set_visible('no-downloads' not in integration.limitations)
        self.toolbar_revealer_el.set_reveal_child(select)

    def get_selected_rows(self) -> list:
        return [row for row in list(self.list_el) if row.__gtype_name__ != 'NocturneDiscIndicator' and row.check_el.get_active()]

    def get_selected_indexes(self) -> list:
        return [i for i, row in enumerate(list(self.list_el)) if row.__gtype_name__ != 'NocturneDiscIndicator' and row.check_el.get_active()]

    def get_all_ids(self) -> list:
        return [row.id for row in list(self.list_el) if row.__gtype_name__ != 'NocturneDiscIndicator']

    @Gtk.Template.Callback()
    def close_selector(self, button=None):
        self.set_selected_mode()

    @Gtk.Template.Callback()
    def delete_download_selected(self, button):
        selected_rows = self.get_selected_rows()
        selected_ids = [r.id for r in selected_rows]
        target_value = GLib.Variant('as', selected_ids)
        self.get_root().activate_action("app.delete_downloads", target_value)
        self.close_selector()

    @Gtk.Template.Callback()
    def download_selected(self, button):
        selected_rows = self.get_selected_rows()
        selected_ids = [r.id for r in selected_rows]
        target_value = GLib.Variant('as', selected_ids)
        self.get_root().activate_action("app.download_songs", target_value)
        self.close_selector()

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
                self.list_el.remove(list(self.list_el)[index])
            self.main_stack.set_visible_child_name('content' if len(list(self.list_el)) > 0 else 'no-content')
        else:
            integration = get_current_integration()
            queue_model = integration.loaded_models.get('currentSong').get_property('queueModel')
            all_ids = [so.get_string() for so in list(queue_model)]
            selected_rows = self.get_selected_rows()
            selected_ids = [r.id for r in selected_rows]
            current_song_id = integration.loaded_models.get('currentSong').get_property('songId')

            if current_song_id in selected_ids: # handle changing song
                if len(selected_rows) == len(all_ids):
                    new_id = None
                else:
                    new_id = [s for s in all_ids if s not in selected_ids][0]
                integration.loaded_models.get('currentSong').set_property('songId', new_id)

            indexes_to_be_removed = []
            for i, song_id in enumerate(all_ids):
                if song_id in selected_ids:
                    indexes_to_be_removed.append(i)
            for index in reversed(indexes_to_be_removed):
                queue_model.remove(index)

        self.close_selector()

    @Gtk.Template.Callback()
    def select_all(self, button):
        for row in list(self.list_el):
            row.check_el.set_active(True)

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

    @Gtk.Template.Callback()
    def handle_visible_bind(self, queue, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def handle_action_name_bind(self, carousel, value) -> str:
        return str("app.replace_root_page") if value else str("")

    @Gtk.Template.Callback()
    def handle_action_target_bind(self, carousel, value) -> GLib.Variant:
        return GLib.Variant.new_string(value or "")

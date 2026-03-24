# window.py
#
# Copyright 2026 Jeffry Samuel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject

from . import actions
from .integrations import get_current_integration
from .constants import SIDEBAR_MENU
import threading

class SidebarItem(Adw.SidebarItem):
    __gtype_name__ = 'NocturneSidebarItem'
    page_tag = GObject.Property(type=str)
    page_type = GObject.Property(type=str) #optional

@Gtk.Template(resource_path='/com/jeffser/Nocturne/window.ui')
class NocturneWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturneWindow'

    breakpoint_el = Gtk.Template.Child()
    main_navigationview = Gtk.Template.Child()
    main_bottom_sheet = Gtk.Template.Child()
    main_split_view = Gtk.Template.Child()
    sheet_split_view = Gtk.Template.Child()
    playing_page = Gtk.Template.Child()
    queue_page = Gtk.Template.Child()
    lyrics_page = Gtk.Template.Child()
    main_sidebar = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    footer = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    login_page = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def close_request(self, window):
        if not self.get_hide_on_close():
            integration = get_current_integration()
            if integration:
                id_list = self.queue_page.song_list_el.get_all_ids()
                current_song = integration.loaded_models.get('currentSong')
                integration.savePlayQueue(id_list, current_song.get_property('songId'), current_song.get_property('positionSeconds') * 1000)
            settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
            settings.set_int('default-width', self.get_width())
            settings.set_int('default-height', self.get_height())
            if self.login_page.navidrome_proc:
                self.login_page.navidrome_proc.terminate()

    @Gtk.Template.Callback()
    def on_sidebar_activated(self, sidebar, index):
        page_tag = sidebar.get_selected_item().page_tag
        page_type = sidebar.get_selected_item().page_type
        self.replace_root_page(page_tag, page_type)

    def replace_root_page(self, page_tag:str, page_type:str=None):
        page = self.main_navigationview.find_page(page_tag)
        if page:
            self.main_bottom_sheet.set_open(False)
            self.main_split_view.set_show_content(True)
            if page_type:
                page.set_property('page_type', page_type)
            threading.Thread(target=page.reload).start()
            self.main_navigationview.replace([page])

    def create_action(self, callback:callable, shortcuts:list=[], parameter_type:str="s"):
        self.get_application().create_action(
            name=callback.__name__,
            callback=lambda at, va, cb=callback, win=self: cb(win, va.unpack()) if va else cb(win),
            shortcuts=shortcuts,
            parameter_type=GLib.VariantType.new(parameter_type) if parameter_type else None
        )

    def setup_sidebar(self):
        for section in SIDEBAR_MENU:
            section_el = Adw.SidebarSection(
                title=section.get('title')
            )
            self.main_sidebar.append(section_el)
            for item in section.get('items'):
                section_el.append(SidebarItem(
                    title=item.get('title'),
                    icon_name=item.get('icon-name'),
                    page_tag=item.get('page-tag'),
                    page_type=item.get('page-type')
                ))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.create_action(actions.replace_root_page)
        self.create_action(actions.visit_url)
        self.create_action(actions.toggle_star)
        self.create_action(actions.logout, parameter_type=None)
        self.create_action(actions.show_external_file_warning, parameter_type=None)

        self.create_action(actions.play_radio)
        self.create_action(actions.add_radio, parameter_type=None)
        self.create_action(actions.update_radio)
        self.create_action(actions.delete_radio)

        self.create_action(actions.play_song)
        self.create_action(actions.play_song_next)
        self.create_action(actions.play_song_later)
        self.create_action(actions.play_songs, parameter_type="as")
        self.create_action(actions.play_songs_next, parameter_type="as")
        self.create_action(actions.play_songs_later, parameter_type="as")
        self.create_action(actions.edit_lyrics)
        self.create_action(actions.save_lyrics, parameter_type="a{sv}") # dict with string keys and any values
        self.create_action(actions.play_random_queue, parameter_type=None)

        self.create_action(actions.show_album)
        self.create_action(actions.play_album)
        self.create_action(actions.play_album_next)
        self.create_action(actions.play_album_later)
        self.create_action(actions.play_album_shuffle)

        self.create_action(actions.show_playlist)
        self.create_action(actions.play_playlist)
        self.create_action(actions.play_playlist_next)
        self.create_action(actions.play_playlist_later)
        self.create_action(actions.play_playlist_shuffle)
        self.create_action(actions.update_playlist)
        self.create_action(actions.create_playlist, parameter_type=None)
        self.create_action(actions.remove_songs_from_playlist, parameter_type="a{sv}")
        self.create_action(actions.prompt_add_songs_to_playlist, parameter_type="as")
        self.create_action(actions.add_songs_to_playlist, parameter_type="a{sv}")
        self.create_action(actions.prompt_add_song_to_playlist)
        self.create_action(actions.prompt_add_album_to_playlist)
        self.create_action(actions.delete_playlist)

        self.create_action(actions.show_artist)
        self.create_action(actions.play_shuffle_artist)
        self.create_action(actions.play_radio_artist)

        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.set_property('default-width', settings.get_value('default-width').unpack())
        self.set_property('default-height', settings.get_value('default-height').unpack())
        self.set_property('hide-on-close', settings.get_value('hide-on-close').unpack())
        settings.bind(
            "hide-on-close",
            self,
            "hide-on-close",
            Gio.SettingsBindFlags.DEFAULT
        )
        if settings.get_value('player-blur-bg').unpack():
            self.add_css_class('player-blur')

        GLib.idle_add(self.setup_sidebar)


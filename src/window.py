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

from gi.repository import Gtk, Adw, GLib, Gio, GObject, Pango

from . import actions
from .integrations import get_current_integration, models
from .constants import SIDEBAR_MENU
import threading
from datetime import datetime, timedelta

class SidebarItem(Adw.SidebarItem):
    __gtype_name__ = 'NocturneSidebarItem'
    page_tag = GObject.Property(type=str)
    playlist_id = GObject.Property(type=str) # optional

@Gtk.Template(resource_path='/com/jeffser/Nocturne/window.ui')
class NocturneWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturneWindow'

    sidebar_headerbar = Gtk.Template.Child()
    loading_label_el = Gtk.Template.Child()
    breakpoint_el = Gtk.Template.Child()
    main_navigationview = Gtk.Template.Child()
    main_bottom_sheet = Gtk.Template.Child()
    main_split_view = Gtk.Template.Child()
    sheet_split_view = Gtk.Template.Child()
    playing_page = Gtk.Template.Child()
    queue_page = Gtk.Template.Child()
    lyrics_page = Gtk.Template.Child()
    player_sidebar_splitview = Gtk.Template.Child()
    sidebar_playing_page = Gtk.Template.Child()
    sidebar_queue_page = Gtk.Template.Child()
    sidebar_lyrics_page = Gtk.Template.Child()
    main_sidebar = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    footer = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    downloads_button_el = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def close_request(self, window):
        if not self.get_hide_on_close():
            if integration := get_current_integration():
                id_list = [so.get_string() for so in integration.loaded_models.get('currentSong').get_property('queueModel')]
                current_song = integration.loaded_models.get('currentSong')

                queue_origin = current_song.get_property('queueOrigin')
                song_id = current_song.get_property('songId')
                timestamp = current_song.get_property('positionSeconds')
                if model := integration.loaded_models.get(queue_origin):
                    if isinstance(model, models.Playlist):
                        integration.savePlaylistResume(
                            queue_origin_id=queue_origin,
                            song_id=song_id,
                            current_timestamp=timestamp
                        )

                integration.savePlayQueue(id_list, song_id, timestamp * 1000)
                integration.terminate_instance()
            self.settings.set_int('default-width', self.get_width())
            self.settings.set_int('default-height', self.get_height())
            if app := self.get_application():
                if player := app.player:
                    GLib.idle_add(player.discord_rpc.close)
                    GLib.idle_add(player.mpris.quit)
                GLib.idle_add(app.quit)

    @Gtk.Template.Callback()
    def on_sidebar_activated(self, sidebar, index):
        page_tag = sidebar.get_selected_item().get_property('page_tag')
        if playlist_id := sidebar.get_selected_item().get_property('playlist_id'):
            self.activate_action("app.replace_root_page", GLib.Variant('s', 'playlists'))
            self.activate_action("app.show_playlist", GLib.Variant('s', playlist_id))
        else:
            self.replace_root_page(page_tag)

    def replace_root_page(self, page_tag:str):
        if page := self.main_navigationview.find_page(page_tag):
            self.main_bottom_sheet.set_open(False)
            self.main_split_view.set_show_content(True)
            threading.Thread(target=page.reload, daemon=True).start()
            self.main_navigationview.replace([page])

    def create_action(self, callback:callable, shortcuts:list=[], parameter_type:str="s"):
        def call_action(cb, va):
            if va is None:
                cb(self)
            else:
                cb(self, va.unpack())

        self.get_application().create_action(
            name=callback.__name__,
            callback=lambda at, va, cb=callback: threading.Thread(target=call_action, args=(cb, va), daemon=True).start(),
            shortcuts=shortcuts,
            parameter_type=GLib.VariantType.new(parameter_type) if parameter_type else None
        )

    def setup_sidebar(self):
        self.main_sidebar.remove_all()
        disabled_sections = self.settings.get_value('sidebar-disabled-sections').unpack()
        disabled_items = self.settings.get_value('sidebar-disabled-items').unpack()
        for section_id, section_data in SIDEBAR_MENU.items():
            if section_id in disabled_sections:
                if row_title := section_data.get("title"):
                    root_section = self.main_sidebar.get_sections()[0]
                    row = SidebarItem(
                        title=row_title,
                        icon_name=section_data.get("icon-name"),
                        page_tag=section_data.get("page-tag")
                    )
                    root_section.append(row)
            else:
                section_el = Adw.SidebarSection(
                    title=section_data.get('title')
                )
                append_section = False
                for item_id, item_data in section_data.get('items').items():
                    if item_id not in disabled_items:
                        if item_id == 'playlists-group':
                            threading.Thread(target=self.update_playlist_section_of_sidebar, args=(section_el,), daemon=True).start()
                        else:
                            if row_title := item_data.get("title"):
                                row = SidebarItem(
                                    title=row_title,
                                    icon_name=item_data.get("icon-name"),
                                    page_tag=item_data.get("page-tag")
                                )
                                section_el.append(row)
                                append_section = True
                if append_section:
                    self.main_sidebar.append(section_el)

    def update_loading_message(self, integration):
        message = integration.get_property("loadingMessage")
        self.loading_label_el.set_visible(message)
        self.loading_label_el.set_label(message)
        if not message:
            threading.Thread(target=self.main_navigationview.get_visible_page().reload, daemon=True).start()

    def update_playlist_section_of_sidebar(self, section_el):
        integration = get_current_integration()
        integration.connect('notify::loadingMessage', lambda integration, ud: self.update_loading_message(integration))
        if integration.get_property('loadingMessage'):
            self.update_loading_message(integration)

        def update_row_paintable(row, paintable):
            picture = Gtk.Picture(
                paintable=paintable,
                margin_top=5,
                margin_bottom=5
            )
            row.set_prefix(picture)

        for playlistId in integration.getPlaylists()[:4]:
            if model := integration.loaded_models.get(playlistId):
                item = SidebarItem(
                    page_tag="playlists",
                    playlist_id=playlistId
                )
                GLib.idle_add(section_el.append, item)
                integration.connect_to_model(playlistId, "name", lambda name, row=item: row.set_title(name))
                integration.connect_to_model(playlistId, "songCount", lambda n, row=item: row.set_subtitle(('{} Songs' if n > 1 else '{} Song').format(n)))
                #integration.connect_to_model(playlistId, "gdkPaintable", lambda paintable, row=item: update_row_paintable(row, paintable))
                #TODO: enable this once Adw 1.10 is out https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/method.SidebarItem.set_prefix.html

    def setup(self):
        # call using glib_add
        self.footer.setup()
        self.playing_page.setup()
        self.lyrics_page.setup()
        self.queue_page.setup()
        self.sidebar_playing_page.setup()
        self.sidebar_lyrics_page.setup()
        self.sidebar_queue_page.setup()
        self.downloads_button_el.setup()
        self.setup_sidebar()
        self.sidebar_playing_page.show_sidebar_el.set_visible(False)
        threading.Thread(target=self.notify_playback).start()
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', self.song_changed)

    def song_changed(self, songId:str):
        playing = bool(songId)
        if application := self.get_root().get_application():
            if playing:
                application.inhibit_suspend()
            else:
                application.uninhibit_suspend()
                if popout_window := application.popout_window:
                    popout_window.close()
        self.big_breakpoint_toggled()

    def notify_playback(self):
        # Notifies user if Nocturne Playback is ready for this month
        prev_month = datetime.now().replace(day=1) - timedelta(days=1)
        if prev_month.strftime("%m-%Y") != self.settings.get_value('last-playback-checked').unpack():
            integration = get_current_integration()
            top_songs = []
            for songId, plays in integration.getPlaybackScrobble(prev_month.strftime("%m-%Y")):
                integration.verifySong(songId, use_threading=False)
                if songId in integration.loaded_models:
                    top_songs.append((songId, plays))
            if len(top_songs) > 5:
                def response(dialog, task):
                    if dialog.choose_finish(task) == "show":
                        self.get_root().activate_action("app.launch_playback")
                dialog = Adw.AlertDialog(
                    heading=_("Nocturne Playback"),
                    body=_("Your Playback queue for {} is available!").format(prev_month.strftime("%B %Y"))
                )
                dialog.add_response("show", _("Show"))
                dialog.add_response("later", _("Later"))
                dialog.set_response_appearance("show", Adw.ResponseAppearance.SUGGESTED)
                dialog.set_default_response("show")
                GLib.idle_add(dialog.choose, self, None, response)
            self.settings.set_string('last-playback-checked', prev_month.strftime("%m-%Y"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        self.create_action(actions.show_error)
        self.create_action(actions.search, shortcuts=['<ctrl>F'], parameter_type=None)
        self.create_action(actions.launch_playback, parameter_type=None)
        self.create_action(actions.generate_auto_play_queue, parameter_type="b")
        self.create_action(actions.set_equalizer_preset)
        self.create_action(actions.replace_root_page)
        self.create_action(actions.visit_url)
        self.create_action(actions.toggle_star)
        self.create_action(actions.logout, parameter_type=None)
        self.create_action(actions.show_external_file_warning, parameter_type=None)
        self.create_action(actions.update_navidrome_server, parameter_type=None)
        self.create_action(actions.delete_navidrome_server, parameter_type=None)
        self.create_action(actions.open_popout_window, shortcuts=['<ctrl>P'], parameter_type=None)
        self.create_action(actions.toggle_fullscreen, shortcuts=['F11'], parameter_type=None)
        self.create_action(actions.set_rating, parameter_type="a{sv}") # dict with string keys and any values

        self.create_action(actions.player_toggle, shortcuts=['<ctrl>K'], parameter_type=None)
        self.create_action(actions.player_play, parameter_type=None)
        self.create_action(actions.player_pause, parameter_type=None)
        self.create_action(actions.player_next, shortcuts=['<ctrl>Right'], parameter_type=None)
        self.create_action(actions.player_previous, shortcuts=['<ctrl>Left'], parameter_type=None)
        self.create_action(actions.player_raise_volume, shortcuts=['<ctrl>Up'], parameter_type=None)
        self.create_action(actions.player_lower_volume, shortcuts=['<ctrl>Down'], parameter_type=None)

        self.create_action(actions.play_radio)
        self.create_action(actions.add_radio, parameter_type=None)
        self.create_action(actions.update_radio)
        self.create_action(actions.delete_radio)

        self.create_action(actions.play_song)
        self.create_action(actions.play_song_from_list, parameter_type="a{sv}")
        self.create_action(actions.play_song_next)
        self.create_action(actions.play_song_later)
        self.create_action(actions.play_songs, parameter_type="as")
        self.create_action(actions.play_songs_next, parameter_type="as")
        self.create_action(actions.play_songs_later, parameter_type="as")
        self.create_action(actions.edit_lyrics, parameter_type=None)
        self.create_action(actions.play_random_queue, parameter_type=None)
        self.create_action(actions.show_song_details)

        self.create_action(actions.show_album)
        self.create_action(actions.show_album_from_song)
        self.create_action(actions.play_album)
        self.create_action(actions.play_album_next)
        self.create_action(actions.play_album_later)
        self.create_action(actions.play_album_shuffle)

        self.create_action(actions.show_playlist)
        self.create_action(actions.resume_playlist)
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
        self.create_action(actions.show_artist_from_song)
        self.create_action(actions.show_artist_from_album)
        self.create_action(actions.play_shuffle_artist)
        self.create_action(actions.play_radio_artist)

        self.create_action(actions.download_song)
        self.create_action(actions.download_songs, parameter_type="as")
        self.create_action(actions.download_album)
        self.create_action(actions.download_playlist)
        self.create_action(actions.delete_download)
        self.create_action(actions.delete_downloads, parameter_type="as")

        self.set_property('default-width', self.settings.get_value('default-width').unpack())
        self.set_property('default-height', self.settings.get_value('default-height').unpack())
        self.set_property('hide-on-close', self.settings.get_value('hide-on-close').unpack())
        self.settings.bind(
            "hide-on-close",
            self,
            "hide-on-close",
            Gio.SettingsBindFlags.DEFAULT
        )

        list(list(self.sidebar_headerbar)[0])[0].get_center_widget().get_child().set_ellipsize(Pango.EllipsizeMode.NONE)

        css_settings = {
            'use-dynamic-accent': 'dynamic-accent',
            'player-blur-bg': 'player-translucent'
        }
        for key, class_name in css_settings.items():
            self.settings.connect('changed::{}'.format(key), self.css_toggled, class_name)
            self.css_toggled(self.settings, key, class_name)

        self.settings.connect('changed::global-dynamic-bg-mode', self.dynamic_bg_mode_changed, 'global-')
        self.dynamic_bg_mode_changed(self.settings, 'global-dynamic-bg-mode', 'global-')
        self.settings.connect('changed::player-dynamic-bg-mode', self.dynamic_bg_mode_changed, '')
        self.dynamic_bg_mode_changed(self.settings, 'player-dynamic-bg-mode', '')
        self.settings.connect('changed::use-sidebar-player', lambda *_: self.big_breakpoint_toggled())

    def css_toggled(self, settings, key, css_class):
        if settings.get_value(key).unpack():
            self.add_css_class(css_class)
        else:
            self.remove_css_class(css_class)

    def dynamic_bg_mode_changed(self, settings, key, prefix):
        value = settings.get_value(key).unpack()
        self.remove_css_class('{}dynamic-bg-gradient'.format(prefix))
        self.remove_css_class('{}dynamic-bg-blur'.format(prefix))
        if value:
            self.add_css_class('{}dynamic-bg-{}'.format(prefix, value))

    @Gtk.Template.Callback()
    def on_drop(self, drop_target, file, x, y):
        self.get_application().do_open([file])

    @Gtk.Template.Callback()
    def big_breakpoint_toggled(self, bp=None):
        if integration := get_current_integration():
            song_playing = bool(integration.loaded_models.get('currentSong').get_property('songId'))
        else:
            song_playing = False

        is_small = self.get_width() <= 840
        if is_small:
            self.player_sidebar_splitview.set_show_sidebar(False)
            self.main_bottom_sheet.set_reveal_bottom_bar(song_playing)
            self.main_bottom_sheet.set_can_open(song_playing)
        else:
            show_sidebar = self.settings.get_value('use-sidebar-player').unpack()
            self.player_sidebar_splitview.set_show_sidebar(show_sidebar and song_playing)
            self.main_bottom_sheet.set_reveal_bottom_bar(not show_sidebar and song_playing)
            self.main_bottom_sheet.set_can_open(not show_sidebar and song_playing)
            if show_sidebar:
                self.main_bottom_sheet.set_open(False)
        if not song_playing:
            self.main_bottom_sheet.set_open(False)

        if self.main_bottom_sheet.get_reveal_bottom_bar():
            self.add_css_class('showing-footer')
        else:
            self.remove_css_class('showing-footer')

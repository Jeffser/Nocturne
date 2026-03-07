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

from gi.repository import Gtk, Adw, GLib

from . import widgets as Widgets
from . import navidrome

import threading, ctypes
from datetime import datetime, UTC

@Gtk.Template(resource_path='/com/jeffser/Nocturne/window.ui')
class NocturneWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturneWindow'

    main_navigationview = Gtk.Template.Child()
    playing_navigationview = Gtk.Template.Child()
    home_page = Gtk.Template.Child()
    main_bottom_sheet = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def on_bottomsheet_open(self, bottomsheet, state):
        if not self.main_bottom_sheet.get_open():
            GLib.timeout_add(1000, self.playing_navigationview.replace_with_tags, ['playing'])

    def show_album(self, action, model_id:GLib.Variant):
        self.main_navigationview.push(Widgets.AlbumPage(model_id.unpack()))

    def show_artist(self, action, model_id:GLib.Variant):
        self.main_navigationview.push(Widgets.ArtistPage(model_id.unpack()))

    def show_playlist(self, action, model_id:GLib.Variant):
        self.main_navigationview.push(Widgets.PlaylistPage(model_id.unpack()))

    def toggle_star(self, action, model_id:GLib.Variant):
        model_id = model_id.unpack()
        integration = navidrome.get_current_integration()
        if model_id in integration.loaded_models:
            model = integration.loaded_models[model_id]
            if model.starred:
                if integration.unstar(model.id):
                    model.starred = None
            else:
                if integration.star(model.id):
                    model.starred = datetime.now(UTC).isoformat(timespec='microseconds').replace('+00:00', 'Z')

    def play_song(self, action, model_id:GLib.Variant):
        model_id = model_id.unpack()
        queue_page = self.playing_navigationview.find_page('queue')
        if model_id in queue_page.song_list_el.get_all_ids():
            integration = navidrome.get_current_integration()
            integration.loaded_models.get('currentSong').songId = model_id
        else:
            queue_page.replace_queue([model_id])

    def play_album(self, action, model_id:GLib.Variant):
        model_id = model_id.unpack()
        integration = navidrome.get_current_integration()
        album = integration.loaded_models.get(model_id)

        def on_update_finish():
            queue_page = self.playing_navigationview.find_page('queue')
            queue_page.replace_queue([s.get('id') for s in album.song])

        if album:
            integration.verifyAlbum(album.id, force_update=True, update_callback=on_update_finish)

    def play_playlist(self, action, model_id:GLib.Variant):
        model_id = model_id.unpack()
        integration = navidrome.get_current_integration()
        playlist = integration.loaded_models.get(model_id)

        def on_update_finish():
            queue_page = self.playing_navigationview.find_page('queue')
            queue_page.replace_queue([s.get('id') for s in playlist.entry])

        if playlist:
            integration.verifyPlaylist(playlist.id, force_update=True, update_callback=on_update_finish)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        """
        Actions to implement:

        play_artist_shuffle
        play_artist_radio
        play_album_suffle
        play_song_next
        play_song_later
        add_song_to_playlist
        add_album_to_playlist
        play_album_later
        play_album_next
        """

        self.get_application().create_action(
            name="play_song",
            callback=self.play_song,
            parameter_type=GLib.VariantType.new('s')
        )

        self.get_application().create_action(
            name="play_album",
            callback=self.play_album,
            parameter_type=GLib.VariantType.new('s')
        )

        self.get_application().create_action(
            name="play_playlist",
            callback=self.play_playlist,
            parameter_type=GLib.VariantType.new('s')
        )

        self.get_application().create_action(
            name="show_album",
            callback=self.show_album,
            parameter_type=GLib.VariantType.new('s')
        )

        self.get_application().create_action(
            name="show_artist",
            callback=self.show_artist,
            parameter_type=GLib.VariantType.new('s')
        )

        self.get_application().create_action(
            name="show_playlist",
            callback=self.show_playlist,
            parameter_type=GLib.VariantType.new('s')
        )

        self.get_application().create_action(
            name="toggle_star",
            callback=self.toggle_star,
            parameter_type=GLib.VariantType.new('s')
        )


# main.py
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

import sys, threading, logging, argparse
from pydbus import SessionBus
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Secret', '1')
gi.require_version('Gst', '1.0')
gi.require_version('Xdp', '1.0')
gi.require_version('XdpGtk4', '1.0')

from gi.repository import Gtk, Gdk, Gio, Adw, GLib
from .window import NocturneWindow
from .preferences import NocturnePreferences
from .constants import get_song_info_from_file, CLI_ARGUMENTS, TRANSLATORS, COPYRIGHT_NOTICE, set_version
from .integrations import get_current_integration, set_current_integration, get_available_integrations, models
from .widgets.playing import Player
from .widgets.pages import LoginDialog

GLib.set_prgname('com.jeffser.Nocturne')
GLib.set_application_name("Nocturne")
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(description="Nocturne has to already be running for the options to work")

class NocturneService:
    """
    <node>
        <interface name="com.jeffser.Nocturne.Service">
            <method name="Search">
                <arg type="a{sa{sv}}" name="result" direction="out"/>
                <arg type="s" name="query" direction="in"/>
            </method>
        </interface>
    </node>
    """

    def __init__(self, app):
        self.app = app

    def Search(self, query:str) -> dict:
        if integration := get_current_integration():
            results = integration.systemSearch(query)
            return results
        return {}

class NocturneApplication(Adw.Application):
    __gtype_name__ = 'NocturneApplication'
    """The main application singleton class."""

    def __init__(self, version):
        self.version = version
        self.external_songs = []
        self.main_window = None
        self.popout_window = None
        self.player = None
        self.inhibit_cookie = None
        self.idle_inhibit_cookie = None
        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        super().__init__(application_id='com.jeffser.Nocturne',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS | Gio.ApplicationFlags.HANDLES_OPEN,
                         resource_base_path='/com/jeffser/Nocturne')
        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action, ['<control>comma'])

    def inhibit_suspend(self):
        if self.inhibit_cookie is None:
            self.inhibit_cookie = self.inhibit(
                self.get_active_window(),
                Gtk.ApplicationInhibitFlags.SUSPEND,
                _("Music is Playing")
            )

    def uninhibit_suspend(self):
        if self.inhibit_cookie is not None:
            self.uninhibit(self.inhibit_cookie)
            self.inhibit_cookie = None

    def inhibit_idle(self, window=None):
        if self.idle_inhibit_cookie is None:
            self.idle_inhibit_cookie = self.inhibit(
                window or self.get_active_window(),
                Gtk.ApplicationInhibitFlags.IDLE,
                _("Fullscreen Player Active")
            )

    def uninhibit_idle(self):
        if self.idle_inhibit_cookie is not None:
            self.uninhibit(self.idle_inhibit_cookie)
            self.idle_inhibit_cookie = None

    def load_default_integration(self):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        selected_local_folder = settings.get_value("integration-library-dir").unpack()

        if selected_instance := settings.get_value("selected-instance-type").unpack():
            if integration_type := get_available_integrations().get(selected_instance):
                integration = integration_type(
                    url=settings.get_value('integration-ip').unpack(),
                    user=settings.get_value('integration-user').unpack(),
                    trustServer=settings.get_value('integration-trust-server').unpack()
                )
                directory = settings.get_value('integration-library-dir').unpack()
                if Gio.File.new_for_path(directory).query_exists():
                    integration.set_property('libraryDir', directory)
                threading.Thread(target=self.try_login, args=(integration,), daemon=True).start()
                return
        self.main_window.main_stack.set_visible_child_name('welcome')

    def try_login(self, integration):
        # call on different thread
        ping_result = integration.ping()
        if ping_result.get('status') == 'ok':
            set_current_integration(integration)
            integration.on_login()
            GLib.idle_add(self.main_window.main_stack.set_visible_child_name, "content")
            GLib.idle_add(self.main_window.setup)
            if not self.player:
                self.player = Player(self)
            settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
            default_page = settings.get_value('default-page-tag').unpack() or 'home'
            self.main_window.activate_action("app.replace_root_page", GLib.Variant('s', default_page))
            if settings.get_value("restore-session").unpack():
                threading.Thread(target=self.player.restore_play_queue, daemon=True).start()
            if dialog := self.main_window.get_visible_dialog():
                dialog.close()
        else:
            GLib.idle_add(self.main_window.main_stack.set_visible_child_name, 'welcome')
            toast = Adw.Toast(
                title=_("Login Failed"),
                action_name='app.show_error',
                action_target=GLib.Variant('s', ping_result.get('message')),
                button_label=_("Show Details")
            )
            dialog = self.main_window.get_visible_dialog()
            if not isinstance(dialog, LoginDialog):
                dialog = LoginDialog(integration)
                GLib.idle_add(dialog.present, self.main_window)
            GLib.idle_add(dialog.toast_overlay.add_toast, toast)
            GLib.idle_add(dialog.login_button_el.set_sensitive, True)

    def do_activate(self):
        if not self.main_window:
            self.main_window = NocturneWindow(application=self)
            self.load_default_integration()
        self.main_window.present()
        app_service = NocturneService(self)
        if 'linux' in sys.platform:
            bus = SessionBus()
            dbus_proxy = bus.get('org.freedesktop.DBus', '/org/freedesktop/DBus')
            if not dbus_proxy.NameHasOwner('com.jeffser.Nocturne.Service'):
                bus.publish('com.jeffser.Nocturne.Service', ('/com/jeffser/Nocturne/Service', app_service))

    def do_open(self, files, n_files=None, hint=None):
        self.external_songs = []
        integration = get_current_integration()
        for file in files:
            result_path = file.get_path()
            audio_info = get_song_info_from_file(result_path, is_external_file=True)
            audio_info['id'] = 'EXTERNAL_SONG:{}'.format(result_path)
            if audio_info:
                self.external_songs.append(models.Song(**audio_info))
                if integration:
                    integration.loaded_models[audio_info.get('id')] = self.external_songs[-1]

        if self.main_window and integration:
            target_value = GLib.Variant('as', [a.id for a in self.external_songs])
            self.main_window.activate_action('app.play_songs', target_value)
            self.external_songs = []
        else:
            self.do_activate()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(
            application_icon="com.jeffser.Nocturne",
            application_name="Nocturne",
            copyright=COPYRIGHT_NOTICE,
            developer_name="Jeffry Samuel",
            issue_url="https://github.com/Jeffser/Nocturne/issues",
            license="GPL-3.0-or-later",
            support_url="https://github.com/Jeffser/Nocturne/discussions",
            version=self.version,
            website="https://jeffser.com/nocturne",
            developers=['Jeffser https://jeffser.com'],
            designers=['Jeffser https://jeffser.com'],
            translator_credits='\n'.join(TRANSLATORS)
        )
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        NocturnePreferences().present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None, parameter_type=None):
        action = Gio.SimpleAction.new(name, parameter_type)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    logging.basicConfig(
        format="%(levelname)s\t[%(filename)s | %(funcName)s] %(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler(stream=sys.stdout)]
    )

    for group_name, group_data in CLI_ARGUMENTS.items():
        group = parser.add_argument_group(group_name)
        for argument_name, argument_data in group_data.items():
            if action_name := argument_data.get('action-name'):
                if metavar := argument_data.get('metavar'):
                    group.add_argument(argument_name, type=str, metavar=metavar, help=argument_data.get('message'), dest=action_name)
                else:
                    group.add_argument(argument_name, action='store_true', help=argument_data.get('message'), dest=action_name)
    exit = False
    try:
        args, unknown = parser.parse_known_args()
        actions_to_call = {} # action-name : value
        for action, value in vars(args).items():
            if action == 'search' and value and isinstance(value, str):
                if app_service := SessionBus().get("com.jeffser.Nocturne.Service"): # .Service cause it returns results
                    results = {}
                    for item_id, item in app_service.Search(value).items():
                        if item.get('type') not in results:
                            results[item.get('type')] = []
                        results[item.get('type')].append({
                            'display': item.get('display'),
                            'id': item_id
                        })
                    print(results)
                    exit = True
            elif value:
                actions_to_call[action] = [GLib.Variant('s', value)] if isinstance(value, str) else []
        if len(actions_to_call) > 0:
            if app_service := SessionBus().get("com.jeffser.Nocturne"):
                for action, value in actions_to_call.items():
                    print(action, value)
                    app_service["org.gtk.Actions"].Activate(action, value, {})
                    exit = True
    except Exception as e:
        logger.error(e)
        sys.exit(1)
    finally:
        if exit:
            sys.exit(0)

    logger.info(f"Nocturne version: {version}")
    set_version(version)
    return NocturneApplication(version).run(sys.argv)

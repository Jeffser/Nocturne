# login.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...integrations import secret, set_current_integration, Navidrome, Local
from ...constants import get_navidrome_path, check_if_navidrome_ready, get_navidrome_env, DEFAULT_MUSIC_DIR
from ..containers import ContextContainer
import threading, subprocess

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/login.ui')
class LoginPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneLoginPage'

    extra_menu_el = Gtk.Template.Child()
    status_page = Gtk.Template.Child()
    url_el = Gtk.Template.Child()
    user_el = Gtk.Template.Child()
    password_el = Gtk.Template.Child()
    directory_el = Gtk.Template.Child()

    link_el = Gtk.Template.Child()

    login_button_el = Gtk.Template.Child()

    def setup_page(self, integration):
        self.integration = integration
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        saved_user = settings.get_value('integration-user').unpack()
        saved_directory = settings.get_value('integration-library-dir').unpack()

        # Metadata
        metadata = self.integration.login_page_metadata
        self.status_page.set_icon_name(metadata.get('icon-name'))
        self.status_page.set_title(metadata.get('title') or _("Login"))

        # Url
        self.url_el.set_visible('url' in metadata.get('entries'))
        self.url_el.set_text(metadata.get("default-url", ""))

        # User
        self.user_el.set_visible('user' in metadata.get('entries'))
        self.user_el.set_text(saved_user)

        # Password
        self.password_el.set_visible('password' in metadata.get('entries'))
        self.password_el.set_text('')

        # Directory
        self.directory_el.set_visible('library-dir' in metadata.get('entries'))
        if Gio.File.new_for_path(saved_directory).query_exists():
            self.directory_el.set_subtitle(saved_directory)
        else:
            self.directory_el.set_subtitle("")

        # Link
        self.link_el.set_visible('link' in metadata)
        self.link_el.get_child().set_uri(metadata.get('link', ''))
        self.link_el.get_child().set_label(metadata.get('link-label', '') or metadata.get('link', ''))

        # Login Button
        self.login_button_el.set_title(metadata.get('login-label') or _("Login"))

        # Extra Menu
        self.extra_menu_el.set_visible('extra-menu' in metadata)
        self.extra_menu_el.set_tooltip_text(metadata.get('extra-menu', {}).get('title', _("Extra Menu")))
        self.extra_menu_el.get_popover().set_child(ContextContainer(metadata.get('extra-menu', {}).get('context', {}), ''))

    @Gtk.Template.Callback()
    def library_changed(self, row, gparam):
        if row.get_visible() and 'library-dir' in self.integration.login_page_metadata.get('entries'):
            self.integration.set_property('library_dir', row.get_subtitle())
            self.integration.terminate_instance()
            threading.Thread(target=self.integration.start_instance).start()

    @Gtk.Template.Callback()
    def open_local_directory(self, row):
        def response(dialog, result):
            if folder := dialog.select_folder_finish(result):
                row.set_subtitle(folder.get_path())

        initial_folder = Gio.File.new_for_path(row.get_subtitle() or DEFAULT_MUSIC_DIR)
        dialog = Gtk.FileDialog(
            title=_("Local Music Library"),
            initial_folder=initial_folder
        )
        dialog.select_folder(self.get_root(), None, response)

    @Gtk.Template.Callback()
    def go_back_clicked(self, button):
        self.integration.terminate_instance()
        GLib.idle_add(self.get_root().main_stack.set_visible_child_name, 'welcome')

    @Gtk.Template.Callback()
    def login_button_clicked(self, button=None, skip_password:bool=False):
        if button:
            button.set_sensitive(False)
        if self.url_el.get_visible():
            self.integration.set_property('url', self.url_el.get_text())
        if self.user_el.get_visible():
            self.integration.set_property('user', self.user_el.get_text())
        if self.password_el.get_visible() and not skip_password:
            secret.store_password(self.password_el.get_text())
        if self.directory_el.get_visible():
            self.integration.set_property('library_dir', self.directory_el.get_subtitle())

        def verify_login():
            if self.integration.ping():
                set_current_integration(self.integration)
                self.integration.on_login()
                GLib.idle_add(self.login_success)
            else:
                toast = Adw.Toast(title=_("Login Failed"))
                GLib.idle_add(self.get_ancestor(Adw.ToastOverlay).add_toast, toast)
                GLib.idle_add(self.get_root().main_stack.set_visible_child_name, 'login')
            if button:
                GLib.idle_add(button.set_sensitive, True)
        threading.Thread(target=verify_login).start()

    def login_success(self):
        root = self.get_root()
        root.main_stack.set_visible_child_name('content')

        root.playing_page.setup()
        root.footer.setup()
        root.lyrics_page.setup()

        threading.Thread(target=root.main_navigationview.find_page('home').reload).start()
        if Gio.Settings(schema_id="com.jeffser.Nocturne").get_value("restore-session").unpack():
            threading.Thread(target=root.playing_page.player.restore_play_queue).start()


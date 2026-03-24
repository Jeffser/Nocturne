# login.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...integrations import secret, set_current_integration, Navidrome, Local
from ...constants import get_navidrome_path, check_if_navidrome_ready, get_navidrome_env
import threading, subprocess

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/login.ui')
class LoginPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneLoginPage'

    url_el = Gtk.Template.Child()
    user_el = Gtk.Template.Child()
    password_el = Gtk.Template.Child()
    navidrome_proc = None

    def load_defaults(self, use_integrated_server:bool):
        self.use_integrated_server = use_integrated_server
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        saved_ip = settings.get_value('integration-ip').unpack()
        saved_user = settings.get_value('integration-user').unpack()
        if saved_user and saved_ip:
            GLib.idle_add(self.verify_login, saved_ip, saved_user)
        else:
            self.get_root().main_stack.set_visible_child_name('login')
        self.password_el.set_text("")
        self.url_el.set_text(saved_ip)
        self.url_el.set_visible(not self.use_integrated_server)
        self.user_el.set_text(saved_user)

        if self.use_integrated_server and not self.navidrome_proc:
            if navidrome_path := get_navidrome_path():
                navidrome_env = get_navidrome_env()
                self.navidrome_proc = subprocess.Popen([navidrome_path], env=navidrome_env)

    def verify_login(self, ip:str, user:str):
        GLib.idle_add(self.get_root().main_stack.set_visible_child_name, 'loading')
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        def run():
            integration = Navidrome(ip, user)
            self.password_el.set_text("")
            if integration.ping():
                settings.set_string('integration-ip', ip)
                settings.set_string('integration-user', user)
                settings.set_int("auto-login", 2 if self.use_integrated_server else 1)
                set_current_integration(integration)
                self.login_success()
            else:
                self.get_root().main_stack.set_visible_child_name('login')
                toast = Adw.Toast(title=_("Login Failed"))
                self.get_ancestor(Adw.ToastOverlay).add_toast(toast)

        if self.use_integrated_server:
            navidrome_env = get_navidrome_env()
            ip = "http://127.0.0.1:{}".format(navidrome_env.get('ND_PORT'))
            if navidrome_path := get_navidrome_path():
                if check_if_navidrome_ready():
                    GLib.idle_add(run)
                else:
                    dialog = Adw.AlertDialog(
                        heading=_("No User Created"),
                        body=_("You need to create a user before using the integrated instance"),
                        extra_child=Gtk.LinkButton(
                            label=ip,
                            uri=ip
                        )
                    )
                    dialog.add_response('close', _("Close"))
                    GLib.idle_add(lambda: dialog.choose(self.get_root(), None, lambda:None))
        else:
            GLib.idle_add(run)

    def login_success(self):
        root = self.get_root()
        root.main_stack.set_visible_child_name('content')

        root.playing_page.setup()
        root.footer.setup()
        root.lyrics_page.setup()

        threading.Thread(target=root.main_navigationview.find_page('home').reload).start()
        if Gio.Settings(schema_id="com.jeffser.Nocturne").get_value("restore-session").unpack():
            GLib.idle_add(root.playing_page.player.restore_play_queue)

    @Gtk.Template.Callback()
    def login_button_clicked(self, button):
        url_str = self.url_el.get_text()
        user_str = self.user_el.get_text()
        password_str = self.password_el.get_text()

        if url_str and user_str and password_str:
            secret.store_password(password_str)
            GLib.idle_add(self.verify_login, url_str, user_str)

    @Gtk.Template.Callback()
    def go_back_clicked(self, button):
        if self.navidrome_proc:
            self.navidrome_proc.terminate()
            self.navidrome_proc = None
        GLib.idle_add(self.get_root().main_stack.set_visible_child_name, 'welcome')

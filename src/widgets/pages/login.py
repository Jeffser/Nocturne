# login.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...navidrome import secret, set_current_integration, Integration
from ...constants import get_navidrome_path, check_if_navidrome_ready, get_navidrome_env
import threading, subprocess

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/login.ui')
class LoginPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneLoginPage'

    use_integrated_el = Gtk.Template.Child()
    url_el = Gtk.Template.Child()
    user_el = Gtk.Template.Child()
    password_el = Gtk.Template.Child()
    navidrome_proc = None

    def load_defaults(self):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        navidrome_path = get_navidrome_path()
        if not navidrome_path:
            settings.set_boolean("use-integrated-server", False)
        self.use_integrated_el.set_visible(navidrome_path)
        settings.bind(
            "use-integrated-server",
            self.use_integrated_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        saved_ip = settings.get_value('integration-ip').unpack()
        saved_user = settings.get_value('integration-user').unpack()
        settings.set_boolean('welcome-viewed', True)
        if saved_user and saved_ip:
            GLib.idle_add(self.verify_login, saved_ip, saved_user)
        self.password_el.set_text("")
        self.url_el.set_text(saved_ip)
        self.user_el.set_text(saved_user)

    def verify_login(self, ip:str, user:str):
        GLib.idle_add(self.get_root().main_stack.set_visible_child_name, 'loading')
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        def run():
            integration = Integration(ip, user)
            self.password_el.set_text("")
            if integration.ping():
                settings.set_string('integration-ip', ip)
                settings.set_string('integration-user', user)
                set_current_integration(integration)
                self.login_success()
            else:
                self.get_root().main_stack.set_visible_child_name('login')
                toast = Adw.Toast(title=_("Login Failed"))
                self.get_ancestor(Adw.ToastOverlay).add_toast(toast)

        if settings.get_value('use-integrated-server').unpack():
            #RUN
            # Give it half a second for the server to start
            navidrome_env = get_navidrome_env()
            ip = "http://127.0.0.1:{}".format(navidrome_env.get('ND_PORT'))
            if navidrome_path := get_navidrome_path():
                if not self.navidrome_proc:
                    self.navidrome_proc = subprocess.Popen([navidrome_path], env=navidrome_env)
                if check_if_navidrome_ready():
                    GLib.timeout_add(500, run)
                    return
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
                GLib.idle_add(self.get_root().main_stack.set_visible_child_name, 'login')
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

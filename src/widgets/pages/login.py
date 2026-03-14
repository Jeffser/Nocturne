# login.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...navidrome import secret, set_current_integration, Navidrome
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/login.ui')
class LoginPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneLoginPage'

    url_el = Gtk.Template.Child()
    user_el = Gtk.Template.Child()
    password_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        saved_ip = settings.get_value('integration-ip').unpack()
        saved_user = settings.get_value('integration-user').unpack()
        GLib.idle_add(self.verify_login, saved_ip, saved_user)
        self.url_el.set_text(saved_ip)
        self.user_el.set_text(saved_user)

    def verify_login(self, ip:str, user:str):
        integration = Navidrome(ip, user)
        if integration.ping():
            settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
            settings.set_string('integration-ip', ip)
            settings.set_string('integration-user', user)
            set_current_integration(integration)
            GLib.idle_add(self.login_success)
        else:
            GLib.idle_add(lambda: self.get_root().main_stack.set_visible_child_name('login'))

    def login_success(self):
        root = self.get_root()
        root.main_stack.set_visible_child_name('content')

        root.playing_page.setup()
        root.footer.setup()
        root.lyrics_page.setup()

        threading.Thread(target=root.main_navigationview.find_page('home').reload).start()
        root.restore_play_queue()

    @Gtk.Template.Callback()
    def login_button_clicked(self, button):
        url_str = self.url_el.get_text()
        user_str = self.user_el.get_text()
        password_str = self.password_el.get_text()

        if url_str and user_str and password_str:
            secret.store_password(user_str, url_str, password_str)
            GLib.idle_add(self.verify_login, url_str, user_str)

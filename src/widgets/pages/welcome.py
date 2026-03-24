# welcome.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...constants import get_navidrome_path
from ...integrations import set_current_integration, Local
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/welcome.ui')
class WelcomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneWelcomePage'

    def __init__(self):
        super().__init__()
        GLib.idle_add(self.check_auto_login)

    def check_auto_login(self):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        auto_login_mode = settings.get_value("auto-login").unpack()
        if auto_login_mode == 0:
            self.get_root().main_stack.set_visible_child_name('welcome')
        elif auto_login_mode == 1:
            self.get_root().login_page.load_defaults(False)
        elif auto_login_mode == 2:
            self.get_root().login_page.load_defaults(True)
        elif auto_login_mode == 3:
            self.local_clicked()


    @Gtk.Template.Callback()
    def existing_clicked(self, button):
        self.get_root().main_stack.set_visible_child_name('login')
        self.get_root().login_page.load_defaults(False)

    @Gtk.Template.Callback()
    def setup_clicked(self, button):
        if get_navidrome_path():
            self.get_root().main_stack.set_visible_child_name('login')
            self.get_root().login_page.load_defaults(True)
        else:
            self.get_root().main_stack.set_visible_child_name('setup')

    @Gtk.Template.Callback()
    def local_clicked(self, button=None):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        settings.set_int("auto-login", 3)
        def run():
            integration = Local()
            set_current_integration(integration)
            GLib.idle_add(self.get_root().login_page.login_success)
        threading.Thread(target=run).start()

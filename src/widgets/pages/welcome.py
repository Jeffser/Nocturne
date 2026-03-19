# welcome.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...constants import get_navidrome_path

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/welcome.ui')
class WelcomePage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneWelcomePage'

    def __init__(self):
        super().__init__()
        GLib.idle_add(self.check_status)

    def check_status(self):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        if get_navidrome_path() or settings.get_value('welcome-viewed').unpack():
            self.get_root().main_stack.set_visible_child_name('login')
            self.get_root().login_page.load_defaults()
        else:
            self.get_root().main_stack.set_visible_child_name('welcome')

    @Gtk.Template.Callback()
    def existing_clicked(self, button):
        self.get_root().main_stack.set_visible_child_name('login')
        self.get_root().login_page.load_defaults()

    @Gtk.Template.Callback()
    def setup_clicked(self, button):
        self.get_root().main_stack.set_visible_child_name('setup')

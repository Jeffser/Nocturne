# volume_button.py

from gi.repository import Gtk, Gio

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/volume_button.ui')
class VolumeButton(Gtk.MenuButton):
    __gtype_name__ = 'NocturneVolumeButton'

    volume_adjustment_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.bind(
            "volume",
            self.volume_adjustment_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )

    @Gtk.Template.Callback()
    def handle_icon_name_bind(self, button, value):
        if value == 0:
            return "speaker-0-symbolic"
        elif value < 0.33:
            return "speaker-1-symbolic"
        elif value < 0.66:
            return "speaker-2-symbolic"
        return "speaker-3-symbolic"

    @Gtk.Template.Callback()
    def full_volume(self, button):
        self.settings.set_double('volume', 1.0)

    @Gtk.Template.Callback()
    def mute_volume(self, button):
        self.settings.set_double('volume', 0.0)

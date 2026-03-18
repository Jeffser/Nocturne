# preferences.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject

from .navidrome import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/preferences.ui')
class NocturnePreferences(Adw.PreferencesDialog):
    __gtype_name__ = 'NocturnePreferencesDialog'

    context_button_el = Gtk.Template.Child()
    dynamic_bg_el = Gtk.Template.Child()
    restore_el = Gtk.Template.Child()

    hp_songs_el = Gtk.Template.Child()
    hp_albums_el = Gtk.Template.Child()
    hp_artists_el = Gtk.Template.Child()
    hp_playlists_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        settings = Gio.Settings.new("com.jeffser.Nocturne")

        settings.bind(
            "show-context-button",
            self.context_button_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "use-dynamic-background",
            self.dynamic_bg_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "restore-session",
            self.restore_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        settings.bind(
            "n-songs-home",
            self.hp_songs_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "n-albums-home",
            self.hp_albums_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "n-artists-home",
            self.hp_artists_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "n-playlists-home",
            self.hp_playlists_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )

    @Gtk.Template.Callback()
    def on_dynamic_bg_toggled(self, row):
        if row.get_active():
            stack_el = self.get_root().playing_page.get_ancestor(Gtk.Stack)
            stack_el.remove_css_class('dynamic-accent-bg')
        else:
            if integration := get_current_integration():
                if song_id := integration.loaded_models.get('currentSong').get_property('songId'):
                    if song_model := integration.loaded_models.get(song_id):
                        if raw_bytes := song_model.get_property('gdkPaintableBytes'):
                            thread = threading.Thread(
                                target=self.get_root().playing_page.update_palette,
                                args=(raw_bytes,)
                            )
                            GLib.idle_add(thread.start)
                            

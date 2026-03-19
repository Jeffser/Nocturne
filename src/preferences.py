# preferences.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject

from .navidrome import get_current_integration
import threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/preferences.ui')
class NocturnePreferences(Adw.PreferencesDialog):
    __gtype_name__ = 'NocturnePreferencesDialog'

    context_button_el = Gtk.Template.Child()
    dynamic_bg_el = Gtk.Template.Child()
    blur_bg_el = Gtk.Template.Child()
    restore_el = Gtk.Template.Child()

    hp_songs_el = Gtk.Template.Child()
    hp_albums_el = Gtk.Template.Child()
    hp_artists_el = Gtk.Template.Child()
    hp_playlists_el = Gtk.Template.Child()

    instance_el = Gtk.Template.Child()

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
            "player-blur-bg",
            self.blur_bg_el,
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

        if integration := get_current_integration():
            self.instance_el.set_visible(True)
            response = integration.make_request('ping')
            self.instance_el.set_title(integration.username.title())
            self.instance_el.set_action_target_value(GLib.Variant('s', integration.base_url))

            if response.get('status') == 'ok':
                self.instance_el.set_subtitle('{} | {} {}'.format(integration.base_url, response.get('type'), response.get('serverVersion')))
                self.instance_el.remove_css_class('error')
            else:
                self.instance_el.set_subtitle('{} | {}'.format(integration.base_url, _("Offline")))
                self.instance_el.add_css_class('error')
        else:
            self.instance_el.set_visible(False)


    @Gtk.Template.Callback()
    def on_dynamic_bg_toggled(self, row, gparam):
        if self.get_root():
            if row.get_active():
                if integration := get_current_integration():
                    if song_id := integration.loaded_models.get('currentSong').get_property('songId'):
                        if song_model := integration.loaded_models.get(song_id):
                            if raw_bytes := song_model.get_property('gdkPaintableBytes'):
                                thread = threading.Thread(
                                    target=self.get_root().playing_page.update_palette,
                                    args=(raw_bytes,)
                                )
                                GLib.idle_add(thread.start)
            else:
                self.get_root().remove_css_class('dynamic-accent-bg')
                            
    @Gtk.Template.Callback()
    def on_blur_bg_toggled(self, row, gparam):
        if self.get_root():
            if row.get_active():
                self.get_root().add_css_class('player-blur')
            else:
                self.get_root().remove_css_class('player-blur')

# preferences.py

from gi.repository import Gtk, Adw, GLib, Gio, Gdk, Pango

from .integrations import get_current_integration, secret
from .constants import SIDEBAR_MENU, BITRATE_OPTIONS, IN_FLATPAK, CACHE_DIR
import os, threading

@Gtk.Template(resource_path='/com/jeffser/Nocturne/preferences.ui')
class NocturnePreferences(Adw.PreferencesDialog):
    __gtype_name__ = 'NocturnePreferencesDialog'

    # General
    ## Behavior
    restore_el = Gtk.Template.Child()
    hide_on_close_el = Gtk.Template.Child()
    simulate_wbwl_el = Gtk.Template.Child()
    auto_download_lyrics_el = Gtk.Template.Child()
    use_gain_el = Gtk.Template.Child()
    default_page_el = Gtk.Template.Child()
    bitrate_el = Gtk.Template.Child()

    ## Gnome Search
    gnome_search_group_el = Gtk.Template.Child()
    gnome_search_artists_el = Gtk.Template.Child()
    gnome_search_albums_el = Gtk.Template.Child()
    gnome_search_songs_el = Gtk.Template.Child()
    gnome_search_playlists_el = Gtk.Template.Child()

    ## Session
    session_group_el = Gtk.Template.Child()
    listenbrainz_stack_el = Gtk.Template.Child()
    instance_avatar_el = Gtk.Template.Child()
    instance_icon_el = Gtk.Template.Child()
    instance_el = Gtk.Template.Child()
    discord_rpc_el = Gtk.Template.Child()
    discord_coverart_share_el = Gtk.Template.Child()

    # Customization
    ## Interface
    context_button_el = Gtk.Template.Child()
    context_label_el = Gtk.Template.Child()
    footer_big_mode_el = Gtk.Template.Child()
    translucent_player_el = Gtk.Template.Child()
    use_sidebar_player_el = Gtk.Template.Child()
    hide_singles_el = Gtk.Template.Child()
    button_size_el = Gtk.Template.Child()

    ## Dynamic Background
    global_dynamic_bg_el = Gtk.Template.Child()
    player_dynamic_bg_el = Gtk.Template.Child()
    popout_dynamic_bg_el = Gtk.Template.Child()
    dynamic_accent_el = Gtk.Template.Child()

    ## Homepage
    hp_frequent_albums_el = Gtk.Template.Child()
    hp_songs_el = Gtk.Template.Child()
    hp_albums_el = Gtk.Template.Child()
    hp_artists_el = Gtk.Template.Child()
    hp_playlists_el = Gtk.Template.Child()

    ## Sidebar
    sidebar_group = Gtk.Template.Child()

    # Visualizer
    ## Preferences
    visualizer_el = Gtk.Template.Child()

    ## Appearance
    visualizer_bar_n_el = Gtk.Template.Child()
    visualizer_type_el = Gtk.Template.Child()
    visualizer_fill_el = Gtk.Template.Child()

    ## Color
    visualizer_auto_color_el = Gtk.Template.Child()
    visualizer_invert_auto_color_el = Gtk.Template.Child()
    visualizer_manual_color_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        integration = get_current_integration()

        # General
        ## Behavior
        settings.bind(
            "restore-session",
            self.restore_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "hide-on-close",
            self.hide_on_close_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "simulate-word-by-word-lyrics",
            self.simulate_wbwl_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "auto-download-lyrics",
            self.auto_download_lyrics_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "use-gain",
            self.use_gain_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        self.default_page_dict = {}
        selected_page = settings.get_value('default-page-tag').unpack()
        for section in SIDEBAR_MENU:
            for item in section.get('items', []):
                if section.get('title') and item.get('page-tag') != "radios":
                    title = '{} ({})'.format(section.get('title'), item.get('title'))
                else:
                    title = item.get('title')
                self.default_page_dict[title] = item.get('page-tag')
                self.default_page_el.get_model().append(title)
                if item.get('page-tag') == selected_page:
                    self.default_page_el.set_selected(len(self.default_page_dict) - 1)
        self.max_bitrate_dict = {}
        selected_bitrate = settings.get_value('max-bitrate').unpack()
        for title, kbps in BITRATE_OPTIONS.items():
            if kbps != 0:
                title = title.format('{} kbps'.format(kbps))
            self.max_bitrate_dict[title] = kbps
            self.bitrate_el.get_model().append(title)
            if kbps == selected_bitrate:
                self.bitrate_el.set_selected(len(self.max_bitrate_dict) - 1)
        if integration:
            self.bitrate_el.set_visible('no-max-bitrate' not in integration.limitations)
        else:
            self.bitrate_el.set_visible(False)

        ## Gnome Search
        self.gnome_search_group_el.set_visible("GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper())
        settings.bind(
            "gnome-search-include-artists",
            self.gnome_search_artists_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "gnome-search-include-albums",
            self.gnome_search_albums_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "gnome-search-include-songs",
            self.gnome_search_songs_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "gnome-search-include-playlists",
            self.gnome_search_playlists_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        ## Session
        settings.bind(
            "discord-rpc-enabled",
            self.discord_rpc_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "discord-instance-art-share",
            self.discord_coverart_share_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        ### Check Flatpak permissions (Discord)
        if IN_FLATPAK:
            settings.connect("changed::discord-rpc-enabled", self.show_discord_flatpak_warning)
            GLib.idle_add(self.show_discord_flatpak_warning, settings, "discord-rpc-enabled")

        self.listenbrainz_stack_el.set_visible_child_name("unlink" if secret.get_plain_password(schema_type="listenbrainz") else "link")

        ### Instance Row
        self.session_group_el.set_visible(integration)
        self.instance_el.set_visible(False)
        threading.Thread(target=self.update_instance_row).start()

        # Customization
        ## Interface
        settings.bind(
            "show-context-button",
            self.context_button_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "show-context-button-label",
            self.context_label_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "use-big-footer",
            self.footer_big_mode_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "player-blur-bg",
            self.translucent_player_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "use-sidebar-player",
            self.use_sidebar_player_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "hide-singles",
            self.hide_singles_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "button-size",
            self.button_size_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )

        ## Dynamic Background
        settings.bind(
            "global-dynamic-bg-mode",
            self.global_dynamic_bg_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "player-dynamic-bg-mode",
            self.player_dynamic_bg_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "popout-dynamic-bg-mode",
            self.popout_dynamic_bg_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "use-dynamic-accent",
            self.dynamic_accent_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        ## Homepage
        settings.bind(
            "n-frequent-albums-home",
            self.hp_frequent_albums_el,
            "value",
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

        ## Sidebar
        disabled_pages = settings.get_value('sidebar-disabled-pages').unpack()
        for section in SIDEBAR_MENU:
            section_expander = None
            if section.get("title"):
                section_expander = Adw.ExpanderRow(
                    title=section.get("title")
                )
                self.sidebar_group.add(section_expander)

            for item in section.get('items', []):
                if item.get('page-tag') != 'home':
                    row = Adw.SwitchRow(
                        title=item.get("title"),
                        active=item.get("page-tag") not in disabled_pages,
                        name=item.get("page-tag")
                    )
                    row.connect('notify::active', self.sidebar_item_toggled)
                    if item.get("icon-name"):
                        row.add_prefix(
                            Gtk.Image(icon_name=item.get("icon-name"))
                        )
                    if section_expander:
                        section_expander.add_row(row)
                    else:
                        self.sidebar_group.add(row)

        # Visualizer
        ## Preferences
        settings.bind(
            "show-visualizer",
            self.visualizer_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )

        ## Appearance
        settings.bind(
            "visualizer-bar-n",
            self.visualizer_bar_n_el,
            "value",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "visualizer-type",
            self.visualizer_type_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "visualizer-fill-mode",
            self.visualizer_fill_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )

        ## Color
        settings.bind(
            "visualizer-auto-color",
            self.visualizer_auto_color_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        settings.bind(
            "visualizer-auto-color-invert",
            self.visualizer_invert_auto_color_el,
            "active",
            Gio.SettingsBindFlags.DEFAULT
        )
        try:
            rgb_str = settings.get_value('visualizer-manual-color').unpack()
            rgb_list = [float(c) for c in rgb_str.split(',')]
        except:
            rgb_list = [0.11, 0.44, 0.85]
        self.visualizer_manual_color_el.set_rgba(Gdk.RGBA(
            red=rgb_list[0],
            green=rgb_list[1],
            blue=rgb_list[2],
            alpha=1
        ))

    def update_instance_row(self):
        if integration := get_current_integration():
            data = integration.getServerInformation()
            GLib.idle_add(self.instance_el.set_title, data.get('username', ""))

            GLib.idle_add(self.instance_el.set_subtitle, data.get('title', ""))

            GLib.idle_add(self.instance_el.set_tooltip_text, data.get('link'))
            GLib.idle_add(self.instance_el.set_action_target_value, GLib.Variant('s', data.get('link', '')))
            GLib.idle_add(self.instance_icon_el.set_visible, data.get('link'))
            GLib.idle_add(self.instance_el.set_activatable, data.get('link'))

            GLib.idle_add(self.instance_avatar_el.set_custom_image, data.get('picture'))
            GLib.idle_add(self.instance_avatar_el.set_text, data.get('username', ''))
            GLib.idle_add(self.instance_el.set_visible, data)

    @Gtk.Template.Callback()
    def default_page_changed(self, combo_row, ud):
        page_tag = self.default_page_dict.get(combo_row.get_selected_item().get_string(), 'home')
        Gio.Settings(schema_id="com.jeffser.Nocturne").set_string('default-page-tag', page_tag)

    @Gtk.Template.Callback()
    def max_bitrate_changed(self, combo_row, ud):
        bitrate = self.max_bitrate_dict.get(combo_row.get_selected_item().get_string(), 0)
        Gio.Settings(schema_id="com.jeffser.Nocturne").set_int('max-bitrate', bitrate)

    @Gtk.Template.Callback()
    def visualizer_manual_color_changed(self, btn, ud):
        rgb = ','.join([str(round(c, 3)) for c in list(btn.get_rgba())[:-1]])
        Gio.Settings(schema_id="com.jeffser.Nocturne").set_string('visualizer-manual-color', rgb)

    @Gtk.Template.Callback()
    def listenbrainz_link_requested(self, button):
        def on_response(dialog, result, token_entry_el):
            response = dialog.choose_finish(result)
            if response == "save":
                if token := token_entry_el.get_text():
                    secret.store_password(
                        token,
                        schema_type="listenbrainz"
                    )
                    self.listenbrainz_stack_el.set_visible_child_name("unlink")

        container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10
        )
        container.append(Gtk.LinkButton(
            label=_("Settings Page"),
            uri="https://listenbrainz.org/settings/"
        ))
        token_el = Gtk.Entry(placeholder_text=_("User Token"))
        container.append(token_el)

        dialog = Adw.AlertDialog(
            heading=_("Link ListenBrainz"),
            body=_("Connect your ListenBrainz account with a user token"),
            extra_child=container
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("save", _("Save"))
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        dialog.choose(
            self.get_root(),
            None,
            on_response,
            token_el
        )

    @Gtk.Template.Callback()
    def listenbrainz_unlink_requested(self, button):
        secret.remove_password(
            schema_type="listenbrainz",
            callback=lambda: self.listenbrainz_stack_el.set_visible_child_name("link")
        )

    @Gtk.Template.Callback()
    def delete_image_cache_requested(self, button):
        db_path = os.path.join(CACHE_DIR, 'cache_database.db')
        if os.path.isfile(db_path):
            os.remove(db_path)
        button.set_end_icon_name('check-plain-symbolic')
        button.set_sensitive(False)

    def sidebar_item_toggled(self, row, gp):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        enabled_pages = settings.get_value('sidebar-disabled-pages').unpack()
        name = row.get_name()
        if not row.get_active():
            if name not in enabled_pages:
                enabled_pages.append(name)
        else:
            if name in enabled_pages:
                enabled_pages.remove(name)
        settings.set_value('sidebar-disabled-pages', GLib.Variant('as', enabled_pages))
        if main_window := self.get_root().get_application().main_window:
            GLib.idle_add(main_window.setup_sidebar)

    def show_discord_flatpak_warning(self, settings, key):
        if settings.get_value(key).unpack():
            directory = os.environ.get("XDG_RUNTIME_DIR")
            if 'discord-ipc-0' not in os.listdir(directory):
                dialog = Adw.AlertDialog(
                    heading=_("Flatpak Sandbox Warning"),
                    body=_("To connect to Discord, an additional permission is required, once you run the following command, please restart Nocturne"),
                    extra_child=Gtk.Label(
                        label='sudo flatpak override com.jeffser.Nocturne --filesystem=xdg-run/discord-ipc-0',
                        css_classes=['rounded-corner', 'osd', 'p10'],
                        selectable=True,
                        wrap=True,
                        wrap_mode=Pango.WrapMode.WORD
                    )
                )
                dialog.add_response('c', _("Close"))
                dialog.choose(self.get_root(), None, lambda *_, st=settings, ky=key: st.set_boolean(ky, False))


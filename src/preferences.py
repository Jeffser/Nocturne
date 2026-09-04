# preferences.py

from gi.repository import GObject, Gtk, Adw, GLib, Gio, Gdk, Pango, Xdp, XdpGtk4

from .integrations import get_current_integration, secret
from .constants import SIDEBAR_MENU, BITRATE_OPTIONS, IN_FLATPAK, CACHE_DIR, DATA_DIR
import os, threading, shutil

# Handles sections and items of sidebar
class NocturneSidebarPreferencesExpanderRow(Adw.ExpanderRow):
    __gtype_name__ = 'NocturneSidebarPreferencesExpanderRow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.toggle_group = Adw.ToggleGroup(
            valign=Gtk.Align.CENTER
        )
        self.toggle_group.add(
            Adw.Toggle(
                label=_("Item"),
                name="item",
                tooltip=_("Item")
            )
        )
        self.toggle_group.add(
            Adw.Toggle(
                label=_("Section"),
                name="section",
                tooltip=_("Section")
            )
        )
        self.add_suffix(self.toggle_group)
        self.bind_property(
            'enable-expansion',
            self.toggle_group,
            "active-name",
            GObject.BindingFlags.SYNC_CREATE,
            lambda bind, value: "section" if value else "item"
        )
        self.toggle_group.bind_property(
            'active-name',
            self,
            "enable-expansion",
            GObject.BindingFlags.SYNC_CREATE,
            lambda bind, value: value == "section"
        )
        self.connect('notify::enable-expansion', self.section_toggled)

    def add_row(self, row):
        row.connect("notify::active", self.item_toggled)
        super().add_row(row)

    def item_toggled(self, row, gparam):
        active = row.get_active()
        name = row.get_name()
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        disabled_items = settings.get_value('sidebar-disabled-items').unpack()
        if active and name in disabled_items:
            disabled_items.remove(name)
        elif not active and name not in disabled_items:
            disabled_items.append(name)
        settings.set_value('sidebar-disabled-items', GLib.Variant('as', disabled_items))
        if main_window := self.get_root().get_application().main_window:
            GLib.idle_add(main_window.setup_sidebar)

    def section_toggled(self, row, gparam):
        active = row.get_enable_expansion()
        name = row.get_name()
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        disabled_sections = settings.get_value('sidebar-disabled-sections').unpack()
        if active and name in disabled_sections:
            disabled_sections.remove(name)
        elif not active and name not in disabled_sections:
            disabled_sections.append(name)
        settings.set_value('sidebar-disabled-sections', GLib.Variant('as', disabled_sections))
        if main_window := self.get_root().get_application().main_window:
            GLib.idle_add(main_window.setup_sidebar)

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
    library_combo_el = Gtk.Template.Child()
    library_expander_el = Gtk.Template.Child()
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
    home_mode_el = Gtk.Template.Child()
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
        for section in SIDEBAR_MENU.values():
            for item in section.get('items', []).values():
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

        ### Library Row
        self.library_list = []
        self.library_combo_el.set_visible(False)
        self.library_expander_el.set_visible(False)
        threading.Thread(target=self.append_library_row).start()

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
            "welcome-mode-home",
            self.home_mode_el,
            "active-name",
            Gio.SettingsBindFlags.DEFAULT
        )
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
        disabled_sections = settings.get_value('sidebar-disabled-sections').unpack()
        disabled_items = settings.get_value('sidebar-disabled-items').unpack()

        for section_id, section_data in SIDEBAR_MENU.items():
            if section_id != 'root':
                section_expander = NocturneSidebarPreferencesExpanderRow(
                    title=section_data.get("title"),
                    enable_expansion=section_id not in disabled_sections,
                    name=section_id
                )
                self.sidebar_group.add(section_expander)
                for item_id, item_data in section_data.get('items', {}).items():
                    row = Adw.SwitchRow(
                        title=item_data.get("title"),
                        active=item_id not in disabled_items,
                        name=item_id
                    )
                    if icon_name := item_data.get("icon-name"):
                        row.add_prefix(
                            Gtk.Image(icon_name=icon_name)
                        )
                    section_expander.add_row(row)

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

    def append_library_row(self):
        if integration := get_current_integration():
            self.library_list, multiselect = integration.getLibraries()
            if len(self.library_list) > 1 and multiselect:
                    self.show_library_expander_row()
            elif self.library_list and not multiselect:
                    self.show_library_combo_row()

    def show_library_expander_row(self):
        stored_ids = Gio.Settings(schema_id="com.jeffser.Nocturne").get_strv("library-ids")
        for library in self.library_list:
            switch_row = Adw.SwitchRow(
                title=library["name"],
                active=library["id"] in stored_ids
            )
            switch_row.connect("notify::active", self.library_switch_toggled, library["id"])
            self.library_expander_el.add_row(switch_row)
        self.library_expander_el.set_visible(True)

    def library_switch_toggled(self, switch_row, _, library_id):
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        library_ids = settings.get_strv("library-ids")

        on = switch_row.get_active()
        library_ids.append(library_id) if on else library_ids.remove(library_id)
        settings.set_strv("library-ids", library_ids)
        self.get_root().activate_action("app.reset_window")

    def show_library_combo_row(self):
        gtk_list = Gtk.StringList.new([library["name"] for library in self.library_list])
        GLib.idle_add(self.library_combo_el.set_model, gtk_list)

        library_ids = Gio.Settings(schema_id="com.jeffser.Nocturne").get_strv("library-ids")
        if library_ids:
            stored_id = library_ids[0]
            index = next((i for i, library in enumerate(self.library_list) if library["id"] == stored_id), 0)
            GLib.idle_add(self.library_combo_el.set_selected, index)
        GLib.idle_add(self.library_combo_el.set_visible, True)

    @Gtk.Template.Callback()
    def library_combo_changed(self, combo_row, ud):
        if not combo_row.get_mapped(): #prevent combo row creation from changing library
            return
        index = combo_row.get_selected()
        selected_id = self.library_list[index].get("id")
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        library_ids = settings.get_strv("library-ids")
        stored_id = library_ids[0] if library_ids else ""
        if combo_row.get_model() and selected_id != stored_id:
            settings.set_strv("library-ids", [selected_id])
            self.get_root().activate_action("app.reset_window")

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

    @Gtk.Template.Callback()
    def home_mode_changed(self, toggle_group, gparam):
        root = self.get_root()
        if not root:
            return
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        home_mode = self.home_mode_el.get_active_name()
        pfp_destination_path = os.path.join(DATA_DIR, 'pfp')
        if os.path.isfile(pfp_destination_path):
            os.remove(pfp_destination_path)
        settings.set_string("welcome-user-home", "")

        def on_portal_response(portal, response):
            try:
                if result := portal.get_user_information_finish(response):
                    settings.set_string("welcome-user-home", result["name"])
                    shutil.copy2(result["image"].removeprefix('file://'), pfp_destination_path)
            except:
                self.home_mode_el.set_active_name('')

        def instance_information_run():
            try:
                integration = get_current_integration()
                data = integration.getServerInformation()
                if username := data.get('username'):
                    settings.set_string("welcome-user-home", username)
                    if profile_picture := data.get('picture'):
                        profile_picture.save_to_png(pfp_destination_path)
                else:
                    self.home_mode_el.set_active_name('')
            except:
                self.home_mode_el.set_active_name('')

        if home_mode == 'system':
            portal = Xdp.Portal()
            portal.get_user_information(
                XdpGtk4.parent_new_gtk(root), "", Xdp.UserInformationFlags.NONE, None, on_portal_response
            )
        elif home_mode == 'instance':
            threading.Thread(target=instance_information_run).run()

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


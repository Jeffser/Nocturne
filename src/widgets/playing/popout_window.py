# popout_window.py

from gi.repository import Gtk, Adw, GLib, Gio
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/popout_window.ui')
class PopoutWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturnePopoutWindow'

    toolbarview = Gtk.Template.Child()
    header_view_switcher = Gtk.Template.Child()
    breakpoint_el = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    playing_page = Gtk.Template.Child()
    lyrics_page = Gtk.Template.Child()
    queue_page = Gtk.Template.Child()
    footer = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    footer_spectrum_el = Gtk.Template.Child()

    fullscreen_btn = None

    def __init__(self, application, fullscreened):
        super().__init__(
            application=application,
            fullscreened=fullscreened
        )

        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        self.playing_page.last_song_id = current_song_id

        GLib.idle_add(self.playing_page.setup)
        GLib.idle_add(self.lyrics_page.setup)
        GLib.idle_add(self.footer.setup)
        GLib.idle_add(self.queue_page.setup)

        self.playing_page.header_bar.get_ancestor(Adw.ToolbarView).set_extend_content_to_top_edge(False)
        self.playing_page.header_bar.set_show_start_title_buttons(True)
        self.playing_page.header_bar.set_show_end_title_buttons(True)

        self.footer.set_property('forceHugeMode', True)

        self.fullscreen_btn = Gtk.Button(
            icon_name="view-fullscreen-symbolic",
            tooltip_text=_("Toggle Fullscreen")
        )
        self.fullscreen_btn.connect('clicked', self.toggle_fullscreen)
        self.playing_page.header_bar.pack_start(self.fullscreen_btn)
        self.footer_spectrum_el.setup()

        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        self.settings.connect('changed::popout-dynamic-bg-mode', self.dynamic_bg_mode_changed)
        self.dynamic_bg_mode_changed(self.settings, 'popout-dynamic-bg-mode')
        self.settings.connect('changed::use-dynamic-accent', self.css_toggled, 'dynamic-accent')
        self.css_toggled(self.settings, 'use-dynamic-accent', 'dynamic-accent')
        self.playing_page.cover_art_el.view_stack_el.connect('notify::visible-child-name', self.cover_art_mode_toggled)

    def cover_art_mode_toggled(self, view_stack, gparam):
        mode = view_stack.get_visible_child_name()
        self.playing_page.clamp.set_maximum_size(1920 if mode == 'video' else 720)

    def css_toggled(self, settings, key, css_class):
        if settings.get_value(key).unpack():
            self.add_css_class(css_class)
        else:
            self.remove_css_class(css_class)

    def dynamic_bg_mode_changed(self, settings, key):
        value = settings.get_value(key).unpack()
        self.remove_css_class('dynamic-bg-gradient')
        self.remove_css_class('dynamic-bg-blur')
        if value:
            self.add_css_class('dynamic-bg-{}'.format(value))

    @Gtk.Template.Callback()
    def close_request(self, window):
        if application := self.get_application():
            application.uninhibit_idle()
        if self.get_application().main_window.get_hide_on_close():
            self.get_application().main_window.present()

    def toggle_fullscreen(self, button):
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    @Gtk.Template.Callback()
    def big_mode_apply(self, breakpoint_el):
        self.add_css_class('big-mode')

    @Gtk.Template.Callback()
    def big_mode_unapply(self, breakpoint_el):
        self.remove_css_class('big-mode')

    @Gtk.Template.Callback()
    def fullscreen_toggled(self, window, gparam):
        fullscreen = window.is_fullscreen()
        if self.fullscreen_btn:
            self.fullscreen_btn.set_icon_name('view-unfullscreen-symbolic' if fullscreen else 'view-fullscreen-symbolic')
        if application := self.get_application():
            if fullscreen:
                application.inhibit_idle(self)
            else:
                application.uninhibit_idle()

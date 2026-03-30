# popout_window.py

from gi.repository import Gtk, Adw, GLib, Gst, Gio, GObject
from . import PlayingControlPage
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/popout_window.ui')
class PopoutWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NocturnePopoutWindow'

    breakpoint_el = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    playing_page = Gtk.Template.Child()
    lyrics_page = Gtk.Template.Child()
    queue_page = Gtk.Template.Child()
    footer = Gtk.Template.Child()
    fullscreen_btn = None

    def __init__(self, application, player, queue_list_el):
        super().__init__(
            application=application
        )

        integration = get_current_integration()
        current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
        self.playing_page.last_song_id = current_song_id
        self.playing_page.pop_status_stack.set_visible_child_name("popin")

        GLib.idle_add(self.playing_page.setup, player)
        GLib.idle_add(self.lyrics_page.setup)
        GLib.idle_add(self.footer.setup)

        self.queue_page.replace_list_element(queue_list_el)
        self.playing_page.header_bar.set_show_start_title_buttons(True)
        self.playing_page.header_bar.set_show_end_title_buttons(True)

        self.footer.cover_el.set_size_request(100, 100)
        self.footer.cover_el.set_pixel_size(100)
        self.footer.title_el.set_lines(2)
        self.footer.title_el.get_ancestor(Gtk.Box).set_spacing(10)
        self.footer.progress_el.set_visible(False)
        self.footer_scale = Gtk.Scale(
            adjustment=Gtk.Adjustment(
                lower=0,
                upper=1,
                value=0
            ),
            css_classes=["p0"]
        )
        self.footer_scale.get_adjustment().connect("value-changed", self.playing_page.progress_bar_changed)
        footer_scale_controller = Gtk.GestureClick()
        footer_scale_controller.connect("pressed", self.playing_page.seek_start)
        footer_scale_controller.connect("stopped", self.playing_page.seek_end)
        self.footer_scale.add_controller(footer_scale_controller)
        self.footer.detail_container.append(self.footer_scale)
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.footer_scale.set_value)

        self.fullscreen_btn = Gtk.Button(
            icon_name="view-fullscreen-symbolic",
            tooltip_text=_("Toggle Fullscreen")
        )
        self.fullscreen_btn.connect('clicked', self.toggle_fullscreen)
        self.playing_page.header_bar.pack_start(self.fullscreen_btn)

    @Gtk.Template.Callback()
    def close_request(self, window):
        self.get_root().activate_action("app.close_popout_window")

    @Gtk.Template.Callback()
    def fullscreen_toggled(self, window, gparam):
        if button := self.fullscreen_btn:
            button.set_icon_name("view-unfullscreen-symbolic" if window.is_fullscreen() else "view-fullscreen-symbolic")

    def toggle_fullscreen(self, button):
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    def song_changed(self, id:str):
        integration = get_current_integration()
        if model := integration.loaded_models.get(id):
            self.footer_scale.get_adjustment().set_upper(model.get_property('duration'))
            self.set_title(model.get_property('title'))


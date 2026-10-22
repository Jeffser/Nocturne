# control_page.py

from gi.repository import Gtk, Adw, GLib, Gst, GObject
from ...constants import get_display_time
from urllib.parse import urlparse

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/control_page.ui')
class PlayingControlPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlayingControlPage'

    extra_widget = GObject.Property(type=Gtk.Widget)

    header_bar = Gtk.Template.Child()
    clamp = Gtk.Template.Child()
    main_container = Gtk.Template.Child()
    cover_art_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    radio_homepage_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    album_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    positive_progress_el = Gtk.Template.Child()
    negative_progress_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    show_sidebar_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    rating_button = Gtk.Template.Child()
    rating_container = Gtk.Template.Child()
    breakpoint_state = False

    def setup(self):
        self.cover_art_el.setup()
        self.setup_sidebar_button_connection()
        if stack := self.get_ancestor(Gtk.Stack):
            stack.get_parent().set_overflow(Gtk.Overflow.HIDDEN)
            if stack2 := stack.get_parent().get_parent():
                stack2.get_parent().set_overflow(Gtk.Overflow.HIDDEN)

    @Gtk.Template.Callback()
    def format_progress_label(self, obj, positionSeconds:float, durationSeconds:float, is_negative:bool) -> str:
        if is_negative:
            return '-{}'.format(get_display_time(durationSeconds - positionSeconds))
        return get_display_time(positionSeconds)

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant:str) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_to_bool(self, obj, value, inverse:bool) -> bool:
        return bool(value) != inverse

    def breakpoint_toggled(self, active:bool):
        self.breakpoint_state = active
        if isinstance(self.get_parent(), Adw.NavigationView) and not self.get_parent().get_vhomogeneous():
            self.get_parent().set_vhomogeneous(True)

    def setup_sidebar_button_connection(self):
        if root := self.get_root():
            root.breakpoint_el.connect('apply', lambda *_: self.breakpoint_toggled(True))
            root.breakpoint_el.connect('unapply', lambda *_: self.breakpoint_toggled(False))
            if width := root.get_width():
                self.breakpoint_toggled(width <= 620)

    @Gtk.Template.Callback()
    def progress_bar_changed(self, scale_el, scroll_type, value):
        def change_time(player, val):
            player.set_property('seeking', False)
            nanoseconds = int(val * Gst.SECOND)
            self.get_root().get_application().player.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )
            player.set_property('positionSeconds', val)

        if root := self.get_root():
            if app := root.get_application():
                if player := app.get_property('player'):
                    value = scale_el.get_adjustment().get_value()
                    player.set_property('seeking', True)
                    GLib.timeout_add(500, lambda v=value, p=player: change_time(p, v) if v == scale_el.get_adjustment().get_value() else None)

    @Gtk.Template.Callback()
    def show_content_clicked(self, button):
        if view := self.get_ancestor(Adw.NavigationSplitView):
            if self.breakpoint_state:
                view.set_show_content(True)
            else:
                view.set_collapsed(not view.get_collapsed())

    @Gtk.Template.Callback()
    def change_rating(self, button):
        if root := self.get_root():
            if app := root.get_application():
                if player := app.get_property('player'):
                    target_value = GLib.Variant('a{sv}', {
                        'model_id': GLib.Variant('s', player.get_property('songId')),
                        'rating': GLib.Variant('i', int(button.get_name()))
                    })
                    root.activate_action("app.set_rating", target_value)

    @Gtk.Template.Callback()
    def format_radio_homepage(self, obj, radioStreamUrl:str, return_variant:bool) -> GLib.Variant | str:
        homepage_url = ""
        if radioStreamUrl:
            stream_url = urlparse(radioStreamUrl)
            homepage_url = '{}://{}'.format(stream_url.scheme, stream_url.netloc)
        if return_variant:
            return GLib.Variant('s', homepage_url)
        else:
            return homepage_url

    @Gtk.Template.Callback()
    def format_all_false(self, obj, *values) -> bool:
        # returns true if all values are false
        return not all([bool(value) for value in values])

    @Gtk.Template.Callback()
    def format_rating_icon_name(self, obj, rating:int, index):
        return "starred-symbolic" if rating >= index else "non-starred-symbolic"

    @Gtk.Template.Callback()
    def format_starred_icon_name(self, obj, starred:bool) -> str:
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
        return "heart-filled-symbolic" if starred else "heart-outline-thick-symbolic"

    @Gtk.Template.Callback()
    def format_show_artist(self, obj, value) -> str:
        return "" if bool(value) else "app.show_artist"

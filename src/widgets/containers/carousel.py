# carousel.py

from gi.repository import GObject, Gtk, GLib, Gdk

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/carousel.ui')
class Carousel(Gtk.Box):
    __gtype_name__ = 'NocturneCarousel'

    header_button = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    pan_container_el = Gtk.Template.Child()
    pan_start_el = Gtk.Template.Child()
    pan_end_el = Gtk.Template.Child()
    header_label = GObject.Property(type=str, default="")
    header_icon_name = GObject.Property(type=str, default="")
    header_page_tag = GObject.Property(type=str, default="")

    def remove_all(self):
        for page in list(self.list_el):
            self.list_el.remove(page)

    def set_widgets(self, widgets:list):
        def scroll_to_middle():
            if self.list_el.get_n_pages() > 0:
                middle_index = int((self.list_el.get_n_pages()-1)/2)
                page = self.list_el.get_nth_page(max(0, middle_index))
                if page:
                    self.list_el.scroll_to(page, True)

        GLib.idle_add(self.set_visible, len(widgets) > 0)
        if self.list_el.get_n_pages() > 0:
            GLib.idle_add(self.remove_all)
        for i, page in enumerate(widgets):
            GLib.idle_add(self.list_el.append, page)
        GLib.timeout_add(200, scroll_to_middle)
        GLib.idle_add(self.pan_container_el.set_visible, len(widgets) >= 2)

    @Gtk.Template.Callback()
    def on_scroll(self, controller, dx, dy):
        position = self.list_el.get_position()
        if position == int(position):
            event = controller.get_current_event()
            state = event.get_modifier_state()
            if (state & Gdk.ModifierType.SHIFT_MASK) or dx != 0:
                direction = dy or dx
                next_position = int(max(0, min(position + direction, self.list_el.get_n_pages())))
                next_page = self.list_el.get_nth_page(next_position)
                if next_page:
                    self.list_el.scroll_to(next_page, True)
        return Gdk.EVENT_PROPAGATE

    def pan(self, to_end:bool):
        if first_page := self.list_el.get_nth_page(0):
            visible_pages_n = int(self.list_el.get_width() / first_page.get_width())
            if to_end:
                next_position = int(self.list_el.get_position() + visible_pages_n)
            else:
                next_position = int(self.list_el.get_position() - visible_pages_n)
            next_position = max(min(next_position, self.list_el.get_n_pages() - 1), 0)
            self.list_el.scroll_to(self.list_el.get_nth_page(next_position), True)

    @Gtk.Template.Callback()
    def pan_start(self, button):
        self.pan(False)

    @Gtk.Template.Callback()
    def pan_end(self, button):
        self.pan(True)

    @Gtk.Template.Callback()
    def page_changed(self, carousel, index):
        self.pan_start_el.set_sensitive(index != 0)
        self.pan_end_el.set_sensitive(index != carousel.get_n_pages() - 1)

    @Gtk.Template.Callback()
    def handle_visible_bind(self, carousel, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def handle_action_name_bind(self, carousel, value) -> str:
        return str("app.replace_root_page") if value else str("")

    @Gtk.Template.Callback()
    def handle_action_target_bind(self, carousel, value) -> GLib.Variant:
        return GLib.Variant.new_string(value or "")

# carousel.py

from gi.repository import Gtk, Adw, GLib, Gdk

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/carousel.ui')
class Carousel(Gtk.Box):
    __gtype_name__ = 'NocturneCarousel'

    header_button = Gtk.Template.Child()
    list_el = Gtk.Template.Child()

    def set_header(self, label:str, icon_name:str, page_tag:str=None):
        self.header_button.set_tooltip_text(label)
        self.header_button.get_child().set_label(label)
        self.header_button.get_child().set_icon_name(icon_name)
        self.header_button.set_visible(True)
        if page_tag:
            self.header_button.set_action_target_value(GLib.Variant.new_string(page_tag))
            self.header_button.set_action_name('app.replace_root_page')

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

    @Gtk.Template.Callback()
    def on_scroll(self, controller, dx, dy):
        position = self.list_el.get_position()
        if position == int(position):
            event = controller.get_current_event()
            state = event.get_modifier_state()
            if (state & Gdk.ModifierType.SHIFT_MASK):
                next_position = int(max(0, min(position + dy, self.list_el.get_n_pages())))
                next_page = self.list_el.get_nth_page(next_position)
                if next_page:
                    self.list_el.scroll_to(next_page, True)
        return Gdk.EVENT_PROPAGATE



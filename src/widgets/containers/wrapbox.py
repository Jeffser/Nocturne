# wrapbox.py

from gi.repository import GObject, Gtk, GLib

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/wrapbox.ui')
class Wrapbox(Gtk.Box):
    __gtype_name__ = 'NocturneWrapbox'

    header_button = Gtk.Template.Child()
    list_el = Gtk.Template.Child()
    header_label = GObject.Property(type=str, default="")
    header_icon_name = GObject.Property(type=str, default="")
    header_page_tag = GObject.Property(type=str, default="")

    def remove_all(self):
        for child in list(self.list_el):
            self.list_el.remove(child)

    def set_widgets(self, widgets:list):
        if len(list(self.list_el)):
            GLib.idle_add(self.remove_all)
        GLib.idle_add(self.set_visible, len(widgets) > 0)
        for page in widgets:
            GLib.idle_add(self.list_el.append, page)

    @Gtk.Template.Callback()
    def handle_visible_bind(self, carousel, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def handle_action_name_bind(self, carousel, value) -> str:
        return str("app.replace_root_page") if value else str("")

    @Gtk.Template.Callback()
    def handle_action_target_bind(self, carousel, value) -> GLib.Variant:
        return GLib.Variant.new_string(value or "")

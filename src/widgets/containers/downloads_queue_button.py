# downloads_queue_button.py

from gi.repository import Gtk, GLib
from .download_row import DownloadRow

@Gtk.Template(resource_path='/com/jeffser/Nocturne/containers/downloads_queue_button.ui')
class DownloadsQueueButton(Gtk.MenuButton):
    __gtype_name__ = 'NocturneDownloadsQueueButton'

    download_list_el = Gtk.Template.Child()

    def setup(self):
        if root := self.get_root():
            if app := root.get_application():
                if player := app.get_property('player'):
                    model = player.get_property('downloadQueueModel')
                    self.download_list_el.get_parent().set_overflow(Gtk.Overflow.VISIBLE)
                    self.download_list_el.bind_model(
                        model,
                        lambda model: DownloadRow(model)
                    )
                    model.connect('notify::n-items', lambda model, ud: self.downloadQueueModelChanged(model))
                    self.downloadQueueModelChanged(model)

    def downloadQueueModelChanged(self, model):
        self.set_visible(len(model) > 0)
        if len(model) > 0:
            self.add_css_class('accent')

    @Gtk.Template.Callback()
    def clear_done_downloads(self, button):
        for row in list(self.download_list_el):
            if row.done_button.get_visible():
                GLib.idle_add(row.remove_from_queue, row.done_button)

    @Gtk.Template.Callback()
    def button_activated(self, button, ud):
        self.remove_css_class('accent')

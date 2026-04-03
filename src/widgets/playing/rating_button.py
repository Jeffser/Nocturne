# rating_button.py

from gi.repository import Gtk, GLib

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/rating_button.ui')
class RatingButton(Gtk.MenuButton):
    __gtype_name__ = 'NocturneRatingButton'

    def __init__(self):
        super().__init__()

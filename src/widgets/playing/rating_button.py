# rating_button.py

from gi.repository import Gtk, GLib

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/rating_button.ui')
class RatingButton(Gtk.MenuButton):
    __gtype_name__ = 'NocturneRatingButton'

    rate_0_el = Gtk.Template.Child()
    rate_1_el = Gtk.Template.Child()
    rate_2_el = Gtk.Template.Child()
    rate_3_el = Gtk.Template.Child()
    rate_4_el = Gtk.Template.Child()
    rate_5_el = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self._buttons = [
            self.rate_0_el, self.rate_1_el, self.rate_2_el,
            self.rate_3_el, self.rate_4_el, self.rate_5_el,
        ]
        self.update_song_id('')

    def update_song_id(self, song_id: str):
        for rating, btn in enumerate(self._buttons):
            btn.set_action_target_value(GLib.Variant('a{sv}', {
                'songId': GLib.Variant('s', song_id),
                'rating': GLib.Variant('i', rating),
            }))

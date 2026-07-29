# playback.py

from gi.repository import Gtk, Adw, GLib, Pango
from ...integrations import get_current_integration
from ..song import SongRow, SongButton
from datetime import datetime

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/playback.ui')
class PlaybackPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlaybackPage'

    spectrum = Gtk.Template.Child()
    top_wrapbox = Gtk.Template.Child()
    song_queue = Gtk.Template.Child()
    playlist_stack = Gtk.Template.Child()
    thanks_label = Gtk.Template.Child()

    def setup(self, songs:list, month:datetime):
        self.songs = songs
        self.month = month
        self.spectrum.setup()

        for item in list(self.top_wrapbox):
            self.top_wrapbox.remove(item)
        self.song_queue.list_el.remove_all()
        self.thanks_label.set_visible(len(songs) >= 50) # Add thank you message if 50 or more songs are included
        self.playlist_stack.set_visible_child_name("active")
        target_value = GLib.Variant('a{sv}', {
            'new_playlist': GLib.Variant('s', _("Nocturne Playback ~ {}").format(self.month.strftime("%B %Y"))),
            'songs': GLib.Variant('as', [song[0] for song in self.songs])
        })
        self.playlist_stack.get_child_by_name('active').set_action_target_value(target_value)
        self.playlist_stack.get_child_by_name('active').set_action_name("app.add_songs_to_playlist")

        integration = get_current_integration()
        for rank, song in enumerate(self.songs[:5]):
            container = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=5
            )
            container.append(Gtk.Label(
                css_classes=["title-1"],
                label="#{}".format(rank+1)
            ))
            container.append(SongButton(song[0]))
            container.append(Gtk.Label(
                css_classes=["dimmed"],
                label=_("{} Plays").format(song[1])
            ))

            self.top_wrapbox.append(container)

        for rank, song in enumerate(self.songs[5:]):
            row = SongRow(song[0])
            row.subtitle_wrapbox.prepend(Gtk.Label(
                ellipsize=Pango.EllipsizeMode.END,
                label="#{} · {} ·".format(rank+6, _("{} Plays").format(song[1])),
                css_classes=["subtitle"]
            ))
            self.song_queue.list_el.append(row)
        self.song_queue.main_stack.set_visible_child_name('content')

    @Gtk.Template.Callback()
    def go_home(self, button):
        if root := self.get_root():
            root.main_stack.set_visible_child_name('content')
            root.replace_root_page('home')

    @Gtk.Template.Callback()
    def save_playlist(self, button):
        self.playlist_stack.set_visible_child_name("inactive")

# row.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango, Gio
from .queue import SongQueue
from ...navidrome import get_current_integration, models
import threading, uuid, cairo
from datetime import timedelta, datetime

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/row.ui')
class SongRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneSongRow'

    icon_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    duration_el = Gtk.Template.Child()
    artist_container_el = Gtk.Template.Child()
    suffixes_stack_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    check_el = Gtk.Template.Child()

    def __init__(self, id:str, draggable:bool=False):
        self.id = id
        self.draggable = draggable
        integration = get_current_integration()
        integration.verifySong(self.id)
        super().__init__(
            action_target=GLib.Variant.new_string(self.id)
        )

        self.star_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'title', self.update_title)
        integration.connect_to_model(self.id, 'artists', self.update_artists)
        integration.connect_to_model(self.id, 'starred', self.update_starred)
        integration.connect_to_model('currentSong', 'songId', self.current_song_changed)

    def update_title(self, title:str):
        self.title_el.set_label(title)

    def update_duration(self, duration:int):
        self.duration_el.set_label(str(timedelta(seconds=duration)))

    def update_artists(self, artists:list):
        if len(artists) == 1:
            button = Gtk.Button(
                action_name = 'app.show_artist',
                action_target = GLib.Variant.new_string(artists[0].get('id')),
                child = Gtk.Label(
                    ellipsize=Pango.EllipsizeMode.END,
                    label=artists[0].get('name'),
                    css_classes=['subtitle']
                ),
                css_classes = ['p0', 'flat'],
                tooltip_text=artists[0].get('name')
            )
        else:
            menu = Gio.Menu()
            for artist in artists:
                item = Gio.MenuItem.new(
                    label=artist.get('name')
                )
                item.set_action_and_target_value(
                    'app.show_artist',
                    GLib.Variant.new_string(artist.get('id'))
                )
                menu.append_item(item)

            button = Gtk.MenuButton(
                child = Gtk.Label(
                    ellipsize=Pango.EllipsizeMode.END,
                    label=_("Multiple Artists"),
                    css_classes=['subtitle']
                ),
                css_classes = ['p0', 'flat'],
                menu_model = menu,
                tooltip_text=_("Multiple Artists")
            )

        self.artist_container_el.set_child(button)

    def update_starred(self, starred:str):
        if starred:
            self.star_el.add_css_class('suggested-action')
            self.star_el.set_icon_name('starred-symbolic')
            local_dt = datetime.fromisoformat(starred).astimezone()
            self.star_el.set_tooltip_text(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.star_el.remove_css_class('suggested-action')
            self.star_el.set_icon_name('non-starred-symbolic')
            self.star_el.set_tooltip_text(_('Star'))

    def current_song_changed(self, songId:str):
        self.set_activatable(songId != self.id)
        if songId == self.id:
            self.icon_el.set_from_icon_name('media-playback-start-symbolic')
            self.icon_el.set_visible(True)
        else:
            if self.draggable:
                self.icon_el.set_from_icon_name('list-drag-handle-symbolic')
                self.icon_el.set_visible(True)
            else:
                self.icon_el.set_from_icon_name(None)
                self.icon_el.set_visible(False)

    # -- Callbacks --

    @Gtk.Template.Callback()
    def on_drop(self, drop_target, row, x, y):
        if self != row and self.draggable:
            row.get_ancestor(Gtk.ListBox).remove(row)
            list_box_target = self.get_ancestor(Gtk.ListBox)
            target_index = list(list_box_target).index(self)
            if y > self.get_height() / 2: # bottom
                target_index += 1
            list_box_target.insert(row, target_index)

    @Gtk.Template.Callback()
    def on_drag_begin(self, drag_source, drag):
        if self.draggable:
            paintable = Gtk.WidgetPaintable.new(self)
            drag_source.set_icon(paintable, 0, 0)

    @Gtk.Template.Callback()
    def on_drag_prepare(self, drag_source, x, y):
        if self.draggable:
            return Gdk.ContentProvider.new_for_value(self)

    @Gtk.Template.Callback()
    def select_clicked(self, button):
        queue = self.get_ancestor(SongQueue)
        queue.set_selected_mode(
            select=True,
            selected_row=self
        )

    @Gtk.Template.Callback()
    def check_toggled(self, checkbutton):
        if not checkbutton.get_active():
            queue = self.get_ancestor(SongQueue)
            if len(queue.get_selected_rows()) == 0:
                queue.set_selected_mode()

    @Gtk.Template.Callback()
    def play_next_clicked(self, button):
        ''

    @Gtk.Template.Callback()
    def play_later_clicked(self, button):
        ''

    @Gtk.Template.Callback()
    def add_to_playlist_clicked(self, button):
        ''


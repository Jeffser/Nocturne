# button.py

from gi.repository import Gtk, Adw, GLib, Gdk, Gio
from ...integrations import get_current_integration
from ...constants import CONTEXT_PLAYLIST
from ..containers import ContextContainer

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/button.ui')
class PlaylistButton(Gtk.Box):
    __gtype_name__ = 'NocturnePlaylistButton'

    play_el = Gtk.Template.Child()
    cover_button_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    name_label_el = Gtk.Template.Child()
    song_count_label_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id, minimal=True)
        super().__init__()

        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        self.settings.connect("changed::button-size", lambda *_: self.update_size())

        self.play_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.cover_button_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.name_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)

    def update_size(self):
        isBig = self.settings.get_value('button-size').unpack() == 'big'
        size = 240 if isBig else 180
        pixel_size = size if self.cover_el.get_paintable() is not None else -1
        self.cover_el.set_size_request(size, size)
        self.cover_el.set_pixel_size(pixel_size)
        if isBig:
            self.name_label_el.remove_css_class('title-4')
            self.name_label_el.add_css_class('title-3')
        else:
            self.name_label_el.remove_css_class('title-3')
            self.name_label_el.add_css_class('title-4')

    def update_cover(self, paintable):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-note-symbolic")
        self.update_size()

    def update_name(self, name:str):
        self.name_el.set_tooltip_text(name)
        self.name_label_el.set_label(name)
        self.cover_button_el.set_tooltip_text(name)
        self.set_name(name)

    def update_song_count(self, songCount:int):
        self.song_count_label_el.set_label(ngettext("{} Song", "{} Songs", songCount).format(songCount))
        self.song_count_label_el.set_visible(songCount)

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        context = CONTEXT_PLAYLIST.copy()
        if 'no-downloads' in get_current_integration().limitations:
            del context['download']

        popover = Gtk.Popover(
            child=ContextContainer(context, self.id),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()


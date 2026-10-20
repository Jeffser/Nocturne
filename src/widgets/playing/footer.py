# footer.py

from gi.repository import Gtk, Adw, GLib, GObject, Gst, Gio, Gdk
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/footer.ui')
class PlayingFooter(Adw.BreakpointBin):
    __gtype_name__ = 'NocturnePlayingFooter'

    forceHugeMode = GObject.Property(type=bool, default=False)

    @Gtk.Template.Callback()
    def format_progress_el_visibility(self, obj, song_id:str) -> bool:
        if integration := get_current_integration():
            if model := integration.loaded_models.get(song_id):
                return not bool(model.get_property('radioStreamUrl'))
        return True

    @Gtk.Template.Callback()
    def format_cover_art_size(self, obj, huge_mode:bool) -> int:
        return 100 if huge_mode else 70

    @Gtk.Template.Callback()
    def format_cover_art_pixel_size(self, obj, huge_mode:bool, paintable:Gdk.Paintable) -> int:
        if paintable:
            return 100 if huge_mode else 70
        return -1

    @Gtk.Template.Callback()
    def format_cover_art_paintable(self, obj, song_id:str) -> Gdk.Paintable | None:
        if integration := get_current_integration():
            if model := integration.loaded_models.get(song_id):
                return model.get_property('gdkPaintable')

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

        if root := self.get_root():
            if app := root.get_application():
                if player := app.get_property('player'):
                    value = scale_el.get_adjustment().get_value()
                    player.set_property('seeking', True)
                    GLib.timeout_add(500, lambda v=value, p=player: change_time(p, v) if v == scale_el.get_adjustment().get_value() else None)


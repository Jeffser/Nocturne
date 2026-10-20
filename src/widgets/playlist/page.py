# page.py

from gi.repository import Gtk, Adw, GLib
from ...integrations import get_current_integration
from ...constants import CONTEXT_PLAYLIST, get_display_time
from ..containers import get_context_buttons_list
from ..song import SongRow
import threading, io
from colorthief import ColorThief

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playlist/page.ui')
class PlaylistPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturnePlaylistPage'

    clamp_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    song_count_el = Gtk.Template.Child()
    duration_el = Gtk.Template.Child()
    song_list_el = Gtk.Template.Child()

    context_wrap_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyPlaylist(self.id, True)
        super().__init__()

        context = CONTEXT_PLAYLIST.copy()
        del context['edit']
        del context['delete']
        if 'no-downloads' in integration.limitations:
            del context['download']
        context_buttons = get_context_buttons_list(context, self.id)
        for btn in context_buttons:
            self.context_wrap_el.append(btn)

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'songCount', self.update_song_count)
        integration.connect_to_model(self.id, 'duration', self.update_duration)
        integration.connect_to_model(self.id, 'entry', self.update_song_list)
        integration.connect_to_model(self.id, 'gdkPaintable', self.update_cover)

        self.song_list_el.playlist_id = self.id
        self.song_ids = []
        self.current_offset = 0
        self.loading = False

    def update_cover(self, paintable):
        if paintable:
            self.cover_el.set_from_paintable(paintable)
            self.cover_el.set_pixel_size(240)
            self.update_background(paintable.save_to_png_bytes().get_data())
        elif isinstance(self.cover_el.get_paintable(), Adw.SpinnerPaintable):
            self.cover_el.set_from_icon_name("music-note-symbolic")
            self.cover_el.set_pixel_size(-1)

    def update_background(self, raw_bytes:bytes):
        def run():
            img_io = io.BytesIO(raw_bytes)
            color = ColorThief(img_io).get_color(quality=10)
            css = f"""
            clamp {{
                transition: background .2s;
                background: linear-gradient(180deg, color-mix(in srgb, rgb({','.join([str(c) for c in color])}) 50%, transparent), transparent 30%);
                background-size: 100% 1000px;
                background-repeat: no-repeat;
            }}
            """
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            GLib.idle_add(self.clamp_el.get_style_context().add_provider,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        if raw_bytes:
            threading.Thread(target=run, daemon=True).start()

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.name_el.set_visible(name)
        self.set_title(name or _('Playlist'))
        self.set_name(name)

    def load_song_rows(self):
        # Pagination of Playlist in order to load hundreds
        if self.current_offset < len(self.song_ids) and not self.loading:
            self.loading = True
            for songId in self.song_ids[self.current_offset:self.current_offset+50]:
                row = SongRow(songId, removable=True)
                row.set_action_name('app.play_song_from_list')
                row.set_action_target_value(GLib.Variant('a{sv}', {
                    'songId': GLib.Variant('s', songId),
                    'songs': GLib.Variant('as', self.song_ids),
                    'originId': GLib.Variant('s', self.id)
                }))
                GLib.idle_add(self.song_list_el.list_el.append, row)
            self.current_offset += 50
            GLib.idle_add(setattr, self, 'loading', False)

    def update_song_list(self, song_list:list):
        self.song_list_el.list_el.remove_all()
        self.song_list_el.main_stack.set_visible_child_name('content' if len(song_list) > 0 else 'no-content')
        self.song_ids = [s.get('id') for s in song_list]
        self.current_offset = 0
        threading.Thread(target=self.load_song_rows, daemon=True).start()

    @Gtk.Template.Callback()
    def scroll_edge_reached(self, scrolledwindow, pos):
        if pos == Gtk.PositionType.BOTTOM:
            threading.Thread(target=self.load_song_rows, daemon=True).start()

    def update_song_count(self, songCount:int):
        self.song_count_el.set_label(ngettext("{} Song", "{} Songs", songCount).format(songCount))
        self.song_count_el.set_visible(songCount)

    def update_duration(self, duration:int):
        self.duration_el.set_label(get_display_time(duration))
        self.duration_el.set_visible(duration)

    def reload(self):
        pass

# dialog.py

from gi.repository import Gtk, Adw, GLib, Gdk, Gio, Gst
from ...integrations import get_current_integration, get_lyrics
from ...constants import DATA_DIR, get_display_time
from ..playing.lyrics_page import LyricData
import threading, os

@Gtk.Template(resource_path='/com/jeffser/Nocturne/lyrics/edit_row.ui')
class LyricEditRow(Adw.EntryRow):
    __gtype_name__ = 'NocturneLyricEditRow'

    ts_button = Gtk.Template.Child()

    def __init__(self, ms, content, invalid_ms:bool=False):
        self.invalid_ms = invalid_ms
        super().__init__(
            text=content
        )
        if self.invalid_ms:
            self.add_css_class('error')
        self.ms = ms
        self.show_timestamp()

    @Gtk.Template.Callback()
    def go_to_timestamp(self, button):
        integration = get_current_integration()
        GLib.idle_add(button.get_ancestor(Gtk.Popover).popdown)
        nanoseconds = int(self.ms/1000 * Gst.SECOND)
        self.get_root().playing_page.player.gst.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            nanoseconds
        )

    @Gtk.Template.Callback()
    def set_current_timestamp(self, button):
        integration = get_current_integration()
        ps = integration.loaded_models.get('currentSong').get_property('positionSeconds')
        self.ms = int(ps * 1000)
        self.invalid_ms = False
        GLib.idle_add(button.get_ancestor(Gtk.Popover).popdown)
        GLib.idle_add(self.show_timestamp)
        GLib.idle_add(self.get_ancestor(Gtk.ListBox).invalidate_sort)

    @Gtk.Template.Callback()
    def remove(self, button):
        GLib.idle_add(button.get_ancestor(Gtk.Popover).popdown)
        GLib.idle_add(self.get_ancestor(Gtk.ListBox).remove, self)

    def show_timestamp(self):
        self.set_title(_("No Timestamp") if self.invalid_ms else get_display_time(self.ms / 1000, True))
        if not self.invalid_ms:
            self.remove_css_class('error')

@Gtk.Template(resource_path='/com/jeffser/Nocturne/lyrics/dialog.ui')
class LyricsDialog(Adw.Dialog):
    __gtype_name__ = 'NocturneLyricsDialog'

    main_stack = Gtk.Template.Child()
    lrc_list_el = Gtk.Template.Child()
    progress_el = Gtk.Template.Child()
    state_stack_el = Gtk.Template.Child()
    position_spin = Gtk.Template.Child()
    is_seeking = False
    focused_row = None

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        super().__init__()
        self.lrc_list_el.set_sort_func(lambda r1, r2: r1.ms - r2.ms)
        integration.loaded_models.get('currentSong').set_property('songId', self.id)
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed, use_gtk_thread=False)
        integration.connect_to_model(self.id, 'title', self.set_title)
        integration.connect_to_model(self.id, 'duration', self.update_duration)

        self.playback_mode_backup = integration.loaded_models.get('currentSong').get_property('playbackMode')
        integration.loaded_models.get('currentSong').set_property('playbackMode', 'repeat-one')
        threading.Thread(target=self.retrieve_lyrics).start()

    def update_duration(self, duration):
        self.progress_el.get_adjustment().set_upper(duration)
        self.position_spin.get_adjustment().set_upper(duration)

    def retrieve_lyrics(self):
        GLib.idle_add(self.main_stack.set_visible_child_name, 'loading')
        GLib.idle_add(self.lrc_list_el.remove_all)
        lyrics = get_lyrics(self.id, True)
        if lyrics.get('type') == 'lrc':
            for line in lyrics.get('content'):
                row = LyricEditRow(
                    ms=line.get('ms'),
                    content=line.get('content', '')
                )
                GLib.idle_add(self.lrc_list_el.append, row)
        elif lyrics.get('type') == 'plain':
            for index, line in enumerate(lyrics.get('content').split('\n')):
                row = LyricEditRow(
                    ms=index*1000000,
                    content=line,
                    invalid_ms=True
                )
                GLib.idle_add(self.lrc_list_el.append, row)
        GLib.idle_add(self.lrc_list_el.invalidate_sort)
        GLib.idle_add(self.main_stack.set_visible_child_name, 'content')

    def position_changed(self, position_seconds:float):
        self.progress_el.get_adjustment().set_value(position_seconds)
        if self.get_focus() not in list(self.position_spin):
            self.position_spin.set_value(position_seconds)
        if len(list(self.lrc_list_el)) > 0:
            ms = int(position_seconds * 1000)+100
            best_match = list(self.lrc_list_el)[0]
            for row in list(self.lrc_list_el):
                if row.ms <= ms:
                    best_match = row
                else:
                    break
            if self.focused_row != best_match:
                if self.focused_row:
                    self.focused_row.ts_button.remove_css_class('suggested-action')
                self.focused_row = best_match
                self.focused_row.ts_button.add_css_class('suggested-action')

    @Gtk.Template.Callback()
    def seek_start(self, gesture, n_press, x, y):
        self.is_seeking = True

    @Gtk.Template.Callback()
    def seek_end(self, gesture):
        self.is_seeking = False

    @Gtk.Template.Callback()
    def progress_bar_changed(self, adjustment):
        if self.is_seeking:
            nanoseconds = int(adjustment.get_value() * Gst.SECOND)
            self.get_root().playing_page.player.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )

    @Gtk.Template.Callback()
    def add_line(self, button):
        integration = get_current_integration()
        ps = integration.loaded_models.get('currentSong').get_property('positionSeconds')
        row = LyricEditRow(
            ms=int(ps * 1000),
            content=""
        )
        self.lrc_list_el.append(row)
        GLib.idle_add(self.lrc_list_el.invalidate_sort)

    @Gtk.Template.Callback()
    def play_clicked(self, button):
        self.get_root().playing_page.player.gst.set_state(Gst.State.PLAYING)

    @Gtk.Template.Callback()
    def pause_clicked(self, button):
        self.get_root().playing_page.player.gst.set_state(Gst.State.PAUSED)

    @Gtk.Template.Callback()
    def position_spin_changed(self, spinbutton):
        if spinbutton.get_sensitive() and self.get_root():
            nanoseconds = int(spinbutton.get_value() * Gst.SECOND)
            self.get_root().playing_page.player.gst.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                nanoseconds
            )

    @Gtk.Template.Callback()
    def state_stack_changed(self, stack, ud):
        self.position_spin.set_sensitive(stack.get_visible_child_name() == "play")

    @Gtk.Template.Callback()
    def cancel_clicked(self, button):
        get_current_integration().loaded_models.get('currentSong').set_property('playbackMode', self.playback_mode_backup)
        self.close()

    @Gtk.Template.Callback()
    def save_clicked(self, button):
        lines = []
        is_synced = True
        for row in list(self.lrc_list_el):
            # ms, content
            lines.append((row.get_title(), row.get_text()))
            is_synced = is_synced and not row.invalid_ms

        if is_synced:
            file_text = '\n'.join(['[{}] {}'.format(ms, content) for ms, content in lines])
        else:
            file_text = '\n'.join([content for ms, content in lines])

        target_value = GLib.Variant('a{sv}', {
            'id': GLib.Variant('s', self.id),
            'content': GLib.Variant('s', file_text),
            'is_synced': GLib.Variant('b', is_synced)
        })
        self.get_root().activate_action("app.save_lyrics", target_value)

        get_current_integration().loaded_models.get('currentSong').set_property('playbackMode', self.playback_mode_backup)
        self.close()


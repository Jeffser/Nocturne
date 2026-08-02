# lyrics_page.py

from gi.repository import Gtk, GObject, GLib, Gio, Pango, Gst
from ...integrations import get_current_integration
from ..lyrics.helpers import prepare_lrc
from ...constants import CONTEXT_LYRICS
from ..containers import ContextContainer
import threading, re

class LyricRow(Gtk.ListBoxRow):
    __gtype_name__ = 'NocturneLyricRow'

    ms = GObject.Property(type=int)

    def __init__(self, content:str, ms:int, duration_ms:int):
        super().__init__(
            ms=ms,
            child=Gtk.Label(
                wrap=True,
                wrap_mode=Pango.WrapMode.WORD_CHAR,
                justify=Gtk.Justification.CENTER,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER
            )
        )

        pattern = r"<(\d{2}):(\d{2})\.(\d{2,3})>\s*([^<]*)"
        matches = re.findall(pattern, content)
        self.cues = {}
        if len(matches) > 0:
            for m, s, ms_part, text in matches:
                if text:
                    minutes = int(m)
                    seconds = int(s)
                    fraction = int(ms_part)
                    if len(ms_part) == 2:
                        fraction *= 10
                    total_ms = (minutes * 60000) + (seconds * 1000) + fraction
                    self.cues[total_ms] = text
        if len(self.cues) == 0:
            if content:
                if duration_ms == 0:
                    self.cues[ms] = content
                else:
                    words = content.split(' ')
                    weights = []
                    for word in words:
                        word = word.replace('.', '...') # Add more time
                        word = word.replace(',', '..') # Add more time
                        word = ''.join(c for c in word if c not in '¡!¿?\'"') # Ignore characters
                        weights.append(len(word))

                    ms_per_letter = int(duration_ms / sum(weights))
                    last_timestamp = 0
                    for i, word in enumerate(words):
                        if i == 0:
                            timestamp = ms
                        else:
                            timestamp = int(last_timestamp + weights[i-1] * ms_per_letter)
                        last_timestamp = timestamp
                        self.cues[timestamp] = word + ' '
            else:
                self.cues[ms] = "🎵" if duration_ms > 1000 else ""

        self.sorted_ts = sorted(self.cues.keys())
        self.alphas = {ts: 0.3 for ts in self.sorted_ts}
        self.last_ms = 0
        self.add_tick_callback(self.on_frame_tick)
        self.on_frame_tick(self, None, True)

    def on_frame_tick(self, widget, frame_clock, force:bool=False):
        lerp_speed = 0.1
        changed = False
        parts = []

        for ts in self.sorted_ts:
            word = GLib.markup_escape_text(self.cues[ts])
            target = 1.0 if self.last_ms >= ts else 0.3
            current = self.alphas[ts]

            if abs(current - target) > 0.001:
                self.alphas[ts] = current + (target - current) * lerp_speed
                changed = True

            alpha_val = int(self.alphas[ts] * 65536) # Pango uses that number as max for some reason
            parts.append(f"<span fgalpha='{alpha_val}'>{word}</span>")

        if changed or force:
            self.get_child().set_markup("".join(parts))
        return self.get_root()


@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/lyrics_page.ui')
class PlayingLyricsPage(Gtk.Stack):
    __gtype_name__ = 'NocturnePlayingLyricsPage'

    plain_label_el = Gtk.Template.Child()
    lrc_list_el = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    lrc_menu_popover = Gtk.Template.Child()
    code_is_selecting = False # used so that `on_lrc_selection` is only executed when manually selecting
    last_best_match = None

    def __init__(self):
        super().__init__()
        context = CONTEXT_LYRICS.copy()
        context["remove"]["connection"] = self.go_to_main
        self.lrc_menu_popover.set_child(ContextContainer(context))

    def setup(self):
        # Called after login
        integration = get_current_integration()
        integration.connect_to_model('currentSong', 'songId', self.song_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.position_changed)

    def update_lyrics(self, song_id:str, attempt_download:bool):
        # We verify if the song requested and the current song are the same
        # We have to do this both before and after downloading the lyrics
        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        integration = get_current_integration()
        if integration.loaded_models.get('currentSong').get_property('songId') != song_id:
            return
        lyrics_type, raw_content = integration.getLyrics(song_id, attempt_download)
        if integration.loaded_models.get('currentSong').get_property('songId') != song_id:
            return

        if settings.get_value('auto-download-lyrics').unpack() and lyrics_type == 'not-found-locally':
            thread = threading.Thread(target=self.update_lyrics, args=(song_id, True), daemon=True)
            GLib.timeout_add(3000, thread.start)
            return

        GLib.idle_add(self.set_visible_child_name, lyrics_type)
        if lyrics_type == 'plain':
            GLib.idle_add(self.plain_label_el.set_label, raw_content)
        elif lyrics_type == 'lrc':
            content = prepare_lrc(raw_content)
            GLib.idle_add(self.lrc_list_el.remove_all)
            if content[0].get('content'):
                content.insert(0, {'content': '', 'ms': 0})
            simulate_wbwl = settings.get_value('simulate-word-by-word-lyrics').unpack()
            for i, line in enumerate(content):
                if simulate_wbwl:
                    duration_ms = 1000
                    if i + 1 < len(content):
                        duration_ms = content[i+1].get('ms') - line.get('ms')
                    else:
                        integration = get_current_integration()
                        if model := integration.loaded_models.get(song_id):
                            duration_ms = model.get_property('duration') * 1000 - line.get('ms')
                else:
                    duration_ms = 0
                row = LyricRow(
                    ms=line.get('ms'),
                    content=line.get('content', ''),
                    duration_ms=duration_ms
                )
                GLib.idle_add(self.lrc_list_el.append, row)

    def song_changed(self, model_id:str, lrclib_download:bool=False):
        self.set_visible_child_name('loading')
        threading.Thread(target=self.update_lyrics, args=(model_id, lrclib_download), daemon=True).start()

    def position_changed(self, position_seconds:float):
        if self.get_visible_child_name() == 'lrc':
            ms = int(position_seconds * 1000)+100
            best_match = None
            for row in list(self.lrc_list_el):
                if row.ms <= ms:
                    best_match = row
                else:
                    break
            if best_match:
                if best_match == self.lrc_list_el.get_selected_row():
                    best_match.last_ms = ms
                else:
                    self.code_is_selecting = True
                    self.lrc_list_el.select_row(best_match)
                    self.code_is_selecting = False

    @Gtk.Template.Callback()
    def on_lrc_selection(self, list_el, position):
        row = list_el.get_selected_row()
        if self.last_best_match:
            self.last_best_match.last_ms = -1
        self.last_best_match = row
        if row:
            if not self.code_is_selecting:
                self.get_root().get_application().player.gst.seek_simple(
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    int(row.ms/1000 * Gst.SECOND)
                )
            vadj = self.scrolledwindow.get_vadjustment()
            row_alloc = row.get_allocation()
            viewport_height = self.scrolledwindow.get_height()
            row_y = row_alloc.y
            row_height = row_alloc.height
            target = row_y - (viewport_height / 2) + (row_height / 2)
            lower = vadj.get_lower()
            upper = vadj.get_upper() - vadj.get_page_size()
            target = max(lower, min(target, upper))
            vadj.set_value(target)

    @Gtk.Template.Callback()
    def lyric_download_requested(self, button):
        integration = get_current_integration()
        self.song_changed(integration.loaded_models.get('currentSong').get_property('songId'), True)

    def copy_lyrics_lrc(self, dialog, task):
        if source_file := dialog.open_finish(task):
            with open(source_file.get_path(), 'r') as f:
                integration = get_current_integration()
                if songId := integration.loaded_models.get('currentSong').get_property('songId'):
                    if content := f.read():
                        integration.saveLyrics(songId, content, 'lrc')
                        self.song_changed(songId)

    @Gtk.Template.Callback()
    def lyric_load_requested(self, button):
        integration = get_current_integration()
        file_filter = Gtk.FileFilter(
            name=_("LRC File")
        )
        file_filter.add_mime_type('text/x-lrc')
        file_filter.add_mime_type('application/x-lrc')
        file_filter.add_suffix('lrc')
        file_filter_list = Gio.ListStore.new(Gtk.FileFilter)
        file_filter_list.append(file_filter)

        Gtk.FileDialog(
            filters=file_filter_list
        ).open(self.get_root(), None, self.copy_lyrics_lrc)

    @Gtk.Template.Callback()
    def go_to_main(self, button=None):
        self.set_visible_child_name('not-found-locally')
        integration = get_current_integration()
        integration.deleteLyrics(integration.loaded_models.get('currentSong').get_property('songId'))


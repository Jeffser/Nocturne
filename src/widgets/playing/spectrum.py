# spectrum.py

from gi.repository import Gtk, GLib, Gio
from ...integrations import get_current_integration
import math

class Spectrum(Gtk.DrawingArea):
    __gtype_name__ = 'NocturneSpectrum'

    def setup(self):
        integration = get_current_integration()
        self.settings = Gio.Settings(schema_id="com.jeffser.Nocturne")

        default_bar_n = self.settings.get_value('visualizer-bar-n').unpack()
        self.target_magnitudes = [0] * default_bar_n
        self.current_magnitudes = [0] * default_bar_n

        self.stopped = False
        self.accent_color = [0.2, 0.6, 0.9]
        self.speed = 0.03

        self.set_draw_func(self.on_draw)

        integration.connect_to_model('currentSong', 'buttonState', self.playback_changed)
        integration.connect_to_model('currentSong', 'positionSeconds', self.on_timestamp_changed)
        integration.connect_to_model('currentSong', 'accentColor', self.update_color)

        self.settings.bind(
            "show-visualizer",
            self,
            "visible",
            Gio.SettingsBindFlags.DEFAULT
        )

        GLib.timeout_add(16, self.on_tick)

    def on_timestamp_changed(self, timestamp:float):
        if self.stopped:
            self.target_magnitudes = [0] * self.settings.get_value('visualizer-bar-n').unpack()
        elif integration := get_current_integration():
            if magnitudes_dict := integration.loaded_models.get('currentSong').get_property('magnitudes'):
                if next_timestamp := min((k for k in magnitudes_dict if k >= timestamp), default=None):
                    self.target_magnitudes = magnitudes_dict.get(next_timestamp)

    def on_tick(self):
        if self.get_visible():
            if len(self.target_magnitudes) != len(self.current_magnitudes):
                self.current_magnitudes = [0] * len(self.target_magnitudes)
            for i in range(len(self.target_magnitudes)):
                speed_modifier = self.speed * max(0.25, min(1, 10*abs(self.target_magnitudes[i] - self.current_magnitudes[i])))
                if self.target_magnitudes[i] >= self.current_magnitudes[i]:
                    self.current_magnitudes[i] = min(self.target_magnitudes[i], self.current_magnitudes[i] + speed_modifier)
                else:
                    self.current_magnitudes[i] = max(0, self.current_magnitudes[i] - speed_modifier)
            self.queue_draw()
        return True

    def on_draw(self, drawing_area, cr, width, height):
        if not self.current_magnitudes or min(width, height) < 24:
            return

        n = len(self.current_magnitudes)
        dx = width / (n - 1)

        fill_mode = self.settings.get_value("visualizer-fill-mode").unpack()
        visualizer_type = self.settings.get_value('visualizer-type').unpack()

        if visualizer_type == "wave" and not fill_mode == "border":
            cr.move_to(0, height)

        opacity = 0.75 if fill_mode == "translucent" else 1
        if self.settings.get_value("visualizer-auto-color").unpack():
            if self.settings.get_value("visualizer-auto-color-invert").unpack():
                cr.set_source_rgba(*[1-c for c in self.accent_color], opacity)
            else:
                cr.set_source_rgba(*self.accent_color, opacity)
        else:
            try:
                rgb_str = self.settings.get_value("visualizer-manual-color").unpack()
                cr.set_source_rgba(*[float(c) for c in rgb_str.split(',')], opacity)
            except:
                cr.set_source_rgba(*self.accent_color, opacity)

        if visualizer_type == "wave":
            cr.line_to(0, height * (1 - self.current_magnitudes[0]))

            for i in range(n - 1):
                x1 = i * dx
                y1 = height * (1 - self.current_magnitudes[i])
                x2 = (i + 1) * dx
                y2 = height * (1 - self.current_magnitudes[i + 1])

                # Control points for smoothness
                xc = (x1 + x2) / 2
                cr.curve_to(xc, y1, xc, y2, x2, y2)

            if fill_mode == "border":
                cr.set_line_width(3.0)
                cr.stroke()
            else:
                cr.line_to(width, height)
                cr.close_path()
                cr.fill_preserve()
        elif visualizer_type in ("bars", "particles"):
            gap = 2 if visualizer_type == "bars" else 4
            bar_w = dx - gap
            radius = 6 if visualizer_type == "bars" else bar_w
            for i in range(n):
                bar_x = (i * dx) - (bar_w / 2)
                if visualizer_type == "particles":
                    bar_h = bar_w
                    bar_y = max(0, min(height * (1 - self.current_magnitudes[i]), height - bar_h))
                else:
                    bar_h = self.current_magnitudes[i] * height
                    bar_y = height - bar_h
                if bar_h > 1:
                    r = min(radius, bar_w / 2, bar_h / 2)
                    cr.new_sub_path()
                    cr.arc(bar_x + bar_w - r, bar_y + r, r, -math.pi/2, 0)
                    cr.arc(bar_x + bar_w - r, bar_y + bar_h - r, r, 0, math.pi/2)
                    cr.arc(bar_x + r, bar_y + bar_h - r, r, math.pi/2, math.pi)
                    cr.arc(bar_x + r, bar_y + r, r, math.pi, 3*math.pi/2)
                    if fill_mode == "border":
                        cr.set_line_width(3.0)
                        cr.close_path()
                        cr.stroke()
                    else:
                        cr.close_path()
                        cr.fill()

    def update_color(self, accent_color):
        if accent_color:
            self.accent_color = [min(c/255, 1) for c in accent_color]
        else:
            self.accent_color = [0.2, 0.6, 0.9]

    def playback_changed(self, playbackState:str):
        if playbackState == "play":
            self.stopped = True
        else:
            self.stopped = False

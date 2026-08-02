# coverArt.py

from gi.repository import GObject, Adw, Gtk, Gdk, GLib
from ...integrations import get_current_integration

@Gtk.Template(resource_path='/com/jeffser/Nocturne/playing/cover_art.ui')
class PlayingCoverArt(Gtk.Box, Adw.Swipeable):
    __gtype_name__ = 'NocturnePlayingCoverArt'

    spectrum_el = Gtk.Template.Child()
    view_stack_el = Gtk.Template.Child()
    cover_el = Gtk.Template.Child()
    video_el = Gtk.Template.Child()
    view_switcher_el = Gtk.Template.Child()
    previous_icon_el = Gtk.Template.Child()
    next_icon_el = Gtk.Template.Child()
    swipeProgress = GObject.Property(type=float, default=0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation_target = Adw.CallbackAnimationTarget.new(lambda val: self.set_property('swipeProgress', val))
        self.animation = Adw.TimedAnimation.new(
            self,
            0,
            0,
            200,
            self.animation_target
        )
        self.swipe_tracker = Adw.SwipeTracker.new(self)
        self.swipe_tracker.set_enabled(True)
        self.swipe_tracker.set_allow_mouse_drag(True)
        self.swipe_tracker.connect('update-swipe', self.on_swipe_update)
        self.swipe_tracker.connect('end-swipe', self.on_swipe_end)
        self.connect('notify::swipeProgress', self.swipe_progress_changed)

    # Swipeable and SwipeTracker code ----

    def do_get_distance(self):
        return float(self.get_width() / 1.5)

    def do_get_progress(self):
        return float(self.get_property('swipeProgress'))

    def do_get_cancel_progress(self):
        return float(0.0)

    def do_get_snap_points(self):
        return [-1.0, -0.9, 0.9, 1.0], 4

    def on_swipe_update(self, tracker, progress):
        self.set_property('swipeProgress', progress)
        self.queue_allocate()

    def on_swipe_end(self, tracker, velocity, to):
        progress = self.get_property('swipeProgress')

        progress = self.get_property('swipeProgress')
        if progress != 0:
            self.animation.set_value_from(progress)
            self.animation.play()

        # Handle changing the song
        if self.get_property('swipeProgress') > 0.9:
            GLib.timeout_add(200, lambda: self.get_root().activate_action("app.player_next") and False)
        elif self.get_property('swipeProgress') < -0.9:
            GLib.timeout_add(200, lambda: self.get_root().activate_action("app.player_previous") and False)


    def swipe_progress_changed(self, widget, gparam):
        progress = self.get_property('swipeProgress')

        # NEXT
        if progress > 0:
            self.next_icon_el.set_margin_start(int(progress*10))
            self.next_icon_el.set_pixel_size(max(int(progress*32), 1))
            self.next_icon_el.set_visible(True)
        else:
            self.next_icon_el.set_margin_start(0)
            self.next_icon_el.set_pixel_size(1)
            self.next_icon_el.set_visible(False)
        if progress > 0.9:
            self.next_icon_el.add_css_class('accent')
            self.next_icon_el.remove_css_class('dimmed')
        else:
            self.next_icon_el.add_css_class('dimmed')
            self.next_icon_el.remove_css_class('accent')

        # PREVIOUS
        if progress < 0:
            self.previous_icon_el.set_margin_end(int(abs(progress)*10))
            self.previous_icon_el.set_pixel_size(max(int(abs(progress)*32), 1))
            self.previous_icon_el.set_visible(True)
        else:
            self.previous_icon_el.set_margin_end(0)
            self.previous_icon_el.set_pixel_size(1)
            self.previous_icon_el.set_visible(False)
        if progress < -0.9:
            self.previous_icon_el.add_css_class('accent')
            self.previous_icon_el.remove_css_class('dimmed')
        else:
            self.previous_icon_el.add_css_class('dimmed')
            self.previous_icon_el.remove_css_class('accent')


    # ------------------------------------

    def setup(self):
        integration = get_current_integration()
        integration.connect_to_current_song('gdkPaintableBig', self.update_cover_art)
        integration.connect_to_model('currentSong', 'videoId', self.video_changed)
        self.spectrum_el.setup()

        if root := self.get_root():
            if app := root.get_application():
                if player := app.player:
                    if video_sink := player.gst.get_property('video-sink'):
                        self.video_el.set_paintable(video_sink.get_property('paintable'))

    def update_cover_art(self, paintable):
        if paintable:
            self.cover_el.remove_css_class('p50')
        else:
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            paintable = icon_theme.lookup_icon(
                'music-note-symbolic',
                None,
                64,
                1,
                Gtk.TextDirection.NONE,
                0
            )
            self.cover_el.add_css_class('p50')
        self.cover_el.set_paintable(paintable)

    def video_changed(self, videoId:str):
        integration = get_current_integration()
        songId = integration.loaded_models.get('currentSong').get_property('songId')
        video_available = videoId and videoId == songId and self.video_el.get_paintable()
        self.view_switcher_el.set_visible(video_available)
        self.view_stack_el.set_visible_child_name('video' if video_available else 'audio')


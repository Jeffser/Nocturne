# page.py

from gi.repository import GObject, Gtk, Gdk, Adw, GLib
from ..song import SongRow
from ...integrations import get_current_integration, models
from ...constants import CONTEXT_ALBUM
from ..containers import get_context_buttons_list
import threading, io
from colorthief import ColorThief

class DiscIndicator(Gtk.ListBoxRow):
    __gtype_name__ = 'NocturneDiscIndicator'

    def __init__(self, discNumber:int):
        self.discNumber = discNumber
        super().__init__(
            child=Gtk.Label(
                label=_("Disc {}").format(self.discNumber),
                xalign=0,
                halign=Gtk.Align.START,
                css_classes=["title-2"]
            ),
            css_classes=["p10"],
            activatable=False
        )

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/page.ui')
class AlbumPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneAlbumPage'

    model = GObject.Property(type=models.Album)

    clamp_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    song_list_el = Gtk.Template.Child()
    context_wrap_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id, True)
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )
        integration.connect_to_model(self.id, 'song', self.update_song_list)
        context = CONTEXT_ALBUM.copy()
        del context['show-artist']
        if 'no-downloads' in integration.limitations:
            del context['download']
        context_buttons = get_context_buttons_list(context, self.id)
        for btn in context_buttons:
            if btn.get_name() != 'show-artist':
                self.context_wrap_el.append(btn)

        self.song_list_el.list_el.set_sort_func(self.song_list_sort_func)

    def song_list_sort_func(self, r1, r2):
        integration = get_current_integration()
        trackN1 = 0
        discN1 = 0
        trackN2 = 0
        discN2 = 0
        if isinstance(r1, DiscIndicator):
            trackN1 = -1
            discN1 = r1.discNumber
        else:
            if model1 := integration.loaded_models.get(r1.id):
                trackN1 = model1.get_property('track')
                discN1 = model1.get_property('discNumber')
        if isinstance(r2, DiscIndicator):
            trackN2 = -1
            discN2 = r2.discNumber
        else:
            if model2 := integration.loaded_models.get(r2.id):
                trackN2 = model2.get_property('track')
                discN2 = model2.get_property('discNumber')

        if discN1 == discN2:
            return trackN1 - trackN2
        else:
            return discN1 - discN2

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

    def update_song_list(self, song_list:list):
        # Generation token so overlapping calls can't interleave their queued idle mutations.
        generation = getattr(self, '_song_list_generation', 0) + 1
        self._song_list_generation = generation
        def is_current():
            return getattr(self, '_song_list_generation', None) == generation
        def run():
            integration = get_current_integration()
            GLib.idle_add(lambda: is_current() and self.song_list_el.list_el.remove_all())
            GLib.idle_add(lambda: is_current() and self.song_list_el.main_stack.set_visible_child_name('content' if len(song_list) > 0 else 'no-content'))
            song_ids = [s.get('id') for s in song_list]
            discs = []
            for song_id in song_ids:
                if not song_id in integration.loaded_models:
                    integration.verifySong(song_id, use_threading=False)

                model = integration.loaded_models.get(song_id)
                discNumber = model.get_property('discNumber')
                if discNumber > 0 and discNumber not in discs:
                    discs.append(discNumber)

                GLib.idle_add(lambda sid=song_id: is_current() and self.song_list_el.list_el.append(SongRow(sid)))
            for disc in discs:
                GLib.idle_add(lambda d=disc: is_current() and self.song_list_el.list_el.append(DiscIndicator(d)))

            GLib.idle_add(lambda: is_current() and self.song_list_el.list_el.invalidate_sort())
            GLib.idle_add(lambda: is_current() and self.connect_rows())
        if len(list(self.song_list_el.list_el)) != len(song_list):
            threading.Thread(target=run, daemon=True).start()

    def connect_rows(self):
        song_ids = []

        def set_action(row):
            row.set_action_name(None)
            row.set_action_target_value(GLib.Variant('a{sv}', {
                'songId': GLib.Variant('s', row.id),
                'songs': GLib.Variant('as', song_ids),
                'originId': GLib.Variant('s', self.id)
            }))
            row.set_action_name('app.play_song_from_list')

        for row in list(self.song_list_el.list_el):
            if isinstance(row, SongRow):
                song_ids.append(row.id)
        for row in list(self.song_list_el.list_el):
            if isinstance(row, SongRow):
                GLib.idle_add(set_action, row)

    @Gtk.Template.Callback()
    def format_rating_icon_name(self, obj, rating:int, index):
        return "starred-symbolic" if rating >= index else "non-starred-symbolic"

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_cover_pixel_size(self, obj, paintable:Gdk.Paintable) -> int:
        if paintable:
            self.update_background(paintable.save_to_png_bytes().get_data())
        return 240 if paintable else -1

    @Gtk.Template.Callback()
    def format_to_bool(self, obj, value) -> bool:
        return bool(value)

    @Gtk.Template.Callback()
    def format_starred_tooltip_text(self, obj, starred:bool) -> str:
        return _("Favorite") if starred else _("Not Favorite")

    @Gtk.Template.Callback()
    def format_starred_icon_name(self, obj, starred:bool) -> str:
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
        return "heart-filled-symbolic" if starred else "heart-outline-thick-symbolic"

    @Gtk.Template.Callback()
    def change_rating(self, button):
        integration = get_current_integration()
        target_value = GLib.Variant('a{sv}', {
            'model_id': GLib.Variant('s', self.id),
            'rating': GLib.Variant('i', int(button.get_name()))
        })
        self.get_root().activate_action("app.set_rating", target_value)

    def reload(self):
        pass

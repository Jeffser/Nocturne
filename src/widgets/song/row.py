# row.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango, Gio
from .queue import SongQueue
from ...integrations import get_current_integration
from ..containers import ContextContainer
from ...constants import CONTEXT_SONG, get_display_time
import threading, uuid, cairo
from datetime import datetime
from urllib.parse import urlparse

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/row.ui')
class SongRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneSongRow'

    icon_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    duration_el = Gtk.Template.Child()
    artist_container_el = Gtk.Template.Child()
    external_file_el = Gtk.Template.Child()
    suffixes_stack_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    check_el = Gtk.Template.Child()
    menu_button_el = Gtk.Template.Child()

    def __init__(self, id:str, draggable:bool=False, removable:bool=False):
        self.id = id
        self.draggable = draggable
        self.removable = removable # used in queue
        integration = get_current_integration()
        integration.verifySong(self.id)
        super().__init__(
            action_target=GLib.Variant.new_string(self.id)
        )

        self.star_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'title', self.update_title)
        integration.connect_to_model(self.id, 'artists', self.update_artists)
        integration.connect_to_model(self.id, 'duration', self.update_duration)
        integration.connect_to_model(self.id, 'starred', self.update_starred)
        integration.connect_to_model(self.id, 'homePageUrl', self.update_homepage) # for radios
        integration.connect_to_model(self.id, 'isExternalFile', self.update_is_external)
        integration.connect_to_model('currentSong', 'songId', self.current_song_changed)

        settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
        settings.bind(
            "show-context-button",
            self.menu_button_el,
            "visible",
            Gio.SettingsBindFlags.DEFAULT
        )

    def update_is_external(self, isExternalFile:bool):
        self.external_file_el.set_visible(isExternalFile)
        self.star_el.set_visible(not isExternalFile)

    def generate_context_menu(self) -> ContextContainer:
        integration = get_current_integration()
        model = integration.loaded_models.get(self.id)
        context_dict = CONTEXT_SONG.copy()
        context_dict["select"]["connection"] = self.select_clicked
        if not self.draggable:
            context_dict["play-next"]["sensitive"] = integration.loaded_models.get('currentSong').get_property('songId') != self.id
            context_dict["play-later"]["sensitive"] = integration.loaded_models.get('currentSong').get_property('songId') != self.id

        if not model or not (model.get_property('isRadio') and not self.draggable):
            del context_dict["edit"]
            del context_dict["delete"]

        if not model or model.get_property('isRadio') or model.get_property('isExternalFile'):
            del context_dict["add-to-playlist"]
            del context_dict["edit-lyrics"]
        if self.removable:
            context_dict["remove"]["connection"] = self.remove_selected
        else:
            del context_dict["remove"]
        return ContextContainer(context_dict, self.id)

    def update_title(self, title:str):
        self.title_el.set_label(title)
        self.title_el.set_tooltip_text(title)

    def update_duration(self, duration:int):
        if duration == -1:
            self.duration_el.set_label(_("Radio"))
        else:
            self.duration_el.set_label(get_display_time(duration))
        self.duration_el.set_visible(duration != 0)

    def update_artists(self, artists:list):
        integration = get_current_integration()
        model = integration.loaded_models.get(self.id)
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
            self.artist_container_el.set_sensitive(not model.get_property('isExternalFile'))
            self.artist_container_el.set_child(button)
        elif len(artists) > 1:
            menu = Gio.Menu()
            for artist in artists:
                item = Gio.MenuItem.new(
                    label=artist.get('name')
                )
                if not model.get_property('isExternalFile'):
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
            self.artist_container_el.set_sensitive(True)
            self.artist_container_el.set_child(button)

    def update_starred(self, starred:str):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.set_icon_name('starred-symbolic')
            local_dt = datetime.fromisoformat(starred).astimezone()
            self.star_el.set_tooltip_text(local_dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.set_icon_name('non-starred-symbolic')
            self.star_el.set_tooltip_text(_('Star'))

    def update_homepage(self, homepage:str):
        if homepage:
            button = Gtk.Button(
                action_name = 'app.visit_url',
                action_target = GLib.Variant.new_string(homepage),
                child = Gtk.Label(
                    ellipsize=Pango.EllipsizeMode.END,
                    label=urlparse(homepage).netloc.capitalize(),
                    css_classes=['subtitle']
                ),
                css_classes = ['p0', 'flat'],
                tooltip_text=homepage
            )
            self.artist_container_el.set_child(button)

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

    def select_clicked(self):
        queue = self.get_ancestor(SongQueue)
        queue.set_selected_mode(
            select=True,
            selected_row=self
        )

    def remove_selected(self):
        queue = self.get_ancestor(SongQueue)
        if queue.playlist_id: #is playlist
            target_value = GLib.Variant('a{sv}', {
                'playlist': GLib.Variant('s', queue.playlist_id),
                'indexes': GLib.Variant('as', str(list(queue.list_el).index(self)))
            })
            self.get_root().activate_action("app.remove_songs_from_playlist", target_value)
            queue.list_el.remove(self)
        else:
            integration = get_current_integration()
            all_ids = queue.get_all_ids()
            if len(all_ids) > 1:
                next_index = all_ids.index(self.id) + 1
                if len(all_ids) <= next_index:
                    next_index = 0
                integration.loaded_models.get('currentSong').set_property('songId', all_ids[next_index])
            else:
                integration.loaded_models.get('currentSong').set_property('songId', None)
            queue.list_el.remove(self)

    @Gtk.Template.Callback()
    def check_toggled(self, checkbutton):
        if not checkbutton.get_active():
            queue = self.get_ancestor(SongQueue)
            if len(queue.get_selected_rows()) == 0:
                queue.set_selected_mode()

    @Gtk.Template.Callback()
    def on_context_button_active(self, button, gparam):
        button.get_popover().set_child(self.generate_context_menu())

    @Gtk.Template.Callback()
    def show_popover(self, *args):
        rect = Gdk.Rectangle()
        if len(args) == 4:
            rect.x, rect.y = args[2], args[3]
        else:
            rect.x, rect.y = args[1], args[2]

        popover = Gtk.Popover(
            child=self.generate_context_menu(),
            pointing_to=rect,
            has_arrow=False
        )
        popover.set_parent(self)
        popover.popup()




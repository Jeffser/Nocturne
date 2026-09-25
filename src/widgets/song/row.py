# row.py

from gi.repository import GObject, Gtk, Adw, Gdk, GLib, Pango, Gio
from .queue import SongQueue
from ...integrations import get_current_integration, models
from ..containers import ContextContainer
from ...constants import CONTEXT_SONG, get_display_time
from urllib.parse import urlparse

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/row.ui')
class SongRow(Adw.ActionRow):
    __gtype_name__ = 'NocturneSongRow'

    model = GObject.Property(type=models.Song)

    icon_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    duration_el = Gtk.Template.Child()
    artist_container_el = Gtk.Template.Child()
    external_file_el = Gtk.Template.Child()
    suffixes_stack_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    check_el = Gtk.Template.Child()
    menu_button_el = Gtk.Template.Child()
    subtitle_wrapbox = Gtk.Template.Child()

    def __init__(self, id:str, draggable:bool=False, removable:bool=False):
        self.id = id
        self.draggable = draggable
        self.removable = removable # used in queue
        integration = get_current_integration()
        integration.verifySong(self.id)
        super().__init__(
            model=integration.loaded_models.get(self.id)
        )
        Gio.Settings(schema_id="com.jeffser.Nocturne").bind(
            "show-context-button",
            self.menu_button_el,
            "visible",
            Gio.SettingsBindFlags.DEFAULT
        )
        integration.connect_to_model(self.id, 'artists', self.update_artists)
        integration.connect_to_model(self.id, 'radioStreamUrl', self.update_radioStreamUrl) # for radios
        integration.connect_to_model(self.id, 'deleted', self.delete_status_changed)
        integration.connect_to_model('currentSong', 'songId', self.current_song_changed)

    @Gtk.Template.Callback()
    def format_action_target(self, obj, value, variant) -> GLib.Variant:
        return GLib.Variant(variant, value)

    @Gtk.Template.Callback()
    def format_duration(self, obj, duration:int) -> str:
        if duration == -1:
            return _("Radio")
        else:
            return get_display_time(duration)

    @Gtk.Template.Callback()
    def format_to_bool(self, obj, value) -> bool:
        return bool(value)

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
    def format_starred_visibility(self, obj, isExternalFile:bool, radioStreamUrl:str) -> bool:
        return not isExternalFile and not radioStreamUrl

    def delete_status_changed(self, status:bool):
        if status:
            if listbox := self.get_ancestor(Gtk.ListBox):
                listbox.remove(self)

    def generate_context_menu(self) -> ContextContainer:
        integration = get_current_integration()
        model = integration.loaded_models.get(self.id)
        context_dict = CONTEXT_SONG.copy()
        context_dict["select"]["connection"] = self.select_clicked

        context_dict["play-next"]["sensitive"] = integration.get_property('current-state').get_property('songId') != self.id
        context_dict["play-later"]["sensitive"] = integration.get_property('current-state').get_property('songId') != self.id

        context_dict['rating']['value'] = integration.loaded_models.get(self.id).get_property('userRating')

        if not model or not (model.get_property('radioStreamUrl') and not self.draggable):
            del context_dict["edit-radio"]
            del context_dict["delete-radio"]

        if "edit" in context_dict and 'no-edit-radio' in integration.limitations:
            del context_dict["edit-radio"]

        if 'no-downloads' in integration.limitations or not model or model.get_property('radioStreamUrl'):
            del context_dict["download"]

        if integration.__gtype_name__ == 'NocturneIntegrationOffline':
            context_dict["delete-download"]["sensitive"] = integration.get_property('current-state').get_property('songId') != self.id
        else:
            del context_dict["delete-download"]

        if not model or model.get_property('radioStreamUrl') or model.get_property('isExternalFile'):
            del context_dict["add-to-playlist"]
            del context_dict["show-album"]
            del context_dict["show-artist"]
            if not self.draggable:
                del context_dict["select"]
        if self.removable:
            context_dict["remove"]["connection"] = self.remove_selected
        else:
            del context_dict["remove"]
        return ContextContainer(context_dict, self.id)

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
            self.artist_container_el.set_child(button)
            self.artist_container_el.set_sensitive(not model.get_property('isExternalFile'))
        elif len(artists) >= 5:
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
            self.artist_container_el.set_child(button)
        else:
            container = Adw.WrapBox(
                line_spacing=2,
                child_spacing=2,
                wrap_policy=Adw.WrapPolicy.MINIMUM
            )
            for artist in artists:
                button = Gtk.Button(
                    action_name = 'app.show_artist',
                    action_target = GLib.Variant.new_string(artist.get('id')),
                    child = Gtk.Label(
                        ellipsize=Pango.EllipsizeMode.END,
                        label=artist.get('name'),
                        css_classes=['subtitle']
                    ),
                    css_classes = ['p0', 'flat'],
                    tooltip_text=artist.get('name')
                )
                container.append(button)
            self.artist_container_el.set_child(container)
            self.artist_container_el.set_sensitive(not model.get_property('isExternalFile'))
        self.artist_container_el.set_visible(self.artist_container_el.get_child())

    def update_starred(self, starred:bool):
        if starred:
            self.star_el.add_css_class('accent')
            self.star_el.remove_css_class('dim-label')
            self.star_el.set_icon_name('heart-filled-symbolic')
            self.star_el.set_tooltip_text(_('Favorite'))
        else:
            self.star_el.remove_css_class('accent')
            self.star_el.add_css_class('dim-label')
            self.star_el.set_icon_name('heart-outline-thick-symbolic')
            self.star_el.set_tooltip_text(_('Not Favorite'))

    def update_radioStreamUrl(self, radioStreamUrl:str):
        if not radioStreamUrl:
            return
        if radioStreamUrl := urlparse(radioStreamUrl):
            homepage_url = '{}://{}'.format(radioStreamUrl.scheme, radioStreamUrl.netloc)
            button = Gtk.Button(
                action_name = 'app.visit_url',
                action_target = GLib.Variant.new_string(homepage_url),
                child = Gtk.Label(
                    ellipsize=Pango.EllipsizeMode.END,
                    label=urlparse(homepage_url).netloc,
                    css_classes=['subtitle']
                ),
                css_classes = ['p0', 'flat'],
                tooltip_text=homepage_url
            )
            self.artist_container_el.set_child(button)

    def current_song_changed(self, songId:str):
        self.set_activatable(songId != self.id)
        if songId == self.id:
            self.icon_el.set_from_icon_name('sound-symbolic')
            self.icon_el.set_visible(True)
            self.add_css_class('accent')
        else:
            self.remove_css_class('accent')
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
            index_source = list(row.get_ancestor(Gtk.ListBox)).index(row)
            index_target = list(self.get_ancestor(Gtk.ListBox)).index(self)
            if y > self.get_height() / 2: # bottom
                index_target += 1
            integration = get_current_integration()
            queue_model = integration.get_property('current-state').get_property('queueModel')
            queue_model.splice(index_source, 1, [])
            queue_model.splice(index_target, 0, [Gtk.StringObject.new(row.id)])

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
            if self.id == integration.get_property('current-state').get_property('songId'):
                all_ids = queue.get_all_ids()
                if len(all_ids) > 1:
                    next_index = all_ids.index(self.id) + 1
                    if len(all_ids) <= next_index:
                        next_index = 0
                    integration.get_property('current-state').set_property('songId', all_ids[next_index])
                else:
                    integration.get_property('current-state').set_property('songId', None)
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






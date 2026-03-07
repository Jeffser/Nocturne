# page.py

from gi.repository import Gtk, Adw, Gdk, GLib, Pango
from ..song import SongRow
from ...navidrome import get_current_integration, models
import threading, uuid
from datetime import datetime, UTC

@Gtk.Template(resource_path='/com/jeffser/Nocturne/album/page.ui')
class AlbumPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneAlbumPage'

    cover_el = Gtk.Template.Child()
    name_el = Gtk.Template.Child()
    artist_el = Gtk.Template.Child()
    star_el = Gtk.Template.Child()
    song_list_el = Gtk.Template.Child()

    play_el = Gtk.Template.Child()

    def __init__(self, id:str):
        self.id = id
        integration = get_current_integration()
        integration.verifyAlbum(self.id, True)
        super().__init__(
            tag=str(uuid.uuid4())
        )

        self.star_el.set_action_target_value(GLib.Variant.new_string(self.id))
        self.play_el.set_action_target_value(GLib.Variant.new_string(self.id))

        integration.connect_to_model(self.id, 'name', self.update_name)
        integration.connect_to_model(self.id, 'artist', self.update_artist)
        integration.connect_to_model(self.id, 'artistId', self.update_artist_id, use_gtk_thread=False)
        integration.connect_to_model(self.id, 'starred', self.update_starred)
        integration.connect_to_model(self.id, 'song', self.update_song_list)
        integration.connect_to_model(self.id, 'coverArt', self.update_cover)

    def update_cover(self, coverArt:str=None):
        def update():
            integration = get_current_integration()
            paintable = integration.getCoverArt(coverArt, 480)
            GLib.idle_add(self.cover_el.set_from_paintable, paintable)
        threading.Thread(target=update).start()

    def update_name(self, name:str):
        self.name_el.set_label(name)
        self.name_el.set_visible(name)
        self.set_title(name or _('Album'))

    def update_artist(self, artist:str):
        self.artist_el.set_label(artist)
        self.artist_el.set_visible(artist)
        self.artist_el.set_tooltip_text(artist)

    def update_artist_id(self, artistId:str):
        self.artist_el.set_action_target_value(GLib.Variant.new_string(artistId))

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

    def update_song_list(self, song_list:list):
        self.song_list_el.list_el.remove_all()
        for song_dict in song_list:
            self.song_list_el.list_el.append(SongRow(song_dict.get('id')))
            

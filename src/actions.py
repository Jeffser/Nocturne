# actions.py

from . import navidrome
import random, threading
from datetime import datetime, UTC
from . import widgets as Widgets
from gi.repository import Gio, Adw, Gtk, GLib

# -- HELPER --

def __show_page(window, page):
    # page is Adw.NavigationViewPage
    window.main_bottom_sheet.set_open(False)
    window.main_split_view.set_show_content(True)
    window.main_navigationview.push(page)

def __show_custom_toast(window, model_id:str, title_property:str, subtitle:str, icon_name:str=None):
    integration = navidrome.get_current_integration()
    custom_widget = Adw.ActionRow(
        title=integration.loaded_models.get(model_id).get_property(title_property),
        subtitle=subtitle
    )
    album_art = Gtk.Image(
        css_classes=['card'],
        pixel_size=48,
        height_request=48,
        width_request=48,
        overflow=Gtk.Overflow.HIDDEN,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER
    )
    if icon_name:
        album_art.set_from_icon_name(icon_name)
    else:
        album_art.set_from_paintable(integration.getCoverArt(model_id))

    custom_widget.add_prefix(album_art)
    toast = Adw.Toast(
        custom_title=custom_widget,
        timeout=2
    )
    GLib.idle_add(window.toast_overlay.add_toast, toast)

# -- MISC --

def replace_root_page(window, page_tag:str):
    if page_tag:
        window.replace_root_page(page_tag)

def visit_url(window, url:str):
    Gio.AppInfo.launch_default_for_uri(url, None)

def toggle_star(window, model_id:str):
    integration = navidrome.get_current_integration()
    if model_id in integration.loaded_models:
        model = integration.loaded_models[model_id]
        if model.starred:
            if integration.unstar(model.id):
                model.starred = None
        else:
            if integration.star(model.id):
                model.starred = datetime.now(UTC).isoformat(timespec='microseconds').replace('+00:00', 'Z')

# -- RADIO --

def play_radio(window, model_id:str):
    if model_id in window.queue_page.song_list_el.get_all_ids():
        integration = navidrome.get_current_integration()
        integration.loaded_models.get('currentSong').songId = model_id
    else:
        window.queue_page.replace_queue([model_id])

def add_radio(window):
    def response(dialog, task, name_el, stream_el, homepage_el):
        if dialog.choose_finish(task) == 'save':
            name = name_el.get_text()
            stream = stream_el.get_text()
            homepage = homepage_el.get_text()
            if name and stream and homepage:
                integration = navidrome.get_current_integration()
                result = integration.createInternetRadioStation(
                    name,
                    stream,
                    homepage
                )
                if result:
                    threading.Thread(target=window.main_navigationview.get_visible_page().reload).start()
            #TODO show toast if all good (or bad)

    list_box = Gtk.ListBox(
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=['boxed-list']
    )
    name_el = Adw.EntryRow(title=_("Name"))
    list_box.append(name_el)
    stream_el = Adw.EntryRow(title=_("Stream Url"))
    list_box.append(stream_el)
    homepage_el = Adw.EntryRow(title=_("Homepage Url"))
    list_box.append(homepage_el)

    dialog = Adw.AlertDialog(
        heading=_("Add Radio Station"),
        extra_child=list_box
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("save", _("Save"))
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.choose(window, None, response, name_el, stream_el, homepage_el)


# -- SONG --

def play_song(window, model_id:str):
    if model_id in window.queue_page.song_list_el.get_all_ids():
        integration = navidrome.get_current_integration()
        integration.loaded_models.get('currentSong').songId = model_id
    else:
        window.queue_page.replace_queue([model_id])

def play_song_next(window, model_id:str):
    window.queue_page.play_next([model_id])
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'title', _("Playing Next"))
    ).start()

def play_song_later(window, model_id:str):
    window.queue_page.play_later([model_id])
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'title', _("Playing Later"))
    ).start()

# -- ALBUM --

def show_album(window, model_id:str):
    __show_page(window, Widgets.AlbumPage(model_id))

def play_album(window, model_id:str):
    integration = navidrome.get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.id, force_update=True, use_threading=False)
        window.queue_page.replace_queue([s.get('id') for s in album.song])

def play_album_next(window, model_id:str):
    integration = navidrome.get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.id, force_update=True, use_threading=False)
        window.queue_page.play_next([s.get('id') for s in album.song])
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Next"))
    ).start()

def play_album_later(window, model_id:str):
    integration = navidrome.get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.id, force_update=True, use_threading=False)
        window.queue_page.play_later([s.get('id') for s in album.song])
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Later"))
    ).start()

def play_album_shuffle(window, model_id:str):
    integration = navidrome.get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.id, force_update=True, use_threading=False)
        song_list = [s.get('id') for s in album.song]
        random.shuffle(song_list)
        window.queue_page.replace_queue(song_list)

# -- PLAYLIST --

def show_playlist(window, model_id:str):
    __show_page(window, Widgets.PlaylistPage(model_id))

def play_playlist(window, model_id:str):
    integration = navidrome.get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.id, force_update=True, use_threading=False)
        window.queue_page.replace_queue([s.get('id') for s in playlist.entry])

def play_playlist_next(window, model_id:str):
    integration = navidrome.get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.id, force_update=True, use_threading=False)
        window.queue_page.play_next([s.get('id') for s in playlist.entry])
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Next"))
    ).start()

def play_playlist_later(window, model_id:str):
    integration = navidrome.get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.id, force_update=True, use_threading=False)
        window.queue_page.play_later([s.get('id') for s in playlist.entry])
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Later"))
    ).start()

def play_playlist_shuffle(window, model_id:str):
    integration = navidrome.get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.id, force_update=True, use_threading=False)
        song_list = [s.get('id') for s in playlist.entry]
        random.shuffle(song_list)
        window.queue_page.replace_queue(song_list)

# -- ARTIST --

def show_artist(window, model_id:str):
    __show_page(window, Widgets.ArtistPage(model_id))


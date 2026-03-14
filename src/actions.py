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
        title=integration.loaded_models.get(model_id).get_property(title_property) if model_id else title_property,
        subtitle=subtitle
    )
    if icon_name:
        custom_widget.set_icon_name(icon_name)
    else:
        album_art = Gtk.Image(
            css_classes=['card'],
            pixel_size=48,
            height_request=48,
            width_request=48,
            overflow=Gtk.Overflow.HIDDEN,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            paintable=integration.getCoverArt(model_id)
        )
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

def update_radio(window, id:str=""):
    integration = navidrome.get_current_integration()
    model = integration.loaded_models[id] if id else None

    def response(dialog, task, name_el, stream_el, homepage_el, id:str):
        if dialog.choose_finish(task) == 'save':
            name = name_el.get_text()
            stream = stream_el.get_text()
            homepage = homepage_el.get_text()
            if name and stream and homepage:
                integration = navidrome.get_current_integration()
                if id:
                    result = integration.updateInternetRadioStation(
                        id,
                        name,
                        stream,
                        homepage
                    )
                else:
                    result = integration.createInternetRadioStation(
                        name,
                        stream,
                        homepage
                    )
                if result:
                    toast = Adw.Toast(
                        title=_("Radio updated successfully") if id else _("Radio added successfully"),
                        timeout=2
                    )
                    window.toast_overlay.add_toast(toast)
                    if id:
                        model.set_property('title', name)
                        model.set_property('streamUrl', stream)
                        model.set_property('homePageUrl', homepage)
                    else:
                        threading.Thread(target=window.main_navigationview.get_visible_page().reload).start()
                    return
            toast = Adw.Toast(
                title=_("Error updating radio") if id else _("Error adding radio"),
                timeout=2
            )
            window.toast_overlay.add_toast(toast)

    list_box = Gtk.ListBox(
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=['boxed-list']
    )
    name_el = Adw.EntryRow(title=_("Name"))
    if model and model.isRadio:
        name_el.set_text(model.title)
    list_box.append(name_el)
    stream_el = Adw.EntryRow(title=_("Stream Url"))
    if model and model.isRadio:
        stream_el.set_text(model.streamUrl)
    list_box.append(stream_el)
    homepage_el = Adw.EntryRow(title=_("Homepage Url"))
    if model and model.isRadio:
        homepage_el.set_text(model.homePageUrl)
    list_box.append(homepage_el)

    dialog = Adw.AlertDialog(
        heading=_("Update Radio Station") if id else _("Add Radio Station"),
        extra_child=list_box
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("save", _("Save"))
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.choose(window, None, response, name_el, stream_el, homepage_el, id)

def add_radio(window):
    update_radio(window)

def delete_radio(window, model_id:str):
    integration = navidrome.get_current_integration()
    model = integration.loaded_models.get(model_id)

    def response(dialog, task, id):
        if dialog.choose_finish(task) == 'delete':
            result = integration.deleteInternetRadioStation(id)
            if result:
                toast = Adw.Toast(
                    title=_("Radio deleted successfully"),
                    timeout=2
                )
                window.toast_overlay.add_toast(toast)
                threading.Thread(target=window.main_navigationview.get_visible_page().reload).start()
            else:
                toast = Adw.Toast(
                    title=_("Error deleting radio"),
                    timeout=2
                )
                window.toast_overlay.add_toast(toast)

    dialog = Adw.AlertDialog(
        heading=_("Delete Radio Station"),
        body=_("Are you sure you want to delete '{}'?").format(model.title)
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("delete", _("Delete"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.choose(window, None, response, model_id)

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

def play_songs(window, song_list:str):
    song_list = song_list.split('|')
    window.queue_page.replace_queue(song_list)

def play_songs_next(window, song_list:str):
    song_list = song_list.split('|')
    window.queue_page.play_next(song_list)
    if len(song_list)> 1:
        threading.Thread(
            target=__show_custom_toast,
            args=(window, None, _("{} Songs").format(len(song_list)), _("Playing Next"), "list-high-priority-symbolic")
        ).start()
    else:
        threading.Thread(
            target=__show_custom_toast,
            args=(window, song_list[0], "title", _("Playing Next"))
        ).start()

def play_songs_later(window, song_list:str):
    song_list = song_list.split('|')
    window.queue_page.play_later(song_list)
    if len(song_list) > 1:
        threading.Thread(
            target=__show_custom_toast,
            args=(window, None, _("{} Songs").format(len(song_list)), _("Playing Later"), "list-low-priority-symbolic")
        ).start()
    else:
        threading.Thread(
            target=__show_custom_toast,
            args=(window, song_list[0], "title", _("Playing Later"))
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

def update_playlist(window, model_id:str=None):
    integration = navidrome.get_current_integration()
    model = integration.loaded_models[model_id] if model_id else None

    def response(dialog, task, name_el, id:str):
        if dialog.choose_finish(task) == 'create':
            name = name_el.get_text()
            if name:
                result = integration.createPlaylist(
                    name,
                    playlistId=id
                )
                if result:
                    toast = Adw.Toast(
                        title=_("Playlist updated successfully") if id else _("Playlist created successfully"),
                        timeout=2
                    )
                    window.toast_overlay.add_toast(toast)
                    if id:
                        model.set_property('name', name)
                    else:
                        threading.Thread(target=window.main_navigationview.get_visible_page().reload).start()
                    return
            toast = Adw.Toast(
                title=_("Error updating playlist") if id else _("Error creating playlist"),
                timeout=2
            )
            window.toast_overlay.add_toast(toast)

    list_box = Gtk.ListBox(
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=['boxed-list']
    )
    name_el = Adw.EntryRow(title=_("Name"))
    if model:
        name_el.set_text(model.name)
    list_box.append(name_el)
    dialog = Adw.AlertDialog(
        heading=_("Update Playlist") if model_id else _("Create Playlist"),
        extra_child=list_box
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("create", _("Update") if model_id else _("Create"))
    dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
    dialog.choose(window, None, response, name_el, model_id)

def create_playlist(window):
    update_playlist(window)

def remove_songs_from_playlist(window, song_list:str):
    song_list = song_list.split('|')
    playlist_id = song_list[0]
    song_list = song_list[1:]

    integration = navidrome.get_current_integration()
    result = integration.updatePlaylist(
        playlist_id,
        songIndexToRemove=song_list
    )
    if result:
        if len(song_list) > 1:
            threading.Thread(
                target=__show_custom_toast,
                args=(window, playlist_id, "name", _("{} Songs Removed").format(len(song_list)))
            ).start()
        else:
            threading.Thread(
                target=__show_custom_toast,
                args=(window, playlist_id, "name", _("Song Removed"))
            ).start()

# -- ARTIST --

def show_artist(window, model_id:str):
    __show_page(window, Widgets.ArtistPage(model_id))


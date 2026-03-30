# actions.py

from .integrations import get_current_integration
import random, threading, os, shutil
from datetime import datetime, UTC
from . import widgets as Widgets
from gi.repository import Gio, Adw, Gtk, GLib
from .constants import DATA_DIR, BASE_NAVIDROME_DIR

# -- HELPER --

def __show_page(window, page):
    # page is Adw.NavigationViewPage
    window.main_bottom_sheet.set_open(False)
    window.main_split_view.set_show_content(True)
    window.main_navigationview.push(page)

def __show_custom_toast(window, model_id:str, title_property:str, subtitle:str, icon_name:str=None):
    integration = get_current_integration()
    custom_widget = Adw.ActionRow(
        title=integration.loaded_models.get(model_id).get_property(title_property) if model_id else title_property,
        subtitle=subtitle
    )
    if icon_name:
        custom_widget.set_icon_name(icon_name)
    else:
        gbytes, paintable = integration.getCoverArt(model_id)
        album_art = Gtk.Image(
            css_classes=['card'],
            height_request=48,
            width_request=48,
            overflow=Gtk.Overflow.HIDDEN,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        if paintable:
            album_art.set_from_paintable(paintable)
            album_art.set_pixel_size(48)
        else:
            album_art.set_from_icon_name("music-note-symbolic")
        custom_widget.add_prefix(album_art)
    toast = Adw.Toast(
        custom_title=custom_widget,
        timeout=2
    )
    GLib.idle_add(window.toast_overlay.add_toast, toast)

# -- MISC --

def replace_root_page(window, page_tag:str):
    try:
        tags = [item.page_tag for item in list(window.main_sidebar.get_items())]
        index = tags.index(page_tag)
        window.main_sidebar.set_selected(index)
        window.replace_root_page(page_tag)
    except Exception:
        pass

def visit_url(window, url:str):
    if url.startswith('file://'):
        url = Gio.File.new_for_path(url.removeprefix('file://')).get_uri()
        os.system('xdg-open {}'.format(url))
        return

    Gio.AppInfo.launch_default_for_uri(url, None)

def toggle_star(window, model_id:str):
    integration = get_current_integration()
    if model_id in integration.loaded_models:
        model = integration.loaded_models.get(model_id)
        if model.get_property('starred'):
            if integration.unstar(model.get_property('id')):
                model.set_property('starred', None)
        else:
            if integration.star(model.get_property('id')):
                model.set_property('starred', datetime.now(UTC).isoformat(timespec='microseconds').replace('+00:00', 'Z'))

def logout(window):
    integration = get_current_integration()
    integration.terminate_instance()
    settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
    settings.set_string('integration-user', '')
    settings.set_string('selected-instance-type', '')
    threading.Thread(target=window.queue_page.replace_queue, args=([],)).start()
    GLib.idle_add(window.main_stack.set_visible_child_name, 'welcome')
    GLib.idle_add(replace_root_page, window, 'home')
    dialogs = window.get_dialogs()
    if len(dialogs) > 0:
        dialogs[0].close()

def show_external_file_warning(window):
    dialog = Adw.AlertDialog(
        heading=_("External File"),
        body=_("This track was loaded from an external file, this means it will have less features compared to a track inside the library")
    )
    dialog.add_response('close', _('Close'))
    dialog.choose(window, None, lambda *_: None, None)

def update_navidrome_server(window):
    window.main_stack.set_visible_child_name('setup')

def delete_navidrome_server(window):
    def response(dialog, task):
        selected_option = dialog.choose_finish(task)
        if selected_option == "delete":
            shutil.rmtree(BASE_NAVIDROME_DIR)
        elif selected_option == "keep_data":
            os.remove(os.path.join(BASE_NAVIDROME_DIR, 'navidrome'))
        elif selected_option == "cancel":
            return
        toast = Adw.Toast(
            title=_("Navidrome server deleted successfully"),
            timeout=2
        )
        GLib.idle_add(window.toast_overlay.add_toast, toast)
        GLib.idle_add(window.main_stack.set_visible_child_name, 'welcome')

    dialog = Adw.AlertDialog(
        heading=_("Delete Navidrome Server"),
        body=_("Are you sure you want to delete the integrated Navidrome server?")
    )
    dialog.add_response('cancel', _('Cancel'))
    dialog.add_response("keep_data", _("Keep Data"))
    dialog.add_response("delete", _("Delete Everything"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.choose(window, None, response)

def open_popout_window(window):
    window.get_application().popout_window = Widgets.PopoutWindow(
        application=window.get_application(),
        player=window.playing_page.player,
        queue_list_el=window.queue_page.song_list_el
    )
    window.get_application().popout_window.present()
    window.sheet_status_stack.set_visible_child_name("pop-out")
    window.main_bottom_sheet.set_open(False)

def toggle_fullscreen(window):
    if len(window.queue_page.song_list_el.get_all_ids()) > 0:
        if not window.get_application().popout_window:
            open_popout_window(window)

        popout_window = window.get_application().popout_window
        if popout_window.is_fullscreen():
            popout_window.unfullscreen()
        else:
            popout_window.fullscreen()

def close_popout_window(window):
    if popoutwindow := window.get_application().popout_window:
        try:
            popoutwindow.close()
        except Exception as e: # might fail if already closed
            print(e)
            pass

        GLib.idle_add(window.queue_page.replace_list_element, popoutwindow.queue_page.song_list_el)
        window.sheet_status_stack.set_visible_child_name("content")
        if len(window.queue_page.song_list_el.get_all_ids()) > 0:
            window.main_bottom_sheet.set_open(True)
        window.get_application().popout_window = None

# -- RADIO --

def play_radio(window, model_id:str):
    if model_id in window.queue_page.song_list_el.get_all_ids():
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('songId', model_id)
    else:
        threading.Thread(target=window.queue_page.replace_queue, args=([model_id],)).start()

def update_radio(window, id:str=""):
    integration = get_current_integration()
    model = integration.loaded_models.get(id) if id else None

    def response(dialog, task, name_el, stream_el, id:str):
        if dialog.choose_finish(task) == 'save':
            name = name_el.get_text()
            stream = stream_el.get_text()
            if name and (stream or not stream_el.get_visible()):
                integration = get_current_integration()
                if id:
                    result = integration.updateInternetRadioStation(
                        id,
                        name,
                        stream
                    )
                else:
                    result = integration.createInternetRadioStation(
                        name,
                        stream
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
    if model and model.get_property('isRadio'):
        name_el.set_text(model.get_property('title'))
    list_box.append(name_el)
    stream_el = Adw.EntryRow(
        title=_("Stream Url"),
        visible=model.get_property('streamUrl')
    )
    if model and model.get_property('isRadio'):
        stream_el.set_text(model.get_property('streamUrl'))
    list_box.append(stream_el)

    dialog = Adw.AlertDialog(
        heading=_("Update Radio Station") if id else _("Add Radio Station"),
        extra_child=list_box
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("save", _("Save"))
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.choose(window, None, lambda *prms: threading.Thread(target=response, args=prms).start(), name_el, stream_el, id)

def add_radio(window):
    update_radio(window)

def delete_radio(window, model_id:str):
    integration = get_current_integration()
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
                del integration.loaded_models[id]
                threading.Thread(target=window.main_navigationview.get_visible_page().reload).start()
            else:
                toast = Adw.Toast(
                    title=_("Error deleting radio"),
                    timeout=2
                )
                window.toast_overlay.add_toast(toast)

    dialog = Adw.AlertDialog(
        heading=_("Delete Radio Station"),
        body=_("Are you sure you want to delete '{}'?").format(model.get_property('title'))
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("delete", _("Delete"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.choose(window, None, response, model_id)

# -- SONG --

def play_song(window, model_id:str):
    if model_id in window.queue_page.song_list_el.get_all_ids():
        integration = get_current_integration()
        integration.loaded_models.get('currentSong').set_property('songId', model_id)
    else:
        threading.Thread(target=window.queue_page.replace_queue, args=([model_id],)).start()

def play_song_next(window, model_id:str):
    threading.Thread(
        target=window.queue_page.play_next,
        args=([model_id],)
    ).start()
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'title', _("Playing Next"))
    ).start()

def play_song_later(window, model_id:str):
    threading.Thread(
        target=window.queue_page.play_later,
        args=([model_id],)
    ).start()
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'title', _("Playing Later"))
    ).start()

def play_songs(window, song_list:list):
    threading.Thread(
        target=window.queue_page.replace_queue,
        args=(song_list,)
    ).start()

def play_songs_next(window, song_list:list):
    threading.Thread(
        target=window.queue_page.play_next,
        args=(song_list,)
    ).start()
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

def play_songs_later(window, song_list:list):
    threading.Thread(
        target=window.queue_page.play_later,
        args=(song_list,)
    ).start()
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

def edit_lyrics(window, song_id:str):
    Widgets.LyricsDialog(song_id).present(window)

def save_lyrics(window, lyric_dict:dict):
    # lyric_dict KEYS
    # id:str
    # content:str

    integration = get_current_integration()
    model = integration.loaded_models.get(lyric_dict.get('id'))
    file_name_without_ext = '{}|{}|{}|{}'.format(
        model.get_property('title'),
        model.get_property('artist'),
        model.get_property('album') or model.get_property('title'),
        model.get_property('duration')
    )
    lyrics_dir = os.path.join(DATA_DIR, 'lyrics')
    lrc_path = os.path.join(lyrics_dir, file_name_without_ext+'.lrc')

    with open(lrc_path, 'w') as f:
        f.write(lyric_dict.get('content'))

    window.lyrics_page.song_changed(lyric_dict.get('id'))

    threading.Thread(
        target=__show_custom_toast,
        args=(window, lyric_dict.get('id'), "title", _("Lyrics Saved"))
    ).start()

def play_random_queue(window):
    integration = get_current_integration()
    threading.Thread(
        target=window.queue_page.replace_queue,
        args=(integration.getRandomSongs(),)
    ).start()

# -- ALBUM --

def show_album(window, model_id:str):
    __show_page(window, Widgets.AlbumPage(model_id))

def play_album(window, model_id:str):
    integration = get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.get_property('id'), force_update=True, use_threading=False)
        threading.Thread(
            target=window.queue_page.replace_queue,
            args=([s.get('id') for s in album.get_property('song')],)
        ).start()

def play_album_next(window, model_id:str):
    integration = get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.get_property('id'), force_update=True, use_threading=False)
        threading.Thread(
            target=window.queue_page.play_next,
            args=([s.get('id') for s in album.get_property('song')],)
        ).start()
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Next"))
    ).start()

def play_album_later(window, model_id:str):
    integration = get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.get_property('id'), force_update=True, use_threading=False)
        threading.Thread(
            target=window.queue_page.play_later,
            args=([s.get('id') for s in album.get_property('song')],)
        ).start()
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Later"))
    ).start()

def play_album_shuffle(window, model_id:str):
    integration = get_current_integration()
    album = integration.loaded_models.get(model_id)

    if album:
        integration.verifyAlbum(album.get_property('id'), force_update=True, use_threading=False)
        song_list = [s.get('id') for s in album.get_property('song')]
        random.shuffle(song_list)
        threading.Thread(
            target=window.queue_page.replace_queue,
            args=(song_list,)
        ).start()

# -- PLAYLIST --

def show_playlist(window, model_id:str):
    __show_page(window, Widgets.PlaylistPage(model_id))

def play_playlist(window, model_id:str):
    integration = get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        threading.Thread(
            target=window.queue_page.replace_queue,
            args=([s.get('id') for s in playlist.get_property('entry')],)
        ).start()

def play_playlist_next(window, model_id:str):
    integration = get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        threading.Thread(
            target=window.queue_page.play_next,
            args=([s.get('id') for s in playlist.get_property('entry')],)
        ).start()
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Next"))
    ).start()

def play_playlist_later(window, model_id:str):
    integration = get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        threading.Thread(
            target=window.queue_page.play_later,
            args=([s.get('id') for s in playlist.get_property('entry')],)
        ).start()
    threading.Thread(
        target=__show_custom_toast,
        args=(window, model_id, 'name', _("Playing Later"))
    ).start()

def play_playlist_shuffle(window, model_id:str):
    integration = get_current_integration()
    playlist = integration.loaded_models.get(model_id)

    if playlist:
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        song_list = [s.get('id') for s in playlist.get_property('entry')]
        random.shuffle(song_list)
        threading.Thread(
            target=window.queue_page.replace_queue,
            args=(song_list,)
        ).start()

def update_playlist(window, model_id:str=None):
    integration = get_current_integration()
    model = integration.loaded_models.get(model_id) if model_id else None

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
        name_el.set_text(model.get_property('name'))
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

def remove_songs_from_playlist(window, data:dict):
    playlist_id = data.get('playlist', "")
    song_list = data.get('indexes', [])

    integration = get_current_integration()
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

def prompt_add_songs_to_playlist(window, song_list:list):
    dialog = Widgets.playlist.PlaylistDialog(song_list)
    dialog.present(window)

def prompt_add_song_to_playlist(window, model_id:str):
    dialog = Widgets.playlist.PlaylistDialog([model_id])
    dialog.present(window)

def prompt_add_album_to_playlist(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    model = integration.loaded_models.get(model_id)
    dialog = Widgets.playlist.PlaylistDialog([s.get('id') for s in model.get_property('song')])
    dialog.present(window)

def add_songs_to_playlist(window, data):
    integration = get_current_integration()
    dialogs = window.get_dialogs()
    if len(dialogs) > 0:
        dialogs[0].close()

    if data.get('new_playlist'):
        response = integration.createPlaylist(
            name=data.get('new_playlist'),
            songId=data.get('songs')
        )
        if response:
            integration.verifyPlaylist(response, force_update=True, use_threading=False)
            if len(data.get("songs")) > 1:
                message = _("{} Songs Added").format(len(data.get("songs")))
            else:
                message = _("1 Song Added")
            threading.Thread(
                target=__show_custom_toast,
                args=(window, response, "name", message)
            ).start()

    elif data.get('playlist'):
        integration.verifyPlaylist(data.get('playlist'), force_update=True, use_threading=False)
        model = integration.loaded_models.get(data.get('playlist'))
        existing_songs = [e.get('id') for e in model.get_property('entry')]
        songs = [s for s in data.get('songs') if s not in existing_songs]
        response = integration.updatePlaylist(
            playlistId=data.get('playlist'),
            songIdToAdd=songs
        )

        message = []
        if len(songs) > 0:
            if len(songs) == 1:
                message.append(_("1 Song Added"))
            else:
                message.append(_("{} Songs Added").format(len(songs)))

        skipped_songs = len(data.get('songs')) - len(songs)
        if skipped_songs > 0:
            if skipped_songs == 1:
                message.append(_("1 Song Skipped"))
            else:
                message.append(_("{} Songs Skipped").format(skipped_songs))

        threading.Thread(
            target=__show_custom_toast,
            args=(window, data.get('playlist'), "name", ' | '.join(message))
        ).start()

def delete_playlist(window, model_id:str):
    integration = get_current_integration()
    model = integration.loaded_models.get(model_id)

    def show_toast(model):
        __show_custom_toast(window, model.get_property('id'), "name", _("Playlist Deleted"))
        del integration.loaded_models[model.id]
        window.main_navigationview.get_visible_page().reload()

    def response(dialog, task, model):
        if dialog.choose_finish(task) == "delete":
            result = integration.deletePlaylist(model.get_property('id'))
            if result:
                threading.Thread(target=show_toast, args=(model,)).start()

    dialog = Adw.AlertDialog(
        heading=_("Delete Playlist"),
        body=_("Are you sure you want to delete '{}'?").format(model.get_property('name'))
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("delete", _("Delete"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.choose(window, None, response, model)

# -- ARTIST --

def show_artist(window, model_id:str):
    __show_page(window, Widgets.ArtistPage(model_id))

def play_shuffle_artist(window, model_id:str):
    integration = get_current_integration()
    def run():
        integration.verifyArtist(model_id, force_update=True, use_threading=False)
        model = integration.loaded_models.get(model_id)
        if model:
            songs = []
            for album in model.get_property('album'):
                integration.verifyAlbum(album.get('id'), force_update=True, use_threading=False)
                album_model = integration.loaded_models.get(album.get('id'))
                if album_model:
                    songs.extend([s.get('id') for s in album_model.get_property('song')])
            if len(songs) > 0:
                play_songs(window, random.sample(songs, min(20, len(songs))))
    threading.Thread(target=run).start()

def play_radio_artist(window, model_id:str):
    integration = get_current_integration()
    def run():
        songs = integration.getSimilarSongs(model_id)
        if len(songs) > 0:
            play_songs(window, songs)
        else:
            toast = Adw.Toast(
                title=_("No songs found")
            )
            GLib.idle_add(window.toast_overlay.add_toast, toast)
    threading.Thread(target=run).start()

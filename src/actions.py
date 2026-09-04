# actions.py

from .integrations import get_current_integration, models
import random, threading, os, shutil, pathlib
from datetime import datetime, timedelta
from . import widgets as Widgets
from gi.repository import Gio, Adw, Gtk, GLib, Gst
from .constants import DATA_DIR, BASE_NAVIDROME_DIR, DOWNLOADS_DIR

# -- HELPER --

def __show_page(window, page:Adw.NavigationPage):
    application = window.get_application()
    active_window = application.props.active_window
    if active_window.__gtype_name__ == 'NocturnePopoutWindow':
        page_dialog = None
        for dialog in active_window.get_dialogs():
            if dialog.__gtype_name__ == 'NocturnePageDialog':
                GLib.idle_add(dialog.navigation_view.push, page)
                return
        GLib.idle_add(Widgets.PageDialog(page).present, active_window)
    else:
        GLib.idle_add(active_window.main_bottom_sheet.set_open, False)
        GLib.idle_add(active_window.main_split_view.set_show_content, True)
        GLib.idle_add(active_window.main_navigationview.push, page)
        for dialog in active_window.get_dialogs():
            GLib.idle_add(dialog.close)

def __show_custom_toast(window, model_id:str, title_property:str, subtitle:str, icon_name:str=None):
    # Thread safe
    integration = get_current_integration()
    model = integration.loaded_models.get(model_id)
    custom_widget = Adw.ActionRow(
        title=model.get_property(title_property) if model else title_property,
        subtitle=subtitle
    )
    if icon_name:
        GLib.idle_add(custom_widget.set_icon_name, icon_name)
    else:
        album_art = Gtk.Image(
            css_classes=['card'],
            height_request=48,
            width_request=48,
            overflow=Gtk.Overflow.HIDDEN,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            icon_name="music-note-symbolic",
            pixel_size=32
        )
        if model:
            if paintable := model.get_property('gdkPaintable'):
                GLib.idle_add(album_art.set_from_paintable, paintable)
                GLib.idle_add(album_art.set_pixel_size, 48)
        GLib.idle_add(custom_widget.add_prefix, album_art)
    toast = Adw.Toast(
        custom_title=custom_widget,
        timeout=2
    )
    GLib.idle_add(window.get_application().props.active_window.toast_overlay.add_toast, toast)

def __save_playlist_resume(window):
    # Check if current queue origin is a playlist if so, save the resume state
    # Call in different thread
    integration = get_current_integration()
    queue_origin = integration.loaded_models.get('currentSong').get_property('queueOrigin') or ""
    if model := integration.loaded_models.get(queue_origin):
        if isinstance(model, models.Playlist):
            timestamp = integration.loaded_models.get('currentSong').get_property('positionSeconds')
            current_song = integration.loaded_models.get('currentSong').get_property('songId')
            integration.savePlaylistResume(
                queue_origin_id=queue_origin,
                song_id=current_song,
                current_timestamp=timestamp
            )

def __replace_queue(window, songs:list, current_id:str=None, origin_id:str=""):
    integration = get_current_integration()
    __save_playlist_resume(window)
    integration.loaded_models.get('currentSong').set_property('queueOrigin', origin_id)
    queue_model = integration.loaded_models.get('currentSong').get_property('queueModel')
    GLib.idle_add(queue_model.remove_all)
    if len(songs) > 0:
        if current_id is None:
            current_id = songs[0]
        GLib.idle_add(queue_model.splice,
            0,
            0,
            [Gtk.StringObject.new(SongId) for SongId in songs]
        )
    GLib.idle_add(integration.loaded_models.get('currentSong').set_property, 'songId', current_id)
    if Gio.Settings(schema_id="com.jeffser.Nocturne").get_value('auto-play').unpack():
        threading.Thread(target=generate_auto_play_queue, args=(window, False), daemon=True).start()

def __play_next(window, songs:list):
    integration = get_current_integration()
    __save_playlist_resume(window)
    integration.loaded_models.get('currentSong').set_property('queueOrigin', "")
    current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
    queue_model = integration.loaded_models.get('currentSong').get_property('queueModel')
    if queue_model.get_property('n-items') == 0 or not current_song_id:
        __replace_queue(window, songs)
    else:
        current_song_index = 0
        for i, so in enumerate(list(queue_model)): # so=string object
            song_id = so.get_string()
            if song_id in songs and song_id != current_song_id:
                GLib.idle_add(queue_model.remove, i)
            elif song_id == current_song_id:
                current_song_index = i + 1
        GLib.idle_add(queue_model.splice,
            current_song_index,
            0,
            [Gtk.StringObject.new(SongId) for SongId in songs if SongId != current_song_id]
        )

def __play_later(window, songs:list):
    integration = get_current_integration()
    __save_playlist_resume(window)
    integration.loaded_models.get('currentSong').set_property('queueOrigin', "")
    current_song_id = integration.loaded_models.get('currentSong').get_property('songId')
    queue_model = integration.loaded_models.get('currentSong').get_property('queueModel')
    if queue_model.get_property('n-items') == 0 or not current_song_id:
        __replace_queue(window, songs)
    else:
        for i, so in enumerate(list(queue_model)): # so=string object
            song_id = so.get_string()
            if song_id in songs and song_id != current_song_id:
                GLib.idle_add(queue_model.remove, i)
        GLib.idle_add(queue_model.splice,
            queue_model.get_property('n-items'),
            0,
            [Gtk.StringObject.new(SongId) for SongId in songs if SongId != current_song_id]
        )

# -- MISC --

def reload(window):
    application = window.get_application()
    active_window = application.props.active_window
    if active_window.__gtype_name__ == 'NocturnePopoutWindow':
        for dialog in active_window.get_dialogs():
            if dialog.__gtype_name__ == 'NocturnePageDialog':
                dialog.navigation_view.get_visible_page().reload()
    else:
        active_window.main_navigationview.get_visible_page().reload()

def show_error(window, message:str):
    if app := window.get_application():
        dialog = Adw.AlertDialog(
            heading=_("Error"),
            body=message or _("No details provided")
        )
        dialog.add_response('close', _('Close'))
        GLib.idle_add(dialog.choose, app.props.active_window, None, None)

def search(window):
    homepage = None
    if app := window.get_application():
        active_window = app.props.active_window
        if active_window == app.main_window:
            active_window.replace_root_page('home')
            homepage = active_window.main_navigationview.find_page('home')
        else:
            for dialog in active_window.get_dialogs():
                if dialog.__gtype_name__ == 'NocturnePageDialog':
                    homepage = dialog.navigation_view.find_page('home')
            if not homepage:
                __show_page(active_window, Widgets.HomePage())
                for dialog in active_window.get_dialogs():
                    if dialog.__gtype_name__ == 'NocturnePageDialog':
                        homepage = dialog.navigation_view.find_page('home')
    if homepage:
        GLib.idle_add(homepage.search_bar.set_search_mode, not homepage.search_bar.get_search_mode())

def launch_playback(window):
    GLib.idle_add(window.main_stack.set_visible_child_name, 'loading')
    integration = get_current_integration()
    prev_month = datetime.now().replace(day=1) - timedelta(days=1)
    top_songs = []
    for songId, plays in integration.getPlaybackScrobble(prev_month.strftime("%m-%Y")):
        integration.verifySong(songId, use_threading=False)
        if songId in integration.loaded_models:
            top_songs.append((songId, plays))

    if len(top_songs) > 5:
        GLib.idle_add(window.main_stack.set_visible_child_name, 'playback')
        GLib.idle_add(window.main_stack.get_child_by_name('playback').setup, top_songs, prev_month)
        __replace_queue(window, [s[0] for s in top_songs])
    else:
        toast = Adw.Toast(
            title=_("Not enough data found for Nocturne Playback ({})").format(prev_month.strftime("%B %Y")),
            timeout=2
        )
        GLib.idle_add(window.toast_overlay.add_toast, toast)
        GLib.idle_add(window.main_stack.set_visible_child_name, 'content')

def generate_auto_play_queue(window, replace_on_finish:bool):
    integration = get_current_integration()
    integration.loaded_models.get('currentSong').set_property('generatingQueue', True)
    queue_model = integration.loaded_models.get('currentSong').get_property('queueModel')
    generated_queue_model = integration.loaded_models.get('currentSong').get_property('generatedQueue')
    generated_queue_model.remove_all()

    song_list = []
    if queue_model.get_property('n-items') > 0:
        artists = []
        for so in list(queue_model):
            if so:
                if model := integration.loaded_models.get(so.get_string()):
                    artists.append(model.artistId)
        if len(artists) > 0:
            main_artist = max(set(artists), key=artists.count)
            song_list = integration.getSimilarSongs(main_artist)

    # Remove repeated songs, if it ends up being less than 5 then just generate a random queue
    song_list = [s for s in song_list if s not in [so.get_string() for so in list(queue_model)]]
    if len(song_list) < 5:
        song_list = integration.getRandomSongs()

    generated_queue_model.splice(
        0,
        0,
        [Gtk.StringObject.new(s) for s in song_list]
    )

    integration.loaded_models.get('currentSong').set_property('generatingQueue', False)

    if replace_on_finish:
        __replace_queue(window, [so.get_string() for so in list(generated_queue_model)])

def set_equalizer_preset(window, preset_name:str):
    preset = {
        "flat": [0.0] * 6,
        "clarity": [-2.0, -4.0, 2.0, 5.0, 3.0, 1.0],
        "jazz": [4.0, 2.0, 1.0, -2.0, -5.0, -8.0],
        "rock": [5.0, 2.0, -2.0, 3.0, 2.0, 0.0],
        "classic": [2.0, -2.0, 0.0, 1.0, 2.0, 4.0],
        "acoustic": [-2.0, 3.0, 1.0, -2.0, 4.0, 2.0]
    }.get(preset_name, [0.0] * 6)

    settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
    for i, value in enumerate(preset):
        settings.set_double("eq-band-{}".format(i), value)

def replace_root_page(window, page_tag:str):
    try:
        index = [i for i, item in enumerate(list(window.main_sidebar.get_items())) if item.get_visible() and item.page_tag == page_tag][0]
        GLib.idle_add(window.main_sidebar.set_selected, index)
    except Exception as e:
        pass
    GLib.idle_add(window.replace_root_page, page_tag)

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
                model.set_property('starred', False)
        else:
            if integration.star(model.get_property('id')):
                model.set_property('starred', True)

def reset_window(window):
    threading.Thread(target=__replace_queue, args=(window,[]), daemon=True).start()
    page_tag = Gio.Settings(schema_id="com.jeffser.Nocturne").get_string('default-page-tag')
    GLib.idle_add(replace_root_page, window, page_tag)
    for page in list(window.main_navigationview):
        if isinstance(page, Adw.NavigationPage):
            if getattr(page, "reset", None):
                GLib.idle_add(page.reset)
    reload(window)

def logout(window):
    integration = get_current_integration()
    threading.Thread(target=integration.terminate_instance, daemon=True).start()
    settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
    settings.set_string('integration-user', '')
    settings.set_string('selected-instance-type', '')
    settings.set_strv('library-ids', [])
    threading.Thread(target=__replace_queue, args=(window,[]), daemon=True).start()
    GLib.idle_add(window.main_stack.set_visible_child_name, 'welcome')
    GLib.idle_add(replace_root_page, window, 'home')
    if settings.get_value('welcome-mode-home').unpack() == 'instance':
        pfp_destination_path = os.path.join(DATA_DIR, 'pfp')
        if os.path.isfile(pfp_destination_path):
            os.remove(pfp_destination_path)
        settings.set_string("welcome-user-home", "")
        settings.set_string("welcome-mode-home", "")
    if window.get_application().player.mpris_published:
        window.get_application().player.mpris.unpublish()
    for dialog in window.get_dialogs():
        GLib.idle_add(dialog.close)
    for page in list(window.main_navigationview):
        if isinstance(page, Adw.NavigationPage):
            GLib.idle_add(page.reset)

def show_external_file_warning(window):
    dialog = Adw.AlertDialog(
        heading=_("External File"),
        body=_("This track was loaded from an external file, this means it will have less features compared to a track inside the library")
    )
    dialog.add_response('close', _('Close'))
    GLib.idle_add(dialog.choose, window, None, lambda *_: None, None)

def update_navidrome_server(window):
    GLib.idle_add(window.main_stack.set_visible_child_name, 'setup')
    if dialog := window.get_visible_dialog():
        GLib.idle_add(dialog.close)

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
        window.toast_overlay.add_toast(toast)
        window.main_stack.set_visible_child_name('welcome')

    if dialog := window.get_visible_dialog():
        dialog.close()
    dialog = Adw.AlertDialog(
        heading=_("Delete Navidrome Server"),
        body=_("Are you sure you want to delete the integrated Navidrome server?")
    )
    dialog.add_response('cancel', _('Cancel'))
    dialog.add_response("keep_data", _("Keep Data"))
    dialog.add_response("delete", _("Delete Everything"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    GLib.idle_add(dialog.choose, window, None, response)

def open_popout_window(window, fullscreened:bool=False):
    if not window.get_application().popout_window:
        window.get_application().popout_window = Widgets.PopoutWindow(
            application=window.get_application(),
            fullscreened=fullscreened
        )
    GLib.idle_add(window.get_application().popout_window.present)

def toggle_fullscreen(window):
    integration = get_current_integration()
    if integration.loaded_models.get('currentSong').get_property('queueModel').get_property('n-items') > 0:
        if popout_window := window.get_application().popout_window:
            GLib.idle_add(popout_window.present)
            if popout_window.is_fullscreen():
                GLib.idle_add(popout_window.unfullscreen)
            else:
                GLib.idle_add(popout_window.fullscreen)
        else:
            open_popout_window(window, True)

def set_rating(window, data):
    integration = get_current_integration()
    if model := integration.loaded_models.get(data.get('model_id')):
        if new_rating := data.get('rating'):
            if new_rating == model.get_property('userRating'):
                new_rating = 0
            if integration.setRating(data.get('model_id'), new_rating):
                model.set_property('userRating', new_rating)

# -- PLAYER --

def player_toggle(window):
    player = window.get_application().player
    success, state, pending = player.gst.get_state(Gst.CLOCK_TIME_NONE)
    if success:
        if state == Gst.State.PLAYING:
            # Pause the song
            player.gst.set_state(Gst.State.PAUSED)
        else:
            # Play the song
            player.gst.set_state(Gst.State.PLAYING)

def player_play(window):
    window.get_application().player.gst.set_state(Gst.State.PLAYING)

def player_pause(window):
    window.get_application().player.gst.set_state(Gst.State.PAUSED)

def player_next(window):
    window.get_application().player.handle_song_change_request("next")

def player_previous(window):
    window.get_application().player.handle_song_change_request("previous")

def player_raise_volume(window):
    settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
    volume = settings.get_value('volume').unpack()
    volume = max(0, min(1, volume + 0.1))
    settings.set_double('volume', volume)

def player_lower_volume(window):
    settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
    volume = settings.get_value('volume').unpack()
    volume = max(0, min(1, volume - 0.1))
    settings.set_double('volume', volume)

# -- RADIO --

def play_radio(window, model_id:str):
    integration = get_current_integration()
    if model_id in [so.get_string() for so in integration.loaded_models.get('currentSong').get_property('queueModel')]:
        integration.loaded_models.get('currentSong').set_property('songId', model_id)
    else:
        __replace_queue(window, [model_id])

def update_radio(window, model_id:str=""):
    integration = get_current_integration()
    model = integration.loaded_models.get(model_id) if model_id else None

    def response(dialog, task, name_el, stream_el):
        if dialog.choose_finish(task) == 'save':
            name = name_el.get_text().strip() or _("No Name")
            stream = stream_el.get_text().strip()
            message = ""
            if not stream.startswith('http'):
                stream = 'http://' + stream
            if name and (stream or not stream_el.get_visible()):
                integration = get_current_integration()
                if model_id:
                    result = integration.updateInternetRadioStation(
                        model_id,
                        name,
                        stream
                    )
                else:
                    result = integration.createInternetRadioStation(
                        name,
                        stream
                    )
                if result:
                    message=_("Radio updated successfully") if model_id else _("Radio added successfully")
                    if model_id:
                        model.set_property('title', name)
                        model.set_property('radioStreamUrl', stream)
                    else:
                        threading.Thread(target=window.main_navigationview.get_visible_page().reload, daemon=True).start()
            if not message:
                message = _("Error updating radio") if model_id else _("Error adding radio")
            toast = Adw.Toast(
                title=message,
                timeout=2
            )
            GLib.idle_add(window.toast_overlay.add_toast, toast)

    list_box = Gtk.ListBox(
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=['boxed-list']
    )
    name_el = Adw.EntryRow(title=_("Name"))
    if model and model.get_property('radioStreamUrl'):
        name_el.set_text(model.get_property('title'))
    list_box.append(name_el)
    stream_el = Adw.EntryRow(
        title=_("Stream Url")
    )
    if model and model.get_property('radioStreamUrl'):
        stream_el.set_text(model.get_property('radioStreamUrl'))
    list_box.append(stream_el)

    dialog = Adw.AlertDialog(
        heading=_("Update Radio Station") if model_id else _("Add Radio Station"),
        extra_child=list_box
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("save", _("Save"))
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.choose(window, None, lambda *prms: threading.Thread(target=response, args=prms, daemon=True).start(), name_el, stream_el)

def add_radio(window):
    update_radio(window)

def delete_radio(window, model_id:str):
    integration = get_current_integration()
    model = integration.loaded_models.get(model_id)

    def do_delete():
        if integration.deleteInternetRadioStation(model_id):
            message = _("Radio deleted successfully")
            del integration.loaded_models[model_id]
            threading.Thread(target=window.main_navigationview.get_visible_page().reload, daemon=True).start()
        else:
            message = _("Error deleting radio")
        toast = Adw.Toast(
            title=message,
            timeout=2
        )
        GLib.idle_add(window.toast_overlay.add_toast, toast)


    def response(dialog, task):
        if dialog.choose_finish(task) == 'delete':
            threading.Thread(target=do_delete, daemon=True).start()

    dialog = Adw.AlertDialog(
        heading=_("Delete Radio Station"),
        body=_("Are you sure you want to delete '{}'?").format(model.get_property('title'))
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("delete", _("Delete"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    GLib.idle_add(dialog.choose, window, None, response)

# -- SONG --

def play_song(window, model_id:str):
    integration = get_current_integration()
    if model_id in [so.get_string() for so in integration.loaded_models.get('currentSong').get_property('queueModel')]:
        integration.loaded_models.get('currentSong').set_property('songId', model_id)
    else:
        __replace_queue(window, [model_id])

def play_song_from_list(window, data:dict):
    if song_id := data.get('songId'):
        __replace_queue(window, data.get('songs', [song_id]), song_id, origin_id=data.get('originId', ""))

def play_song_next(window, model_id:str):
    __play_next(window, [model_id])
    __show_custom_toast(window, model_id, 'title', _("Playing Next"))

def play_song_later(window, model_id:str):
    __play_later(window, [model_id])
    __show_custom_toast(window, model_id, 'title', _("Playing Later"))

def play_songs(window, song_list:list):
    __replace_queue(window, song_list)

def play_songs_next(window, song_list:list):
    __play_next(window, song_list)
    if len(song_list)> 1:
        __show_custom_toast(window, None, _("{} Songs").format(len(song_list)), _("Playing Next"), "list-high-priority-symbolic")
    else:
        __show_custom_toast(window, song_list[0], "title", _("Playing Next"))

def play_songs_later(window, song_list:list):
    __play_later(window, song_list)
    if len(song_list) > 1:
        __show_custom_toast(window, None, _("{} Songs").format(len(song_list)), _("Playing Later"), "list-low-priority-symbolic")
    else:
        __show_custom_toast(window, song_list[0], "title", _("Playing Later"))

def edit_lyrics(window):
    GLib.idle_add(Widgets.LyricsDialog().present, window.get_application().props.active_window)

def play_random_queue(window):
    integration = get_current_integration()
    __replace_queue(window, integration.getRandomSongs())

def show_song_details(window, model_id):
    dialog = Widgets.SongDetailsDialog(model_id)
    GLib.idle_add(dialog.present, window.get_application().props.active_window)

# -- ALBUM --

def show_album(window, model_id:str):
    __show_page(window, Widgets.AlbumPage(model_id))

def show_album_from_song(window, model_id:str):
    integration = get_current_integration()
    if model := integration.loaded_models.get(model_id):
        if album_id := model.get_property('albumId'):
            __show_page(window, Widgets.AlbumPage(album_id))

def play_album(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if album := integration.loaded_models.get(model_id):
        __replace_queue(window, [s.get('id') for s in album.get_property('song')], origin_id=model_id)

def play_album_next(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if album := integration.loaded_models.get(model_id):
        __play_next(window, [s.get('id') for s in album.get_property('song')])
        __show_custom_toast(window, model_id, 'name', _('Playing Next'))

def play_album_later(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if album := integration.loaded_models.get(model_id):
        __play_later(window, [s.get('id') for s in album.get_property('song')])
        __show_custom_toast(window, model_id, 'name', _('Playing Later'))

def play_album_shuffle(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if album := integration.loaded_models.get(model_id):
        song_list = [s.get('id') for s in album.get_property('song')]
        random.shuffle(song_list)
        __replace_queue(window, song_list, origin_id=model_id)

# -- PLAYLIST --

def show_playlist(window, model_id:str):
    __show_page(window, Widgets.PlaylistPage(model_id))

def play_playlist(window, model_id:str):
    integration = get_current_integration()
    if playlist := integration.loaded_models.get(model_id):
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        __replace_queue(window, [s.get('id') for s in playlist.get_property('entry')], origin_id=model_id)

def resume_playlist(window, model_id:str):
    integration = get_current_integration()
    integration.verifyPlaylist(model_id, force_update=True, use_threading=False)
    current_id, timestamp = integration.getPlaylistResume(model_id)
    integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
    __replace_queue(
        window,
        [s.get('id') for s in playlist.get_property('entry')],
        origin_id=model_id,
        current_id=current_id
    )
    nanoseconds = int(timestamp * Gst.SECOND)
    GLib.timeout_add(100, lambda: window.get_application().player.gst.seek_simple(
        Gst.Format.TIME,
        Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
        nanoseconds
    ) and False)

def play_playlist_next(window, model_id:str):
    integration = get_current_integration()
    if playlist := integration.loaded_models.get(model_id):
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        __play_next(window, [s.get('id') for s in playlist.get_property('entry')])
        __show_custom_toast(window, model_id, 'name', _("Playing Next"))

def play_playlist_later(window, model_id:str):
    integration = get_current_integration()
    if playlist := integration.loaded_models.get(model_id):
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        __play_later(window, [s.get('id') for s in playlist.get_property('entry')])
        __show_custom_toast(window, model_id, 'name', _("Playing Later"))

def play_playlist_shuffle(window, model_id:str):
    integration = get_current_integration()
    if playlist := integration.loaded_models.get(model_id):
        integration.verifyPlaylist(playlist.get_property('id'), force_update=True, use_threading=False)
        song_list = [s.get('id') for s in playlist.get_property('entry')]
        random.shuffle(song_list)
        __replace_queue(window, song_list, origin_id=model_id)

def update_playlist(window, model_id:str=None):
    integration = get_current_integration()

    def do_update(name:str):
        if result := integration.createPlaylist(name, playlistId=model_id):
            integration.verifyPlaylist(result, force_update=True, use_threading=False)
            window.setup_sidebar()
            window.main_navigationview.get_visible_page().reload()
            message = _("Playlist updated successfully") if model_id else _("Playlist created successfully")
        else:
            message = _("Error updating playlist") if model_id else _("Error creating playlist"),
        toast = Adw.Toast(
            title=message,
            timeout=2
        )
        GLib.idle_add(window.toast_overlay.add_toast, toast)

    def response(dialog, task, name_el):
        if dialog.choose_finish(task) == 'create':
            if name := name_el.get_text():
                threading.Thread(target=do_update, args=(name,), daemon=True).start()

    list_box = Gtk.ListBox(
        selection_mode=Gtk.SelectionMode.NONE,
        css_classes=['boxed-list']
    )
    name_el = Adw.EntryRow(title=_("Name"))
    if model := integration.loaded_models.get(model_id):
        name_el.set_text(model.get_property('name'))
    list_box.append(name_el)
    dialog = Adw.AlertDialog(
        heading=_("Update Playlist") if model_id else _("Create Playlist"),
        extra_child=list_box
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("create", _("Update") if model_id else _("Create"))
    dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
    GLib.idle_add(dialog.choose, window, None, response, name_el)

def create_playlist(window):
    update_playlist(window)

def remove_songs_from_playlist(window, data:dict):
    playlist_id = data.get('playlist', "")
    song_list = data.get('indexes', [])
    if playlist_id and song_list:
        integration = get_current_integration()
        if result := integration.updatePlaylist(playlist_id, songIndexToRemove=song_list):
            __show_custom_toast(window, playlist_id, "name", ngettext("{} Song Removed", "{} Songs Removed", len(song_list)).format(len(song_list)))

def prompt_add_songs_to_playlist(window, song_list:list):
    dialog = Widgets.playlist.PlaylistDialog(song_list)
    GLib.idle_add(dialog.present, window.get_application().props.active_window)

def prompt_add_song_to_playlist(window, model_id:str):
    dialog = Widgets.playlist.PlaylistDialog([model_id])
    GLib.idle_add(dialog.present, window.get_application().props.active_window)

def prompt_add_album_to_playlist(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if model := integration.loaded_models.get(model_id):
        dialog = Widgets.playlist.PlaylistDialog([s.get('id') for s in model.get_property('song')])
        GLib.idle_add(dialog.present, window.get_application().props.active_window)

def add_songs_to_playlist(window, data):
    integration = get_current_integration()
    for dialog in window.get_dialogs():
        GLib.idle_add(dialog.close)

    if data.get('new_playlist'):
        if response := integration.createPlaylist(name=data.get('new_playlist'), songId=data.get('songs')):
            integration.verifyPlaylist(response, force_update=True, use_threading=False)
            message = ngettext("{} Song Added", "{} Songs Added", len(data.get("songs"))).format(len(data.get("songs")))
            __show_custom_toast(window, response, "name", message)
            window.setup_sidebar()
    elif data.get('playlist'):
        integration.verifyPlaylist(data.get('playlist'), force_update=True, use_threading=False)
        if model := integration.loaded_models.get(data.get('playlist')):
            existing_songs = [e.get('id') for e in model.get_property('entry')]
            songs = [s for s in data.get('songs') if s not in existing_songs]
            response = integration.updatePlaylist(
                playlistId=data.get('playlist'),
                songIdToAdd=songs
            )
            message = []
            if len(songs) > 0:
                message.append(ngettext("{} Song Added", "{} Songs Added", len(songs)).format(len(songs)))

            skipped_songs = len(data.get('songs')) - len(songs)
            if skipped_songs > 0:
                message.append(ngettext("{} Song Skipped", "{} Songs Skipped", skipped_songs).format(skipped_songs))

            __show_custom_toast(window, data.get('playlist'), 'name', ' | '.join(message))

def delete_playlist(window, model_id:str):
    integration = get_current_integration()
    model = integration.loaded_models.get(model_id)

    def response(dialog, task, model):
        if dialog.choose_finish(task) == "delete":
            if result := integration.deletePlaylist(model.get_property('id')):
                __show_custom_toast(window, model.get_property('id'), "name", _("Playlist Deleted"))
                show_toast(model)
                del integration.loaded_models[model.id]
                window.main_navigationview.get_visible_page().reload()
                window.setup_sidebar()

    dialog = Adw.AlertDialog(
        heading=_("Delete Playlist"),
        body=_("Are you sure you want to delete '{}'?").format(model.get_property('name'))
    )
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("delete", _("Delete"))
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    GLib.idle_add(dialog.choose, window, None, response, model)

# -- ARTIST --

def show_artist(window, model_id:str):
    __show_page(window, Widgets.ArtistPage(model_id))

def show_artist_from_song(window, model_id:str):
    integration = get_current_integration()
    if model := integration.loaded_models.get(model_id):
        if artist_id := model.get_property('artistId'):
            __show_page(window, Widgets.ArtistPage(artist_id))

def show_artist_from_album(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if model := integration.loaded_models.get(model_id):
        if artist_id := model.get_property('artistId'):
            GLib.idle_add(__show_page, window, Widgets.ArtistPage(artist_id))
        elif artists := model.get_property('artists'):
            if artist_id := artists[0].get('id'):
                GLib.idle_add(__show_page, window, Widgets.ArtistPage(artist_id))

def play_shuffle_artist(window, model_id:str):
    integration = get_current_integration()
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

def play_radio_artist(window, model_id:str):
    integration = get_current_integration()
    songs = integration.getSimilarSongs(model_id)
    if len(songs) > 0:
        play_songs(window, songs)
    else:
        toast = Adw.Toast(
            title=_("No songs found")
        )
        GLib.idle_add(window.toast_overlay.add_toast, toast)

# -- DOWNLOADS --

def __request_song_download(model_id:str) -> bool:
    # returns true if download is started (not finished)
    # should be called in different thread (cause of verifySong)
    integration = get_current_integration()
    integration.verifySong(model_id, use_threading=False)
    if song_model := integration.loaded_models.get(model_id):
        download_queue = integration.loaded_models.get('currentSong').get_property('downloadQueueModel')
        download_model = models.SongDownload(songId=model_id)

        artist_name = song_model.get_property('artist').split(';')[0]
        if artists := song_model.get_property('artists'):
            artist_name = artists[0].get('name')
        file_title = '{} - {} - {}'.format(song_model.get_property('title'), song_model.get_property('album'), artist_name).replace('/', ' ')
        if any(pathlib.Path(DOWNLOADS_DIR).glob('{}.*'.format(file_title))):
            return False
        found, position = download_queue.find_with_equal_func(
            download_model,
            lambda item_a, item_b, ud: item_a.get_property('songId') == item_b.get_property('songId'),
            0
        )
        if found:
            return False
        GLib.idle_add(download_queue.insert, 0, download_model)
        callback = lambda frac, md=download_model: md.set_property('progress', frac)
        threading.Thread(target=integration.downloadSong, args=(model_id, file_title, callback), daemon=True).start()
        return True
    return False

def download_song(window, model_id:str):
    is_downloading = __request_song_download(model_id)
    if is_downloading:
        __show_custom_toast(
            window,
            model_id,
            'title',
            _("Download Started")
        )
    else:
        __show_custom_toast(
            window,
            model_id,
            'title',
            _("Already Downloaded")
        )

def download_songs(window, model_list:str):
    if len(model_list) == 1:
        download_song(window, model_list[0])
        return
    integration = get_current_integration()
    successful_starts = 0
    for songId in model_list:
        successful_starts += 1 if __request_song_download(songId) else 0

    if len(model_list) == successful_starts:
        __show_custom_toast(
            window,
            None,
            _("{} Songs").format(len(model_list)),
            _("Download Started")
        )
    elif successful_starts > 0:
        skipped_songs = len(song_ids) - successful_starts
        skip_message = ngettext("{} Song Skipped", "{} Songs Skipped", skipped_songs).format(skipped_songs)
        message = ngettext("{} Song ({})", "{} Songs ({})", successful_starts).format(successful_starts, skip_message)

        __show_custom_toast(
            window,
            None,
            message,
            _("Already Downloaded")
        )
    else:
        __show_custom_toast(
            window,
            None,
            _("Download Skipped"),
            _("Already Downloaded")
        )

def download_album(window, model_id:str):
    integration = get_current_integration()
    integration.verifyAlbum(model_id, force_update=True, use_threading=False)
    if model := integration.loaded_models.get(model_id):
        song_ids = [song.get('id') for song in model.get_property('song')]
        successful_starts = 0
        for songId in song_ids:
            successful_starts += 1 if __request_song_download(songId) else 0

        if len(song_ids) == successful_starts:
            __show_custom_toast(
                window,
                model_id,
                'name',
                _("Download Started")
            )
        elif successful_starts > 0:
            skipped_songs = len(song_ids) - successful_starts
            message = ngettext("Download Started ({} Song Skipped)", "Download Started ({} Songs Skipped)", skipped_songs).format(skipped_songs)
            __show_custom_toast(
                window,
                model_id,
                'name',
                message
            )
        else:
            __show_custom_toast(
                window,
                model_id,
                'name',
                _("Already Downloaded")
            )

def download_playlist(window, model_id:str):
    integration = get_current_integration()
    integration.verifyPlaylist(model_id, force_update=True, use_threading=False)
    if model := integration.loaded_models.get(model_id):
        song_ids = [song.get('id') for song in model.get_property('entry')]
        successful_starts = 0
        for songId in song_ids:
            successful_starts += 1 if __request_song_download(songId) else 0

        if len(song_ids) == successful_starts:
            __show_custom_toast(
                window,
                model_id,
                'name',
                _("Download Started")
            )
        elif successful_starts > 0:
            skipped_songs = len(song_ids) - successful_starts
            message = ngettext("Download Started ({} Song Skipped)", "Download Started ({} Songs Skipped)", skipped_songs).format(skipped_songs)
            __show_custom_toast(
                window,
                model_id,
                'name',
                message
            )
        else:
            __show_custom_toast(
                window,
                model_id,
                'name',
                _("Already Downloaded")
            )

def __request_download_delete(model_id:str) -> bool:
    # returns true if download is deleted
    # should call del loaded_models[id] after toast is shown
    integration = get_current_integration()
    if model := integration.loaded_models.get(model_id):
        try:
            model.set_property('deleted', True)
            os.remove(model.get_property('path'))
            return True
        except:
            return False
    return False

def delete_download(window, model_id:str):
    integration = get_current_integration()
    deleted = __request_download_delete(model_id)
    if deleted:
        __show_custom_toast(
            window,
            model_id,
            'title',
            _("Deleted")
        )
        del integration.loaded_models[model_id]

def delete_downloads(window, model_list:list):
    integration = get_current_integration()
    successful_deletes = 0
    for songId in model_list:
        deleted = __request_download_delete(songId)
        successful_deletes += 1 if deleted else 0
        if deleted:
            del integration.loaded_models[songId]

    __show_custom_toast(
        window,
        None,
        _("{} Songs").format(successful_deletes),
        _("Deleted")
    )



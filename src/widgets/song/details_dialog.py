# details_dialog.py

from gi.repository import Gtk, Adw, GLib
from ...integrations import get_current_integration
from ...constants import get_display_time

@Gtk.Template(resource_path='/com/jeffser/Nocturne/song/details_dialog.ui')
class SongDetailsDialog(Adw.Dialog):
    __gtype_name__ = 'NocturneSongDetailsDialog'

    cover_el = Gtk.Template.Child()
    title_el = Gtk.Template.Child()
    listbox_el = Gtk.Template.Child()

    def __init__(self, model_id:str):
        self.id = model_id
        integration = get_current_integration()
        super().__init__()

        value_transformations = {
            "size": lambda size: "{} MB".format(round(size * 0.000001, 2)),
            "starred": lambda starred: _("Yes") if starred else _("No"),
            "duration": lambda duration: get_display_time(duration),
            "bitRate": lambda bitRate: "{} kbps".format(bitRate),
            "bitDepth": lambda bitDepth: "{}-bit".format(bitDepth),
            "samplingRate": lambda samplingRate: "{} kHz".format(samplingRate / 1000),
            "musicBrainzId": lambda mbid: mbid or _("Not Found")
        }

        property_order = [
            "album", "artist", "artists", "musicBrainzId", "year", "duration", "starred", "discNumber", "track",
            "size", "contentType", "path", "suffix", "bitRate", "bitDepth", "samplingRate", "channelCount",
            "trackGain", "albumGain", "bpm", "genres"
        ]
        order_map = {name: i for i, name in enumerate(property_order)}

        song_details = integration.getSongDetails(self.id)
        self.title_el.set_label(song_details.get_property('title'))

        paintable = None
        if model := integration.loaded_models.get(self.id):
            paintable = model.get_property('gdkPaintable')
        self.cover_el.set_paintable(paintable)
        self.cover_el.set_visible(paintable)
        property_list = song_details.list_properties()
        property_list.sort(key=lambda x: order_map.get(x.get_name(), -1))

        for prop in property_list:
            if nick := prop.get_nick():
                raw_value = song_details.get_property(prop.get_name())
                if isinstance(raw_value, list):
                    expander = Adw.ExpanderRow(
                        title=nick
                    )
                    for item in raw_value:
                        row = Adw.ActionRow(
                            title=item.get('name', str(item)),
                            use_markup=False
                        )
                        if model_id := item.get('id'):
                            row.set_action_name('app.show_artist')
                            row.set_action_target_value(GLib.Variant('s', model_id))
                            row.set_activatable(True)
                        expander.add_row(row)
                    self.listbox_el.append(expander)
                else:
                    row = Adw.ActionRow(
                        title=nick,
                        subtitle=value_transformations.get(prop.get_name(), lambda val: str(val))(raw_value),
                        css_classes=['property'],
                        use_markup=False
                    )
                    if prop.get_name() == 'album':
                        if model_id := song_details.get_property('albumId'):
                            row.set_action_name('app.show_album')
                            row.set_action_target_value(GLib.Variant('s', model_id))
                            row.set_activatable(True)
                    elif prop.get_name() == 'artist':
                        if model_id := song_details.get_property('artistId'):
                            row.set_action_name('app.show_artist')
                            row.set_action_target_value(GLib.Variant('s', model_id))
                            row.set_activatable(True)
                    elif prop.get_name() == 'musicBrainzId':
                        if mbid := song_details.get_property('musicBrainzId'):
                            row.set_action_name('app.visit_url')
                            url = 'https://musicbrainz.org/recording/{}'.format(mbid)
                            row.set_action_target_value(GLib.Variant('s', url))
                            row.set_tooltip_text(url)
                            row.set_activatable(True)
                    self.listbox_el.append(row)

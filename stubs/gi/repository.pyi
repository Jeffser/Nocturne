from typing import Any

# Minimal stub for gi.repository names used in this project.
Adw: Any
Gtk: Any
GLib: Any
GObject: Any
Gdk: Any
Gio: Any
GdkPixbuf: Any
Gst: Any
Pango: Any

def require_version(name: str, version: str) -> None: ...
def require_foreign(name: str) -> None: ...

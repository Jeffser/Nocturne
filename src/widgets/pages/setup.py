# setup.py

from gi.repository import Gtk, Adw, Gio, GLib
from ...constants import BASE_NAVIDROME_DIR, CACHE_DIR, get_navidrome_path, get_navidrome_env

import os, requests, tarfile, threading, subprocess, platform

@Gtk.Template(resource_path='/com/jeffser/Nocturne/pages/setup.ui')
class SetupPage(Adw.NavigationPage):
    __gtype_name__ = 'NocturneSetupPage'

    main_stack = Gtk.Template.Child()
    downloading_status_page = Gtk.Template.Child()
    progressbar_el = Gtk.Template.Child()
    continue_button = Gtk.Template.Child()

    def get_latest_url(self) -> str:
        url = "https://api.github.com/repos/navidrome/navidrome/releases/latest"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            latest_tag = response.json().get('tag_name')
        except Exception as e:
            print(e)
            latest_tag = "v0.60.3"
        latest_tag = latest_tag.removeprefix("v")
        arch = {
            "x86_64": "amd",
            "amd64": "amd",
            "arm64": "arm",
            "aarch64": "arm",
        }.get(platform.machine().lower())
        return "https://github.com/navidrome/navidrome/releases/download/v{tag}/navidrome_{tag}_linux_{architecture}64.tar.gz".format(tag=latest_tag, architecture=arch)

    def download_worker(self):
        try:
            url = self.get_latest_url()
            print("Downloading Navidrome from: ", url)
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = response.headers.get('content-length')
            total_size = int(total_size) if total_size else None
            downloaded = 0
            download_path = os.path.join(CACHE_DIR, "navidrome.tar.gz")

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size:
                            GLib.idle_add(self.progressbar_el.set_fraction, downloaded / total_size)
                            GLib.idle_add(self.downloading_status_page.set_description, '{}%'.format(round(downloaded / total_size * 100)))

            GLib.idle_add(self.progressbar_el.pulse)
            GLib.idle_add(self.downloading_status_page.set_description, _("Installing"))
            with tarfile.open(download_path, "r:gz") as tar:
                tar.extractall(path=BASE_NAVIDROME_DIR, filter='fully_trusted')
            GLib.idle_add(self.start_server)
            settings = Gio.Settings(schema_id="com.jeffser.Nocturne")
            settings.set_boolean('use-integrated-server', True)
            GLib.idle_add(self.main_stack.set_visible_child_name, 'success')
            if os.path.isfile(download_path):
                os.remove(download_path)

        except Exception:
            self.main_stack.set_visible_child_name('error')

    def start_server(self):
        self.get_root().login_page.navidrome_proc = subprocess.Popen([get_navidrome_path()], env=get_navidrome_env())

    @Gtk.Template.Callback()
    def download_clicked(self, button):
        self.main_stack.set_visible_child_name('downloading')
        threading.Thread(target=self.download_worker).start()

    @Gtk.Template.Callback()
    def link_visited(self, button):
        self.continue_button.set_sensitive(True)

    @Gtk.Template.Callback()
    def continue_clicked(self, button):
        self.get_root().main_stack.set_visible_child_name('login')
        self.get_root().login_page.load_defaults()

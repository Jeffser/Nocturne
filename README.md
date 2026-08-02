<p align="center"><img src="https://jeffser.com/images/nocturne/logo.svg">
<h1 align="center">Nocturne</h1>

<p align="center">Nocturne is a Jellyfin, OpenSubsonic and Bandcamp client that brings all your music together in one place, Nocturne not only connects to existing instances but it's capable of installing and managing its own Navidrome instance</p>

<p align="center"><a href='https://flathub.org/apps/com.jeffser.Nocturne'><img width='190' alt='Download on Flathub' src='https://flathub.org/api/badge?locale=en'/></a></p>

---

> [!IMPORTANT]
> Please be aware that [GNOME Code of Conduct](https://conduct.gnome.org) applies to Nocturne before interacting with this repository.

> [!WARNING]
> AI generated issues and PRs will be denied, repeated offence will result in a ban from the repository.

## Features

- Exploration by songs, artists, albums, radios and playlists
- Playlist management
- Compatibility with Jellyfin, OpenSubsonic, Bandcamp and local files
- Audio equalizer and audio visualizer
- Mpris integration
- Integrated Navidrome instance management
- Automatic lyrics fetching
- Downloads and offline mode
- Cool interface

## Screenies

HomePage | Song Playing
:------------------:|:-----------------:
![screenie1](https://jeffser.com/images/nocturne/screenie1.png) | ![screenie2](https://jeffser.com/images/nocturne/screenie3.png)

## Install (Official)

These are the officially supported packages that have been validated and are guaranteed to be up to date with the project.

### Linux (Flatpak)

Most Linux distributions come with Flatpak preinstalled, make sure your device has [the Flathub repo enabled](https://flathub.org/en/setup).
```sh
flatpak install flathub com.jeffser.Nocturne
```

### Arch Linux (AUR)

Nocturne is packaged officially in the AUR, to install it first make sure you have an AUR helper such as [yay](https://github.com/jguer/yay).
```sh
yay -S nocturne
```

By default, this package is missing a dependency required to play videos. To add this functionality, install this package.
```sh
yay -S gst-plugin-gtk4
```

## Install (Unofficial)

Nocturne is an open source project that accepts and encourages the creation of independent packages, although I cannot guarantee that they are up to date.

### Debian

Nocturne is packaged unofficially in the official Debian archive (Available in Debian 14 'forky' and above). Install it via apt.
```sh
apt install nocturne
```

### NixOS/nix

Nocturne is packaged unofficially in nixpkgs.
You can either try it out using nix-shell:
```sh
nix-shell -p nocturne
```

or add it to your sytem packages:
```nix
environment.systemPackages = [
pkgs.nocturne
];
```

## Build

### Linux (Flatpak)

Dependencies are automatically managed and built depending on host environment.
```sh
flatpak-builder build com.jeffser.Nocturne.yml --force-clean --install-deps-from=flathub
flatpak-builder --run build com.jeffser.Nocturne.yml nocturne
```

### macOS

#### 1. Install Dependencies with [Homebrew](https://brew.sh/)
```sh
brew install python@3.14 meson ninja pkgconf \
  glib gtk4 libadwaita pygobject3 gstreamer \
  gobject-introspection libsecret \
  desktop-file-utils
```

#### 2. Install Project & Packages
```sh
# 1. Install blueprint-compiler
git clone https://github.com/GNOME/blueprint-compiler
cd blueprint-compiler
meson build --prefix=/usr/local
sudo ninja install -C build
cd ..

# 2. Clone the project
git clone https://github.com/Jeffser/Nocturne/
cd Nocturne

# 3. Install python packages
python3 -m venv ./venv
source ./venv/bin/activate
pip install requests colorthief syncedlyrics tinytag mpris-server
```

#### 3. Build Project
```sh
meson setup build --prefix=$HOME/.local
ninja -C build
ninja install -C build
```

#### 4. Run Development Build
```sh
nocturne
```

## Running Nocturne From Terminal

In addition to running Nocturne by opening it graphically, you can also start it from a terminal.
```sh
# Flatpak
flatpak run com.jeffser.Nocturne

# Others
nocturne
```

You can also control Nocturne from a terminal, to get started make sure Nocturne is running and then run the following command to see all the available options:

```sh
# Flatpak
flatpak run com.jeffser.Nocturne --help

# Others
nocturne --help
```

## Dependencies

The following dependencies are requirements of the project in case you want to package it.
- `python3 >= 3.13`
- `gtk4`
- `libadwaita-1 >= 1.9`
- `glib-2.0 >= 2.84.0`
- `libsecret`
- `gstreamer`
- `blueprint-compiler >= 0.18.0`
- `python-requests >= 2.33.1`
- `python-colorthief >= 0.2.1`
- `python-syncedlyrics >= 1.0.1`
- `python-mpris-server >= 0.10.0`
- `python-tinytag >= 2.2.1`
- `gst-plugin-gtk4` (optional, needed for video rendering)

## Special Thanks

### Translators

Language                | Contributors
:-----------------------|:-----------
Spanish                 | [Jeffry Samuel](https://github.com/jeffser)
Catalan                 | [Jordi Bultó](https://github.com/formajestically)
Basque                  | [Ibai Oihanguren Sala](https://ibaios.eus)
German                  | [Martin Prokoph](https://github.com/Motschen)
Russian                 | [Aleksandr Shamaraev](https://github.com/AlexanderShad) [gttn-84](https://github.com/gttn-84)
Simplified Chinese      | [Saul Gman](https://github.com/Ja4e)
Turkish                 | [Muhammed Emin Akalan](https://github.com/muhammedeminakalan)
Traditional Chinese     | [Yuan Chiu](https://yuaner.tw)
Croatian                | [Milo Ivir](https://github.com/milotype)
Telugu                  | [Aryan Karamtoth](https://github.com/spaciouskarter78)
Brazilian Portuguese    | [Rikelry Souza](https://github.com/Rikelry)

## Legal Disclaimer

- Nocturne is an independent application and is not affiliated with, endorsed, or sponsored by OpenSubsonic, Bandcamp, or Jellyfin. All logos and illustrative assets used within the app are the property of their respective owners. All rights are reserved by their respective holders, and will be taken down if requested.

- Nocturne functions strictly as a client application. All network connections and data transfers are performed exclusively at the request and authorization of the server owner. Nocturne does not independently access or host any content.

- Nocturne does not facilitate, encourage, or provide mechanisms for music piracy. Users are responsible for ensuring they have the legal right to access and stream the content hosted on the servers they connect to.

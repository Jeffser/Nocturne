<p align="center"><img src="https://jeffser.com/images/nocturne/logo.svg">
<h1 align="center">Nocturne</h1>

<p align="center">Nocturne is a Navidrome / Jellyfin client that brings all your music together in one place, Nocturne not only connects to existing instances but it's capable of installing and managing it's own Navidrome instance</p>

<p align="center"><a href='https://flathub.org/apps/com.jeffser.Nocturne'><img width='190' alt='Download on Flathub' src='https://flathub.org/api/badge?locale=en'/></a></p>

---

> [!IMPORTANT]
> Please be aware that [GNOME Code of Conduct](https://conduct.gnome.org) applies to Nocturne before interacting with this repository.

> [!WARNING]
> AI generated issues and PRs will be denied, repeated offense will result in a ban from the repository.

## Features

- Exploration by songs, artists, albums, radios and playlists
- Playlist management
- Mpris integration
- Integrated Navidrome instance management
- Cool interface
- Automatic lyrics fetching

## Screenies

HomePage | Song Queue | Lyrics | Song List | Album Page
:------------------:|:-----------------:|:----------------:|:---------------------------:|:--------------------:
![screenie1](https://jeffser.com/images/nocturne/screenie1.png) | ![screenie2](https://jeffser.com/images/nocturne/screenie2.png) | ![screenie3](https://jeffser.com/images/nocturne/screenie3.png) | ![screenie4](https://jeffser.com/images/nocturne/screenie4.png) | ![screenie5](https://jeffser.com/images/nocturne/screenie5.png)

## Dependencies
The following dependencies are requirements of the project.
- `python3 >= 3.13`
- `gtk4`
- `libadwaita-1 >= 1.9`
- `glib-2.0 >= 2.84.0`
- `libsecret`
- `gstreamer`
- `blueprint-compiler >= 0.18.0`

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
pip install requests colorthief favicon mutagen mpris-server
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

## Special Thanks
### Translators

Language                | Contributors
:-----------------------|:-----------
Spanish              | [Jeffry Samuel](https://github.com/jeffser)

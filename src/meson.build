pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'nocturne'
gnome = import('gnome')

blueprints = files(
  'ui/window.blp',
  'ui/shortcuts-dialog.blp',
  'ui/preferences.blp',

  'ui/playing/footer.blp',
  'ui/playing/control_page.blp',
  'ui/playing/queue_page.blp',
  'ui/playing/lyrics_page.blp',
  'ui/playing/popout_window.blp',

  'ui/pages/home.blp',
  'ui/pages/login.blp',
  'ui/pages/artists.blp',
  'ui/pages/playlists.blp',
  'ui/pages/songs.blp',
  'ui/pages/albums.blp',
  'ui/pages/albums_all.blp',
  'ui/pages/radios.blp',
  'ui/pages/welcome.blp',
  'ui/pages/setup.blp',

  'ui/album/button.blp',
  'ui/album/page.blp',
  'ui/album/row.blp',

  'ui/artist/button.blp',
  'ui/artist/page.blp',
  'ui/artist/row.blp',

  'ui/playlist/button.blp',
  'ui/playlist/page.blp',
  'ui/playlist/row.blp',
  'ui/playlist/dialog.blp',
  'ui/playlist/selector_row.blp',

  'ui/song/row.blp',
  'ui/song/queue.blp',
  'ui/song/small_row.blp',

  'ui/containers/carousel.blp',
  'ui/containers/wrapbox.blp',

  'ui/lyrics/dialog.blp',
  'ui/lyrics/edit_row.blp',
)

blueprints = custom_target('blueprints',
  input: blueprints,
  output: '.',
  command: [
    find_program('blueprint-compiler', version: '>= 0.18.0'),
    'batch-compile',
    '@OUTPUT@',
    '@CURRENT_SOURCE_DIR@',
    '@INPUT@'
  ],
)

gnome.compile_resources(
  'nocturne',
  'nocturne.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
  source_dir: meson.current_source_dir(),
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'nocturne.in',
  output: 'nocturne',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

nocturne_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'actions.py',
  'constants.py',
  'preferences.py',
]

install_data(nocturne_sources, install_dir: moduledir)

subdir('widgets')
subdir('integrations')
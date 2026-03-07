moduledir = get_option('prefix') / get_option('datadir') / meson.project_name() / 'nocturne' / 'widgets'

widgets = [
  '__init__.py',
]

install_data(widgets, install_dir: moduledir)

subdir('playing')
subdir('pages')
subdir('album')
subdir('artist')
subdir('playlist')
subdir('song')
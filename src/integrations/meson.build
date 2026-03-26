moduledir = get_option('prefix') / get_option('datadir') / meson.project_name() / 'nocturne' / 'integrations'

widgets = [
  '__init__.py',
  'secret.py',
  'models.py',
  'local.py',
  'navidrome.py',
  'base.py',
]

install_data(widgets, install_dir: moduledir)
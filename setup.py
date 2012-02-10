from distutils.core import setup, Extension

pkg = 'Extensions.MeteoViewer'
setup (name = 'enigma2-plugin-extensions-meteoviewer',
       version = '1.68',
       description = 'meteo pictures viewer',
       packages = [pkg],
       package_dir = {pkg: 'plugin'},
       package_data = {pkg:
           ['plugin.png']},
      )

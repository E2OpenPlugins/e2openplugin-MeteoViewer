from distutils.core import setup
import setup_translate

pkg = 'Extensions.MeteoViewer'
setup (name = 'enigma2-plugin-extensions-meteoviewer',
       version = '1.73',
       description = 'meteo pictures viewer',
       packages = [pkg],
       package_dir = {pkg: 'plugin'},
       package_data = {pkg: ['*.png', '*.xml', '*/*.png', 'locale/*/LC_MESSAGES/*.mo']},
       cmdclass = setup_translate.cmdclass, # for translation
      )

from distutils.core import setup
import setup_translate

pkg = 'Extensions.AutoFan'
setup(name = 'enigma2-plugin-extensions-autofan',
	version = '1.0.3',
	description = 'control fan for osmega',
	packages = [pkg],
	package_dir = {pkg: 'plugin'},
	package_data = {pkg: ['locale/*.pot', 'locale/*/LC_MESSAGES/*.mo']},
	cmdclass = setup_translate.cmdclass, # for translation
	)

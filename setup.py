#!/usr/bin/env python

from setuptools import setup

__version__ = None  # pyflakes
execfile('buck/pprint/version.py')

setup(
    name = 'buck.pprint',
    version = __version__,
    description = "A fork of the cpython's pprint which gives standard indentation.",
    long_description = open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    author = 'Buck Golemon',
    author_email = 'buck.golemon@gmail.com',
	url = 'https://github.com/bukzor/buck.pprint',
	license = 'LICENSE.txt',
    packages = ['buck.pprint'],
	namespace_packages = ['buck'],
    classifiers = [
		"Development Status :: 3 - Alpha",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Natural Language :: English",
		"Operating System :: OS Independent",
		"Topic :: Software Development :: Code Generators",
    ],
	test_suite = 'buck.pprint.test',
)

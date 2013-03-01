#!/usr/bin/env python

from distutils.core import setup

__version__ = None  # pyflakes
execfile('pprint2/version.py')

setup(
    name = 'pprint2',
    version = __version__,
    description = 'A fork of the stdlib pprint which uses standard indentation',
    long_description = open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    author = 'Buck Golemon',
    author_email = 'buck.golemon@gmail.com',
    url = '(TODO)',
    packages = [
        'pprint2',
    ],
	## 'TODO: Add trove classifiers (http://pypi.python.org/pypi?%3Aaction=list_classifiers)'
    classifiers = [
    ]
)

from setuptools import setup

config = {
    'description': 'A simple RTL design and simulation toolkit.',
    'author': 'UC Santa Barbara Computer Architecture Lab',
    'url': 'https://github.com/UCSBarchlab/PyRTL',
    'download_url': 'https://github.com/UCSBarchlab/PyRTL/tarball/master'
    'author_email': 'sherwood@cs.ucsb.edu',
    'version': '0.1',
    'install_requires': ['pyparsing'],
    'packages': ['pyrtl'],
    'scripts': [],
    'name': 'PyRTL'
}

setup(**config)

from setuptools import setup

config = {
    'name': 'pyrtl',
    'description': 'A RTL-level hardware design and simulation toolkit.',
    'author': 'Timothy Sherwood, John Clow, and the UCSBarchlab',
    'url': 'http://ucsbarchlab.github.io/PyRTL/',
    'download_url': 'https://github.com/UCSBarchlab/PyRTL/tarball/master',
    'author_email': 'sherwood@cs.ucsb.edu',
    'version': '0.8',
    'install_requires': ['pyparsing'],
    'packages': ['pyrtl'],
    'scripts': []
}

setup(**config)

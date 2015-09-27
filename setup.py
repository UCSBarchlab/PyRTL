from setuptools import setup

setup(
    name = 'pyrtl',
    version = '0.8.0',
    packages =  ['pyrtl'],
    description = 'RTL-level Hardware Design and Simulation Toolkit',
    author =  'Timothy Sherwood, John Clow, and UCSBarchlab',
    author_email =  'sherwood@cs.ucsb.edu',
    url =  'http://ucsbarchlab.github.io/PyRTL/',
    download_url = 'https://github.com/UCSBarchlab/PyRTL/tarball/0.8.0',
    install_requires =  ['six'],
    test_requires =  ['tox','nose'],
    extras_requires =  ['pyparsing'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'Topic :: System :: Hardware']
)

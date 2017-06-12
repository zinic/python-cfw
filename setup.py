#!/usr/bin/env python
from setuptools import setup, find_packages

# Installation requirements needed absolutely for the program to run
install_requires = [
]

# Additional feature sets and their requirements
extras_require = {
}

setup(
    name='cfw',
    version='0.0.1',
    description='Python Command Line Interface Library',
    author='John Hopper',
    author_email='john.hopper@jpserver.net',
    packages=find_packages(),

    install_requires=install_requires,
    extras_require=extras_require,

    entry_points={
        'console_scripts': [],
    }
)

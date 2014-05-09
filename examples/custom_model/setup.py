#!/usr/bin/env python

from distutils.core import setup

setup(
    name='custom_model',
    description='Custom model example for jwstlib.models',
    packages=['custom_model', 'custom_model.tests'],
    package_dir={'custom_model': 'lib'},
    package_data={'custom_model': ['schemas/*.schema.json'],
                  'custom_model.tests' : ['data/*.fits']}
    )

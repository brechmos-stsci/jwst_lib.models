#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

setup(
    setup_requires=['d2to1>=0.2.11', 'stsci.distutils>=0.3.7'],
    namespace_packages=['jwst_lib'], packages=['jwst_lib'],
    d2to1=True
)

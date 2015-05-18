# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os
import shutil
import tempfile

import numpy as np
from astropy.io import fits

from .. import DataModel

TMP_FITS = None
TMP_DIR = None


def setup():
    global TMP_DIR, TMP_FITS

    TMP_DIR = tempfile.mkdtemp()
    TMP_FITS = os.path.join(TMP_DIR, 'tmp.fits')


def teardown():
    shutil.rmtree(TMP_DIR)


def test_history_from_model_to_fits():
    m = DataModel()
    m.history.append("First entry")
    m.history.append("Second entry")
    assert m.history == ["First entry", "Second entry"]
    m.save(TMP_FITS)

    hdulist = fits.open(TMP_FITS)
    assert list(hdulist[0].header['HISTORY']) == ["First entry", "Second entry"]
    hdulist.close()

    m = DataModel(TMP_FITS)
    m2 = DataModel()
    m2.update(m)
    m2.history = m.history

    print(m2.history)
    assert m2.history == ["First entry", "Second entry"]

    m2.save(TMP_FITS)

    hdulist = fits.open(TMP_FITS)
    assert list(hdulist[0].header['HISTORY']) == ["First entry", "Second entry"]
    hdulist.close()


def test_history_from_fits():
    header = fits.Header()
    header['HISTORY'] = "First entry"
    header['HISTORY'] = "Second entry"
    fits.writeto(TMP_FITS, np.array([]), header, clobber=True)

    m = DataModel(TMP_FITS)
    assert m.history == ["First entry", "Second entry"]

    del m.history[0]
    m.history.append("Third entry")
    assert m.history == ["Second entry", "Third entry"]

    m.save(TMP_FITS)

    m = DataModel(TMP_FITS)
    assert m.history == ["Second entry", "Third entry"]

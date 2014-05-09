from ..bad_pixel_mask import *

import os

import numpy as np

FITS_FILE = os.path.join(
    os.path.dirname(__file__), "data", "bad_pixel_mask.fits")


def test_bad_pixel_mask_open():
    with MiriBadPixelMaskModel(FITS_FILE) as dm:
        assert dm.mask.dtype == np.uint16
        assert dm.field_def[1]['name'] == 'HOT'


def test_extra_metadata():
    with MiriBadPixelMaskModel(FITS_FILE) as dm:
        assert dm.mask.dtype == np.uint16
        assert dm.field_def[1]['name'] == 'HOT'


def test_get_mask_for_field():
    with MiriBadPixelMaskModel(FITS_FILE) as dm:
        assert dm.mask.dtype == np.uint16
        assert dm.field_def[1]['name'] == 'HOT'

        hot_pixels = dm.get_mask_for_field('HOT')
        assert np.sum(hot_pixels) == 2330

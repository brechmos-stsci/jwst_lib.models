import os
import shutil
import tempfile

from nose.tools import raises

import numpy as np
from numpy.testing.decorators import knownfailureif
from numpy.testing import assert_array_equal

from .. import DataModel, ImageModel, RampModel, open
from .. import schema

ROOT_DIR = None
FITS_FILE = None
TMP_FITS = None
TMP_FITS2 = None
TMP_YAML = None
TMP_JSON = None
TMP_DIR = None


def setup():
    global ROOT_DIR, FITS_FILE, TMP_DIR, TMP_FITS, TMP_YAML, TMP_JSON, TMP_FITS2
    ROOT_DIR = os.path.dirname(__file__)
    FITS_FILE = os.path.join(ROOT_DIR, 'test.fits')

    TMP_DIR = tempfile.mkdtemp()
    TMP_FITS = os.path.join(TMP_DIR, 'tmp.fits')
    TMP_YAML = os.path.join(TMP_DIR, 'tmp.yaml')
    TMP_JSON = os.path.join(TMP_DIR, 'tmp.json')
    TMP_FITS2 = os.path.join(TMP_DIR, 'tmp2.fits')


def teardown():
    shutil.rmtree(TMP_DIR)


@raises(AttributeError)
def test_from_new_hdulist():
    from astropy.io import fits
    hdulist = fits.HDUList()
    with open(hdulist) as dm:
        sci = dm.data


def test_from_new_hdulist2():
    from astropy.io import fits
    hdulist = fits.HDUList()
    data = np.empty((50, 50))
    primary = fits.PrimaryHDU()
    hdulist.append(primary)
    science = fits.ImageHDU(data=data, name='SCI')
    hdulist.append(science)
    with open(hdulist) as dm:
        sci = dm.data
        dq = dm.dq
        assert dq is not None


def test_setting_arrays_on_fits():
    from astropy.io import fits
    hdulist = fits.HDUList()
    data = np.empty((50, 50))
    primary = fits.PrimaryHDU()
    hdulist.append(primary)
    science = fits.ImageHDU(data=data, name='SCI')
    hdulist.append(science)
    with open(hdulist) as dm:
        dm.data = np.empty((50, 50))
        dm.dq = np.empty((10, 50, 50))


@raises(AttributeError)
def delete_array():
    from astropy.io import fits
    hdulist = fits.HDUList()
    data = np.empty((50, 50))
    science = fits.ImageHDU(data=data, name='SCI')
    hdulist.append(science)
    hdulist.append(science)
    with open(hdulist) as dm:
        del dm.data
        assert len(hdulist) == 1
        x = dm.data


def test_from_fits():
    with RampModel(FITS_FILE) as dm:
        assert dm.meta.instrument.name == 'MIRI'
        assert dm.shape == (5, 35, 40, 32)


def test_from_scratch():
    with ImageModel((50, 50)) as dm:
        data = np.asarray(np.random.rand(50, 50), np.float32)
        dm.data[...] = data

        dm.meta.instrument.name = 'NIRCAM'

        dm.to_fits(TMP_FITS, clobber=True)

        with ImageModel.from_fits(TMP_FITS) as dm2:
            assert dm2.shape == (50, 50)
            assert dm2.meta.instrument.name == 'NIRCAM'
            assert dm2.dq.dtype.name == 'uint32'
            assert np.all(dm2.data == data)


def test_delete():
    with DataModel(FITS_FILE) as dm:
        dm.meta.instrument.name = 'NIRCAM'
        assert dm.meta.instrument.name == 'NIRCAM'
        del dm.meta.instrument.name
        assert dm.meta.instrument.name is None


def test_section():
    with RampModel((5, 35, 40, 32)) as dm:
        section = dm.get_section('data')[3:4, 1:3]
        assert section.shape == (1, 2, 40, 32)


def test_date_obs():
    with DataModel(FITS_FILE) as dm:
        assert dm.meta.observation.date.microsecond == 314592


def test_fits_without_sci():
    from astropy.io import fits
    schema = {
        "allOf": [
            {"$ref": "http://jwst_lib.stsci.edu/schemas/core.schema.json"},
            {
                "type": "object",
                "properties": {
                    "coeffs": {
                        'type': 'data',
                        'fits_hdu': 'COEFFS'
                    }
                }
            }
        ]
    }

    fits = fits.HDUList(
        [fits.PrimaryHDU(),
         fits.ImageHDU(name='COEFFS', data=np.array([0.0]))])

    with DataModel(fits, schema=schema) as dm:
        assert_array_equal(dm.coeffs, [0.0])


def test_extra_fits():
    path = os.path.join(ROOT_DIR, "headers.fits")

    with DataModel(path) as dm:
        assert not hasattr(dm._extra_fits.PRIMARY, 'BITPIX')
        assert dm._extra_fits.PRIMARY.CORONMSK == '#TODO'
        dm2 = dm.copy()
        dm2.to_fits(TMP_FITS, clobber=True)

    with DataModel(TMP_FITS) as dm3:
        assert not hasattr(dm3._extra_fits.PRIMARY, 'BITPIX')
        assert dm3._extra_fits.PRIMARY.CORONMSK == '#TODO'


def test_extra_fits_update():
    path = os.path.join(ROOT_DIR, "headers.fits")

    with DataModel(path) as dm:
        with DataModel() as dm2:
            dm2.update(dm)
            assert not hasattr(dm2._extra_fits.PRIMARY, 'BITPIX')
            assert dm2._extra_fits.PRIMARY.CORONMSK == '#TODO'


def test_hdu_order():
    from astropy.io import fits

    with ImageModel(data=[[0.0]], dq=[[0.0]], err=[[0.0]]) as dm:
        print(dm.dq)
        print(dm.err)
        dm.save(TMP_FITS)

    with fits.open(TMP_FITS) as hdulist:
        assert hdulist[1].header['EXTNAME'] == 'SCI'
        assert hdulist[2].header['EXTNAME'] == 'DQ'
        assert hdulist[3].header['EXTNAME'] == 'ERR'


def test_casting():
    with ImageModel(FITS_FILE) as dm:
        sum = np.sum(dm.data)
        dm.data[:] = dm.data + 2
        assert np.sum(dm.data) > sum


def test_comments():
    with ImageModel(FITS_FILE) as dm:
        assert dm._extra_fits.PRIMARY.COMMENT == ['This is a comment']
        dm._extra_fits.PRIMARY.COMMENT = ['foobar']
        assert dm._extra_fits.PRIMARY.COMMENT == ['foobar']


def test_fits_comments():
    with ImageModel() as dm:
        dm.meta.subarray.xstart = 42
        dm.save(TMP_FITS, clobber=True)

    from astropy.io import fits
    hdulist = fits.open(TMP_FITS)

    header = hdulist[0].header

    find = ['Subarray parameters']
    found = 0

    for card in header.cards:
        if card[1] in find:
            found += 1

    assert found == len(find)


def test_metadata_doesnt_override():
    with ImageModel() as dm:
        dm.save(TMP_FITS, clobber=True)

    from astropy.io import fits
    hdulist = fits.open(TMP_FITS, mode='update')
    hdulist[0].header['FILTER'] = 'JUNK'
    hdulist.close()

    with ImageModel(TMP_FITS) as dm:
        assert dm.meta.instrument.filter == 'JUNK'


def test_table_with_metadata():
    schema = {
        "allOf": [
            {"$ref": "http://jwst_lib.stsci.edu/schemas/core.schema.json"},
            {"type": "object",
             "properties" : {
                 "flux_table" : {
                     "type" : "data",
                     "title" : "Photometric flux conversion table",
                     "fits_hdu" : "FLUX",
                     "dtype" :
                     [
                         {"name" : "parameter",    "dtype" : "string7"},
                         {"name" : "factor",       "dtype" : "float64"},
                         {"name" : "uncertainty",  "dtype" : "float64"}
                     ]
                 },
                 "meta" : {
                     "type": "object",
                     "properties": {
                         "fluxinfo" : {
                             "title" : "Information about the flux conversion",
                             "type" : "object",
                             "properties" : {
                                 "exposure" : {
                                     "title" : "Description of exposure analyzed",
                                     "type" : "string",
                                     "fits_hdu" : "FLUX",
                                     "fits_keyword" : "FLUXEXP"
                                 }
                             }
                         }
                     }
                 }
             }
         }
    ]
    }

    class FluxModel(DataModel):
        def __init__(self, init=None, flux_table=None, **kwargs):
            super(FluxModel, self).__init__(init=init, schema=schema, **kwargs)

            if flux_table is not None:
                self.flux_table = flux_table

    flux_im = [
        ('F560W',  1.0e-5,  1.0e-7),
        ('F770W',  1.1e-5,  1.6e-7),
        ]
    with FluxModel(flux_table=flux_im) as datamodel:
        datamodel.meta.fluxinfo.exposure = 'Exposure info'
        datamodel.save(TMP_FITS, clobber=True)
        del datamodel

    from astropy.io import fits
    hdulist = fits.open(TMP_FITS)
    assert len(hdulist) == 3
    assert isinstance(hdulist[1], fits.BinTableHDU)
    assert hdulist[1].name == 'FLUX'
    assert isinstance(hdulist[2], fits.ImageHDU)
    assert hdulist[2].name == 'METADATA'


def test_replace_table():
    from astropy.io import fits

    schema_narrow = {
        "allOf": [
            {"$ref": "http://jwst_lib.stsci.edu/schemas/core.schema.json"},
            {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "data",
                        "title": "relative sensitivity table",
                        "fits_hdu": "RELSENS",
                        "dtype": [
                            {"name" : "TYPE",       "dtype" : "string16"},
                            {"name" : "T_OFFSET",   "dtype" : "float32"},
                            {"name" : "DECAY_PEAK", "dtype" : "float32"},
                            {"name" : "DECAY_FREQ", "dtype" : "float32"},
                            {"name" : "TAU",        "dtype" : "float32"}
                        ]
                    }
                }
            }
        ]
    }

    schema_wide = {
        "allOf": [
            {"$ref": "http://jwst_lib.stsci.edu/schemas/core.schema.json"},
            {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "data",
                        "title": "relative sensitivity table",
                        "fits_hdu": "RELSENS",
                        "dtype": [
                            {"name" : "TYPE",       "dtype" : "string16"},
                            {"name" : "T_OFFSET",   "dtype" : "float64"},
                            {"name" : "DECAY_PEAK", "dtype" : "float64"},
                            {"name" : "DECAY_FREQ", "dtype" : "float64"},
                            {"name" : "TAU",        "dtype" : "float64"}
                        ]
                    }
                }
            }
        ]
    }

    x = np.array([("string", 1., 2., 3., 4.)],
                 dtype=[('TYPE', 'S16'),
                        ('T_OFFSET', np.float32),
                        ('DECAY_PEAK', np.float32),
                        ('DECAY_FREQ', np.float32),
                        ('TAU', np.float32)])

    m = DataModel(schema=schema_narrow)
    m.data = x
    m.to_fits(TMP_FITS, clobber=True)

    with fits.open(TMP_FITS) as hdulist:
        assert repr(list(x)) == repr(list(np.asarray(hdulist[1].data)))
        assert hdulist[1].data.dtype[1].str == '>f4'
        assert hdulist[1].header['TFORM2'] == 'E'

    with DataModel(TMP_FITS,
                   schema=schema_wide) as m:
        foo = m.data
        m.to_fits(TMP_FITS2, clobber=True)

    with fits.open(TMP_FITS2) as hdulist:
        assert repr(list(x)) == repr(list(np.asarray(hdulist[1].data)))
        assert hdulist[1].data.dtype[1].str == '>f8'
        assert hdulist[1].header['TFORM2'] == 'D'


def test_metadata_from_fits():
    from astropy.io import fits

    mask = np.array([[0, 1], [2, 3]])
    fits.ImageHDU(data=mask, name='DQ').writeto(TMP_FITS, clobber=True)
    with DataModel(init=TMP_FITS) as dm:
        dm.save(TMP_FITS2)

    with fits.open(TMP_FITS2) as hdulist:
        assert hdulist[2].name == 'METADATA'


def test_float_as_int():
    from astropy.io import fits

    hdulist = fits.HDUList()
    primary = fits.PrimaryHDU()
    hdulist.append(primary)
    hdulist[0].header['SUBSTRT1'] = 42.7
    hdulist.writeto(TMP_FITS, clobber=True)

    with DataModel(TMP_FITS) as dm:
        assert dm.meta.subarray.xstart == 42.7

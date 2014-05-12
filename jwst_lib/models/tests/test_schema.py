import os
import shutil
import tempfile

from nose.tools import raises

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal

from .. import DataModel, ImageModel, RampModel, MaskModel, MultiSlitModel, open
from .. import schema


FITS_FILE = None
MASK_FILE = None
TMP_FITS = None
TMP_FITS2 = None
TMP_YAML = None
TMP_JSON = None
TMP_DIR = None

def setup():
    global FITS_FILE, MASK_FILE, TMP_DIR, TMP_FITS, TMP_YAML, TMP_JSON, TMP_FITS2
    ROOT_DIR = os.path.dirname(__file__)
    FITS_FILE = os.path.join(ROOT_DIR, 'test.fits')
    MASK_FILE = os.path.join(ROOT_DIR, 'mask.fits')

    TMP_DIR = tempfile.mkdtemp()
    TMP_FITS = os.path.join(TMP_DIR, 'tmp.fits')
    TMP_FITS2 = os.path.join(TMP_DIR, 'tmp2.fits')
    TMP_YAML = os.path.join(TMP_DIR, 'tmp.yaml')
    TMP_JSON = os.path.join(TMP_DIR, 'tmp.json')


def teardown():
    shutil.rmtree(TMP_DIR)


@raises(ValueError)
def test_choice():
    with ImageModel(FITS_FILE) as dm:
        assert dm.meta.instrument.name == 'MIRI'
        dm.meta.instrument.name = 'FOO'


@raises(ValueError)
def test_get_na_ra():
    with DataModel(FITS_FILE) as dm:
        # It's invalid in the file, so we should get the default of None
        assert dm.meta.target.ra is None

        # But this should raise a ValueError
        dm.meta.target.ra = "FOO"


@raises(ValueError)
def test_date():
    with ImageModel((50, 50)) as dm:
        dm.meta.date = 'Not an acceptable date'


def test_date2():
    import datetime

    with ImageModel((50, 50)) as dm:
        assert isinstance(dm.meta.date, datetime.datetime)


transformation_overlays = [
    ("meta.transformations", {
        "title" : "A list of transformations",
        "type" : "array",
        "items" : {
            "title" : "A transformation",
            "type" : "object",
            "properties" : {
                "type" : {
                    "title" : "Transformation type",
                    "type" : "string"
                },
                "coeff" : {
                    "title" : "coefficients",
                    "type" : "number"
                }
            },
            "additionalProperties" : False
        }
    })]


@raises(ValueError)
def test_list():
    with ImageModel(
            (50, 50),
            schema_overlays=transformation_overlays) as dm:
        dm.meta.transformations = []
        object = dm.meta.transformations.item(
            transformation="SIN",
            coeff=2.0)


@raises(ValueError)
def test_list2():
    with ImageModel(
            (50, 50),
            schema_overlays=transformation_overlays) as dm:
        dm.meta.transformations = []
        object = dm.meta.transformations.append(
            {'transformation' : 'FOO',
             'coeff' : 2.0})


def test_list3():
    with DataModel(schema_overlays=transformation_overlays) as dm:
        assert dm.meta.transformations == []
        trans = dm.meta.transformations.item(
            type = "SIN",
            coeff = 2.0)
        l = dm.meta.transformations
        l.append(trans)
        l.append(
            {'type': 'TAN', 'coeff': 42.0})
        r = repr(l)
        assert r[0] == '[' and r[-1] == ']'
        dm.to_json(TMP_JSON)

        with DataModel.from_json(
            TMP_JSON, schema_overlays=transformation_overlays) as dm2:
            l2 = dm2.meta.transformations
            assert len(l2) == 2
            assert l2[0].type == 'SIN'
            assert l2[1].type == 'TAN'

            assert not l < l2
            assert not l > l2
            assert l <= l2
            assert l >= l2
            assert l == l2
            assert not l != l2

            assert trans in l2
            assert {'type': 'TAN', 'coeff': 42.0} in l2
            assert l2.index({'type': 'TAN', 'coeff': 42.0}) == 1

            l3 = l + l2
            assert len(l3) == len(l) + len(l2)
            assert {'type': 'TAN', 'coeff': 42.0} in l3

            l4 = l * 5
            assert len(l4) == len(l) * 5
            assert l4.count({'type': 'TAN', 'coeff': 42.0}) == 5
            item = l4.pop()
            l4.remove({'type': 'TAN', 'coeff': 42.0})
            # TODO: Reinstate assert l4[0] == l[1]

            l2[1] = {'type': 'SIN', 'coeff': 72.0}
            assert {'type': 'TAN', 'coeff': 42.0} not in l2
            del l2[1]
            assert {'type': 'SIN', 'coeff': 72.0} not in l2


def test_ad_hoc_json():
    with DataModel() as dm:
        dm.meta.foo = {'a': 42, 'b': ['a', 'b', 'c']}

        dm.to_json(TMP_JSON)

    with DataModel.from_json(TMP_JSON) as dm2:
        assert dm2.meta.foo == {'a': 42, 'b': ['a', 'b', 'c']}


def test_ad_hoc_fits():
    with DataModel() as dm:
        dm.meta.foo = {'a': 42, 'b': ['a', 'b', 'c']}

        dm.to_fits(TMP_FITS, clobber=True)

    with DataModel.from_fits(TMP_FITS) as dm2:
        assert dm2.meta.foo == {'a': 42, 'b': ['a', 'b', 'c']}


schema_extra = [
    ('meta.foo',
     {'title': 'Custom type',
      'type': 'string',
      'default': 'bar',
      'fits_keyword': 'FOO'}
     ),

    ('meta.restricted',
     {'title': 'Custom type',
      'type': 'object',
      'additionalProperties': False,
      'properties': {
          'allowed': {
              'type': 'number'
          }
      }
     }
     ),

    ('meta.subarray.size',
     {'title': 'Subarray size',
      'type': 'number'}
     ),

    ('meta.bar.baz',
     {'title': 'Deep custom type',
      'type': 'string'}
     ),

    ('meta.subarray', {
        'properties': {
            'xstart': {
                'type': 'string',
                'default': 'fubar'
                }
            }
        }
     ),
    ]


def test_schema_overlay():
    with DataModel(schema_overlays=schema_extra) as x:
        assert x.meta.foo == 'bar'

        try:
            x.meta.subarray.size = 'string'
        except:
            pass
        else:
            raise AssertionError()

        x.meta.restricted.allowed = 42.0
        try:
            x.meta.restricted.foobar = 32.0
        except AttributeError:
            pass
        else:
            raise AssertionError()

        x.meta.bar.baz = 'google'
        assert x.meta.bar.baz == 'google'

        x.meta.subarray.xstart = 'fubar'

        x.to_fits(TMP_FITS, clobber=True)

    with DataModel.from_fits(TMP_FITS, schema_overlays=schema_extra) as y:
        foo = y.meta.foo

        y.extend_schema(schema_extra)

        assert y.meta.foo == 'bar'


def test_extend_schema():
    with DataModel() as x:
        x.meta.instrument.type = 'NIRCAM'
        x.extend_schema(schema_extra)

        assert x.meta.foo == 'bar'
        x.meta.bar.baz = 'google'
        x.meta.instrument.type = 'MIRI'
        assert x.meta.instrument.type == 'MIRI'


def test_find_fits_keyword():
    with DataModel() as x:
        assert x.find_fits_keyword('DATE-OBS', return_result=True) == \
          ['meta.observation.date']


def test_search_schema():
    with DataModel() as x:
        results = x.search_schema('target', return_result=True)

    results = [x[0] for x in results]
    assert 'meta.target' in results
    assert 'meta.target.ra' in results


def test_dictionary_like():
    with DataModel(schema_overlays=schema_extra) as x:
        assert x['meta.foo'] == 'bar'

        try:
            x['meta.subarray.size'] = 'string'
        except:
            pass
        else:
            raise AssertionError()

        x['meta.bar.baz'] = 'google'
        assert x['meta.bar.baz'] == 'google'

        x['meta.subarray.xstart'] = 'fubar'

        try:
            y = x['meta.FOO.BAR.BAZ']
        except KeyError:
            pass
        else:
            raise AssertionError()


def test_to_flat_dict():
    with DataModel(schema_overlays=schema_extra) as x:
        assert x['meta.foo'] == 'bar'

        d = x.to_flat_dict()

        assert d['meta.foo'] == 'bar'


def test_table_array():
    table_schema = [
        ('table',
         {'title': 'A structured table',
          'fits_hdu': 'table',
          'type': 'data',
          'dtype': [
              'bool8',
              {'dtype': 'int16',
               'name': 'my_int'},
              {'dtype': 'float32',
               'name': 'my_float',
               'shape': [3, 2]},
               {'dtype': 'string64',
                'name': 'my_string'}
               ]
            }
        )
        ]

    with DataModel(schema_overlays=table_schema) as x:
        table = x.table
        assert table.dtype == [
            ('f0', '|i1'),
            ('my_int', '=i2'),
            ('my_float', '=f4', (3, 2)),
            ('my_string', 'S64')
            ]

        x.to_fits(TMP_FITS, clobber=True)

    with DataModel(TMP_FITS, schema_overlays=table_schema) as x:
        table = x.table
        assert table.dtype == [
            ('f0', '|i1'),
            ('my_int', '=i2'),
            ('my_float', '=f4', (3, 2)),
            ('my_string', 'S64')
            ]


def test_table_array_convert():
    """
    Test that structured arrays are converted when necessary, and
    reused as views when not.
    """
    from jwst_lib.models import util

    table_schema = [
        ('table',
         {'title': 'A structured table',
          'fits_hdu': 'table',
          'type': 'data',
          'dtype': [
              'bool8',
              {'dtype': 'int16',
               'name': 'my_int'},
               {'dtype': 'string64',
                'name': 'my_string'}
               ]
            }
        )
        ]

    table = np.array(
        [(42, 32000, 'foo')],
        dtype=[
            ('f0', '|i1'),
            ('my_int', '=i2'),
            ('my_string', 'S64')
            ])

    x = util.gentle_asarray(table, dtype=[
        ('f0', '|i1'),
        ('my_int', '=i2'),
        ('my_string', 'S64')
    ])

    assert x is table

    with DataModel(schema_overlays=table_schema) as x:
        x.table = table
        assert x.table is table

    table = np.array(
        [(42, 32000, 'foo')],
        dtype=[
            ('f0', '|i1'),
            ('my_int', '=i2'),
            ('my_string', 'S3')
            ])

    with DataModel(schema_overlays=table_schema) as x:
        x.table = table
        assert x.table is not table
        assert x.table['my_string'][0] == table['my_string'][0]


def test_schema_url():
    with DataModel(schema={
            "type": "object",
            "extends": {
                "$ref": "http://jwstlib.stsci.edu/schemas/jwst_lib.models/image.schema.json"}
                }
        ) as x:
        assert isinstance(x.data, np.ndarray)


def test_mask_model():
    with MaskModel(MASK_FILE) as dm:
        assert dm.dq.dtype == np.uint8


def test_data_array():
    data_array_schema = [
        ('arr',
         {'title': 'An array of data',
          'type': 'array',
          "fits_hdu" : ["FOO", "DQ"],

          "items" : {
              "title" : "entry",
              "type" : "object",
              "properties" : {
                    "data" : {
                        "type" : "data",
                        "fits_hdu" : "FOO",
                        "default" : 0.0,
                        "ndim" : 2,
                        "dtype" : "float32"
                    },
                    "dq" : {
                        "type" : "data",
                        "fits_hdu" : "DQ",
                        "default" : 1,
                        "dtype" : "uint8"
                    },
            }
        }
    }
    )]

    array1 = np.random.rand(5, 5)
    array2 = np.random.rand(5, 5)
    array3 = np.random.rand(5, 5)

    with DataModel(schema_overlays=data_array_schema) as x:
        x.arr.append(x.arr.item())
        x.arr[0].data = array1
        assert len(x.arr) == 1
        x.arr.append(x.arr.item(data=array2))
        assert len(x.arr) == 2
        x.arr.append({})
        assert len(x.arr) == 3
        x.arr[2].data = array3
        del x.arr[1]
        assert len(x.arr) == 2
        x.to_fits(TMP_FITS, clobber=True)

    with DataModel(TMP_FITS, schema_overlays=data_array_schema) as x:
        assert len(x.arr) == 2
        assert len(x._storage._fits) == 4
        assert_array_almost_equal(x.arr[0].data, array1)
        assert_array_almost_equal(x.arr[1].data, array3)

        del x.arr[0]
        assert len(x._storage._fits) == 3
        assert len(x.arr) == 1
        assert len(x._storage._fits) == 3

        x.arr = []
        assert len(x.arr) == 0
        x.arr.append({})
        assert len(x.arr) == 1
        x.arr.extend([x.arr.item(), x.arr.item()])
        assert len(x.arr) == 3
        del x.arr[1]
        assert len(x.arr) == 2
        assert len(x._storage._fits) == 5
        x.to_fits(TMP_FITS2, clobber=True)

    import pyfits
    with pyfits.open(TMP_FITS2) as hdulist:
        x = set()
        for hdu in hdulist:
            x.add((hdu.header.get('EXTNAME'),
                   hdu.header.get('EXTVER')))
        assert x == set([
            ('FOO', 1),
            ('FOO', 2),
            (None, None),
            ('METADATA', None),
            ('DQ', 1),
            ('DQ', 2)])


def test_multislit_model():
    array1 = np.asarray(np.random.rand(2, 2), dtype='float32')
    array2 = np.asarray(np.random.rand(2, 2), dtype='float32')

    with MultiSlitModel() as ms:
        assert len(ms.slits) == 0
        ms.slits.append(ms.slits.item())
        ms.slits[-1].data = array1
        assert len(ms.slits) == 1
        ms.slits.append(ms.slits.item())
        ms.slits[-1].data = array2
        assert len(ms.slits) == 2
        for i, slit in enumerate(ms.slits):
            assert slit == ms.slits[i]
        ms2 = ms.copy()
        assert len(ms2.slits) == 2
        assert_array_equal(ms.slits[-1].data, array2)
        del ms.slits[0]
        assert len(ms.slits) == 1
        assert_array_equal(ms.slits[0].data, array2)


class Picklable(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c


def test_pickle():
    schema_extra = [
        ('meta.pickled',
         {'title': 'A pickled item',
          'type': 'pickle'
          }
          )]

    obj = Picklable("Hi", 42, 1)

    with DataModel(schema_overlays=schema_extra) as x:
        x.meta.pickled = obj
        x.save(TMP_FITS)
        assert x.meta.pickled.a == "Hi"
        assert x.meta.pickled.b == 42
        assert x.meta.pickled.c == 1

    with DataModel(TMP_FITS, schema_overlays=schema_extra) as x:
        assert x.meta.pickled.a == "Hi"
        assert x.meta.pickled.b == 42
        assert x.meta.pickled.c == 1


def test_implicit_creation_lower_dimensionality():
    with RampModel(np.zeros((10, 20, 30, 40))) as rm:
        assert rm.pixeldq.shape == (30, 40)

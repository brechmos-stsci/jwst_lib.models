from __future__ import absolute_import, unicode_literals, division, print_function

from .. import DataModel, open
import numpy as np
from .. import util


def test_copyied_model():
    def oops():
        raise AssertionError()

    def ok():
        pass

    with DataModel() as dm:
        dm.storage.close = oops
        with open(dm) as dm2:
            pass
        dm.storage.close = ok



def test_gentle_asarray():
    x = np.array([('abc', 1.0)], dtype=[
        (str('FOO'), str('S3')),
        (str('BAR'), str('>f8'))])

    new_dtype = [(str('foo'), str('|S3')), (str('bar'), str('<f8'))]

    y = util.gentle_asarray(x, new_dtype)

    assert y['bar'][0] == 1.0

from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from . import wcs


__all__ = ['CubeModel']


class CubeModel(model_base.DataModel, wcs.HasFitsWcs):
    """
    A data model for 3D image cubes.
    """
    schema_url = "cube.schema.json"

    def __init__(self, init=None, data=None, dq=None, err=None, zeroframe=None,
                 **kwargs):
        super(CubeModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if dq is not None:
            self.dq = dq

        if err is not None:
            self.err = err

        if zeroframe is not None:
            self.zeroframe = zeroframe

        # Implicitly create arrays
        self.dq = self.dq
        self.err = self.err


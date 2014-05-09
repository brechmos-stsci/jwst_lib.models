from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from . import wcs


__all__ = ['RampModel']


class RampModel(model_base.DataModel, wcs.HasFitsWcs):
    """
    A data model for 4D ramps.
    """
    schema_url = "ramp.schema.json"

    def __init__(self, init=None, data=None, pixeldq=None, groupdq=None,
                 err=None, **kwargs):
        super(RampModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if pixeldq is not None:
            self.pixeldq = pixeldq

        if groupdq is not None:
            self.groupdq = groupdq

        if err is not None:
            self.err = err

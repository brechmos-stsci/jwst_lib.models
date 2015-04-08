from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from . import wcs
from .dynamicdq import dynamic_mask


__all__ = ['FlatModel']


class FlatModel(model_base.DataModel, wcs.HasFitsWcs):
    """
    A data model for 2D flat-field images.
    """
    schema_url = "flat.schema.json"

    def __init__(self, init=None, data=None, dq=None, err=None,
                 dq_def=None, **kwargs):
        super(FlatModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if dq is not None:
            self.dq = dq

        if err is not None:
            self.err = err

        if dq_def is not None:
            self.dq_def = dq_def

        self.dq = dynamic_mask(self)

        # Implicitly create arrays
        self.dq = self.dq
        self.err = self.err

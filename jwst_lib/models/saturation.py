from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from .dynamicdq import dynamic_mask

__all__ = ['SaturationModel']

class SaturationModel(model_base.DataModel):
    """
    A data model for saturation checking information.
    """
    schema_url = "saturation.schema.json"

    def __init__(self, init=None, sat=None, dq=None, dq_def=None, **kwargs):
        super(SaturationModel, self).__init__(init=init, **kwargs)

        if sat is not None:
            self.sat = sat

        if dq is not None:
            self.dq = dq

        if dq_def is not None:
            self.dq_def = dq_def

        self.dq = dynamic_mask(self)

from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base

__all__ = ['SaturationModel']

class SaturationModel(model_base.DataModel):
    """
    A data model for saturation checking information.
    """
    schema_url = "saturation.schema.json"

    def __init__(self, init=None, sat=None, **kwargs):
        super(SaturationModel, self).__init__(init=init, **kwargs)

        if sat is not None:
            self.sat = sat

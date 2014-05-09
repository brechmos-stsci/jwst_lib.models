from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from .dynamicdq import dynamic_mask

__all__ = ['DarkModel']


class DarkModel(model_base.DataModel):
    """
    A data model for dark current reference files.
    """
    schema_url = "dark.schema.json"

    def __init__(self, init=None, data=None, dq=None, err=None, **kwargs):
        super(DarkModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if dq is not None:
            self.dq = dq
        self.dq = dynamic_mask(self)

        if err is not None:
            self.err = err

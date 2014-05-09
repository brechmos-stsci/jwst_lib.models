from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from .dynamicdq import dynamic_mask

__all__ = ['LastFrameModel']


class LastFrameModel(model_base.DataModel):
    """
    A data model for Last frame correction reference files.
    """
    schema_url = "lastframe.schema.json"

    def __init__(self, init=None, data=None, dq=None, err=None, **kwargs):
        super(LastFrameModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if dq is not None:
            self.dq = dq
        self.dq = dynamic_mask(self)

        if err is not None:
            self.err = err

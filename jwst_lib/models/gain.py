from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base


__all__ = ['GainModel']


class GainModel(model_base.DataModel):
    """
    A data model for 2D gain
    """
    schema_url = "gain.schema.yaml"

    def __init__(self, init=None, data=None, **kwargs):
        super(GainModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from .dynamicdq import dynamic_mask


__all__ = ['LinearityModel']


class LinearityModel(model_base.DataModel):
    """
    A data model for linearity correction information.
    """
    schema_url = "linearity.schema.json"

    def __init__(self, init=None, coeffs=None, dq=None, **kwargs):
        super(LinearityModel, self).__init__(init=init, **kwargs)

        if coeffs is not None:
            self.coeffs = coeffs

        if dq is not None:
            self.dq = dq
        self.dq = dynamic_mask(self)

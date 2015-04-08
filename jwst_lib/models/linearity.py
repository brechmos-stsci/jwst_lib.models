from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from .dynamicdq import dynamic_mask


__all__ = ['LinearityModel']


class LinearityModel(model_base.DataModel):
    """
    A data model for linearity correction information.
    """
    schema_url = "linearity.schema.json"

    def __init__(self, init=None, coeffs=None, dq=None, dq_def=None,
                 **kwargs):
        super(LinearityModel, self).__init__(init=init, **kwargs)

        if coeffs is not None:
            self.coeffs = coeffs

        if dq is not None:
            self.dq = dq

        if dq_def is not None:
            self.dq_def = dq_def

        self.dq = dynamic_mask(self)

        # Implicitly create arrays
        self.dq = self.dq
        seld.err = self.err

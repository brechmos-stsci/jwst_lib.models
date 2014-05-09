from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from . import wcs


__all__ = ['RampFitOutputModel']


class RampFitOutputModel(model_base.DataModel, wcs.HasFitsWcs):
    """
    A data model for the optional output of the ramp fitting step.
    """
    schema_url = "rampfitoutput.schema.json"

    def __init__(self, init=None,
                 slope=None,
                 sigslope=None,
                 yint=None,
                 sigyint=None,
                 pedestal=None,
                 weights=None,
                 crmag=None,
                 **kwargs):
        super(RampFitOutputModel, self).__init__(init=init, **kwargs)

        if slope is not None:
            self.slope = slope

        if sigslope is not None:
            self.sigslope = sigslope

        if yint is not None:
            self.yint = yint

        if sigyint is not None:
            self.sigyint = sigyint

        if pedestal is not None:
            self.pedestal = pedestal

        if weights is not None:
            self.weights = weights

        if crmag is not None:
            self.crmag = crmag


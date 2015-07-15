from __future__ import absolute_import, unicode_literals, division, print_function

from . import ramp
from . import wcs


__all__ = ['MIRIRampModel']


class MIRIRampModel(ramp.RampModel, wcs.HasFitsWcs):
    """
    A data model for MIRI ramps.
    Includes the REFOUT extension
    """
    schema_url = "miri_ramp.schema.json"

    def __init__(self, init=None, data=None, pixeldq=None, groupdq=None,
                 err=None, refout=None, zeroframe=None, **kwargs):
        super(MIRIRampModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if pixeldq is not None:
            self.pixeldq = pixeldq

        if groupdq is not None:
            self.groupdq = groupdq

        if err is not None:
            self.err = err

        if refout is not None:
            self.refout = refout

        if zeroframe is not None:
            self.zeroframe = zeroframe
            
        # Implicitly create arrays
        self.pixeldq = self.pixeldq
        self.groupdq = self.groupdq
        self.err = self.err
        self.zeroframe = self.zeroframe

from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base


__all__ = ['RampModel']


class RampModel(model_base.DataModel):
    """
    A data model for 4D ramps.

    Parameters
    ----------
    init : any
        Any of the initializers supported by `~jwst_lib.models.DataModel`.

    data : numpy array
        The science data.

    pixeldq : numpy array
        2-D data quality array.

    groupdq : numpy array
        3-D or 4-D data quality array.

    err : numpy array
        The error array.
    """
    schema_url = "ramp.schema.yaml"

    def __init__(self, init=None, data=None, pixeldq=None, groupdq=None,
                 err=None, zeroframe=None, **kwargs):
        super(RampModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if pixeldq is not None:
            self.pixeldq = pixeldq

        if groupdq is not None:
            self.groupdq = groupdq

        if err is not None:
            self.err = err

        if zeroframe is not None:
            self.zeroframe = zeroframe

        # Implicitly create arrays
        self.pixeldq = self.pixeldq
        self.groupdq = self.groupdq
        self.err = self.err

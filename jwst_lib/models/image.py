from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from . import wcs


__all__ = ['ImageModel']


class ImageModel(model_base.DataModel, wcs.HasFitsWcs):
    """
    A data model for 2D images.
    """
    schema_url = "image.schema.json"

    def __init__(self, init=None, data=None, dq=None, err=None, relsens=None,
                 zeroframe=None, **kwargs):
        super(ImageModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

        if dq is not None:
            self.dq = dq

        if err is not None:
            self.err = err

        if relsens is not None:
            self.relsens = relsens

        if zeroframe is not None:
            self.zeroframe = zeroframe

        # Implicitly create arrays
        self.dq = self.dq
        self.err = self.err
        self.zeroframe = self.zeroframe 

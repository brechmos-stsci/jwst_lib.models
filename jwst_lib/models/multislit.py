from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from .image import ImageModel


__all__ = ['MultiSlitModel']


class MultiSlitModel(model_base.DataModel):
    """
    A data model for multi-slit images.

    This model has a special member `slits` that can be used to
    deal with an entire slit at a time.  It behaves like a list::

       >>> multislit_model.slits.append(image_model)
       >>> multislit_model.slits[0]
       <ImageModel>
    """
    schema_url = "multislit.schema.yaml"

    def __init__(self, init=None, **kwargs):
        if isinstance(init, ImageModel):
            super(MultiSlitModel, self).__init__(init=None, **kwargs)
            self.update(init)
            self.slits.append(self.slits.item())
            self.slits[0].data = init.data
            self.slits[0].dq = init.dq
            self.slits[0].err = init.err
            self.slits[0].relsens = init.relsens
            self.slits[0].area = init.area
            return

        super(MultiSlitModel, self).__init__(init=init, **kwargs)

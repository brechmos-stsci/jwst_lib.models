from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base
from . import wcs
from .spec import SpecModel


__all__ = ['MultiSpecModel']


class MultiSpecModel(model_base.DataModel, wcs.HasFitsWcs):
    """
    A data model for multi-spec images.

    This model has a special member `spec` that can be used to
    deal with an entire spectrum at a time.  It behaves like a list::

       >>> multispec_model.spec.append(spec_model)
       >>> multispec_model.spec[0]
       <SpecModel>
    """
    schema_url = "multispec.schema.json"

    def __init__(self, init=None, **kwargs):
        if isinstance(init, SpecModel):
            super(MultiSpecModel, self).__init__(init=None, **kwargs)
            self.spec.append(self.spec.item())
            self.spec[0].spec_table = init.spec_table
            return

        super(MultiSpecModel, self).__init__(init=init, **kwargs)

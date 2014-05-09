from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base


__all__ = ['SpecModel']


class SpecModel(model_base.DataModel):
    """
    A data model for 1D spectra.
    """
    schema_url = "spec.schema.json"

    def __init__(self, init=None, spec_table=None, **kwargs):
        super(SpecModel, self).__init__(init=init, **kwargs)

        if spec_table is not None:
            self.spec_table = spec_table


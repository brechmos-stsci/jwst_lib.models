from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base

__all__ = ['AsnModel']


class AsnModel(model_base.DataModel):
    """
    A data model for association tables.
    """
    schema_url = "asn.schema.json"

    def __init__(self, init=None, asn_table=None, **kwargs):
        super(AsnModel, self).__init__(init=init, **kwargs)

        if asn_table is not None:
            self.asn_table = asn_table



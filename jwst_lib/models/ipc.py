from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base

__all__ = ['IPCModel']

class IPCModel(model_base.DataModel):
    """
    A data model for IPC kernel checking information.
    """
    schema_url = "ipc.schema.json"

    def __init__(self, init=None, data=None, **kwargs):
        super(IPCModel, self).__init__(init=init, **kwargs)

        if data is not None:
            self.data = data

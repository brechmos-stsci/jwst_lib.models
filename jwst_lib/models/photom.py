from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base

__all__ = ['PhotomModel']


class PhotomModel(model_base.DataModel):
    """
    A data model for photom reference files.
    """
    schema_url = "photom.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(PhotomModel, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class NircamPhotomModel(PhotomModel):
    """
    A data model for NIRCam photom reference files.
    """
    schema_url = "nircam_photom.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(NircamPhotomModel, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class NirissPhotomModel(PhotomModel):
    """
    A data model for NIRISS photom reference files.
    """
    schema_url = "niriss_photom.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(NirissPhotomModel, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class NirspecPhotomModel(PhotomModel):
    """
    A data model for NIRSpec photom reference files.
    """
    schema_url = "nirspec_photom.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(NirspecPhotomModel, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class MiriImgPhotomModel(PhotomModel):
    """
    A data model for MIRI imaging photom reference files.
    """
    schema_url = "mirimg_photom.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(MiriImgPhotomModel, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class MiriMrsPhotomModel(PhotomModel):
    """
    A data model for MIRI MRS photom reference files.
    """
    schema_url = "mirmrs_photom.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(MiriMrsPhotomModel, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table

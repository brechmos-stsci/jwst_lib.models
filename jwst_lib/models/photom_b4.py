from __future__ import absolute_import, unicode_literals, division, print_function

from . import model_base

__all__ = ['PhotomModelB4']


class PhotomModelB4(model_base.DataModel):
    """
    A data model for photom reference files.
    """
    schema_url = "photomb4.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(PhotomModelB4, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class NircamPhotomModelB4(PhotomModelB4):
    """
    A data model for NIRCam photom reference files.
    """
    schema_url = "nircam_photomb4.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(NircamPhotomModelB4, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class NirissPhotomModelB4(PhotomModelB4):
    """
    A data model for NIRISS photom reference files.
    """
    schema_url = "niriss_photomb4.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(NirissPhotomModelB4, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class NirspecPhotomModelB4(PhotomModelB4):
    """
    A data model for NIRSpec photom reference files.
    """
    schema_url = "nirspec_photomb4.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(NirspecPhotomModelB4, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class MiriImgPhotomModelB4(PhotomModelB4):
    """
    A data model for MIRI imaging photom reference files.
    """
    schema_url = "mirimg_photomb4.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(MiriImgPhotomModelB4, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table


class MiriMrsPhotomModelB4(PhotomModelB4):
    """
    A data model for MIRI MRS photom reference files.
    """
    schema_url = "mirmrs_photomb4.schema.yaml"

    def __init__(self, init=None, phot_table=None, **kwargs):
        super(MiriMrsPhotomModelB4, self).__init__(init=init, **kwargs)

        if phot_table is not None:
            self.phot_table = phot_table

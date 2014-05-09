import numpy as np

from jwst_lib.models import DataModel

class MiriBadPixelMaskModel(DataModel):
    schema_url = "bad_pixel_mask.schema.json"

    def __init__(self, init=None, mask=None, field_def=None, **kwargs):
        super(MiriBadPixelMaskModel, self).__init__(init=init, **kwargs)

        if mask is not None:
            self.mask = mask

        if field_def is not None:
            self.field_def = field_def

    def get_mask_for_field(self, name):
        """
        Returns an array that is `True` everywhere a given bitfield is
        True in the mask.

        Parameters
        ----------
        name : str
            The name of the bit field to retrieve

        Returns
        -------
        array : boolean numpy array
            `True` everywhere the requested bitfield is `True`.  This
            is the same shape as the mask array.  This array is a copy
            and changes to it will not affect the underlying model.
        """
        # Find the field value that corresponds to the given name
        field_value = None
        for value, field_name, title in self.field_def:
            if field_name == name:
                field_value = value
                break
        if field_value is None:
            raise ValueError("Field name {0} not found".format(name))

        # Create an array that is `True` only for the requested
        # bit field
        return self.mask & field_value

    def on_save(self, path):
        super(MiriBadPixelMaskModel, self).on_save(path)

        self.meta.bad_pixel_count = np.sum(self.mask != 0)

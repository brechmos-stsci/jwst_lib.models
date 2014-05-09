import numpy as np
from . import dqflags

def dynamic_mask(input_model):
    #
    # Return a mask model given a mask with dynamic DQ flags
    # Dynamic flags define what each plane refers to using header keywords of the form
    # DQ_1, DQ_2, DQ_4, DQ_8 etc.

    # Get the DQ array and the flag definitions
    try:
        dqcards = input_model.storage.get_fits_header(1, hdu_name='DQ')['DQ_*']
    except AttributeError:
        #
        # If the model wasn't created directly from a FITS file, there's no FITS storage, so this
        # won't work.  E.g. if the model is a .copy() of another model.  In that case, just return
        # the original dq array
        dqmask = input_model.dq
        return dqmask

    #
    # Even if there are no header cards with a name beginning with 'DQ_', this will still
    # execute and return a Header object with length 0


    # Then create a new mask model with the DQ flags the conform to our standard definitions

    if len(dqcards) > 0:
        dqmask = np.zeros(input_model.dq.shape, dtype=input_model.dq.dtype)
        for keyword, value in zip(dqcards.keys(), dqcards.values()):
            bits = int(keyword[keyword.find('_')+1:])
            truevalue = dqflags.pixel.__dict__.__getitem__(value)
            maskedpixels = np.where(np.bitwise_and(input_model.dq, bits) == bits)
            dqmask[maskedpixels] = dqmask[maskedpixels] + truevalue

    else:
        dqmask = input_model.dq

    return dqmask

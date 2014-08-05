import numpy as np
from . import dqflags

def dynamic_mask(input_model):
    #
    # Return a mask model given a mask with dynamic DQ flags
    # Dynamic flags define what each plane refers to using header keywords
    # of the form
    # DQ_1, DQ_2, DQ_4, DQ_8 etc.
    dq_in = input_model.dq
    # Get the DQ array and the flag definitions
    try:
        dqcards = input_model.storage.get_fits_header(1, hdu_name='DQ')['DQ_*']
    except AttributeError:
        #
        # If the model wasn't created directly from a FITS file, there's no
        # FITS storage, so this won't work.  E.g. if the model is a .copy()
        # of another model.  In that case, just return the original dq array
        dqmask = dq_in
        return dqmask

    #
    # Even if there are no header cards with a name beginning with 'DQ_', this
    # will still execute and return a Header object with length 0

    # Then create a new mask model with the DQ flags the conform to our
    # standard definitions

    if len(dqcards) > 0:
        dqmask = np.zeros(dq_in.shape, dtype=dq_in.dtype)
        for keyword, value in zip(dqcards.keys(), dqcards.values()):
            bitplane = int(keyword[keyword.find('_')+1:])
            bitvalue = 2**bitplane
            try:
                truevalue = dqflags.pixel[value]
            except KeyError:
                print 'Keyword %s = %s is not an existing DQ mnemonic, so will be ignored' % (keyword, value)
                continue
            mask = np.where(np.bitwise_and(dq_in, bitvalue) == bitvalue)
            dqmask[mask] = np.bitwise_or(dqmask[maskedpixels], truevalue)

    else:
        dqmask = dq_in

    return dqmask

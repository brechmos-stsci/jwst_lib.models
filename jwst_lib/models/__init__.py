# Copyright (C) 2010 Association of Universities for Research in Astronomy(AURA)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#       endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY AURA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

from __future__ import absolute_import, unicode_literals, division, print_function

import numpy as np

from .model_base import DataModel
from .amilg import AmiLgModel
from .asn import AsnModel
from .combinedspec import CombinedSpecModel
from .contrast import ContrastModel
from .cube import CubeModel
from .dark import DarkModel
from .drizpars import DrizParsModel, NircamDrizParsModel, MiriImgDrizParsModel
from .drizproduct import DrizProductModel
from .filter import FilterModel
from .flat import FlatModel
from .fringe import FringeModel
from .gain import GainModel
from .gls_rampfit import GLS_RampFitModel
from .image import ImageModel
from .ipc import IPCModel
from .lastframe import LastFrameModel
from .linearity import LinearityModel
from .mask import MaskModel
from .miri_ramp import MIRIRampModel
from .multislit import MultiSlitModel
from .multispec import MultiSpecModel
from .pixelarea import PixelAreaModel
from .photom import PhotomModel, NircamPhotomModel, NirissPhotomModel
from .photom import NirspecPhotomModel, MiriImgPhotomModel, MiriMrsPhotomModel
from .photom_b4 import PhotomModelB4, NircamPhotomModelB4, NirissPhotomModelB4
from .photom_b4 import NirspecPhotomModelB4, MiriImgPhotomModelB4, MiriMrsPhotomModelB4
from .ramp import RampModel
from .rampfitoutput import RampFitOutputModel
from .readnoise import ReadnoiseModel
from .reset import ResetModel
from .saturation import SaturationModel
from .spec import SpecModel
from .straylight import StrayLightModel
from .superbias import SuperBiasModel
from .util import fits_header_name

from .version import (__version__, __svn_revision__, __svn_full_info__, __setup_datetime__)


__all__ = [
    'open',
    'DataModel', 'AmiLgModel', 'AsnModel', 'ContrastModel',
    'CubeModel', 'DarkModel', 'DrizParsModel', 'NircamDrizParsModel',
    'MiriImgDrizParsModel', 'DrizProductModel', 'FilterModel',
    'FlatModel', 'FringeModel', 'GainModel', 'GLS_RampFitModel',
    'ImageModel', 'IPCModel', 'LastFrameModel', 'LinearityModel',
    'MaskModel', 'MIRIRampModel', 'MultiSlitModel', 'MultiSpecModel',
    'PhotomModel', 'NircamPhotomModel', 'NirissPhotomModel',
    'NirspecPhotomModel', 'MiriImgPhotomModel', 'MiriMrsPhotomModel',
    'RampModel', 'RampFitOutputModel', 'ReadnoiseModel', 'ResetModel',
    'SaturationModel', 'SpecModel', 'StrayLightModel']


def open(init=None):
    """
    Creates a Model from a number of different types

    Parameters
    ----------

    init : shape tuple, file path, file object, astropy.io.fits.HDUList, numpy array, dict, None

        - None: A default data model with no shape

        - shape tuple: Initialize with empty data of the given shape

        - file path: Initialize from the given file (FITS or ASDF)

        - readable file object: Initialize from the given file object

        - astropy.io.fits.HDUList: Initialize from the given
          `~astropy.io.fits.HDUList`

        - A numpy array: A new model with the data array initialized
          to what was passed in.

        - dict: The object model tree for the data model

    Results
    -------

    model : DataModel instance
    """
    from astropy.io import fits

    if init is None:
        return DataModel(None)
    elif isinstance(init, DataModel):
        # Copy the object so it knows not to close here
        return init.__class__(init)
    elif isinstance(init, tuple):
        for item in init:
            if not isinstance(item, int):
                raise ValueError("shape must be a tuple of ints")
        shape = init
    elif isinstance(init, np.ndarray):
        shape = init.shape
    else:
        if isinstance(init, (unicode, bytes)) or hasattr(init, "read"):
            hdulist = fits.open(init)
        elif isinstance(init, fits.HDUList):
            hdulist = init
        else:
            raise TypeError(
                "init must be None, shape tuple, file path, "
                "readable file object, or astropy.io.fits.HDUList")

        shape = ()
        try:
            hdu = hdulist[fits_header_name('SCI')]
        except KeyError:
            pass
        else:
            if hasattr(hdu, 'shape'):
                shape = hdu.shape

    # Here, we try to be clever about which type to
    # return, otherwise, just return a new instance of the
    # requested class
    if len(shape) == 0:
        new_class = DataModel
    elif len(shape) == 4:
        try:
            refouthdu = hdulist[fits_header_name('REFOUT')]
        except KeyError:
	    from . import ramp
            new_class = ramp.RampModel
        else:
            from . import miri_ramp
            new_class = miri_ramp.MIRIRampModel
    elif len(shape) == 3:
        from . import cube
        new_class = cube.CubeModel
    elif len(shape) == 2:
        from . import image
        new_class = image.ImageModel
    else:
        raise ValueError("Don't have a model class to match the shape")

    return new_class(init)


def test( verbose=False ) :
    import nose

    # get the pandokia plugin if it is available (it will only
    # do anything if we are run from pandokia).
    try :
        import pandokia.helpers.nose_plugin as nose_plugin
    except ImportError :
        nose_plugin = None

    if nose_plugin :
        addplugins = [ nose_plugin.Pdk() ]
    else :
        addplugins = None

    # get the name of the test package
    argv = [ 'nosetests', '--exe', __name__ + '.tests' ]

    import jwst_lib.models.tests

    print ("ARGS", argv )

    # run nose
    return nose.main( argv = argv,  addplugins=addplugins )

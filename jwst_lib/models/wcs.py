"""
FITS WCS integration
"""
from __future__ import absolute_import, unicode_literals, division, print_function


def _get_wcs_class():
    try:
        from astropy.wcs import WCS
    except ImportError:
        from pywcs import WCS
    except ImportError:
        raise ImportError(
            "astropy or pywcs must be installed for this functionality")
    return WCS


class HasFitsWcs(object):
    def get_fits_wcs(self, hdu_name='PRIMARY', key=' '):
        """
        Get a `astropy.wcs.WCS` or `pywcs.WCS` object created from the
        FITS WCS information in the model.

        Note that modifying the returned WCS object will not modify
        the data in this model.  To update the model, use `set_fits_wcs`.

        Parameters
        ----------
        hdu_name : str, optional
            The name of the HDU to get the WCS from.  This must use
            named HDU's, not numerical order HDUs.  To get the primary HDU,
            pass ``'PRIMARY'`` (default).

        key : str, optional
            The name of a particular WCS transform to use.  This may
            be either ``' '`` or ``'A'``-``'Z'`` and corresponds to
            the ``"a"`` part of the ``CTYPEia`` cards.  *key* may only
            be provided if *header* is also provided.

        Returns
        -------
        wcs : `astropy.wcs.WCS` or `pywcs.WCS` object
            The type will depend on what libraries are installed on
            this system.
        """
        WCS = _get_wcs_class()

        header = self.storage.get_fits_header(self, hdu_name)

        return WCS(header, key=key, relax=True, fix=True)

    def set_fits_wcs(self, wcs, hdu_name='PRIMARY'):
        """
        Sets the FITS WCS information on the model using the given
        `astropy.wcs.WCS` or `pywcs.WCS` object.

        Note that the "key" of the WCS is stored in the WCS object
        itself, so it can not be set as a parameter to this method.

        Parameters
        ----------
        wcs : `astropy.wcs.WCS` or `pywcs.WCS` object
            The object containing FITS WCS information

        hdu_name : str, optional
            The name of the HDU to set the WCS from.  This must use
            named HDU's, not numerical order HDUs.  To set the primary
            HDU, pass ``'PRIMARY'`` (default).
        """
        from . import fits

        header = wcs.to_header()

        hdus = {hdu_name: header.cards}

        # First, extend the schema to include all of the keywords that
        # pywcs gives us.  Some of them may already exist, but it
        # doesn't matter.
        fits.extend_schema_with_fits_keywords(self, hdus)

        # Now set the values on all of the items
        for key, val, comment in header.cards:
            path = "_extra_fits.{0}.{1}".format(hdu_name, key)
            self[path] = val

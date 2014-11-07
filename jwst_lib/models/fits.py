"""
This module deals with all of the FITS-specific handling.
"""
from __future__ import absolute_import, unicode_literals, division, print_function

import collections
import copy
import io
import re
import sys
import warnings

import numpy as np

from . import storage
from .schema import ValidationError, schema_property
from . import schema
from . import util


_builtin_regexes = [
    '', 'NAXIS[0-9]{0,3}', 'BITPIX', 'XTENSION', 'PCOUNT', 'GCOUNT',
    'EXTEND', 'BSCALE', 'BZERO', 'BLANK', 'DATAMAX', 'DATAMIN',
    'EXTNAME', 'EXTVER', 'EXTLEVEL', 'GROUPS', 'PYTPE[0-9]',
    'PSCAL[0-9]', 'PZERO[0-9]', 'SIMPLE', 'TFIELDS',
    'TBCOL[0-9]{1,3}', 'TFORM[0-9]{1,3}', 'TTYPE[0-9]{1,3}',
    'TSCAL[0-9]{1,3}', 'TZERO[0-9]{1,3}',
    'TNULL[0-9]{1,3}', 'TDISP[0-9]{1,3}'
    ]


_builtin_regex = re.compile(
    '|'.join('(^{0}$)'.format(x) for x in _builtin_regexes))


def is_builtin_fits_keyword(key):
    """
    Returns `True` if the given `key` is a built-in FITS keyword, i.e.
    a keyword that is managed by ``astropy.io.fits`` and we wouldn't
    want to propagate through the `_extra_fits` mechanism.
    """
    return _builtin_regex.match(key) is not None


def _convert_hdu_name(hdu_name):
    if hdu_name in (None, 'PRIMARY'):
        hdu_name = 0
    else:
        hdu_name = util.fits_header_name(hdu_name)
    return hdu_name


class CommentaryCardProxy(list):
    def __init__(self, header, keyword):
        self._header = header
        self._keyword = keyword

    def _update_with(self, l):
        if self._keyword in self._header:
            del self._header[self._keyword]
        for x in l:
            self._header[self._keyword] = x

    def _get_list(self):
        return list(self._header.get(self._keyword, []))

    def __iter__(self):
        return iter(self._get_list())

    def __repr__(self):
        return repr(self._get_list())

    def __str__(self):
        return str(self._get_list())

    def __lt__(self, other):
        return self._get_list() < other

    def __le__(self, other):
        return self._get_list() <= other

    def __eq__(self, other):
        return self._get_list() == other

    def __ne__(self, other):
        return self._get_list() != other

    def __gt__(self, other):
        return self._get_list() > other

    def __ge__(self, other):
        return self._get_list() >= other

    def __cmp__(self, other):
        return cmp(self._get_list(), other)

    def __add__(self, other):
        return self._get_list() + other

    def __radd__(self, other):
        return other + self._get_list()

    def __iadd__(self, other):
        self.extend(other)

    def __mul__(self, other):
        return self._get_list() * other

    def __imul__(self, other):
        my_list = self._get_list()
        for i in xrange(other):
            self.extend(my_list)

    def __contains__(self, item):
        for x in self._get_list():
            if x == item:
                return True
        else:
            return False

    def __len__(self):
        return len(self._get_list())

    def __getitem__(self, i):
        return self._get_list()[i]

    def __setitem__(self, i, item, check_exists=False):
        l = self._get_list()
        l[i] = item
        self._update_with(l)

    def __delitem__(self, i):
        l = self._get_list()
        del l[i]
        self._update_with(l)

    def append(self, item):
        self._header[self._keyword] = item

    def insert(self, i, item):
        l = self._get_list()
        l.insert(i, item)
        self._update_with(l)

    def pop(self, i=-1):
        l = self._get_list()
        l.pop(i)
        self._update_with(l)

    def remove(self, item):
        l = self._get_list()
        l.remove(item)
        self._update_with(l)

    def count(self, item):
        l = self._get_list()
        return l.count(item)

    def index(self, item, *args):
        l = self._get_list()
        return l.index(item, *args)

    def extend(self, other):
        for item in other:
            self.append(item)

    def clear(self):
        if self._keyword in self._header:
            del self._header[self._keyword]


class FitsListProxy(object):
    """
    A list of data that is backed by FITS HDUs.

    Parameters
    ----------
    storage : FitsStorage instance

    schema : schema fragment for each of the data elements

    name : string
        The HDU name (EXTNAME) to use
    """
    _do_not_validate = True

    def __init__(self, storage, prop, obj):
        self._storage = storage
        self._prop = prop
        self._obj = obj

        items = prop.schema.get('items')
        subprop = schema_property(schema=items, **items)
        subprop.name = prop.name
        subprop.path = prop.path
        self._schema = subprop.schema
        self._name = subprop.name
        self._subprop = subprop

        def find_hdus(d, schema, path):
            if schema.get('type', None) == 'data' and 'fits_hdu' in schema:
                d.append((schema['fits_hdu'], path))
        hdus = []
        schema.walk_schema(subprop.schema, find_hdus, hdus)

        self._hdu_names = [x[0] for x in hdus]
        self._hdu_names = [_convert_hdu_name(x) for x in self._hdu_names]
        self._path_to_default = hdus[0][1]

    def _get_for_index(self, index):
        if (self._subprop.schema is not None and
            self._subprop.type == 'object'):
            storage = copy.copy(self._storage)
            storage._hdu_index = index
            instance = schema.schema_to_tree(
                self._schema, storage=storage,
                name=self._name)
            return instance
        raise RuntimeError("Invalid schema")

    def item(self, d=None, **kwargs):
        if (self._schema is not None and
            self._schema.get('type') == 'object'):
            if d is None:
                d = kwargs
            try:
                schema.validate(d, self._schema)
            except ValidationError as e:
                raise ValueError(e.message)
            instance = schema.schema_to_tree(
                self._schema, storage=storage.TreeStorage(d),
                name=self._name)
            return instance
        else:
            return d

    def __repr__(self):
        return repr(list(self))

    def __str__(self):
        return str(list(self))

    def __lt__(self, other):
        return list(self) < other

    def __le__(self, other):
        return list(self) <= other

    def __eq__(self, other):
        return list(self) == other

    def __ne__(self, other):
        return list(self) != other

    def __gt__(self, other):
        return list(self) > other

    def __ge__(self, other):
        return list(self) >= other

    def __cmp__(self, other):
        return cmp(list(self), other)

    def __add__(self, other):
        return list(self) + other

    def __radd__(self, other):
        return other + list(self)

    def __iadd__(self, other):
        self.extend(other)

    def __mul__(self, other):
        return list(self) * other

    def __imul__(self, other):
        my_list = list(self)
        for i in xrange(other):
            self.extend(my_list)

    def __contains__(self, item):
        for x in self:
            if x == item:
                return True
        else:
            return False

    def __len__(self):
        count = 0
        while True:
            for hdu_name in self._hdu_names:
                try:
                    self._storage._get_hdu(self._prop.name, hdu_name, count)
                except AttributeError:
                    continue
                else:
                    count += 1
                    break
            else:
                return count

    def __getitem__(self, i):
        # Make sure it exists
        for hdu_name in self._hdu_names:
            try:
                self._storage._get_hdu(self._prop.name, hdu_name, i)
            except AttributeError:
                continue
            else:
                break
        else:
            raise IndexError("No hdus for index {0}".format(i))

        # Create an item object for it
        return self._get_for_index(i)

    def __setitem__(self, i, item, check_exists=False):
        if check_exists:
            for hdu_name in self._hdu_names:
                try:
                    self._storage._get_hdu(self._prop.name, hdu_name, i)
                except AttributeError:
                    continue
                else:
                    break
            else:
                raise IndexError("No hdus for index {0}".format(i))

        proxy = self._get_for_index(i)
        if isinstance(item, dict):
            proxy.from_tree(item)
        else:
            proxy.from_tree(item.to_tree())

    def __delitem__(self, i):
        # Before doing any deletions, make sure everything exists
        self.__getitem__(i)

        for hdu_name in self._hdu_names:
            try:
                self._storage._del_hdu(self._prop.name, hdu_name, i)
            except AttributeError:
                pass

    def append(self, item):
        length = len(self)

        self.__setitem__(length, item, check_exists=False)

        # If none of the HDUs exist, create the first one so it has a
        # placeholder.
        try:
            self.__getitem__(length)
        except IndexError:
            getattr(self._get_for_index(length), self._path_to_default)

    def insert(self, i, item):
        for hdu in self._storage.get_hdulist():
            for hdu_name in self._hdu_names:
                if (hdu.name == hdu_name and
                    hdu.header.get('EXTVER', 1) >= i + 1):
                    hdu.ver = hdu.header.get('EXTVER', 1) + 1
        self[i] = item

        # If none of the HDUs exist, create the first one so it has a
        # placeholder.
        try:
            self.__getitem__(i)
        except IndexError:
            getattr(self._get_for_index(i), self._path_to_default)

    def pop(self, i=-1):
        item = self[i]
        del self[i]
        return item

    def remove(self, item):
        for i, x in enumerate(self):
            if x is item:
                del self[i]
                return
        else:
            raise ValueError("item not found in list")

    def count(self, item):
        count = 0
        for x in self:
            if item == x:
                count += 1
        return count

    def index(self, item, *args):
        for i, x in enumerate(self):
            if x == item:
                return i
        raise ValueError("item not found in list")

    def extend(self, other):
        for item in other:
            self.append(item)

    def clear(self):
        hdulist = self._storage.get_hdulist()
        for hdu in list(hdulist):
            for hdu_name in self._hdu_names:
                if hdu.name == hdu_name:
                    hdulist.remove(hdu)


class FitsStorage(storage.Storage):
    def __init__(self, hdulist=None, hdu_index=None):
        from astropy.io import fits

        self._do_close = False

        if hdulist is None:
            hdulist = fits.HDUList()
            hdulist.append(fits.PrimaryHDU())

        if isinstance(hdulist, (unicode, bytes)):
            hdulist = fits.open(hdulist, uint=True)
            self._do_close = True
        elif hasattr(hdulist, "read"):
            hdulist = fits.open(hdulist, uint=True)

        self._fits = hdulist
        self._fallback = storage.TreeStorage()

        self._hdu_index = hdu_index

    def get_hdulist(self):
        if hasattr(self, '_fits'):
            return self._fits
        raise RuntimeError("FITS file already closed")

    def _get_hdu_name(self, prop):
        return _convert_hdu_name(getattr(prop, 'fits_hdu', None))

    def _assert_non_primary_hdu(self, prop, hdu_name):
        if hdu_name in (None, 0, 'PRIMARY'):
            raise ValueError(
                "schema for property '{0}' does not specify a non-primary hdu name".format(
                    '.'.join(prop.path)))

    def _get_hdu_pair(self, hdu_name, index=None):
        if index is None:
            pair = hdu_name
        else:
            pair = (hdu_name, index + 1)
        return pair

    def _get_hdu(self, name, hdu_name, index=None):
        if index is None:
            index = self._hdu_index
        pair = self._get_hdu_pair(hdu_name, index=index)
        try:
            hdu = self.get_hdulist()[pair]
        except (KeyError, IndexError, AttributeError):
            try:
                if index == 0:
                    hdu = self.get_hdulist()[pair[0]]
                else:
                    raise
            except (KeyError, IndexError, AttributeError):
                raise AttributeError(
                    "{0!r} property missing because FITS file has no "
                    "{1!r} HDU".format(
                        name, pair))

        if index is not None:
            if hdu.header.get('EXTVER', 1) != index + 1:
                raise AttributeError(
                    "{0!r} property missing because FITS file has no "
                    "{1!r} HDU".format(
                        name, pair))

        return hdu

    def _del_hdu(self, name, hdu_name, index=None):
        # We need to first call _get_hdu to make sure the HDU
        # we're about to delete actually exists
        self._get_hdu(name, hdu_name, index=index)

        pair = self._get_hdu_pair(hdu_name, index=index)

        try:
            del self.get_hdulist()[pair]
        except (KeyError, IndexError, AttributeError):
            if index == 0:
                del self.get_hdulist()[pair[0]]
            else:
                raise

        # We need to update all of the other EXTVER indices
        # greater than this one
        if index is not None:
            for hdu in self.get_hdulist():
                if (hdu.name == pair[0] and
                    hdu.header.get('EXTVER', 1) > index + 1):
                    hdu.ver = hdu.header.get('EXTVER', 1) - 1

    def close(self):
        if self._do_close:
            self.get_hdulist().close()
            # Delete the FITS object to ensure the file handle truly is closed.
            del self._fits

    def __get_array_section__(self, prop, obj, key, index=None):
        hdu_name = self._get_hdu_name(prop)
        name = prop.name
        hdu = self._get_hdu(name, hdu_name, index=index)

        val = hdu.section[key]
        return val

    def __get_shape__(self):
        hdu_name = _convert_hdu_name('SCI')

        try:
            hdu = self.get_hdulist()[hdu_name]
        except KeyError:
            hdu = self.get_hdulist()[0]
        try:
            return hdu.shape
        except AttributeError:
            # Support earlier versions of pyfits
            return hdu.data.shape

    def exists(self, prop, obj, index=None):
        from astropy.io import fits

        if index is None:
            index = self._hdu_index

        hdu_name = self._get_hdu_name(prop)
        name = prop.name

        if prop.is_data():
            self._assert_non_primary_hdu(prop, hdu_name)
            try:
                hdu = self._get_hdu(name, hdu_name, index)
            except AttributeError:
                return False
            return True
        else:
            if not hasattr(prop, 'fits_keyword'):
                if prop.type == 'array':
                    return False
                return self._fallback.exists(prop, obj)

            try:
                hdu = self._get_hdu(name, hdu_name, index)
            except AttributeError:
                return False

            try:
                val = hdu.header[prop.fits_keyword]
            except KeyError:
                return False

            return True

    def __get__(self, prop, obj, index=None):
        from astropy.io import fits

        if index is None:
            index = self._hdu_index

        hdu_name = self._get_hdu_name(prop)
        name = prop.name

        if prop.is_data():
            self._assert_non_primary_hdu(prop, hdu_name)
            try:
                hdu = self._get_hdu(name, hdu_name, index)
            except AttributeError:
                if index is None:
                    array = prop._make_default(obj)
                    if isinstance(prop.dtype, list):
                        hdu = fits.BinTableHDU(array, name=hdu_name)
                    else:
                        hdu = fits.ImageHDU(array, name=hdu_name)
                    if index is not None:
                        hdu.ver = index + 1
                    self.get_hdulist().append(hdu)
                else:
                    raise

            val = hdu.data
            return val
        else:
            if not hasattr(prop, 'fits_keyword'):
                if prop.type == 'array':
                    return FitsListProxy(self, prop, obj)
                return self._fallback.__get__(prop, obj)

            hdu = self._get_hdu(name, hdu_name, index)

            try:
                val = hdu.header[prop.fits_keyword]
            except KeyError:
                raise AttributeError(
                    "Fits file has no keyword {0}".format(prop.fits_keyword))

            if prop.fits_keyword in ('COMMENT', 'HISTORY'):
                val = CommentaryCardProxy(hdu.header, prop.fits_keyword)

            return val

    def __set__(self, prop, obj, val, index=None):
        from astropy.io import fits

        hdu_name = self._get_hdu_name(prop)
        name = prop.name
        if index is None:
            index = self._hdu_index

        def make_new_hdu():
            if isinstance(prop.dtype, list):
                hdu = fits.BinTableHDU(val, name=hdu_name)
            else:
                hdu = fits.ImageHDU(val, name=hdu_name)
            if index is not None:
                hdu.ver = index + 1
            self.get_hdulist().append(hdu)
            return hdu

        if prop.is_data():
            self._assert_non_primary_hdu(prop, hdu_name)
            try:
                hdu = self._get_hdu(name, hdu_name, index)
            except AttributeError:
                hdu = make_new_hdu()
            else:
                # The HDU may already have been created by setting
                # some metadata on it, but it might then be of the
                # wrong type.  If so, create a new HDU of the correct
                # type, and then copy the metadata over.
                if ((isinstance(prop.dtype, list) and
                     not isinstance(hdu, fits.BinTableHDU)) or
                    (not isinstance(prop.dtype, list) and
                     not isinstance(hdu, fits.ImageHDU))):
                    new_hdu = make_new_hdu()
                    for key, val in hdu.header.iteritems():
                        if not is_builtin_fits_keyword(key):
                            new_hdu.header[key] = val
                    self.get_hdulist().remove(hdu)
                else:
                    hdu.data = val
        else:
            if not hasattr(prop, 'fits_keyword'):
                if prop.type == 'array':
                    list_proxy = self.__get__(prop, obj)
                    list_proxy.clear()

                    for x in val:
                        list_proxy.append(x)
                else:
                    return self._fallback.__set__(prop, obj, val)
            else:
                try:
                    hdu = self._get_hdu(name, hdu_name, index=index)
                except AttributeError:
                    hdu = fits.ImageHDU(name=hdu_name)
                    if index is not None:
                        hdu.ver = index + 1
                    self.get_hdulist().append(hdu)

                # Can't store Unicode in a FITS comment
                comment = prop.get_short_doc().encode('ascii', 'replace')
                if isinstance(val, unicode) and sys.version_info[0] < 3:
                    val = val.encode('ascii', 'replace')
                if prop.fits_keyword in ('COMMENT', 'HISTORY'):
                    if prop.fits_keyword in hdu.header:
                        del hdu.header[prop.fits_keyword]
                    for item in val:
                        hdu.header[prop.fits_keyword] = item
                elif prop.fits_keyword in hdu.header:
                    hdu.header[prop.fits_keyword] = (val, comment)
                else:
                    hdu.header.append((prop.fits_keyword, val, comment), end=True)

    def __delete__(self, prop, obj, index=None):
        hdu_name = self._get_hdu_name(prop)
        name = prop.name

        if prop.is_data():
            self._assert_non_primary_hdu(prop, hdu_name)
            try:
                self._get_hdu(name, hdu_name, index=index)
            except AttributeError:
                pass
            else:
                self._del_hdu(name, hdu_name, index=index)
        else:
            if not hasattr(prop, 'fits_keyword'):
                return self._fallback.__delete__(prop, obj)

            try:
                hdu = self._get_hdu(name, hdu_name, index=index)
            except AttributeError:
                pass
            else:
                try:
                    del hdu.header[prop.fits_keyword]
                except KeyError:
                    pass

    def writeto(self, path, *args, **kwargs):
        self.get_hdulist().writeto(path, *args, **kwargs)

    @classmethod
    def write_model_to(cls, model, path, *args, **kwargs):
        storage = cls()

        # Write out the non-_extra_fits keywords first
        for obj, prop, val in model.iter_properties(include_comments=True):
            if isinstance(obj, basestring) and obj == 'comment':
                storage.add_comment(val)
            else:
                storage.__set__(prop, obj, val)

        storage.history = model.history

        storage.save_metadata_extension(model)
        storage.writeto(path, *args, **kwargs)

    def validate(self, model):
        for obj, prop, val in model.meta.iter_properties():
            if hasattr(prop, 'fits_keyword'):
                try:
                    prop.validate(model, val)
                except ValidationError:
                    warnings.warn(
                        "{0!r} is not valid in keyword {1!r}".format(
                            val, prop.fits_keyword))

    def extract_extra_elements(self, model):
        """
        Find any extra keywords in the FITS file that are not known by
        the schema and add them to `model._extra_fits_keys`.
        """
        self.load_metadata_extension(model)

        # Build a list of all known FITS keywords in the schema
        def extract_fits_info(known, tree, path):
            hdu = tree.get('fits_hdu', 0)
            key = tree.get('fits_keyword', None)
            if key is not None:
                known.setdefault(hdu, set()).add(key)

        known = {}
        schema.walk_schema(model.schema, extract_fits_info, data=known)

        hdus = {}
        for i, hdu in enumerate(self.get_hdulist()):
            cards = []
            for key, val, comment in hdu.header.cards:
                if is_builtin_fits_keyword(key):
                    continue
                if key in known.get(i, set()):
                    continue
                if key in known.get(hdu.name, set()):
                    continue
                cards.append((key, val, comment))
            if len(cards):
                hdus[hdu.name] = cards

        extend_schema_with_fits_keywords(model, hdus)

    def get_fits_header(self, model, hdu_name='PRIMARY'):
        """
        Generates a FITS header for a given FITS hdu.

        Parameters
        ----------
        model : ModelBase object

        hdu_name : str, optional
            The name of the HDU to get the WCS from.  This must use
            named HDU's, not numerical order HDUs.  To get the primary HDU,
            pass ``'PRIMARY'`` (default).

        Returns
        -------
        header : `astropy.io.fits.Header` object
        """
        try:
            hdu = self.get_hdulist()[_convert_hdu_name(hdu_name)]
        except KeyError:
            raise AttributeError(
                "FITS file has no {0!r} HDU".format(hdu_name))
        return hdu.header

    def add_comment(self, comment):
        """
        Add a blank comment to the primary header.
        """
        header = self.get_fits_header(None, 0)
        header.append((' ', ''), end=True)
        header.append((' ', comment), end=True)
        header.append((' ', ''), end=True)

    def save_metadata_extension(self, model):
        """
        Saves all of the metadata as a blob of json in an extension.
        """
        from astropy.io import fits

        try:
            hdu = self._get_hdu('meta', b'METADATA')
        except AttributeError:
            hdu = fits.ImageHDU(name=b'METADATA')
            self.get_hdulist().append(hdu)
        json_buffer = io.BytesIO()
        model.to_json(json_buffer)
        hdu.data = np.frombuffer(json_buffer.getvalue(), dtype='u1')

    def load_metadata_extension(self, model):
        """
        Loads metadata from a FITS extension.
        """
        from . import json_yaml

        assert self._fallback._tree == {}

        try:
            hdu = self._get_hdu('meta', b'METADATA')
        except AttributeError:
            # It's ok if we don't have a metadata extension,
            # we can just skip it and get all the metadata from
            # the FITS headers
            tree = {}
        else:
            json_buffer = io.BytesIO(hdu.data.tostring())
            json_buffer.seek(0)
            tree = {'meta': json_yaml.load(json_buffer)}
        self._fallback = storage.TreeStorage(tree)

    @property
    def history(self):
        return CommentaryCardProxy(self._fits[0].header, 'HISTORY')

    @history.setter
    def history(self, val):
        header = self._fits[0].header
        if 'HISTORY' in header:
            del header['HISTORY']
        for item in val:
            header['HISTORY'] = item


def extend_schema_with_fits_keywords(model, hdus):
    """
    Extends the schema of a model to include a bunch of FITS keywords.

    These will be put in the `_extra_fits` section of the model, with
    dictionaries for each of the HDUs.

    Parameters
    ----------
    model : `ModelBase` object
        The model whose schema we are to extend

    hdus : dictionary of lists
        Each key is the name of an HDU.  Each value is a list of
        tuples (key, val, comment) to include on that HDU.
    """
    properties = {}

    for hdu_name, cards in hdus.items():
        hdu_properties = collections.OrderedDict()
        for key, val, comment in cards:
            if is_builtin_fits_keyword(key):
                continue

            hdu_properties[key] = {
                "title": comment,
                "type": ["string", "number", "boolean"],
                "fits_hdu": hdu_name,
                "fits_keyword": key
                }

            if key in ('COMMENT', 'HISTORY'):
                hdu_properties[key]['type'] = 'array'
                hdu_properties[key]['items'] = {
                    "type": "string"
                    }

        if len(hdu_properties):
            properties[hdu_name] = {
                "title": ("Extra FITS keywords from "
                          "{0} HDU".format(hdu_name)),
                "type": "object",
                "properties": hdu_properties}

    properties = properties.items()
    properties.sort()
    properties = collections.OrderedDict(properties)

    model.extend_schema(
        {"type": "object",
         "properties": {
            "_extra_fits": {
            "title": "Extra FITS keywords that were not defined in "
            "the schema",
            "type": "object",
            "properties": properties
            }
         }
     })

    assert hasattr(model, '_extra_fits')

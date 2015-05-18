# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os
import re
import warnings

import numpy as np

import jsonschema

from astropy.extern import six
from astropy.io import fits

from pyasdf import AsdfFile
from pyasdf import resolver
from pyasdf import schema as pyasdf_schema
from pyasdf.tags.core import ndarray
from pyasdf import treeutil

from jsonschema import validators

from . import properties
from . import schema as mschema
from . import util


__all__ = ['to_fits', 'from_fits', 'fits_hdu_name', 'get_hdu']


_builtin_regexes = [
    '', 'NAXIS[0-9]{0,3}', 'BITPIX', 'XTENSION', 'PCOUNT', 'GCOUNT',
    'EXTEND', 'BSCALE', 'BZERO', 'BLANK', 'DATAMAX', 'DATAMIN',
    'EXTNAME', 'EXTVER', 'EXTLEVEL', 'GROUPS', 'PYTPE[0-9]',
    'PSCAL[0-9]', 'PZERO[0-9]', 'SIMPLE', 'TFIELDS',
    'TBCOL[0-9]{1,3}', 'TFORM[0-9]{1,3}', 'TTYPE[0-9]{1,3}',
    'TUNIT[0-9]{1,3}', 'TSCAL[0-9]{1,3}', 'TZERO[0-9]{1,3}',
    'TNULL[0-9]{1,3}', 'TDISP[0-9]{1,3}', 'HISTORY'
    ]


_builtin_regex = re.compile(
    '|'.join('(^{0}$)'.format(x) for x in _builtin_regexes))


def _is_builtin_fits_keyword(key):
    """
    Returns `True` if the given `key` is a built-in FITS keyword, i.e.
    a keyword that is managed by ``astropy.io.fits`` and we wouldn't
    want to propagate through the `_extra_fits` mechanism.
    """
    return _builtin_regex.match(key) is not None


_keyword_indices = [
    ('nnn', 1000, None),
    ('nn', 100, None),
    ('n', 10, None),
    ('s', 27, ' ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    ]


def _get_indexed_keyword(keyword, i):
    for (sub, max, r) in _keyword_indices:
        if sub in keyword:
            if i >= max:
                raise ValueError(
                    "Too many entries for given keyword '{0}'".format(keyword))
            if r is None:
                val = six.text_type(i)
            else:
                val = r[i]
            keyword = keyword.replace(sub, val)

    return keyword


if six.PY3:
    def fits_hdu_name(name):
        """
        Returns a FITS hdu name in the correct form for the current
        version of Python.
        """
        if isinstance(name, bytes):
            return name.decode('ascii')
        return name
else:
    def fits_hdu_name(name):
        """
        Returns a FITS hdu name in the correct form for the current
        version of Python.
        """
        if isinstance(name, unicode):
            return name.encode('ascii')
        return name


def _get_hdu_name(schema):
    hdu_name = schema.get('fits_hdu')
    if hdu_name in (None, 'PRIMARY'):
        hdu_name = 0
    else:
        hdu_name = fits_hdu_name(hdu_name)
    return hdu_name


def _make_new_hdu(hdulist, value, hdu_name, index=None):
    if isinstance(value.dtype, list):
        hdu = fits.BinTableHDU(value, name=hdu_name)
    else:
        hdu = fits.ImageHDU(value, name=hdu_name)
    if index is not None:
        hdu.ver = index + 1
    hdulist.append(hdu)
    return hdu


def _get_hdu_pair(hdu_name, index=None):
    if index is None:
        pair = hdu_name
    else:
        pair = (hdu_name, index + 1)
    return pair


def get_hdu(hdulist, hdu_name, index=None):
    pair = _get_hdu_pair(hdu_name, index=index)
    try:
        hdu = hdulist[pair]
    except (KeyError, IndexError, AttributeError):
        try:
            if index is None:
                hdu = hdulist[(pair, 1)]
            elif index == 0:
                hdu = hdulist[pair[0]]
            else:
                raise
        except (KeyError, IndexError, AttributeError):
            raise AttributeError(
                "Property missing because FITS file has no "
                "'{0!r}' HDU".format(
                    pair))

    if index is not None:
        if hdu.header.get('EXTVER', 1) != index + 1:
            raise AttributeError(
                "Property missing because FITS file has no "
                "{0!r} HDU".format(
                    pair))

    return hdu


def _make_hdu(hdulist, hdu_name, index=None, hdu_type=None, value=None):
    if hdu_type is None:
        if hdu_name in (0, 'PRIMARY'):
            hdu_type = fits.PrimaryHDU
        else:
            hdu_type = fits.ImageHDU
    hdu = hdu_type(value, name=hdu_name)
    if index is not None:
        hdu.ver = index + 1
    hdulist.append(hdu)
    return hdu


def _get_or_make_hdu(hdulist, hdu_name, index=None, hdu_type=None, value=None):
    try:
        hdu = get_hdu(hdulist, hdu_name, index=index)
    except AttributeError:
        hdu = _make_hdu(hdulist, hdu_name, index=index, hdu_type=hdu_type,
                        value=value)
    else:
        if hdu_type is not None and not isinstance(hdu, hdu_type):
            new_hdu = _make_hdu(hdulist, hdu_name, index=index,
                                hdu_type=hdu_type, value=value)
            for key, val in six.iteritems(hdu.header):
                if not _is_builtin_fits_keyword(key):
                    new_hdu.header[key] = val
            hdulist.remove(hdu)
            hdu = new_hdu
        elif value is not None:
            hdu.data = value
    return hdu


def _assert_non_primary_hdu(hdu_name):
    if hdu_name in (None, 0, 'PRIMARY'):
        raise ValueError(
            "Schema for data property does not specify a non-primary hdu name")


##############################################################################
# WRITER


def _fits_comment_section_handler(validator, properties, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    title = schema.get('title')
    if title is not None:
        current_comment_stack = validator.comment_stack
        current_comment_stack.append(util.ensure_ascii(title))

    for property, subschema in six.iteritems(properties):
        if property in instance:
            for error in validator.descend(
                instance[property],
                subschema,
                path=property,
                schema_path=property,
            ):
                yield error

    if title is not None:
        current_comment_stack.pop(-1)


def _fits_element_writer(validator, fits_keyword, instance, schema):
    if schema.get('type', 'object') in ('object', 'array'):
        raise ValueError(
            "'fits_keyword' not valid with type of 'object' or 'array'")

    hdu_name = _get_hdu_name(schema)
    index = getattr(validator, 'sequence_index', None)
    hdu = _get_or_make_hdu(validator.hdulist, hdu_name, index=index)

    for comment in validator.comment_stack:
        hdu.header.append((' ', ''), end=True)
        hdu.header.append((' ', comment), end=True)
        hdu.header.append((' ', ''), end=True)
    validator.comment_stack = []

    comment = util.ensure_ascii(util.get_short_doc(schema))
    instance = util.ensure_ascii(instance)

    if fits_keyword in ('COMMENT', 'HISTORY'):
        for item in instance:
            hdu.header[fits_keyword] = util.ensure_ascii(item)
    elif fits_keyword in hdu.header:
        hdu.header[fits_keyword] = (instance, comment)
    else:
        hdu.header.append((fits_keyword, instance, comment), end=True)


def _fits_array_writer(validator, _, instance, schema):
    if instance is None:
        return

    instance = np.asarray(instance)

    if not len(instance.shape):
        return

    if 'ndim' in schema:
        ndarray.validate_ndim(validator, schema['ndim'], instance, schema)
    if 'dtype' in schema:
        ndarray.validate_dtype(validator, schema['dtype'], instance, schema)

    hdu_name = _get_hdu_name(schema)
    _assert_non_primary_hdu(hdu_name)
    if instance.dtype.names is not None:
        hdu_type = fits.BinTableHDU
    else:
        hdu_type = fits.ImageHDU
    index = getattr(validator, 'sequence_index', None)
    hdu = _get_or_make_hdu(validator.hdulist, hdu_name, index=index, hdu_type=hdu_type)

    hdu.data = instance


# This is copied from jsonschema._validators and modified to keep track
# of the index of the item we've recursed into.
def _fits_item_recurse(validator, items, instance, schema):
    if not validator.is_type(instance, "array"):
        return

    if validator.is_type(items, "object"):
        for index, item in enumerate(instance):
            print(index, item)
            validator.sequence_index = index
            for error in validator.descend(item, items, path=index):
                yield error
    else:
        # We don't do the index trick on "tuple validated" sequences
        for (index, item), subschema in zip(enumerate(instance), items):
            for error in validator.descend(
                item, subschema, path=index, schema_path=index,
            ):
                yield error


def _fits_type(validator, items, instance, schema):
    if instance in ('N/A', '#TODO', '', None):
        return
    return validators._validators.type_draft4(validator, items, instance, schema)


FITS_VALIDATORS = pyasdf_schema.YAML_VALIDATORS.copy()


FITS_VALIDATORS.update({
    'fits_keyword': _fits_element_writer,
    'ndim': _fits_array_writer,
    'datatype': _fits_array_writer,
    'items': _fits_item_recurse,
    'properties': _fits_comment_section_handler,
    'type': _fits_type
})


META_SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'metaschema'))


FITS_SCHEMA_URL_MAPPING = resolver.Resolver([
    ('http://stsci.edu/schemas/fits-schema/',
     'file://' + META_SCHEMA_PATH + '/{url_suffix}.yaml')], 'url')


_fits_saver = None
def _get_fits_saver():
    global _fits_saver
    if _fits_saver is not None:
        return _fits_saver

    validator = validators.create(
        meta_schema=pyasdf_schema.load_schema(
            'http://stsci.edu/schemas/fits-schema/fits-schema',
            FITS_SCHEMA_URL_MAPPING),
        validators=FITS_VALIDATORS)

    _fits_saver = validator
    return _fits_saver


# print(validators.meta_schemas)


# TODO
# validators.meta_schemas['http://stsci.edu/schemas/fits-schema/fits-schema'] = \
#     validators.meta_schemas['http://stsci.edu/schemas/asdf-schema/0.1.0/asdf-schema']


def _save_from_schema(hdulist, tree, schema):
    fits_saver = _get_fits_saver()

    validator = fits_saver(schema)

    validator.hdulist = hdulist
    # TODO: Handle comment stack on per-hdu-basis
    validator.comment_stack = []
    # This actually kicks off the saving
    validator.validate(tree)


def _save_extra_fits(hdulist, tree):
    # Handle _extra_fits
    for hdu_name, parts in six.iteritems(tree.get('extra_fits', {})):
        hdu_name = fits_hdu_name(hdu_name)
        hdu = _get_or_make_hdu(hdulist, hdu_name)
        if 'header' in parts:
            for key, val, comment in parts['header']:
                if _is_builtin_fits_keyword(key):
                    continue
                hdu.header.append((key, val, comment), end=True)
        if 'data' in parts:
            hdu.data = parts['data']


def _save_metadata_extension(hdulist, tree):
    def remove_arrays(node):
        if isinstance(node, np.ndarray):
            return None
        return node
    tree = treeutil.walk_and_modify(tree, remove_arrays)

    # Saves the tree as a raw YAML dump in a special extension called "METADATA"
    yaml_buffer = io.BytesIO()
    af = AsdfFile(tree)
    af.write_to(yaml_buffer)
    array = np.frombuffer(yaml_buffer.getvalue(), dtype='u1')
    _get_or_make_hdu(
        hdulist, b'METADATA', hdu_type=fits.ImageHDU, value=array)


def _save_history(hdulist, tree):
    history = tree.get('history', [])
    for entry in history:
        hdulist[0].header['HISTORY'] = entry


def to_fits(hdulist, tree, schema):
    if hdulist is None:
        hdulist = fits.HDUList()
        hdulist.append(fits.PrimaryHDU())

    _save_from_schema(hdulist, tree, schema)
    _save_extra_fits(hdulist, tree)
    _save_metadata_extension(hdulist, tree)
    _save_history(hdulist, tree)

    return hdulist


##############################################################################
# READER


def _fits_keyword_loader(hdulist, fits_keyword, schema, hdu_index, known_keywords):
    hdu_name = _get_hdu_name(schema)
    try:
        hdu = get_hdu(hdulist, hdu_name, hdu_index)
    except AttributeError:
        return None

    if schema['type'] == 'data':
        return hdu.data

    try:
        val = hdu.header[fits_keyword]
    except KeyError:
        return None

    if val in ('N/A', '#TODO', ''):
        return None

    known_keywords.setdefault(hdu, set()).add(fits_keyword)

    return val


def _fits_array_loader(hdulist, schema, hdu_index, known_datas):
    hdu_name = _get_hdu_name(schema)
    _assert_non_primary_hdu(hdu_name)
    try:
        hdu = get_hdu(hdulist, hdu_name, hdu_index)
    except AttributeError:
        return None

    known_datas.add(hdu)

    data = hdu.data
    data = properties._cast(data, schema)
    return data


def _schema_has_fits_hdu(schema):
    has_fits_hdu = [False]

    def walker(node):
        if isinstance(node, dict) and 'fits_hdu' in node:
            has_fits_hdu[0] = True
    treeutil.walk(schema, walker)
    return has_fits_hdu[0]


def _load_metadata_extension(hdulist, schema):
    try:
        hdu = get_hdu(hdulist, b'METADATA')
    except AttributeError:
        return {}
    else:
        yaml_buffer = io.BytesIO(hdu.data.tostring())
        yaml_buffer.seek(0)
        with AsdfFile.open(yaml_buffer) as af:
            tree = af.tree
        return tree


def _load_from_schema(hdulist, schema, tree, validate=True):
    known_keywords = {}
    known_datas = set()

    def callback(schema, path, combiner, ctx, recurse):
        result = None

        if 'fits_keyword' in schema:
            fits_keyword = schema['fits_keyword']
            result = _fits_keyword_loader(
                hdulist, fits_keyword, schema,
                ctx.get('hdu_index', 0), known_keywords)
            if result is not None:
                temp_schema = {
                    '$schema':
                    'http://stsci.edu/schemas/asdf-schema/0.1.0/asdf-schema'}
                temp_schema.update(schema)
                try:
                    pyasdf_schema.validate(result, schema=temp_schema)
                except jsonschema.ValidationError:
                    if validate:
                        raise
                    else:
                        warnings.warn(
                            "'{0}' is not valid in keyword '{1}'".format(
                                result, fits_keyword))
                else:
                    properties.put_value(path, result, tree)

        elif 'ndim' in schema or 'datatype' in schema:
            result = _fits_array_loader(
                hdulist, schema, ctx.get('hdu_index', 0), known_datas)
            if result is not None:
                temp_schema = {
                    '$schema':
                    'http://stsci.edu/schemas/asdf-schema/0.1.0/asdf-schema'}
                temp_schema.update(schema)
                pyasdf_schema.validate(result, schema=temp_schema)
                properties.put_value(path, result, tree)

        if schema.get('type') == 'array':
            has_fits_hdu = _schema_has_fits_hdu(schema)
            if has_fits_hdu:
                for i in range(len(hdulist)):
                    recurse(schema['items'], path + [i], combiner, {'hdu_index': i})
                return True

    mschema.walk_schema(schema, callback, {'hdu_index': 0})

    return known_keywords, known_datas


def _load_extra_fits(hdulist, known_keywords, known_datas, tree):
    # Handle _extra_fits
    for hdu in hdulist:
        known = known_keywords.get(hdu, set())

        cards = []
        for key, val, comment in hdu.header.cards:
            if not (_is_builtin_fits_keyword(key) or
                    key in known):
                cards.append([key, val, comment])

        if len(cards):
            properties.put_value(
                ['extra_fits', hdu.name, 'header'], cards, tree)

        if hdu not in known_datas:
            if hdu.data is not None:
                properties.put_value(
                    ['extra_fits', hdu.name, 'data'], hdu.data, tree)


def _load_history(hdulist, tree):
    try:
        hdu = get_hdu(hdulist, 0)
    except AttributeError:
        return

    header = hdu.header
    if 'HISTORY' not in header:
        return

    history = tree['history'] = []

    for entry in header['HISTORY']:
        history.append(entry)


def from_fits(hdulist, schema, validate=True):
    tree = _load_metadata_extension(hdulist, schema)
    known_keywords, known_datas = _load_from_schema(hdulist, schema, tree, validate)
    _load_extra_fits(hdulist, known_keywords, known_datas, tree)
    _load_history(hdulist, tree)

    return tree
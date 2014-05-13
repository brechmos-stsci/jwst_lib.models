"""
This module contains functionality related to the data model's use of
JSON Schema.
"""

# TODO: Add __all__ members to modules

from __future__ import absolute_import, unicode_literals, division, print_function

import collections
import copy
import io
import os
import sys
import urllib
import urlparse
import warnings

import numpy as np

from .lib import jsonschema
from .lib.jsonschema import ValidationError

from . import arrays
from . import extensions
from . import json_yaml
from . import storage
from . import util

# Silence a warning from jsonschema
jsonschema.securedict = True


# Extend the version 4 schema to include the two custom types we use:
# data and pickle
jsonschema.Draft4Validator.META_SCHEMA['definitions']['simpleTypes']['enum'].extend(
    ['data', 'pickle'])


class ValidatingList(object):
    """
    A list that validates itself against a JSON schema fragment on
    every change.

    Parameters
    ----------
    schema : dict
        JSON schema fragment from the "items" property of the list.

    name : string
        Name of the array.  Used when generating new items of the
        expected type

    x : list
        A list to initialize with

    Examples
    --------
    For example, suppose we had the following schema which defines a
    list of objects::

        people = {
            "type" : "object",
            "properties" : {
                "name" : {
                    "type" : "string"
                },
                "age" : {
                    "type" : "number"
                }
            },
            "additionalProperties" : False
            }

    This class ensures that no invalid items can be added to the list::

        >>> l = ValidatingList(people, 'people')
        >>> l.append({'name': 'John Doe', 'age': 64})
        >>> l.append({'foo': 'bar})
        ValueError: Additional properties are not allowed ('foo' was unexpected)
        >>> l.append(42)
        ValueError: 42 is not of type 'object'
    """
    def __init__(self, schema, name, x=[]):
        if not isinstance(schema, dict):
            raise NotImplementedError(
                "tuple-checking on arrays is not supported")

        self._schema = schema
        self._name = name
        if isinstance(x, ValidatingList):
            x = x._x
        for item in x:
            self._check(item)
        self._x = x

    def item(self, d=None, **kwargs):
        if (self._schema is not None and
            self._schema.get('type') == 'object'):
            if d is None:
                d = kwargs
            try:
                validate(d, self._schema)
            except ValidationError as e:
                raise ValueError(e.message)
            instance = schema_to_tree(
                self._schema, storage=storage.TreeStorage(d),
                name=self._name)
            return instance
        else:
            return d

    def _check(self, item):
        if isinstance(item, MetaBase):
            # This should only be treestorage
            item = item.storage._tree
        try:
            validate(item, self._schema)
        except ValidationError as e:
            raise ValueError(e.message)
        return item

    def __cast(self, other):
        if isinstance(other, ValidatingList):
            return other._x
        else:
            return other

    def __repr__(self):
        return repr(self._x)

    def __lt__(self, other):
        return self._x < self.__cast(other)

    def __le__(self, other):
        return self._x <= self.__cast(other)

    def __eq__(self, other):
        return self._x == self.__cast(other)

    def __ne__(self, other):
        return self._x != self.__cast(other)

    def __gt__(self, other):
        return self._x > self.__cast(other)

    def __cmp__(self, other):
        return cmp(self._x, self.__cast(other))

    def __contains__(self, item):
        item = self._check(item)
        return item in self._x

    def __len__(self):
        return len(self._x)

    def __iter__(self):
        for x in self._x:
            yield self.item(x)

    def __getitem__(self, i):
        return self.item(self._x[i])

    def __setitem__(self, i, item):
        item = self._check(item)
        self._x[i] = item

    def __delitem__(self, i):
        del self._x[i]

    def __add__(self, other):
        return self.__class__(
            self._schema,
            self._name,
            self._x + self.__cast(other))

    def __radd__(self, other):
        return self.__class__(
            self._schema,
            self._name,
            self.__cast(other) + self._x)

    def __iadd__(self, other):
        for item in self.__cast(other):
            self.append(item)

    def __mul__(self, n):
        return self.__class__(self._schema, self._name, self._x * n)

    def __imul__(self, n):
        self._x *= n
        return self

    def append(self, item):
        item = self._check(item)
        self._x.append(item)

    def insert(self, i, item):
        item = self._check(item)
        self._x.insert(i, item)

    def pop(self, i=-1):
        return self.item(self._x.pop(i))

    def remove(self, item):
        item = self._check(item)
        self._x.remove(item)

    def count(self, item):
        item = self._check(item)
        return self._x.count(item)

    def index(self, item, *args):
        item = self._check(item)
        return self._x.index(item, *args)

    def reverse(self):
        self._x.reverse()

    def extend(self, other):
        other = self.__cast(other)
        for item in other:
            self.append(item)


class schema_property(object):
    """
    This is a convenient way to describe a property that can have
    different storage backends.  It can be automatically validated
    against a JSON Schema chunk, and converted to and from native
    datatypes (see `extensions.py`).

    It is a \"descriptor\" which ends up looking like a member
    variable (or property) when assigned to a class.  See this:

        http://docs.python.org/howto/descriptor.html
    """
    _extensions = extensions.extensions

    def __init__(self, name=None, path=None, doc=None, schema={},
                 readonly=False, default=None, type='string',
                 is_ad_hoc=False, dtype=np.float_, ndim=None, **kwargs):
        """
        Parameters
        ----------
        name : str
            The name of this property

        path : list
            The fully-qualified path to the property

        doc : str, optional
            The docstring for this property.

        schema : dict, optional
            The JSON schema of the value

        readonly : bool, optional
            If True, the property will be readonly

        default : any, optional
            The default value to fill any newly-created arrays with

        type : str, optional
            The data type of the property

        is_ad_hoc : bool, optional
            When True, this is an ad-hoc property that is not part of
            the schema

        Extra parameters
        ----------------

        ndim : int, optional
            Insist that the array has the given number of dimensions.

        dtype : numpy dtype or str, optional
            The dtype of the array to create.  Must be one of the fixed-size
            data types.

        **kwargs : dict
            Other attributes that may be used by other storage
            backends.  These will all be set as attributes on this
            property object.
        """
        self.name = name

        if path is None:
            path = [name]
        self.path = path

        title = kwargs.get('title')
        description = kwargs.get('description')
        if description is None:
            description = title
        else:
            if title is not None:
                description = title + '\n\n' + description
        self.__doc__ = doc or description
        self.description = description

        self.schema = schema

        self.readonly = readonly

        if default is None:
            if type == 'data':
                default = 0.0
            elif type == 'array':
                default = []
        self.default = default

        self.type = type

        if self.is_data() and is_ad_hoc:
            raise ValueError("'data' schema elements may not be ad-hoc")

        self.is_ad_hoc = is_ad_hoc

        if self.is_data():
            if dtype is not None:
                dtype = arrays.schema_dtype_to_numpy_dtype(dtype)
            self.dtype = dtype

            self.ndim = ndim

        for key, val in kwargs.items():
            setattr(self, key, val)

    def _formatted_error(self, errtype, message):
        return errtype("{0}: {1}".format('.'.join(self.path), message))

    def get_short_doc(self):
        """
        Retrieves the first line of the docstring.  Useful for
        summaries in eg., FITS comments.
        """
        return self.__doc__.partition('\n')[0]

    def validate(self, obj, val):
        """
        Validate the given value against the JSON Schema associated
        with this property.

        A `ValueError` is raised if the value does not validate.

        It may also be converted from a basic datatype to a native
        datatype and returned.
        """
        if self.is_data():
            if val is not None:
                val = util.gentle_asarray(val, self.dtype)

                # # Check the shape of the data array
                # if obj.shape is not None:
                #     if not util.can_broadcast(val.shape, obj.shape):
                #         raise self._formatted_error(
                #             ValueError,
                #             "Shape mismatch. Got {0}, expected {1}".format(
                #             val.shape, obj.shape))
                # else:
                #     obj._shape = val.shape

            return val
        else:
            format = self.schema.get('format')
            if val is not None and format and format in self._extensions:
                extension = self._extensions[format]
                try:
                    try:
                        extension.validate(val)
                    except (ValueError, TypeError):
                        extension.validate(extension.from_basic(val))
                except (ValueError, TypeError) as e:
                    raise self._formatted_error(type(e), e.message)
            else:
                try:
                    validate(val, self.schema)
                except ValidationError as e:
                    raise self._formatted_error(ValueError, e.message)

            return val

    def __get__(self, obj, objtype):
        """
        Get the value of the property.

        This is a special method that is part of Python's
        \"descriptor\" protocol.

        If `obj` is backed by a FITS file, it returns the keyword from
        the requested header.  Otherwise the value stored in `obj` is
        returned.  If neither is available, the default is set on
        `obj` and that is returned.

        Parameters
        ----------
        obj : object instance
            The object containing the property.  A member variable of
            this object ('_' + self.name) may be used to store the
            value.

        objtype : type of `obj`
        """
        # This is needed so the docstring can be obtained
        if obj is None:
            return self

        try:
            val = obj.storage.__get__(self, obj)
            if self.is_data():
                new_val = self.validate(obj, val)
                if new_val is not val:
                    obj.storage.__set__(self, obj, new_val)
                    val = new_val
            elif val is not None and not hasattr(val, '_skip_validation'):
                try:
                    val = self.from_basic_type(val)
                except ValueError as e:
                    val = self._make_default(obj)
                    self.__set__(obj, val)
                    warnings.warn(
                        "{0}. Setting to default of {1!r}".format(
                            e.message, val))
                    return val
        except AttributeError as e:
            if self.is_ad_hoc:
                raise
            else:
                val = self._make_default(obj)
                if val is not None:
                    obj.storage.__set__(self, obj, val)
                if self.type == "array":
                    items = self.schema.get('items')
                    val = ValidatingList(items, self.name, val)

        return val

    def __set__(self, obj, val):
        """
        Set the value of the property.

        This is a special method that is part of Python's
        \"descriptor\" protocol.

        Parameters
        ----------
        obj : object instance
            The object containing the property.

        val : any
            The value.
        """
        if self.readonly:
            raise self._formatted_error(
                AttributeError, "is readonly")

        if self.is_data():
            val = util.gentle_asarray(val, dtype=self.dtype)
            val = self.validate(obj, val)

            if self.ndim:
                if val.ndim != self.ndim:
                    raise self._formatted_error(
                        ValueError, "must have {0} dimensions".format(
                            self.ndim))

        val = self.to_basic_type(val)

        obj.storage.__set__(self, obj, val)

    def __delete__(self, obj):
        """
        Delete the value of the property.

        This is a special method that is part of Python's
        \"descriptor\" protocol.

        Parameters
        ----------
        obj : object instance
            The object containing the property.
        """
        if self.readonly:
            raise self._formatted_error(
                AttributeError, "is readonly")

        obj.storage.__delete__(self, obj)

    def _make_default(self, obj):
        if self.is_data():
            primary_array_name = obj.get_primary_array_name()
            if self.name == primary_array_name:
                if obj.shape is None:
                    shape = (0,)
                else:
                    shape = obj.shape
                array = np.empty(shape, dtype=self.dtype)
                array[...] = self.default
            else:
                if isinstance(self.dtype, list):
                    if self.ndim is None:
                        array = np.empty((1,), dtype=self.dtype)
                    else:
                        array = np.empty(tuple([1] * self.ndim),
                                         dtype=self.dtype)
                else:
                    has_primary_array_shape = False
                    if primary_array_name is not None:
                        primary_array = getattr(obj, primary_array_name, None)
                        has_primary_array_shape = primary_array is not None

                    if has_primary_array_shape:
                        if self.ndim is None:
                            array = np.empty(
                                primary_array.shape, dtype=self.dtype)
                        else:
                            array = np.empty(
                                primary_array.shape[-self.ndim:],
                                dtype=self.dtype)
                    elif self.ndim is None:
                        array = np.empty((0,), dtype=self.dtype)
                    else:
                        array = np.empty(tuple([0] * self.ndim),
                                         dtype=self.dtype)
                    if self.default is not None:
                        array[...] = self.default
            return array
        else:
            return copy.deepcopy(self.default)

    def from_basic_type(self, val):
        """
        Convert the given value (which must comply with this property)
        from a basic serializable type to a native type.
        """
        if val is not None and not hasattr(val, '_do_not_validate'):
            if (self.schema.get('type') == 'pickle' and
                isinstance(val, basestring)):
                import cPickle
                if isinstance(val, unicode):
                    val = val.encode('latin-1')
                val = cPickle.loads(val)
            else:
                try:
                    validate(val, self.schema)
                except ValidationError as e:
                    raise self._formatted_error(ValueError, e.message)
                format = self.schema.get('format')
                if format and format in self._extensions:
                    try:
                        val = self._extensions[format].from_basic(val)
                    except (ValueError, TypeError) as e:
                        raise self._formatted_error(ValueError, e.message)
                if self.schema.get('type') == 'array':
                    items = self.schema.get('items')
                    val = ValidatingList(items, self.name, val)
        return val

    def to_basic_type(self, val):
        """
        Convert the given value (which must comply with this property)
        from a native type to a basic serializable type.
        """
        if val is not None:
            if self.schema.get('type') == 'array':
                if isinstance(val, ValidatingList):
                    val = val._x
                else:
                    val = list(val)
                new_val = []
                for x in val:
                    if isinstance(x, MetaBase):
                        new_val.append(x.to_tree())
                    else:
                        new_val.append(x)
                val = new_val
            elif (self.schema.get('type') == 'pickle' and
                  not isinstance(val, basestring)):
                import cPickle
                val = cPickle.dumps(val)
                val = val.decode('latin-1')

            format = self.schema.get('format')
            if format and format in self._extensions:
                extension = self._extensions[format]
                try:
                    extension.validate(val)
                except (ValueError, TypeError) as e:
                    raise self._formatted_error(ValueError, e.message)
                try:
                    val = extension.to_basic(val)
                except (ValueError, TypeError) as e:
                    raise self._formatted_error(ValueError, e.message)

            if not self.is_data():
                try:
                    validate(val, self.schema)
                except ValidationError as e:
                    raise self._formatted_error(ValueError, e.message)
        return val

    def is_data(self):
        """
        Returns `True` if the property refers to a data array.
        """
        return self.type == 'data'


class HasArrayProperties(object):
    """
    This is a mixin class for all objects that have array properties.
    It simply provides a way to iterate over all of the array
    properties.
    """
    def get_section(self, name):
        """
        Retrieve only a section of a data array from disk.

        Parameters
        ----------
        name : str
            The array member's name, eg. 'data', 'dq' or 'err'

        Returns
        -------
        proxy : Section instance
            Returns a proxy that can be used to get a subarray

        Notes
        -----
        With recent versions of astropy, it may be more efficient to
        just use its memmapping feature rather than `get_section`.

        Examples
        --------
        model.get_section('data')[1:45,95:100]
        """
        try:
            prop = getattr(self.__class__, name)
            if not prop.is_data():
                raise AttributeError()
        except AttributeError:
            raise AttributeError("No array member {0!r}".format(name))

        class Section(object):
            def __init__(self, obj, prop, storage):
                self._obj = obj
                self._prop = prop
                self._storage = storage

            def __getitem__(self, key):
                return self._storage.__get_array_section__(
                    self._prop, self._obj, key)

        return Section(self, prop, self.storage)


def validate_schema(schema):
    """
    Validates the given schema to ensure it is a compliant JSON
    Schema.

    Parameters
    ----------
    schema : JSON schema fragment

    Raises
    ------
    ValidationError :
        If the schema is not valid
    """
    jsonschema.Draft4Validator.check_schema(schema)


def validate(instance, schema):
    """
    Validates the given instance against the given JSON schema.

    Parameters
    ----------
    instance : any
        An instance of the given schema

    schema : JSON schema fragment

    Raises
    ------
    ValidationError :
        If `instance` does not validate against `schema`.
    """
    jsonschema.validate(instance, schema, cls=jsonschema.Draft4Validator, types=[
        ('data', np.ndarray), ('pickle', object)])


def get_schema_path(path, base_url):
    """
    Given a relative schema path, return a the fully resolve URL and
    the fragment (the part after '#'), if any.

    Parameters
    ----------
    path : str
        The relative schema path

    base_url : str
        The base URL to resolve against.  May also be a local
        filesystem path, in which case it will be converted to a URL
        using `urllib.pathname2url`.

    Returns
    -------
    url, fragment : tuple
        A fully resolved URL and a fragment (the part after the '#')

    Notes
    -----
    Schema paths come from a number of sources: the `schema_url`
    member in model classes, and the `$ref` feature in JSON Schema.

    If the schema path starts with a '/', it is treated as an absolute
    file path.

    If the schema path points to the special HTTP location
    ``http://jwst_lib.stsci.edu/schemas/$PACKAGE/$SCHEMA``, a heuristic
    is used to find the schema within the local Python package
    namespace.  ``$PACKAGE`` is the dot-separated path to a Python
    package, and ``$SCHEMA`` is the name of a schema file that ships
    with that package.  For example, to refer to the (hypothetical)
    ``bad_pixel_mask`` schema that ships with a Python package called
    ``mirilib``, use the following URL::

        http://jwst_lib.stsci.edu/schemas/mirilib/bad_pixel_mask.schema.json

    The ``$PACKAGE`` portion may be omitted to refer to schemas in the
    `jwst_lib.models` core::

        http://jwst_lib.stsci.edu/schemas/mirilib/image.schema.json
    """
    url_path, pound, json_pointer = path.partition('#')

    parts = urlparse.urlparse(base_url)
    if parts[0] == '' or os.path.isabs(base_url):
        parts = list(parts)
        parts[0] = 'file'
        parts[2] = urllib.pathname2url(base_url)
        base_url = urlparse.urlunparse(parts)
        if not base_url.endswith('/'):
            base_url += '/'

    url = urlparse.urljoin(
        base_url, url_path, allow_fragments=False)

    if url.startswith('http://jwst_lib.stsci.edu/schemas/'):
        import importlib

        path = urlparse.urlparse(url)[2]
        parts = path.split('/')
        if len(parts) == 4:
            package = parts[-2]
        elif len(parts) == 3:
            package = "jwst_lib.models"
        else:
            raise ValueError("Unknown schema URL {0!r}".format(url))
        filename = parts[-1]
        try:
            mod = importlib.import_module(package)
        except ImportError:
            # If the module can't be imported, try as a regular URL
            return url, json_pointer
        path = os.path.join(os.path.dirname(mod.__file__), 'schemas', filename)
        path = urllib.pathname2url(path)
        url = urlparse.urlunparse(('file', '', path, '', '', ''))

    return url, json_pointer


_schemas = {}
def get_schema(schema_url, base_url):
    """
    Load the schema from disk, resolve references, validate it, and
    return the tree of objects.

    Parameters
    ----------
    schema_url : str
        The relative URL to the schema to load.

    base_url : str
        The base URL to resolve against.

    Notes
    -----
    The schemas are cached in memory, so after the first time that a
    schema of a given name is loaded, it will not change.

    See also
    --------
    get_schema_path :
        For a description of the `schema_url` parameter.
    """
    schema_path, json_pointer = get_schema_path(schema_url, base_url)
    if (schema_path, json_pointer) not in _schemas:
        tree = _fetch_schema_subtree(schema_path, json_pointer)
        tree = resolve_references(tree, schema_path)
        validate_schema(tree)
        _schemas[(schema_path, json_pointer)] = tree
    return _schemas[(schema_path, json_pointer)]


class MetaBase(storage.HasStorage):
    """
    The base class for meta data namespaces.  These correspond to
    \"object\" types in JSON Schema.

    This allows the programmer to refer to properties of objects (in
    JSON parlance) using attribute syntax (``foo.bar``) rather than
    item syntax (``foo['bar']``).  Since each of the attributes is
    actually a property, on-the-fly type checking against the schema
    can also be performed for each of the values.

    You should not need to inherit from this directly, but instead let
    the subclasses be created in `schema_to_tree`.
    """
    def get_primary_array_name(self):
        """
        Returns the name "primary" array for this model, which
        controls the size of other arrays that are implicitly created.
        This is intended to be overridden in the subclasses if the
        primary array's name is not "data".
        """
        return None

    def __eq__(self, other):
        if isinstance(other, MetaBase):
            tree_b = other.to_tree()
        elif isinstance(other, dict):
            tree_b = other
        else:
            raise TypeError(
                "Can not compare MetaBase to {!r}".format(type(other)))

        tree_a = self.to_tree()
        return tree_a == tree_b

    def validate_tree(self, tree):
        validate(tree, self._schema)

    def iter_properties(self, include_comments=False):
        """
        Iterates recursively over all of the property values.

        It first returns all of the values in the schema, in the order
        in which they were defined.  Then, it returns all of the
        ad-hoc attributes that were added to this instance, in
        undefined order.

        Values that are `None`, indicating missing or undefined, are
        not included in the results.

        Parameters
        ----------
        include_comments : bool, optional
            If True, include results that indicate the beginning of
            a new namespace in the hierarchy.  These results are
            of the form ('comment', *prop*, *comment*)

        Returns
        -------
        properties : iterator over tuples

            Each element is a tuple (*obj*, *prop*, *val*), where:

            - *obj*: the instance storing the value

            - *prop* is a `schema_property` instance describing
              the property

            - *val* is the value
        """
        # Return the defined schema properties first
        properties = _get_properties(self)
        for key in properties:
            val = getattr(self, key)
            prop = getattr(self.__class__, key)
            if isinstance(val, MetaBase):
                if include_comments:
                    subresults = list(val.iter_properties(True))
                    if len(subresults):
                        # Only emit the comments if it has some children
                        comment = prop._description
                        if comment is None:
                            comment = key
                        yield 'comment', prop, comment
                        for x in subresults:
                            yield x
                else:
                    for x in val.iter_properties():
                        yield x
            else:
                val = prop.__get__(self, type(self))
                if val is not None:
                    val = prop.to_basic_type(val)
                    yield self, prop, val

        # Return any extra ad-hoc values next
        prop = schema_property(
            self.__class__.__name__.lower(), path=self._path)
        try:
            d = self.storage.__get__(prop, self)
        except AttributeError:
            pass
        else:
            for key, val in d.items():
                if val is not None and key not in properties:
                    prop = schema_property(key, path=self._path + [key])
                    yield self, prop, val

    def to_tree(self):
        """
        Convert the metadata in this object to a tree, suitable for
        serializing as JSON or YAML.
        """
        tree = {}

        # Return the defined schema properties first
        properties = _get_properties(self)
        for key in properties:
            val = getattr(self, key)
            if isinstance(val, MetaBase):
                tree[key] = val.to_tree()
            elif val is not None:
                prop = getattr(self.__class__, key)
                tree[key] = prop.to_basic_type(val)

        # Return the ad hoc values
        prop = schema_property(
            self.__class__.__name__.lower(), path=self._path)
        try:
            d = self.storage.__get__(prop, self)
        except AttributeError:
            pass
        else:
            for key, val in d.items():
                if val is not None and key not in properties:
                    tree[key] = val

        return tree

    def from_tree(self, tree):
        """
        Set the items in this metadata tree from a tree of basic
        objects, such as might come from JSON or YAML.
        """
        if isinstance(tree, dict):
            for key, val in tree.items():
                if hasattr(self, key):
                    if isinstance(val, dict):
                        getattr(self, key).from_tree(val)
                    else:
                        setattr(self, key, val)


class MetaBaseWithAdHoc(MetaBase):
    """
    This is a special kind of MetaBase that also allows ad-hoc values.
    """
    def __getattr__(self, attr):
        path = self.__class__._path
        prop = schema_property(
            name=attr, path=path + [attr], is_ad_hoc=True)
        return prop.__get__(self, type(self))

    def __setattr__(self, attr, val):
        if attr == 'shape':
            raise AttributeError("Can not set shape value")
        if attr.startswith('_'):
            self.__dict__[attr] = val
        else:
            for cls in self.__class__.mro():
                if attr in cls.__dict__:
                    object.__setattr__(self, attr, val)
                    return

            if self._schema.get('additionalProperties', True):
                path = self.__class__._path
                prop = schema_property(
                    name=attr, path=path + [attr], is_ad_hoc=True)
                return prop.__set__(self, val)
            else:
                raise AttributeError(
                    "schema does not allow additional properties here")


def schema_to_tree(schema, storage=None, name='root'):
    """
    Convert the schema tree to a tree of MetaBase classes.

    Parameters
    ----------
    schema : JSON schema fragment

    storage : Storage instance, optional
        The storage instance to use for the metadata tree.  If None,
        each part will use its own storage.

    Returns
    -------
    meta : a MetaBase subclass
    """
    class Node(object):
        def __init__(self, name, tree, path):
            self._name = name
            self._tree = tree
            self._path = path
            self._entries = {}

    def tree_to_nodes(name, tree, path, mapping):
        combinations = tree.get('allOf', []) + tree.get('anyOf', [])
        if len(combinations) or tree.get('type') == 'object':
            path_string = '.'.join(path)
            if path_string in mapping:
                node = mapping[path_string]
            else:
                node = Node(name, tree, path)
                mapping[path_string] = node

            if len(combinations):
                for entry in combinations:
                    tree_to_nodes(name, entry, path, mapping)
            else:
                for key, val in tree.get('properties', {}).items():
                    node._entries[key] = tree_to_nodes(
                        key, val, path + [key], mapping)

            return node
        else:
            return schema_property(name, path, schema=tree, **tree)

    def nodes_to_classes(node):
        d = {}
        for key, val in node._entries.iteritems():
            if isinstance(val, Node):
                d[key] = nodes_to_classes(val)
            else:
                d[key] = val

        d['_schema'] = node._tree
        d['_path'] = node._path
        d['_description'] = node._tree.get('title')
        class_name = util.to_camelcase(node._name)
        if sys.version_info[0] < 3:
            class_name = class_name.encode('ascii')
        if len(node._path):
            base = MetaBaseWithAdHoc
        else:
            base = MetaBase
        return type.__new__(type, class_name, (base,), d)(storage=storage)

    nodes = tree_to_nodes(name, schema, [], {})
    return nodes_to_classes(nodes)


def walk_schema(schema, func, data=None):
    """
    Walks the schema tree, calling a function at each schema location.

    Parameters
    ----------
    schema : JSON schema fragment

    func : function
        Function to call with each schema location in the tree.
        It will be passed (*data*, *subschema*, *path*) where:

        - *data* is the *data* parameter to `walk_schema`.

        - *subschema* is a subschema

        - *path* is a dot-separated path to the current subschema

    data : any, optional
        An arbitrary data object to pass to `func`.
    """
    def walk(schema, path):
        combinations = schema.get('allOf', []) + schema.get('anyOf', [])
        if len(combinations):
            for entry in combinations:
                walk(entry, path)
        else:
            func(data, schema, '.'.join(path))
            if schema.get('type') == 'object':
                for key, val in schema.get('properties', {}).items():
                    walk(val, path + [key])

    walk(schema, [])


def _fetch_schema_subtree(url, json_pointer):
    """
    Given an absolute URL, retrieves requested part of the
    schema file.

    Use `get_schema_path` to get an absolute URL from a relative URL.

    Parameters
    ----------
    url : str
        An absolute URL

    json_pointer : str
        The fragment part of the URL (after the '#')

    Returns
    -------
    schema_fragment
    """
    fh = urllib.urlopen(url)
    try:
        buffer = io.BytesIO(fh.read())
    finally:
        fh.close()
    subtree = json_yaml.load(buffer)

    if json_pointer:
        subtree = jsonschema.resolve_json_pointer(
            subtree, '#' + json_pointer)

    subtree = resolve_references(subtree, url)

    return subtree


def resolve_references(schema, base_url):
    """
    Resolves all of the "$ref" links in the JSON schema by loading
    external files and inserting them in place if necessary.

    Parameters
    ----------
    schema : JSON schema fragment
        The schema in which to resolve references.  The references are
        resolved in place.

    base_url : str or unicode
        The base URL of the schema, used to resolve references
        against.

    Returns
    -------
    resolved_schema : JSON schema fragment
    """
    def replace_ref(tree):
        if isinstance(tree, dict):
            if '$ref' in tree:
                subtree = get_schema(tree['$ref'], base_url)
                return subtree
            else:
                for key, val in tree.items():
                    tree[key] = replace_ref(val)
        elif isinstance(tree, list):
            for i in xrange(len(tree)):
                tree[i] = replace_ref(tree[i])

        return tree

    return replace_ref(schema)


def get_elements_for_fits_hdu(schema, hdu_name='PRIMARY'):
    """
    Returns a list of metadata element names that are stored in a
    given FITS HDU.

    Parameters
    ----------
    schema : JSON schema fragment

    hdu_name : str, optional
        The name of the HDU to extract.  Defaults to ``'PRIMARY'``.

    Returns
    -------
    elements : dict
        The keys are FITS keywords, and the values are dot-separated
        paths to the metadata elements.
    """
    def find_fits_elements(results, schema, path):
        if (schema.get('fits_hdu', 'PRIMARY') == hdu_name and
                'fits_keyword' in schema):
            results[schema.get('fits_keyword')] = path

    results = {}
    walk_schema(schema, find_fits_elements, results)

    return results


def find_fits_keyword(schema, keyword, return_result=False):
    """
    Utility function to find a reference to a FITS keyword in a given
    schema.  This is intended for interactive use, and not for use
    within library code.

    Parameters
    ----------
    schema : JSON schema fragment
        The schema in which to search.

    keyword : str
        A FITS keyword name

    return_result : bool, optional
        If `False` (default) print result to stdout.  If `True`,
        return the result as a list.

    Returns
    -------
    locations : list of str
        If `return_result` is `True, a list of the locations in the
        schema where this FITS keyword is used.  Each element is a
        dot-separated path.
    """
    def find_fits_keyword(results, schema, path):
        if path.startswith('_extra_fits'):
            return
        if schema.get('fits_keyword') == keyword:
            results.append(path)

    results = []
    walk_schema(schema, find_fits_keyword, results)

    if return_result:
        return results
    else:
        if not len(results):
            print("No match found.")
        else:
            for location in results:
                print(location)


def search_schema(schema, substring, return_result=False, verbose=False):
    """
    Utility function to search the metadata schema for a particular
    phrase.

    This is intended for interactive use, and not for use within
    library code.

    The searching is case insensitive.

    Parameters
    ----------
    schema : JSON schema fragment
        The schema in which to search.

    substring : str
        The substring to search for.

    return_result : bool, optional
        If `False` (default) print result to stdout.  If `True`,
        return the result as a list.

    verbose : bool, optional
        If `False` (default) display a one-line description of each
        match.  If `True`, display the complete description of each
        match.

    Returns
    -------
    locations : list of tuples
        If `return_result` is `True`, returns tuples of the form
        (*location*, *description*)
    """
    substring = substring.lower()

    def find_substring(results, schema, path):
        matches = False
        for param in ('title', 'description'):
            if substring in schema.get(param, '').lower():
                matches = True
                break

        if param in path.lower():
            matches = True

        if matches:
            description = '\n\n'.join([
                schema.get('title', ''),
                schema.get('description', '')]).strip()
            results.append((path, description))

    results = []
    walk_schema(schema, find_substring, results)

    if return_result:
        return results
    else:
        import textwrap

        results.sort()

        if not len(results):
            print("No match found.")
        else:
            if verbose:
                for path, description in results:
                    print(path)
                    print(textwrap.fill(
                        description, initial_indent='    ',
                        subsequent_indent='    '))
            else:
                for path, description in results:
                    print('{0}: {1}'.format(
                        path, description.partition('\n')[0]))


def _get_properties(self):
    return [x for x in dir(self.__class__)
            if isinstance(getattr(self.__class__, x),
                          (schema_property, MetaBase))]

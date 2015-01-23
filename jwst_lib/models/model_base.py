"""
Data model class heirarchy
"""
from __future__ import absolute_import, unicode_literals, division, print_function

import copy
import datetime
import inspect
import os

import numpy as np

from . import schema as mschema
from . import storage as mstorage
from .util import IS_PY3K


__all__ = ['DataModel']


class DataModel(mschema.HasArrayProperties, mstorage.HasStorage):
    """
    Base class of all of the data models.

    The actual storage of values in the data model is performed by a
    pluggable storage backend (in self.storage).  See storage.py for
    more information.
    """
    schema_url = "core.schema.json"

    def __init__(self, init=None, schema=None):
        """Parameters
        ----------
        init : shape tuple, file path, file object, astropy.io.fits.HDUList, numpy array, None

            - None: A default data model with no shape

            - shape tuple: Initialize with empty data of the given
              shape

            - file path: Initialize from the given file

            - readable file object: Initialize from the given file
              object

            - ``astropy.io.fits.HDUList``: Initialize from the given
              `~astropy.io.fits.HDUList`.

            - Storage instance: Use the given storage backend
              (internal use)

            - A numpy array: Used to initialize the data array

        schema : tree of objects representing a JSON schema, or string naming a schema, optional
            The schema to use to understand the elements on the model.
            If not provided, the schema associated with this class
            will be used.

        """
        self._owns_storage = True
        is_array = False
        shape = None
        if init is None:
            storage = mstorage.TreeStorage()
        elif isinstance(init, np.ndarray):
            storage = mstorage.TreeStorage()
            shape = init.shape
            is_array = True
        elif isinstance(init, self.__class__):
            self.__dict__.update(init.__dict__)
            self._owns_storage = False
            self.__class__ = init.__class__
            self._parent = init
            return
        elif isinstance(init, DataModel):
            raise TypeError(
                "Passed in {0!r} is not of the expected subclass {1!r}".format(
                init.__class__.__name__, self.__class__.__name__))
        elif isinstance(init, mstorage.Storage):
            storage = init
            self._owns_storage = False
        elif isinstance(init, tuple):
            for item in init:
                if not isinstance(item, int):
                    raise ValueError("shape must be a tuple of ints")
            shape = init
            storage = mstorage.TreeStorage()
        else:
            from . import fits
            try:
                storage = fits.FitsStorage(init)
            except IOError as e:
                raise IOError("Failed to read from file path: {0}".format(
                    str(e)))
            except:
                raise TypeError(
                    "First argument must be None, shape tuple, file path, "
                    "readable file object or Storage instance")

        mschema.HasArrayProperties.__init__(self)
        mstorage.HasStorage.__init__(self, storage=storage)
        self._shape = shape

        filename = os.path.abspath(inspect.getfile(self.__class__))
        base_url = os.path.join(
            os.path.dirname(filename), 'schemas', '')
        if schema is None:
            schema = mschema.get_schema(self.schema_url, base_url)
        elif isinstance(schema, basestring):
            schema = mschema.get_schema(schema, base_url)
        elif isinstance(schema, dict):
            schema = mschema.resolve_references(schema, base_url)
        else:
            raise TypeError("schema must be str, dict or None")

        self._schema = schema

        tree = mschema.schema_to_tree(schema, self.storage)

        # Create a new class on the fly that combines this class and the
        # custom schema-built class
        real_cls = self.__class__
        new_cls = type(real_cls.__name__, (real_cls, tree.__class__), dict())
        self.__class__ = new_cls
        self._real_cls = real_cls

        self._storage.extract_extra_elements(self)

        self.meta.date = datetime.datetime.utcnow()

        if is_array:
            primary_array_name = self.get_primary_array_name()
            if primary_array_name is None:
                raise TypeError(
                    "Array passed to model.__init__, but model has no primary "
                    "array in its schema")
            setattr(self, primary_array_name, init)

    def __del__(self):
        try:
            self.close()
        except RuntimeError:
            pass

    def copy(self):
        """
        Returns a deep copy of this model.
        """
        new = self._real_cls(schema=self._schema)

        for obj, prop, val in self.iter_properties(include_empty_arrays=False):
            if val is not None:
                if isinstance(val, np.ndarray):
                    c = val.copy()
                else:
                    c = copy.copy(val)
            new.storage.__set__(prop, obj, c)

        return new

    def get_primary_array_name(self):
        """
        Returns the name "primary" array for this model, which
        controls the size of other arrays that are implicitly created.
        This is intended to be overridden in the subclasses if the
        primary array's name is not "data".
        """
        return 'data'

    def on_save(self, path=None):
        """
        This is a hook that is called just before saving the file.
        It can be used, for example, to update values in the metadata
        that are based on the content of the data.

        Override it in the subclass to make it do something, but don't
        forget to "chain up" to the base class, since it does things
        there, too.

        Parameters
        ----------
        path : str
            The path to the file that we're about to save to.
        """
        if isinstance(path, basestring):
            if self.meta.filename is None:
                self.meta.filename = os.path.basename(path)

    def save(self, path, *args, **kwargs):
        self.on_save(path)

        # TODO: For now, this just saves to fits
        kwargs.setdefault('clobber', True)
        self.to_fits(path, *args, **kwargs)

    @classmethod
    def from_fits(cls, init, schema=None):
        """
        Load a model from a FITS file.

        Parameters
        ----------
        init : file path, file object, astropy.io.fits.HDUList
            - file path: Initialize from the given file
            - readable file object: Initialize from the given file object
            - astropy.io.fits.HDUList: Initialize from the given
              `~astropy.io.fits.HDUList`.

        schema :
            Same as for `__init__`

        Returns
        -------
        model : DataModel instance
        """
        return cls(init, schema=schema)

    def to_fits(self, init, *args, **kwargs):
        """
        Write a DataModel to a FITS file.

        Parameters
        ----------
        init : file path or file object

        *args, **kwargs
            Any additional arguments are passed along to
            `astropy.io.fits.writeto`.
        """
        from . import fits

        if isinstance(self._storage, fits.FitsStorage):
            self._storage.save_metadata_extension(self)
            self._storage.writeto(init, *args, **kwargs)
        else:
            fits.FitsStorage.write_model_to(self, init, *args, **kwargs)

    @classmethod
    def from_json(cls, init, schema=None):
        """
        Load the metadata for a DataModel from a JSON file.

        Note that arrays can not be loaded/saved from JSON.

        Parameters
        ----------
        init : file path or file object

        schema :
            Same as for `__init__`

        Returns
        -------
        model : DataModel instance
        """
        from . import json_yaml

        tree = json_yaml.load(init)
        tree = {'meta': tree}
        storage = mstorage.TreeStorage(tree)
        self = cls(storage, schema=schema)
        self.validate_tree(tree)
        return self
    from_yaml = from_json

    def to_json(self, init):
        """
        Write a DataModel to a JSON file.

        Note that arrays can not be loaded/saved from a JSON file.

        Parameters
        ----------
        init : file path or file object
        """
        from . import json_yaml

        self.storage.validate(self)

        if isinstance(self.storage, mstorage.TreeStorage):
            tree = self.storage.tree
        else:
            tree = self.to_tree()

        json_yaml.dump(tree.get('meta', {}), init, format="json")

    def to_yaml(self, path):
        """
        Write a DataModel to a YAML file.

        Note that arrays can not be loaded/saved from a JSON file.

        Parameters
        ----------
        init : file path or file object
        """
        from . import json_yaml

        self.storage.validate(self)

        if isinstance(self.storage, mstorage.TreeStorage):
            tree = self.storage.tree
        else:
            tree = self.to_tree()

        json_yaml.dump(tree['meta'], path, format="yaml")

    @property
    def shape(self):
        if self._shape is None:
            return self._storage.__get_shape__()
        return self._shape

    def extend_schema(self, new_schema):
        """
        Extend the model's schema using the given schema, by combining
        it in an "allOf" array.

        Parameters
        ----------
        new_schema : schema tree
        """
        schema = {'allOf': [self._schema, new_schema]}

        tree = mschema.schema_to_tree(schema, self.storage)

        # Replace the MetaBase base class with the new one
        bases = list(self.__class__.__bases__)
        bases[1] = tree.__class__
        self.__class__.__bases__ = tuple(bases)

        # Validate ourselves
        self.storage.validate(self)

        self._schema = schema

        return self

    def add_schema_entry(self, position, new_schema):
        """
        Extend the model's schema by placing the given new_schema at
        the given dot-separated position in the tree.

        Parameters
        ----------
        position : str

        new_schema : schema tree
        """
        parts = position.split('.')
        schema = new_schema
        for part in parts[::-1]:
            schema = {'type': 'object', 'properties': {part: schema}}
        return self.extend_schema(schema)

    def find_fits_keyword(self, keyword, return_result=False):
        """
        Utility function to find a reference to a FITS keyword in this
        model's schema.  This is intended for interactive use, and not
        for use within library code.

        Parameters
        ----------
        keyword : str
            A FITS keyword name

        return_result : bool, optional
            If `False` (default) print result to stdout.  If `True`,
            return the result as a list.
        Returns
        -------
        locations : list of str

            If `return_result` is `True, a list of the locations in
            the schema where this FITS keyword is used.  Each element
            is a dot-separated path.

        Example
        -------
        >>> model.find_fits_keyword('DATE-OBS')
        ['observation.date']
        """
        return mschema.find_fits_keyword(
            self.schema, keyword, return_result=return_result)

    def search_schema(self, substring, return_result=False, verbose=False):
        """
        Utility function to search the metadata schema for a
        particular phrase.

        This is intended for interactive use, and not for use within
        library code.

        The searching is case insensitive.

        Parameters
        ----------
        substring : str
            The substring to search for.

        return_result : bool, optional
            If `False` (default) print result to stdout.  If `True`,
            return the result as a list.

        verbose : bool, optional
            If `False` (default) display a one-line description of
            each match.  If `True`, display the complete description
            of each match.

        Returns
        -------
        locations : list of tuples
            If `return_result` is `True`, returns tuples of the form
            (*location*, *description*)
        """
        return mschema.search_schema(
            self.schema, substring, return_result=return_result, verbose=verbose)

    def __getitem__(self, key):
        """
        Get a metadata value using a dotted name.
        """
        assert isinstance(key, basestring)
        meta = self
        for part in key.split('.'):
            try:
                meta = getattr(meta, part)
            except AttributeError:
                raise KeyError(repr(key))
        return meta

    def get_item_as_json_value(self, key):
        """
        Equivalent to __getitem__, except returns the value as a JSON
        basic type, rather than an arbitrary Python type.
        """
        assert isinstance(key, basestring)
        meta = self
        parts = key.split('.')
        for part in parts[:-1]:
            try:
                meta = getattr(meta, part)
            except AttributeError:
                raise KeyError(repr(key))
        last_part = parts[-1]
        prop = getattr(type(meta), last_part)
        return prop.to_basic_type(getattr(meta, last_part))

    def __setitem__(self, key, value):
        """
        Set a metadata value using a dotted name.
        """
        assert isinstance(key, basestring)
        meta = self
        parts = key.split('.')
        for part in parts[:-1]:
            try:
                meta = getattr(meta, part)
            except AttributeError:
                raise KeyError(repr(key))
        part = parts[-1]
        setattr(meta, part, value)

    def iteritems(self, include_arrays=False, primary_only=False,
                  everything=False):
        """
        Iterates over all of the schema items in a flat way.

        Each element is a pair (`key`, `value`).  Each `key` is a
        dot-separated name.  For example, the schema element
        `meta.observation.date` will end up in the result as::

            ( "meta.observation.date": "2012-04-22" )

        Parameters
        ----------
        include_arrays : bool, optional
            When `True`, include numpy arrays in the result.  Default
            is `False`.

        primary_only : bool, optional
            When `True`, only return values from the PRIMARY FITS HDU.

        everything : bool, optional
            When `True`, include even non-serializable items.
        """
        for obj, prop, val in self.iter_properties(include_arrays=include_arrays):
            if (include_arrays or (
                (isinstance(val, (bytes, unicode, int, long, float, bool))
                 or everything) and
                    not prop.is_data())):

                if (primary_only and
                    prop.schema.get('fits_hdu', 'PRIMARY') != 'PRIMARY'):
                    continue
                yield ('.'.join(prop.path), val)

    if IS_PY3K:
        items = iteritems
    else:
        def items(self, include_arrays=False, primary_only=False, everything=False):
            """
            Get all of the schema items in a flat way.

            Each element is a pair (`key`, `value`).  Each `key` is a
            dot-separated name.  For example, the schema element
            `meta.observation.date` will end up in the result as::

                ( "meta.observation.date": "2012-04-22" )

            Parameters
            ----------
            include_arrays : bool, optional
                When `True`, include numpy arrays in the result.
                Default is `False`.

            primary_only : bool, optional
                When `True`, only return values from the PRIMARY FITS
                HDU.

            everything : bool, optional
                When `True`, include even non-serializable items.
            """
            return list(self.iteritems(include_arrays=include_arrays,
                                       primary_only=primary_only,
                                       everything=everything))

    def iterkeys(self, include_arrays=False, primary_only=False):
        """
        Iterates over all of the schema keys in a flat way.

        Each result of the iterator is a `key`.  Each `key` is a
        dot-separated name.  For example, the schema element
        `meta.observation.date` will end up in the result as the
        string `"meta.observation.date"`.

        Parameters
        ----------
        include_arrays : bool, optional
            When `True`, include keys that point to numpy arrays
            in the result.  Default is `False`.

        primary_only : bool, optional
            When `True`, only return values from the PRIMARY FITS HDU.
        """
        for key, val in self.items(include_arrays=include_arrays,
                                   primary_only=primary_only):
            yield key

    if IS_PY3K:
        keys = iterkeys
    else:
        def keys(self, include_arrays=False, primary_only=False):
            """
            Gets all of the schema keys in a flat way.

            Each result of the iterator is a `key`.  Each `key` is a
            dot-separated name.  For example, the schema element
            `meta.observation.date` will end up in the result as the
            string `"meta.observation.date"`.

            Parameters
            ----------
            include_arrays : bool, optional
                When `True`, include keys that point to numpy arrays
                in the result.  Default is `False`.


            primary_only : bool, optional
                When `True`, only return values from the PRIMARY FITS
                HDU.
            """
            return list(self.iterkeys(include_arrays=include_arrays,
                                      primary_only=primary_only))

    def itervalues(self, include_arrays=False, primary_only=False):
        """
        Iterates over all of the schema values in a flat way.

        Parameters
        ----------
        include_arrays : bool, optional
            When `True`, include numpy arrays in the result.  Default
            is `False`.

        primary_only : bool, optional
            When `True`, only return values from the PRIMARY FITS HDU.
        """
        for key, val in self.items(include_arrays=include_arrays,
                                   primary_only=primary_only):
            yield val

    if IS_PY3K:
        values = itervalues
    else:
        def values(self, include_arrays=False, primary_only=False):
            """
            Gets all of the schema values in a flat way.

            Parameters
            ----------
            include_arrays : bool, optional
                When `True`, include numpy arrays in the result.  Default
                is `False`.

            primary_only : bool, optional
                When `True`, only return values from the PRIMARY FITS
                HDU.
            """
            return list(self.itervalues(include_arrays=include_arrays))

    def update(self, d, include_arrays=False, primary_only=False):
        """
        Updates this model with the metadata elements from another model.

        Parameters
        ----------
        d : model or dictionary-like object
            The model to copy the metadata elements from.  If
            dictionary-like, it must have an `items` method that
            returns (key, value) pairs where the keys are
            dot-separated paths to metadata elements.

        include_arrays : bool, optional
            When `True`, update numpy array elements.  Default
            is `False`.

        primary_only : bool, optional
            When `True`, only transfer values from the PRIMARY FITS
            HDU.
        """
        if hasattr(d, '_extra_fits'):
            self.extend_schema(
                {'type': 'object',
                 'properties': {'_extra_fits': d._extra_fits.__class__._schema}})

        if isinstance(d, DataModel):
            items = d.items(include_arrays=include_arrays,
                            primary_only=primary_only,
                            everything=True)
        else:
            items = d.iteritems()

        for key, val in items:
            if isinstance(val, mschema.PickleProxy):
                val = val.x
            self[key] = val

        if hasattr(d, 'history'):
            self.history.extend(d.history)

    def to_flat_dict(self, include_arrays=False):
        """
        Returns a dictionary of all of the schema items as a flat dictionary.

        Each dictionary key is a dot-separated name.  For example, the
        schema element `meta.observation.date` will end up in the
        dictionary as::

            { "meta.observation.date": "2012-04-22" }

        Parameters
        ----------
        include_arrays : bool, optional
            When `True`, include numpy arrays in the dictionary.
            Default is `False`.
        """
        return dict(self.items(include_arrays=include_arrays))

    @property
    def schema(self):
        return self._schema

    def get_fileext(self):
        return 'fits'

    @property
    def history(self):
        return self._storage.history

    @history.setter
    def history(self, v):
        self._storage.history = v

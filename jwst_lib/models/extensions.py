"""
This is a collection of custom data types that are used as metadata
values in the data model.

The purpose of each class here is to convert to/from basic datatypes,
where "basic" means one of the JSON-serializable datatypes, i.e., int,
float, list, dictionary and string.

Each class here should implement the following methods:

  - `to_basic`: Converts from a native type to one of the basic types.

  - `from_basic`: Converts from a basic type to the native type.

  - `validate`: Should raise ValueError or TypeError if the given object
    is not of the native type.

Each class should be registered with the schema mechanism by adding it
to the `extensions` dictionary.  The keys in the dictionary are used
in the `format` attribute in JSON schema to identify the type.  This
should be something globally unique, and by convention are a URL.
"""
from __future__ import absolute_import, unicode_literals, division, print_function


import datetime
import time


class FitsDateTime(object):
    """
    Proxy class for serializing datetime.datetime objects.
    """

    BASE_FORMAT = "%Y-%m-%dT%H:%M:%S"
    FULL_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

    @classmethod
    def to_basic(cls, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(cls.FULL_FORMAT)
        else:
            return obj

    @classmethod
    def from_basic(cls, obj):
        # The builtin strptime only handles fractional seconds up to 6
        # decimal places.  Therefore, we have to parse in a more
        # manual way.
        base, dot, fractional = obj.partition('.')
        parts = list(time.strptime(base, cls.BASE_FORMAT))[0:6]
        if fractional:
            us = int(fractional) * (10.0 ** -len(fractional)) * 1000000.0
            parts.append(int(us))
        return datetime.datetime(*parts)

    @classmethod
    def validate(cls, obj):
        if not isinstance(obj, datetime.datetime):
            try:
                obj = cls.from_basic(obj)
            except ValueError:
                raise ValueError("Must be a datetime object")


class FitsDate(object):
    """
    Proxy class for serializing datetime.datetime or datetime.date
    objects as dates.
    """

    FULL_FORMAT = "%Y-%m-%d"

    @classmethod
    def to_basic(cls, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.strftime(cls.FULL_FORMAT)
        else:
            return obj

    @classmethod
    def from_basic(cls, obj):
        return datetime.datetime.strptime(obj, cls.FULL_FORMAT)

    @classmethod
    def validate(cls, obj):
        if not isinstance(obj, (datetime.datetime, datetime.date)):
            try:
                obj = cls.from_basic(obj)
            except ValueError:
                raise ValueError(
                    "Must be a datetime.datetime or datetime.date object")


class FitsTime(object):
    """
    Proxy class for serializing datetime.datetime or datetime.time
    objects as times.
    """

    BASE_FORMAT = "%H:%M:%S"
    FULL_FORMAT = "%H:%M:%S.%f"

    @classmethod
    def to_basic(cls, obj):
        if isinstance(obj, (datetime.datetime, datetime.time)):
            return obj.strftime(cls.FULL_FORMAT)
        else:
            return obj

    @classmethod
    def from_basic(cls, obj):
        # The builtin strptime only handles fractional seconds up to 6
        # decimal places.  Therefore, we have to parse in a more
        # manual way.
        base, dot, fractional = obj.partition('.')
        parts = list(time.strptime(base, cls.BASE_FORMAT))[0:6]
        if fractional:
            us = int(fractional) * (10.0 ** -len(fractional)) * 1000000.0
            parts.append(int(us))
        return datetime.datetime(*parts)

    @classmethod
    def validate(cls, obj):
        if not isinstance(obj, (datetime.datetime, datetime.time)):
            try:
                obj = cls.from_basic(obj)
            except ValueError:
                raise ValueError(
                    "Must be a datetime.datetime or datetime.time object")



# Map a URL (which doesn't have to exist, it just has to be unique) to
# each of the classes in this module.  These correspond to custom
# "format" values in the JSON Schema.
extensions = {
    'http://www.stsci.edu/types/fits-date': FitsDate,
    'http://www.stsci.edu/types/fits-time': FitsTime,
    'http://www.stsci.edu/types/fits-date-time': FitsDateTime
    }

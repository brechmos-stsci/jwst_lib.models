.. _metadata:

Metadata
````````

Metadata information associated with a data model is accessed through
its `meta` member.  For example, to access the date that an
observation was made::

    print model.meta.observation.date

Metadata values are automatically type-checked when they are set.
Therefore, setting a value that expects a number to a string will
raise an exception::

    >>> from jwst_lib.models import ImageModel
    >>> dm = ImageModel()
    >>> dm.meta.target.ra = "foo"
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "site-packages/jwst_lib.models/schema.py", line 672, in __setattr__
        object.__setattr__(self, attr, val)
      File "site-packages/jwst_lib.models/schema.py", line 490, in __set__
        val = self.to_basic_type(val)
      File "site-packages/jwst_lib.models/schema.py", line 422, in to_basic_type
        raise ValueError(e.message)
    ValueError: 'foo' is not of type u'number'

Some values can not be saved directly in a FITS file.  If one of those
is values is set, a warning will be raised when saving to a FITS file.

    >>> dm.to_fits("test.fits")
    No way to save property 'transformations' in FITS

The set of available metadata elements is defined in a JSON Schema
that ships with `jwst_lib.models`.  To see what elements are available,
this schema can be viewed in the following formats:

.. toctree::
   :maxdepth: 2

   schema_json
   schema_yaml
   schema_human

There is also a utility method for finding elements in the metadata
schema.  `search_schema` will search the schema for the given
substring in metadata names as well as their documentation.  The
search is case-insensitive::

    >>> from jwst_lib.models import ImageModel
    # Create a model of the desired type
    >>> model = ImageModel()
    # Call `search_schema` on it to find possibly related elements.
    >>> model.search_schema('target')
    target: Information about the target
    target.dec: DEC of the target
    target.name: Standard astronomical catalog name for the target
    target.proposer: Proposer's name for the target
    target.ra: RA of the target
    target.type: Fixed target, moving target, or generic target

An alternative method to get and set metadata values is to use a
dot-separated name as a dictionary lookup.  This is useful for
databases, such as CRDS, where the path to the metadata element is
most conveniently stored as a string.  The following two lines are
equivalent::

    print model['meta.observation.date']
    print model.meta.observation.date

Working with lists
==================

Unlike ordinary Python lists, lists in the schema may be restricted to
only accept a certain set of values.  Items may be added to lists in
two ways: by passing a dictionary containing the desired key/value
pairs for the object, or using the lists special method `item` to
create a metadata object and then assigning that to the list.

For example, suppose the metadata element `meta.transformations` is a
list of transformation objects, each of which has a `type` (string)
and a `coeff` (number) member.  We can assign elements to the list in
the following equivalent ways::

    >>> trans = dm.meta.transformations.item()
    >>> trans.type = 'SIN'
    >>> trans.coeff = 42.0
    >>> dm.meta.transformations.append(trans)

    >>> dm.meta.transformations.append({'type': 'SIN', 'coeff': 42.0})

When accessing the items of the list, the result is a normal metadata
object where the attributes are type-checked::

    >>> trans = dm.meta.transformations[0]
    >>> print trans
    <jwst_lib.models.schema.Transformations object at 0x123a810>
    >>> print trans.type
    SIN
    >>> trans.type = 42.0
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "site-packages/jwst_lib.models/schema.py", line 672, in __setattr__
         object.__setattr__(self, attr, val)
      File "site-packages/jwst_lib.models/schema.py", line 490, in __set__
         val = self.to_basic_type(val)
      File "site-packages/jwst_lib.models/schema.py", line 422, in to_basic_type
         raise ValueError(e.message)
    ValueError: 42.0 is not of type u'string'

JSON Schema
===========

The `jwst_lib.models` library defines its metadata using `Draft 3 of
the JSON Schema specification
<http://tools.ietf.org/html/draft-zyp-json-schema-03>`_.  The most
important and commonly used parts are excerpted here.  The mapping
from Javascript to Python concepts (such as Javascript “array” ==
Python “list”) is added where applicable.

Each element in the schema is defined using nested dictionaries, each
using special keys that define the acceptable type.  A “schema” refers
to each dictionary that describes a type.  These schemas may be
nested.

For example, a simple object describing a person with a name and an
age may be described as follows:

.. code-block:: javascript

  {
     "description":"A person",
     "type":"object",

     "properties":{
       "name":{"type":"string"},
       "age" :{
           "type":"integer",
           "maximum":125
       }
     }
   }

The entire example above is a schema, and the subschema for the name
(``{"type":"string"}``) is also considered a schema.

Schema attributes
-----------------

type
++++

The ``type`` attribute defines what the primitive type or the schema
of the instance MUST be in order to validate.  This attribute can take
one of two forms:

  - **Simple Types:** A string indicating a primitive or simple type.
    The following are acceptable string values:

    - ``string``: Value MUST be a string.

    - ``number``: Value MUST be a number, floating point numbers are
      allowed.

    - ``integer``: Value MUST be an integer, no floating point
      numbers are allowed.  This is a subset of the number type.

    - ``boolean``: Value MUST be a boolean.

    - ``object``: Value MUST be an object.

    - ``array``: Value MUST be an array

    - ``null``:  Value MUST be null.  Note this is mainly for purpose of
      being able use union types to define nullability.  If this type
      is not included in a union, null values are not allowed (the
      primitives listed above do not allow nulls on their own).

    - ``any``:  Value MAY be of any type including null.

  - **Union Types:** An array of two or more simple type definitions.
    Each item in the array MUST be a simple type definition or a
    schema.  The instance value is valid if it is of the same type as
    one of the simple type definitions, or valid by one of the
    schemas, in the array.

    For example, a schema that defines if an instance can be a string or
    a number would be:

    .. code-block:: javascript

      {"type": ["string", "number"]}

.. _schema-data-type:

  - **Extra Types:** In addition to these types defined as part of the
    offical JSON Schema standard, `jwst_lib.models` also understands a
    new type ``data`` used for *n* - dimensional arrays and tables
    (aka structured arrays).  (It would have been easier to use the
    name "array", but that is already used by the standard to handle
    "lists".)  ``data`` typed values also have the following
    properties to specify more detail about their type:

    - ``ndim``: The number of dimensions of the array.

    - ``dtype``: For defining an array, ``dtype`` should be a string.
      For defining a table, it should be a list.

      - **array**: ``dtype`` should be one of the following strings,
        representing fixed-length datatypes::

          bool8, int8, int16, int32, int64, uint8, uint16, uint32,
          uint64, float16, float32, float64, float128, complex64,
          complex128, complex256

        Or, for fixed-length strings, ``stringXX``, where ``XX`` is
        the maximum length of the string.

        (Datatypes whose size depend on the platform are not supported
        since this would make files less portable).

      - **table**: ``dtype`` should be a list of dictionaries.  Each
        element in the list defines a column and has the following
        keys:

          - ``dtype``: A string to select the type of the column.
            This is the same as the ``dtype`` for an array (as
            described above).

          - ``name`` (optional): An optional name for the column.

          - ``shape`` (optional): The shape of the data in the column.
            May be either an integer (for a single-dimensional shape),
            or a list of integers.

    - ``default``: The default value for *every* element in the array.
      Note this implies it is a single numerical value, not an array
      of values.

properties
++++++++++

The ``properties`` attribute is an object with property definitions
that define the valid values of instance object property values.  When
the instance value is an object, the property values of the instance
object MUST conform to the property definitions in this object.  In
this object, each property definition's value MUST be a schema, and
the property's name MUST be the name of the instance property that it
defines.  The instance property value MUST be valid according to the
schema from the property definition.

.. note::

   According to the JSON Schema spec, properties are logically
   unordered.  However, `jwst_lib.models` will preserve the order of
   the properties as written in the schema when writing out to a file.

additionalProperties
++++++++++++++++++++

The ``additionalProperties`` attribute defines a schema for all
properties that are not explicitly defined in an object type
definition.  If specified, the value MUST be a schema or a boolean.
If false is provided, no additional properties are allowed beyond the
properties defined in the schema.  The default value is an empty
schema which allows any value for additional properties.

items
+++++

The ``items`` attribute defines the allowed items in an instance array,
and MUST be a schema or an array of schemas.  The default value is an
empty schema which allows any value for items in the instance array.

When this attribute value is a schema and the instance value is an
array, then all the items in the array MUST be valid according to the
schema.

When this attribute value is an array of schemas and the instance
value is an array, each position in the instance array MUST conform to
the schema in the corresponding position for this array.  This called
tuple typing.  When tuple typing is used, additional items are
allowed, disallowed, or constrained by the "additionalItems" attribute
using the same rules as “additionalProperties".

required
++++++++

The ``required`` attribute indicates if the instance must have a
value, and not be undefined.  This is ``false`` by default, making the
instance optional.

enum
++++

The ``enum`` attribute provides an enumeration of all possible values
that are valid for the instance property.  This MUST be an array, and
each item in the array represents a possible value for the instance
value.  If this attribute is defined, the instance value MUST be one
of the values in the array in order for the schema to be valid.

default
+++++++

This ``default`` attribute defines the default value of the instance
when the instance is undefined.

title
+++++

This ``title`` attribute is a string that provides a short description
of the instance property.

description
+++++++++++

This ``description`` attribute is a string that provides a full
description of the of purpose the instance property.

.. note::

   The Python docstring for the property is generated by concatenating
   ``title`` and ``description`` together.  The ``title`` member is
   used for the comment when writing to a FITS file.

format
++++++

.. note::

   This ``format`` attribute is not currently supported by the JSON
   Schema validation library used by `jwst_lib.models`.  However, some
   special values are defined for types used by FITS:

       - `http://www.stsci.edu/types/fits-date-time`: Defines a
         datetime in FITS-like ISO format: `YYYY-mm-ddTHH:MM:SS.ssss`.
         The value is set and returned as a Python `datetime.datetime`
         object.

$ref
++++

The ``$ref`` attribute allows for referencing other parts of the
schema, or even other parts of a schema in another file.

Any dictionary containing a ``$ref`` attribute is replaced entirely with
the target of the reference.

The reference value is a URL.  `jwst_lib.models` supports file and http
urls.  The URL may also have a local part following the ``#``
character.  This local part is in `JSON Pointer
<http://tools.ietf.org/html/draft-ietf-appsawg-json-pointer-03>`_
syntax and allows a subset of the schema file to be extracted.

`jwst_lib.models` also supports special URLs that refer to schema files
installed alongside Python code.  If URL is of the form
``http://jwst_lib.stsci.edu/schemas/$PACKAGE/$SCHEMA``, a heuristic is
used to find the schema within the local Python package namespace.
``$PACKAGE`` is the dot-separated path to a Python package, and
``$SCHEMA`` is the name of a schema file that ships with that package.
For example, to refer to a (hypothetical) ``bad_pixel_mask`` schema
that ships with a Python package called ``mirilib``, use the following
URL::

  http://jwst_lib.stsci.edu/schemas/mirilib/bad_pixel_mask.schema.json

The ``$PACKAGE`` portion may be omitted to refer to schemas in the
`jwst_lib.models` core::

  http://jwst_lib.stsci.edu/schemas/image.schema.json

.. note::

   In the future, we will also be hosting these schemas on an HTTP
   server at a location such as this.  The exact web address may
   change at that point, so if you use this feature, expect to need to
   change it at some point in the future.

For example, say you want to define a person, with a name and address,
and reuse that snippet elsewhere in the schema:

.. code-block:: javascript

   {
      "type": "object"
      "properties": {
          "author": {
              "type": "object",
              "properties": {
                  "name": {
                      "type": "string"
                  },
                  "address": {
                      "type": "string"
                  }
              }
          },
          "editor": {
              "$ref": "#properties/author"
          }
      }
    }

You may also want to include that from another file:

.. code-block:: javascript

    { "$ref": "core.schema.json#/properties/author" }

.. seealso::

   This feature is based on two related JSON standards that may be
   useful as reference:

     - `JSON Reference
       <http://tools.ietf.org/html/draft-pbryan-zyp-json-ref-02>`_.

     - `JSON Pointer
       <http://tools.ietf.org/html/draft-ietf-appsawg-json-pointer-03>`_.

`extends`
+++++++++

Like ``$ref``, the ``extends`` attribute is a way of building a schema
out of pieces of another.  However, unlike ``$ref``, ``extends`` does
not replace the contents of the object, but merely merges it.  The
target of the ``extents`` attribute is loaded in, and then any locally
defined attributes override attributes in the target.

For example, all of the built-in schemas in `jwst_lib.models` extend the
same core schema by using the `extends` attribute:

.. code-block:: javascript

  {
      "type" : "object",
      "extends" : {"$ref": "core.schema.json"},
      "properties" : {
          "data" :
              {
                  "type" : "data",
      // etc...

FITS-specific Schema Attributes
-------------------------------

`jwst_lib.models` also adds some new keys to the schema language in
order to handle reading and writing FITS files.  These attributes all
have the prefix ``fits_``.

fits_keyword
++++++++++++

Specifies the FITS keyword to store the value in.  Must be a string
with a maximum length of 8 characters.

fits_hdu
++++++++

Specifies the FITS HDU to store the value in.  May be a number (to
specify the nth HDU) or a name (to specify the extension with the
given ``EXTNAME``).  By default this is set to 0, and therefore refers
to the primary HDU.

Going beyond the schema
=======================

There are two options to add metadata elements that are not defined in
the core schema:

   1. Arbitrary attributes may be assigned to a metadata object.

   2. Extend the schema by adding new elements to it.

Option 1) is more convenient.  As long as the arbitrary data is made
up of standard data types, it can be saved to and loaded from JSON or
YAML format, However, since the model system knows nothing about the
new elements, it can not store them in a FITS file or perform
automatic type-checking.  Option 2) is more robust, and does not
require “permission” to change the core schema in order to add
application-specific metadata elements.

Extending the schema
--------------------

Since it would be cumbersome to update the core schema everytime a
library wants to use application-specific keywords, `jwst_lib.models`
makes it easy to overlay schema fragments on top of the core schema.

Schema overlays are represented using a tuple of the form
(*location*, *schema_fragment*).  *location* is a dot-separated path
indicating where to insert the *schema_fragment*.  *schema_fragment*
is a piece of JSON Schema as defined above.

For example, suppose you are writing an application that needs to know
the population of the target being observed.  To store this in the
model, we'll create a new metadata element ``meta.target.population``
that accepts a number.  When reading/writing FITS, we want to store
this this information in the keyword ``TARGPOP`` in the primary HDU.
The schema fragment to describe this new element is::

    my_schema = (
        "meta.target.population",
        {"title": "Population of the target",
         "type": "integer",
         "fits_keyword": "TARGPOP"
         }
        )

Schema overlays may be used in two ways:

  1. When constructing the model from scratch, a list of overlays may
     be passed to the `schema_overlays` keyword argument::

         from jwst_lib.models import ImageModel
         model = ImageModel(schema_overlays=[my_schema])
         model.meta.target.population = 6e12

  2. To extend an already-created model instance, call the
     `extend_schema` method to add the new schema overlays in place::

         def process(input_model):
             input_model.extend_schema([my_schema])
             input_model.meta.target.population = 6e12

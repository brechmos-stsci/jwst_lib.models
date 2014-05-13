Data models
```````````

The purpose of the data model is to abstract away the peculiarities of
the underlying file format.  The same data model may be used for data
created from scratch in memory, or loaded from FITS files or some
future FITS-replacement format.

About models
============

Hierarchy of models
-------------------

There are different data model classes for different kinds of data.

.. note::

    TODO: This currently only includes image and ramp, but will grow
    to include spectral types etc.

One model instance, many arrays
-------------------------------

Each model instance generally has many arrays that are associated with
it.  For example, the `ImageModel` class has the following arrays
associated with it:

    - `data`: The science data
    - `dq`: The data quality array
    - `err`: The error array

The shape of these arrays must be broadcast-compatible.  If you try to
assign an array to one of these members that is not
broadcast-compatible with the data array, an exception is raised.

Working with models
===================

Creating a data model from scratch
----------------------------------

To create a new `ImageModel`, just call its constructor.  To create a
new model where all of the arrays will have default values, simply
provide a shape as the first argument::

    from jwst_lib.models import ImageModel
    with ImageModel((1024, 1024)) as im:
        ...

In this form, the memory for the arrays will not be allocated until
the arrays are accessed.  This is useful if, for example, you don’t
need a data quality array -- the memory for such an array will not be
consumed::

        # Print out the data array.  It is allocated here on first access
        # and defaults to being filled with zeros.
        print im.data

If you already have data in a numpy array, you can also create a model
using that array by passing it in as a data keyword argument::

    data = np.empty((50, 50))
    dq = np.empty((50, 50))
    with ImageModel(data=data, dq=dq) as im:
        ...

Creating a data model from a file
---------------------------------

The `jwst_lib.models.open` function is a convenient way to create a
model from a file on disk.  It may be passed any of the following:

    - a path to a FITS file
    - a path to a FINF file (TODO: At some future date)
    - a `astropy.io.fits.HDUList` object

The file will be opened, and based on the nature of the data in the
file, the correct data model class will be returned.  For example, if
the file contains 2-dimensional data, an `ImageModel` instance will be
returned.  You will generally want to instantiate a model using a
`with` statement so that the file will be closed automatically when
exiting the `with` block.

::

    from jwst_lib import models
    with models.open("myimage.fits") as im:
        assert isinstance(im, models.ImageModel)

If you know the type of data stored in the file, or you want to ensure
that what is being loaded is of a particular type, use the constructor
of the desired concrete class.  For example, if you want to ensure
that the file being opened contains 2-dimensional image data::

    from jwst_lib.models import ImageData
    with ImageData("myimage.fits") as im:
        # raises exception if myimage.fits is not an image file
        pass

This will raise an exception if the file contains data of the wrong
shape.

Saving a data model to a file
-----------------------------

Simply call the `save` method on the model instance.  The format to
save into will either be deduced from the filename (if provided) or
the `format` keyword argument::

    im.save("myimage.fits")

It also accepts a writable file-like object (opened in binary mode).
In that case, a format must be specified::

    with open("myimage.fits", "wb") as fd:
        im.save(fd, format="fits")

Copying a model
---------------

To create a new model based on another model, simply use its `copy`
method.  This will perform a deep-copy: that is, no changes to the
original model will propagate to the new model::

    new_model = old_model.copy()

It is also possible to copy all of the known metadata from one
model into a new one using the update method::

    new_model.update(old_model)

History information
-------------------

Models contain a list of history records, accessed through the
`history` attribute.  This is just an ordered list of strings --
nothing more sophisticated.

To get to the history::

    model.history

To add an entry to the history::

    model.history.append("Processed through the frobulator step")

These history entries are stored in ``HISTORY`` keywords when saving
to FITS format.

Converting from ``astropy.io.fits``
===================================

This section describes how to port code that uses ``astropy.io.fits``
to use `jwst_lib.models`.

Opening a file
--------------

Instead of::

    astropy.io.fits.open("myfile.fits")

use::

    from jwst_lib.models import ImageModel
    with ImageModel("myfile.fits") as model:
        ...

In place of `ImageModel`, use the type of data one expects to find in
the file.  For example, if spectrographic data is expected, use
`SpecModel`.  If it doesn't matter (perhaps the application is only
sorting FITS files into categories) use the base class `DataModel`.

Accessing data
--------------

Data should be accessed through one of the pre-defined data members on
the model (`data`, `dq`, `err`).  There is no longer a need to hunt
through the HDU list to find the data.

Instead of::

    hdulist['SCI'].data

use::

    model.data

Accessing a section of the data
-------------------------------

To access only a section of the data from disk, replace::

    hdulist['SCI'].section[0:5,:]

with::

    model.get_section('data')[0:5,:]

Furthermore, the use of `section` or `get_section` may not be
necessary in most cases, since the file is, by default, memory mapped
from disk, and the full penalty of loading in the entire array is not
incurred.  In most cases, the performance of simply doing::

    model.data[0:5,:]

should be adequate.

Accessing keywords
------------------

The data model hides direct access to FITS header keywords.  Instead,
use the :ref:`metadata` tree.

There is a convenience method, `find_fits_keyword` to find where a
FITS keyword is used in the metadata tree::

    >>> from jwst_lib.models import DataModel
    # First, create a model of the desired type
    >>> model = DataModel()
    >>> model.find_fits_keyword('DATE-OBS')
    [u'meta.observation.date']

This information shows that instead of::

    print hdulist[0].header['DATE-OBS']

use::

    print model.meta.observation.date

Extra FITS keywords
-------------------

When loading arbitrary FITS files, there will inevitably by keywords
that the schema doesn't know about.  These "extra" FITS keywords are
put under the model in the `_extra_fits` namespace.  The preceding
underscore indicates that this is an implementation detail and may
change in the future.  No code should rely on its continued existence.

Under `_extra_fits` namespace is a section for each header data unit,
and under those are the extra FITS keywords.  For example, if the FITS
file contains a keyword `FOO` in the primary header, its value can be
obtained using::

    model._extra_fits.PRIMARY.FOO

This feature is useful to retain any extra keywords from input files
to output products.

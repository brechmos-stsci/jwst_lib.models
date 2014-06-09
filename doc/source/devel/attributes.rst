Data model attributes
`````````````````````

The purpose of the data model is to abstract away the peculiarities of
the underlying file format.  The same data model may be used for data
created from scratch in memory, or loaded from FITS files or some
future FITS-replacement format.

Calling sequences of models
===========================

List of current models
----------------------

The current models are as follows:

    - CubeModel
    - DarkModel
    - FlatModel
    - FringeModel
    - GainModel
    - ImageModel
    - IPCModel
    - LastFrameModel
    - LinearityModel
    - MaskModel
    - MIRIRampModel
    - MultiSlitModel
    - MultiSpecModel
    - RampFitOutputModel
    - RampModel
    - ReadnoiseModel
    - ResetModel
    - SpecModel

Commonly used attributes
------------------------

Here are a few model attributes that are used by many of the pipeline
steps.  Note that the starting pixel numbers in X and Y are one-indexed.
Getting the number of integrations and the number of groups from the
first and second axes assumes that the input data array is 4-D data.
Much of the jwst_pipeline step code assumes that the data array is 4-D.

    - number of integrations = input_model.data.shape[0]
    - number of groups = input_model.data.shape[1]
    - number of frames = input_model.meta.exposure.nframes
    - group gap = input_model.meta.exposure.groupgap
    - starting pixel in X = input_model.meta.subarray.xstart
    - starting pixel in Y = input_model.meta.subarray.ystart
    - number of columns = input_model.meta.subarray.xsize
    - number of rows = input_model.meta.subarray.ysize

The `data`, `err`, `dq`, etc., attributes of most models are assumed to be
numpy.ndarray arrays, or at least objects that have some of the attributes
of these arrays.  numpy is used explicitly to create these arrays in some
cases (e.g. when a default value is needed).  The `data` and `err` arrays
are a floating point type, and the data quality arrays are an integer type.

Some of the step code makes assumptions about image array sizes.  For
example, full-frame MIRI data have 1032 columns and 1024 rows, and all
other detectors have 2048 columns and rows; anything smaller must be a
subarray.  Also, full-frame MIRI data are assumed to have four columns of
reference pixels on the left and right sides (the reference output array
is stored in a separate image extension).  Full-frame data for all other
instruments have four columns or rows of reference pixels on each edge
of the image.

Calling sequences and model-specific attributes
-----------------------------------------------

`DataModel(init=None, schema=None)`

    `DataModel` is a base class.

    - `init`: A shape tuple, file path or object, HDUList, numpy array.
    - `schema`: A tree of objects representing a JSON schema, or a string
      naming a schema (optional).

`CubeModel(init=None, data=None, dq=None, err=None, **kwargs)`

    `CubeModel` is for a file (suffix '_integ') of integration-specific
    results.

    - `init`: The name of the input file.
    - `data`: The science data, a 3-D array.
    - `dq`: The data quality array, a 3-D array.
    - `err`: The error array, a 3-D array.

`DarkModel(init=None, data=None, dq=None, err=None, **kwargs)`

    - `init`: The name of the dark reference file.
    - `data`: The science data.
    - `dq`: The data quality array.
    - `err`: The error array.

`FlatModel(init=None, data=None, dq=None, err=None, **kwargs)`

    - `init`: The name of the flat-field reference file.
    - `data`: The science data.
    - `dq`: The data quality array.
    - `err`: The error array.

`FringeModel(init=None, data=None, dq=None, err=None, **kwargs)`

    - `init`: The name of the fringe-correction reference file.
    - `data`: The science data.
    - `dq`: The data quality array.
    - `err`: The error array.

`GainModel(init=None, data=None, **kwargs)`

    - `init`: The name of the gain reference file.
    - `data`: The 2-D gain array.

`ImageModel(init=None, data=None, dq=None, err=None, relsens=None, **kwargs)`

    - `init`: The name of the input file.
    - `data`: The science data.
    - `dq`: The data quality array.
    - `err`: The error array.
    - `relsens`: The relative sensitivity table.

`IPCModel(init=None, data=None, **kwargs)`

    - `init`: The name of the IPC reference file.
    - `data`: The deconvolution kernel (a very small image).

`LastFrameModel(init=None, data=None, dq=None, err=None, **kwargs)`

    - `init`: The name of the last-frame reference file.
    - `data`: The science data.
    - `dq`: The data quality array.
    - `err`: The error array.

`LinearityModel(init=None, coeffs=None, dq=None, **kwargs)`

    - `init`: The name of the linearity reference file.
    - `coeffs`: Coefficients defining the nonlinearity function.
    - `dq`: The data quality array.

`MaskModel(init=None, dq=None, **kwargs)`

    - `init`: The name of the mask reference file.
    - `dq`: The data quality array.

`MIRIRampModel(init=None, data=None, pixeldq=None, groupdq=None, err=None, refout=None, **kwargs)`

    - `init`: The name of the input file.
    - `data`: The science data.
    - `pixeldq`: 2-D data quality array.
    - `groupdq`: 3-D or 4-D data quality array.
    - `err`: The error array.
    - `refout`: The array of reference output data.

`MultiSlitModel(init=None, **kwargs)`

    If `init` is a file name or an `ImageModel` instance, an empty
    `ImageModel` will be created and assigned to attribute `slits[0]`,
    and the `data`, `dq`, `err`, and `relsens` attributes from the
    input file or `ImageModel` will be copied to the first element of
    `slits`.

    - `init`: The name of the input file or model.
    - `model.slits`: A list-like object containing ImageModel instances.

`MultiSpecModel(init=None, **kwargs)`

    If `init` is a `SpecModel` instance, an empty `SpecModel` will be
    created and assigned to attribute `spec[0]`, and the `spec_table`
    attribute from the input `SpecModel` instance will be copied to the
    first element of `spec`.  `SpecModel` objects can be appended to the
    `spec` attribute by using its `append` method.

    - `init`: The name of the input file or model.
    - `model.spec`: A list-like object containing `SpecModel` instances.

    Here is an example::

    >>> output_model = models.MultiSpecModel()
    >>> spec = models.SpecModel()           # for the default data type
    >>> for slit in input_model.slits:
    >>>     slitname = slit.name
    >>>     slitmodel = ExtractModel()
    >>>     slitmodel.fromJSONFile(extref, slitname)
    >>>     column, wavelength, countrate = slitmodel.extract(slit.data)
    >>>     otab = np.array(zip(column, wavelength, countrate),
    >>>                     dtype=spec.spec_table.dtype)
    >>>     spec = models.SpecModel(spec_table=otab)
    >>>     output_model.spec.append(spec)

`RampFitOutputModel(init=None, slope=None, sigslope=None, yint=None, sigyint=None, pedestal=None, weights=None, crmag=None, **kwargs)`

    `RampFitOutputModel` is the model for an optional output file giving
    information about the ramp fit.
    `n_int` is the number of integrations, `max_seg` is the maximum
    number of segments that were fit, `nreads` is the number of reads in
    an integration, and `ny` and `nx` are the height and width of the
    image.

    - `init`: The name of the output file.
    - `slope`: Array of shape (n_int, max_seg, ny, nx).
    - `sigslope`: Array of shape (n_int, max_seg, ny, nx).
    - `yint`: Array of shape (n_int, max_seg, ny, nx).
    - `sigyint`: Array of shape (n_int, max_seg, ny, nx).
    - `pedestal`: Array of shape (n_int, ny, nx).
    - `weights`: Array of shape (n_int, max_seg, ny, nx).
    - `crmag`: Array of shape (n_int, nreads, ny, nx).

`RampModel(init=None, data=None, pixeldq=None, groupdq=None, err=None, **kwargs)`

    - `init`: The name of the input file.
    - `data`: The science data.
    - `pixeldq`: 2-D data quality array.
    - `groupdq`: 3-D or 4-D data quality array.
    - `err`: The error array.

`ReadnoiseModel(init=None, data=None, **kwargs)`

    - `init`: The name of the readnoise reference file.
    - `data`: Read noise for all pixels (2-D array).

`ResetModel(init=None, data=None, dq=None, err=None, **kwargs)`

    - `init`: The name of the reset reference file.
    - `data`: The science data.
    - `dq`: The data quality array.
    - `err`: The error array.

`SaturationModel(init=None, sat=None, **kwargs)`

    - `init`: The name of the saturation reference file.
    - `sat`: Saturation mask.

`SpecModel(init=None, spec_table=None, **kwargs)`

    - `init`: The name of the input file.
    - `spec_table`: An array with three columns: pixel number, wavelength,
      and count rate.

Base class methods
==================

`model.copy()`

    Returns a deep copy of this model.

`model.get_primary_array_name()`

    Returns a string giving the name (e.g. 'data' or 'dq') of the primary
    array for this model.

`model.on_save(path)`

    This is a hook that is called just before saving the file.
    It can be used, for example, to update values in the metadata
    that are based on the content of the data.

    - `path`: The path to the file that we're about to save to.

`model.save(path, *args, **kwargs)`

    Currently just saves to a FITS file.

    - `path`: The path to the file that we're about to save to.

`ModelClassName.from_fits(path, *args, **kwargs)`

    Load a model from a FITS file.

    - `path`: The path to the file that is to be read.

    Returns an instance of the class ModelClassName (use an actual model
    name), loaded from the file specified as `path`.

`model.to_fits(init, *args, **kwargs)`

    Write the model to a FITS file.  Any additional arguments are passed
    along to the `writeto` convenience function in `astropy.io.fits`.

    - `init`: File path or file object for the output FITS file.

`ModelClassName.from_json(init, schema=None)`

    Load the metadata for a model from a JSON file.

    - `init`: File path or file object for a JSON file.
    - `schema`: Schema tree.

    Returns an instance of the class ModelClassName (use an actual model
    name), loaded from a JSON file.  Note that arrays cannot be loaded
    from or saved to JSON.

`model.to_json(init)`

    Write the model to a JSON file.  Note that arrays cannot be
    loaded from or saved to a JSON file.

    - `init`: File path or file object for a JSON file.

`model.to_yaml(path)`

    Write the model to a YAML file.

    - `path`: File path or file object for a YAML file.

`model.extend_schema(new_schema)`

    Extend the model's schema using the given schema, by combining it in
    an "allOf" array.

    - `new_schema`: Schema tree.

`model.add_schema_entry(position, new_schema)`

    Extend the model's schema by placing `new_schema` at
    the given dot-separated position in the tree.

    - `position`: str
    - `new_schema`: Schema tree.

`model.find_fits_keyword(keyword, return_result=False)`

    - `keyword`: A FITS keyword name (case sensitive).
    - `return_result`: If `False` (default) print result to stdout.  If
      `True`, return the result as a list.

    If `return_result` is `True`, returns a list of the
    locations in the schema where this FITS keyword is used.  Each
    element is a dot-separated path.

`model.search_schema(substring, return_result=False, verbose=False)`

    - `substring`: The substring to search for.
    - `return_result`: If `False` (default) print result to stdout.  If
      `True`, return the result as a list.
    - `verbose`: If `False` (default) display a one-line description of
      each match.  If `True`, display the complete description
      of each match.

    If `return_result` is `True`, returns a list of tuples of the form
    (*location*, *description*)

`model.get_item_as_json_value(key)`

    Equivalent to __getitem__, except returns the value as a JSON basic
    type, rather than an arbitrary Python type.

    - `key`: str

`model.iteritems(include_arrays=False, primary_only=False)`

    Iterate over all of the schema items in a flat way.  Each element
    is a pair (`key`, `value`).  Each `key` is a dot-separated name.  For
    example, the schema element `meta.observation.date` will end up in
    the result as::

    ( "meta.observation.date": "2012-04-22T03:22:05.432" )

    - `include_arrays`: When `True`, include numpy arrays in the result.
    - `primary_only`: When `True`, only return values from the PRIMARY
      FITS HDU.

`model.items(include_arrays=False, primary_only=False)`

    - `include_arrays`: When `True`, include numpy arrays in the result.
    - `primary_only`: When `True`, only return values from the PRIMARY
      FITS HDU.

    Returns a list of all the schema items as (`key`, `value`) pairs.

`model.iterkeys(self, include_arrays=False, primary_only=False)`

    Iterate over all of the schema keys in a flat way.  Each result of
    the iterator is a `key`.  Each `key` is a dot-separated name, such as
    `meta.observation.date`.

    - `include_arrays`:  When `True`, include keys that point to numpy
      arrays in the result.
    - `primary_only`: When `True`, only return values from the PRIMARY
      FITS HDU.

`model.keys(include_arrays=False, primary_only=False)`

    - `include_arrays`: When `True`, include keys that point to numpy
      arrays in the result.
    - `primary_only`: When `True`, only return values from the PRIMARY
      FITS HDU.

    Returns a list of all the schema keys.

`model.itervalues(include_arrays=False, primary_only=False)`

    Iterate over all the schema values in a flat way.

    - `include_arrays`: When `True`, include numpy arrays in the result.
    - `primary_only`: When `True`, only return values from the PRIMARY
      FITS HDU.

`model.values(include_arrays=False, primary_only=False)`

    - `include_arrays`: When `True`, include numpy arrays in the result.
    - `primary_only`: When `True`, only return values from the PRIMARY
      FITS HDU.

    Returns a list of all the schema values.

`model.update(d, include_arrays=False, primary_only=False)`

    Update this model with the metadata elements from another model.

    - `d`: model or dictionary-like object.
      The model to copy the metadata elements from.  If dictionary-like,
      it must have an `items` method that returns (key, value) pairs,
      where the keys are dot-separated paths to metadata elements.
    - `include_arrays`: When `True`, update numpy array elements.
    - `primary_only`: When `True`, only transfer values from the PRIMARY
      FITS HDU.

`model.to_flat_dict(include_arrays=False)`

    - `include_arrays`: When `True`, update numpy arrays in the
      dictionary.

    Returns a dictionary of all of the schema items as a flat dictionary.
    Each dictionary key is a dot-separated name.  For example, the schema
    element `meta.observation.date` will end up in the dictionary as::

        { "meta.observation.date": "2012-04-22T03:22:05.432" }

`model.schema`

    Returns the `_schema` attribute.

`model.shape`

    Returns the `_shape` attribute.

`value = model.<attribute>`

    Returns the value of an attribute of the model.

`model.<attribute> = value`

    Set an attribute of the model to the specified value.

`model.history`

    Returns the `_storage.history` attribute.

`model.history(value)`

    Assign `value` to the _storage.history attribute.

`model.get_fileext()`

    Returns the filename extension (currently "fits").

Methods in base class HasFitsWcs
--------------------------------

`wcs.get_fits_wcs(hdu_name='PRIMARY', key=' ')`

    Get a WCS object (either `astropy.wcs.WCS` or `pywcs.WCS`) created
    from the FITS WCS information in the model.

    - `hdu_name`: The name of the HDU to get the WCS from.  This must
      use named HDU's, not numerical order HDUs.  To get the primary
      HDU, pass ``'PRIMARY'`` (default).
    - `key`: The name of a particular WCS transform to use.  This may
      be either ``' '`` or ``'A'``-``'Z'`` and corresponds to
      the ``"a"`` part of the ``CTYPEia`` cards.  *key* may only
      be provided if *hdu_name* is also provided.

`wcs.set_fits_wcs(wcs, hdu_name='PRIMARY')`

    Set the FITS WCS information on the model using the given
    `astropy.wcs.WCS` or `pywcs.WCS` object.
    Note that the "key" of the WCS is stored in the WCS object
    itself, so it cannot be set as a parameter to this method.

    - `wcs`: The object containing FITS WCS information.
    - `hdu_name`: The name of the HDU to set the WCS from.  This must
      use named HDU's, not numerical order HDUs.  To set the primary
      HDU, pass ``'PRIMARY'`` (default).

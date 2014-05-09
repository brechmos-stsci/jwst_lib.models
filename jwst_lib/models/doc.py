"""
Used by the documentation to build representations of the schema in
different formats.
"""
from __future__ import absolute_import, unicode_literals, division, print_function

import collections
import io
import os
import tempfile
import textwrap
import urllib

import yaml
from yaml.nodes import MappingNode

from . import schema


###########################################################################


def SchemaAsJson():
    """
    The core schema in JSON format

    .. code-block:: javascript

        {0}

    """
    pass

fd = urllib.urlopen(schema.get_schema_path(
    'schemas/core.schema.json', os.path.dirname(__file__))[0])
try:
    SchemaAsJson.__doc__ = (
        textwrap.dedent(SchemaAsJson.__doc__).format(
            '    '.join(fd.readlines())))
finally:
    fd.close()


###########################################################################


def SchemaAsYaml():
    """
    The core schema in YAML format

    .. code-block:: yaml

        {0}
    """
    pass

tree = schema.get_schema(
    'schemas/core.schema.json', os.path.dirname(__file__))


def yaml_representer(dumper, obj):
    if isinstance(obj, collections.OrderedDict):
        # PyYAML explicitly sorts by keys on mappings, so we have
        # to work really hard not have them sorted
        value = []
        node = MappingNode('tag:yaml.org,2002:map', value, flow_style=False)
        for key, val in obj.items():
            node_key = dumper.represent_data(key)
            node_val = dumper.represent_data(val)
            value.append((node_key, node_val))

        return node
    else:
        raise TypeError("Can't serialize {0}".format(obj))

yaml.SafeDumper.add_representer(None, yaml_representer)

with tempfile.TemporaryFile("w+") as fd:
    yaml.safe_dump(tree, fd, default_flow_style=False, canonical=False)
    fd.seek(0)
    SchemaAsYaml.__doc__ = (
        textwrap.dedent(SchemaAsYaml.__doc__).format(
            '    '.join(fd.readlines())))


###########################################################################


def SchemaAsHuman():
    """The core schema in a tabular format.

{0}
    """
    pass


def recurse(name, tree, rows, indent):
    name = ('\N{EM DASH}' * indent) + name
    fits_keyword = tree.get('fits_keyword')
    if fits_keyword is not None:
        fits_keyword = '``{0}``'.format(fits_keyword)
    else:
        fits_keyword = ''
    type = tree.get('type', 'any')
    if isinstance(type, list):
        type = '/'.join(type)
    title = tree.get('title', '')

    rows.append((name, fits_keyword, type, title))

    if tree.get('type') == 'object':
        for key, val in tree.get('properties', {}).items():
            recurse(key, val, rows, indent + 1)

    elif tree.get('type') == 'array':
        for value in tree.get('items', []):
            recurse('*item*', val, rows, indent + 1)


rows = []
recurse('meta', tree, rows, 0)

widths = [0] * len(rows[0])
for row in rows:
    for i, col in enumerate(row):
        widths[i] = max(widths[i], len(col))

headers = ('Name', 'FITS keyword', 'Type', 'Description')

o = io.StringIO()


def write_row(row):
    for i, col in enumerate(row):
        width = widths[i]
        o.write('{0:<{width}} '.format(col[:width], width=width))
    o.write('\n')


def write_sep():
    lines = '=' * 1000
    write_row([lines] * len(widths))


write_sep()
write_row(headers)
write_sep()
for row in rows:
    write_row(row)
write_sep()

SchemaAsHuman.__doc__ = SchemaAsHuman.__doc__.format(o.getvalue())

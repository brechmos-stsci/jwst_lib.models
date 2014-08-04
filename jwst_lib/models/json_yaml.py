"""
Utilities to support order-preserving loading/saving of JSON and YAML
files, and a unified interface to each.
"""

from __future__ import absolute_import, unicode_literals, division, print_function


import collections
import io
import json
import os.path

from . import util


def _load_json(fd):
    import json
    return json.load(fd, object_pairs_hook=collections.OrderedDict)


def _load_yaml(fd):
    import yaml

    class OrderedDictYAMLLoader(yaml.Loader):
        """
        A YAML loader that loads mappings into ordered dictionaries.
        """
        def __init__(self, *args, **kwargs):
            yaml.Loader.__init__(self, *args, **kwargs)

            self.add_constructor(
                'tag:yaml.org,2002:map', type(self).construct_yaml_map)
            self.add_constructor(
                'tag:yaml.org,2002:omap', type(self).construct_yaml_map)

        def construct_yaml_map(self, node):
            data = collections.OrderedDict()
            yield data
            value = self.construct_mapping(node)
            data.update(value)

        def construct_mapping(self, node, deep=False):
            if isinstance(node, yaml.MappingNode):
                self.flatten_mapping(node)
            else:
                raise yaml.constructor.ConstructorError(
                    None, None,
                    'expected a mapping node, but found {0}'.format(node.id),
                    node.start_mark)

            mapping = collections.OrderedDict()
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    hash(key)
                except TypeError as exc:
                    raise yaml.constructor.ConstructorError(
                        'while constructing a mapping',
                        node.start_mark,
                        'found unacceptable key ({0!r})'.format(exc),
                        key_node.start_mark)
                value = self.construct_object(value_node, deep=deep)
                mapping[key] = value
            return mapping

    return yaml.load(fd, Loader=OrderedDictYAMLLoader)


def load(fd):
    """
    Load either JSON or YAML from the given file object or file path.
    """
    def is_json(fd):
        try:
            while True:
                block = fd.read(64)
                if block is None:
                    return True

                for char in block:
                    if char.isspace():
                        continue
                    elif char == '{':
                        return True
                    else:
                        return False
        finally:
            fd.seek(0)

    def do_load(fd):
        if is_json(fd):
            return _load_json(fd)
        else:
            return _load_yaml(fd)

    if isinstance(fd, (bytes, unicode)):
        with open(fd, 'r') as fobj:
            return do_load(fobj)
    else:
        return do_load(fd)


def loads(s):
    """
    Read either JSON or YAML from the given string.
    """
    with io.StringIO(s) as fd:
        return load(fd)


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, o):
        from . import schema
        if isinstance(o, schema.PickleProxy):
            return unicode(o)
        return super(CustomJsonEncoder, self).default(o)


def _dump_json(tree, fd):
    import json
    return json.dump(tree, fd, indent=2, cls=CustomJsonEncoder)


def _dump_yaml(tree, fd):
    import yaml
    from yaml.nodes import MappingNode

    def yaml_meta_representer(dumper, obj):
        if isinstance(obj, collections.OrderedDict):
            # PyYAML explicitly sorts by keys on mappings, so we have
            # to work really hard not have them sorted
            value = []
            node = MappingNode(
                'tag:yaml.org,2002:map', value, flow_style=False)
            for key, val in obj.items():
                node_key = dumper.represent_data(key)
                node_val = dumper.represent_data(val)
                value.append((node_key, node_val))

            return node
        elif isinstance(obj, util.ValidatingList):
            return dumper.represent_list(obj)
        else:
            raise TypeError("Can't serialize {0}".format(obj))

    yaml.SafeDumper.add_representer(None, yaml_meta_representer)

    return yaml.safe_dump(tree, fd, default_flow_style=False, canonical=False)


def dump(tree, fd, format=None):
    """
    Dump either JSON or YAML to the given file object or file path.
    """
    def do_dump(tree, fd, format):
        if format == 'json':
            return _dump_json(tree, fd)
        elif format == 'yaml':
            return _dump_yaml(tree, fd)

    if isinstance(fd, (bytes, unicode)):
        if format is None:
            _, ext = os.path.splitext(fd)[1:]
            if ext in ('json', 'yaml'):
                format = ext
            else:
                raise ValueError(
                    "Could not determine output format from extension, "
                    "and no format kw provided")
        with open(fd, 'w') as fobj:
            return do_dump(tree, fobj, format)
    else:
        if format not in ('json', 'yaml'):
            raise ValueError(
                "format must be 'json' or 'yaml'")
        return do_dump(tree, fd, format)


def dumps(tree, format=None):
    """
    Dump either JSON or YAML to a string.
    """
    with io.StringIO() as fd:
        return dump(tree, fd, format=format)

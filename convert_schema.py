#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Convert a schema from the old JSON-based format to the new
YAML-based one.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

import collections
import json
import sys

import yaml

from pyasdf import treeutil

import six


def convert(in_path, out_path):
    with open(in_path, "rb") as fd:
        tree = json.load(fd, object_pairs_hook=collections.OrderedDict)

    def yaml_representer(dumper, obj):
        if isinstance(obj, collections.OrderedDict):
            # PyYAML explicitly sorts by keys on mappings, so we have
            # to work really hard not have them sorted
            value = []
            node = yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value, flow_style=False)
            for key, val in obj.items():
                node_key = dumper.represent_data(key)
                node_val = dumper.represent_data(val)
                value.append((node_key, node_val))

            return node
        else:
            raise TypeError("Can't serialize {0}".format(obj))

    yaml.SafeDumper.add_representer(None, yaml_representer)

    def convert_references(node):
        if isinstance(node, six.string_types):
            if node.endswith('schema.json'):
                return node[:-4] + 'yaml'
        return node
    tree = treeutil.walk_and_modify(tree, convert_references)

    def remove_type_of_data(node):
        if isinstance(node, dict):
            if node.get('type') == 'data':
                del node['type']
        return node
    tree = treeutil.walk_and_modify(tree, remove_type_of_data)

    def convert_datatypes(node):
        if isinstance(node, dict) and 'dtype' in node:
            node['datatype'] = node['dtype']
            del node['dtype']

            if (isinstance(node['datatype'], (str, unicode)) and
                node['datatype'].startswith('string')):
                node['datatype'] = ['ascii', int(node['datatype'][6:])]
        return node
    tree = treeutil.walk_and_modify(tree, convert_datatypes)

    tree['$schema'] = 'http://stsci.edu/schemas/fits-schema/fits-schema'

    with open(out_path, 'wb') as fd:
        yaml.dump(tree, fd, Dumper=yaml.SafeDumper)


def convert_all(files):
    for filename in files:
        convert(filename, filename[:-5] + '.yaml')


if __name__ == '__main__':
    convert_all(sys.argv[1:])

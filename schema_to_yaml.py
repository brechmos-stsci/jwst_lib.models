#!/usr/bin/env python

import json
import yaml
from yaml.nodes import MappingNode
import collections

with open("lib/jwstlib/models/schema.json", "r") as fd:
    tree = json.load(fd, object_pairs_hook=collections.OrderedDict)

def yaml_representer(dumper, obj):
    if isinstance(obj, collections.OrderedDict):
        # PyYAML explicitly sorts by keys on mappings, so we have
        # to work really hard not have them sorted
        value = []
        node = MappingNode(u'tag:yaml.org,2002:map', value, flow_style=False)
        for key, val in obj.items():
            node_key = dumper.represent_data(key)
            node_val = dumper.represent_data(val)
            value.append((node_key, node_val))

        return node
    else:
        raise TypeError("Can't serialize {0}".format(obj))

yaml.SafeDumper.add_representer(None, yaml_representer)

with open("schema.yaml", "w") as fd:
    yaml.safe_dump(tree, fd, default_flow_style=False, canonical=False)



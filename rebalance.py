#!/usr/bin/env python3
# TODO: All the annoying auth stuff
# client = ...

import yaml

def calculate_allocations(portfolio):
    pass

with open('config.yaml', 'r') as f:
    configs = yaml.safe_load(f)

for config in configs:
    target_allocation = calculate_allocations(config['portfolio'])

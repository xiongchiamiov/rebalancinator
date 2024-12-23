#!/usr/bin/env python3
# TODO: All the annoying auth stuff
# client = ...

import yaml

def calculate_allocations(portfolio, multiplier=1):
    allocations = {}
    for percentage, investment in portfolio.items():
        if isinstance(investment, str):
            allocations[investment] = int(percentage * multiplier)
            continue

        allocations.update(calculate_allocations(investment, percentage/100))

    return allocations

if __name__ == '__main__':
    with open('config.yaml', 'r') as f:
        configs = yaml.safe_load(f)

    for config in configs:
        target_allocation = calculate_allocations(config['portfolio'])

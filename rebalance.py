#!/usr/bin/env python3
# TODO: All the annoying auth stuff
# client = ...

# May you recognize your weaknesses and share your strengths.
# May you share freely, never taking more than you give.
# May you find love and love everyone you find.

import yaml

class RebalancinatorException(Exception): pass
class IncorrectWeightingException(RebalancinatorException):
    def __init__(self, allocations):
        self.allocations = allocations

    def __str__(self):
        return "Weights don't add up to 100: {}".format(self.allocations)

def calculate_allocations(portfolio, multiplier=1):
    allocations = {}
    running_total = 0
    for asset_class in portfolio:
        for percentage, investment in asset_class.items():
            running_total += percentage

            # Is this a single ticker?
            if isinstance(investment, str):
                allocations[investment] = int(percentage * multiplier)
                continue

            # If it's a nested breakdown instead, recurse.
            allocations.update(calculate_allocations(investment, percentage/100))

    # Check that the user correctly gave us numbers that add up to 100%.
    if running_total != 100:
        raise IncorrectWeightingException(allocations)

    return allocations

if __name__ == '__main__':
    with open('config.yaml', 'r') as f:
        configs = yaml.safe_load(f)

    for config in configs:
        target_allocation = calculate_allocations(config['portfolio'])

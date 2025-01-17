#!/usr/bin/env python3
import unittest
from rebalance import IncorrectWeightingException, calculate_allocations


class TestCalculateAllocations(unittest.TestCase):
    def test_empty(self):
        with self.assertRaises(IncorrectWeightingException):
            calculate_allocations({})

    def test_not_100(self):
        with self.assertRaises(IncorrectWeightingException):
            calculate_allocations([{90: 'VTI'}, {90: 'VXUS'}])

        with self.assertRaises(IncorrectWeightingException):
            calculate_allocations(
                [
                    {60: [
                        {50: 'VTI'},
                        {49: 'VXUS'},
                    ]},
                    {40: 'BND'},
                ])

    def test_one_fund(self):
        self.assertEqual(calculate_allocations([{100: 'VFIFX'}]),
                         {'VFIFX': 100})

    def test_two_fund(self):
        self.assertEqual(calculate_allocations([{60: 'VT', 40: 'BND'}]),
                         {'VT': 60, 'BND': 40})

    def test_two_layer(self):
        self.assertEqual(calculate_allocations(
            [
                {60: [
                    {50: 'VTI'},
                    {50: 'VXUS'},
                ]},
                {40: 'BND'},
            ]),
            {'VTI': 30, 'VXUS': 30, 'BND': 40})


if __name__ == '__main__':
    unittest.main()

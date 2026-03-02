# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.menu.formatter import CurrencyFormatter, QuantityFormatter


class TestCurrencyFormatter(unittest.TestCase):
    def test_default_format(self):
        fmt = CurrencyFormatter()
        result = fmt.format(100)
        self.assertIn("$", result)
        self.assertIn("100", result)

    def test_custom_symbol_before(self):
        fmt = CurrencyFormatter(symbol="€", position="before")
        result = fmt.format(42)
        self.assertTrue(result.startswith("€"))
        self.assertIn("42", result)

    def test_custom_symbol_after(self):
        fmt = CurrencyFormatter(symbol="¥", position="after")
        result = fmt.format(999)
        self.assertTrue(result.endswith("¥"))
        self.assertIn("999", result)

    def test_zero_amount(self):
        fmt = CurrencyFormatter()
        result = fmt.format(0)
        self.assertIn("0", result)

    def test_large_amount(self):
        fmt = CurrencyFormatter(width=8)
        result = fmt.format(12345678)
        self.assertIn("12345678", result)

    def test_negative_amount(self):
        fmt = CurrencyFormatter()
        result = fmt.format(-50)
        self.assertIn("-50", result)

    def test_custom_width(self):
        fmt = CurrencyFormatter(width=6)
        result = fmt.format(1)
        self.assertIn("1", result)
        self.assertEqual(len(result), 7)  # symbol + 6 width


class TestQuantityFormatter(unittest.TestCase):
    def test_default_format(self):
        fmt = QuantityFormatter()
        self.assertEqual(fmt.format(5), "x 5")

    def test_custom_symbol(self):
        fmt = QuantityFormatter(symbol="qty")
        self.assertEqual(fmt.format(10), "qty 10")

    def test_zero_quantity(self):
        fmt = QuantityFormatter()
        self.assertEqual(fmt.format(0), "x 0")

    def test_large_quantity(self):
        fmt = QuantityFormatter()
        self.assertEqual(fmt.format(9999), "x 9999")

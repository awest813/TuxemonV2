# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.ui.paginator import Paginator


class TestPaginator(unittest.TestCase):
    def test_basic_pagination(self):
        items = list(range(10))
        p = Paginator(items, page_size=3)
        self.assertEqual(p.total_pages(), 4)

    def test_first_page(self):
        items = list(range(10))
        p = Paginator(items, page_size=3)
        result = p.paginate(0)
        self.assertEqual(result, [0, 1, 2])

    def test_last_page(self):
        items = list(range(10))
        p = Paginator(items, page_size=3)
        result = p.paginate(3)
        self.assertEqual(result, [9])

    def test_invalid_page_returns_empty(self):
        items = list(range(5))
        p = Paginator(items, page_size=3)
        result = p.paginate(10)
        self.assertEqual(result, [])

    def test_negative_page_returns_empty(self):
        items = list(range(5))
        p = Paginator(items, page_size=3)
        result = p.paginate(-1)
        self.assertEqual(result, [])

    def test_is_valid_page(self):
        items = list(range(10))
        p = Paginator(items, page_size=5)
        self.assertTrue(p.is_valid_page(0))
        self.assertTrue(p.is_valid_page(1))
        self.assertFalse(p.is_valid_page(2))

    def test_clamp_page(self):
        items = list(range(10))
        p = Paginator(items, page_size=5)
        self.assertEqual(p.clamp_page(-1), 0)
        self.assertEqual(p.clamp_page(99), 1)

    def test_empty_items(self):
        p = Paginator([], page_size=5)
        self.assertEqual(p.total_pages(), 0)
        self.assertEqual(p.paginate(0), [])

    def test_single_item(self):
        p = Paginator([42], page_size=5)
        self.assertEqual(p.total_pages(), 1)
        self.assertEqual(p.paginate(0), [42])

    def test_invalid_page_size_raises(self):
        with self.assertRaises(ValueError):
            Paginator([1, 2, 3], page_size=0)

    def test_calculate_page_data(self):
        items = list(range(10))
        p = Paginator(items, page_size=3)
        total, page_items = p.calculate_page_data(1)
        self.assertEqual(total, 4)
        self.assertEqual(page_items, [3, 4, 5])

    def test_update_items(self):
        p = Paginator([1, 2, 3], page_size=2)
        self.assertEqual(p.total_pages(), 2)
        p.update_items([1, 2, 3, 4, 5])
        self.assertEqual(p.total_pages(), 3)

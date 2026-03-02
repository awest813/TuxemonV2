# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.ui.text_paginator import TextPaginator


class TestTextPaginator(unittest.TestCase):
    def test_default_paginator_returns_single_page(self):
        p = TextPaginator()
        result = p.paginate_text("Hello, world!")
        self.assertEqual(result, ["Hello, world!"])

    def test_empty_string(self):
        p = TextPaginator()
        result = p.paginate_text("")
        self.assertEqual(result, [""])

    def test_paginate_with_max_lines(self):
        p = TextPaginator(max_lines_per_page=2)
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        result = p.paginate_text(text)
        self.assertEqual(len(result), 2)

    def test_paginate_preserves_content(self):
        p = TextPaginator(max_lines_per_page=1)
        text = "Line 1\nLine 2\nLine 3"
        result = p.paginate_text(text)
        self.assertEqual(len(result), 3)

    def test_single_line(self):
        p = TextPaginator(max_lines_per_page=5)
        result = p.paginate_text("Just one line")
        self.assertEqual(len(result), 1)

    def test_newlines_split_correctly(self):
        p = TextPaginator(max_lines_per_page=1)
        text = "A\nB\nC"
        result = p.paginate_text(text)
        self.assertTrue(len(result) >= 3)

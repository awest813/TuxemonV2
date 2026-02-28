# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

from tuxemon.ui.text_paginator import TextPaginator


def test_paginate_preserves_middle_blank_lines_when_wrapping() -> None:
    paginator = TextPaginator(max_line_length=10, max_lines_per_page=10)

    pages = paginator.paginate_text("first line\n\nsecond line")

    assert pages == ["first line\n\nsecond\nline"]


def test_paginate_trims_only_edge_blank_lines_when_wrapping() -> None:
    paginator = TextPaginator(max_line_length=10, max_lines_per_page=10)

    pages = paginator.paginate_text("\n\nfirst line\n\nsecond line\n\n")

    assert pages == ["first line\n\nsecond\nline"]

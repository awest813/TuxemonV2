# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tuxemon.event.actions.spawn_monster import _determine_tastes


class TestDetermineTastes(unittest.TestCase):
    def test_returns_mutated_taste_slugs(self):
        mother = SimpleNamespace(taste_warm="sweet", taste_cold="mint")
        father = SimpleNamespace(taste_warm="spicy", taste_cold="bitter")

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            side_effect=["sweet", "mint"],
        ), patch(
            "tuxemon.event.actions.spawn_monster._mutate_taste",
            side_effect=["umami", "icy"],
        ):
            warm_slug, cold_slug = _determine_tastes(mother, father)

        self.assertEqual((warm_slug, cold_slug), ("umami", "icy"))

    def test_returns_parent_tastes_when_no_mutation(self):
        mother = SimpleNamespace(taste_warm="sweet", taste_cold="mint")
        father = SimpleNamespace(taste_warm="spicy", taste_cold="bitter")

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            side_effect=["spicy", "bitter"],
        ), patch(
            "tuxemon.event.actions.spawn_monster._mutate_taste",
            side_effect=["spicy", "bitter"],
        ):
            warm_slug, cold_slug = _determine_tastes(mother, father)

        self.assertEqual((warm_slug, cold_slug), ("spicy", "bitter"))


if __name__ == "__main__":
    unittest.main()

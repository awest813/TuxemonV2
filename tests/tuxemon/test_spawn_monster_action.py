# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tuxemon.event.actions.spawn_monster import (
    _determine_tastes,
    _inherit_parental_moves,
)


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


class TestInheritParentalMoves(unittest.TestCase):
    def test_inherits_one_move_from_each_parent_into_random_slots(self):
        mother_move = SimpleNamespace(slug="water_pulse")
        father_move = SimpleNamespace(slug="thunder_wave")
        child_move_1 = SimpleNamespace(slug="quick_attack")
        child_move_2 = SimpleNamespace(slug="tail_whip")

        replace_move = unittest.mock.Mock()

        child = SimpleNamespace(
            moves=SimpleNamespace(
                current_moves=[child_move_1, child_move_2],
                replace_move=replace_move,
            )
        )
        mother = SimpleNamespace(
            moves=SimpleNamespace(
                current_moves=[mother_move], get_moves=lambda: [mother_move]
            )
        )
        father = SimpleNamespace(
            moves=SimpleNamespace(
                current_moves=[father_move], get_moves=lambda: [father_move]
            )
        )

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            side_effect=[mother_move, father_move],
        ), patch(
            "tuxemon.event.actions.spawn_monster.random.sample",
            return_value=[1, 0],
        ):
            _inherit_parental_moves(child, mother, father)

        replace_move.assert_any_call(1, mother_move)
        replace_move.assert_any_call(0, father_move)
        self.assertEqual(replace_move.call_count, 2)

    def test_skips_duplicate_slug_when_both_parents_share_same_move(self):
        shared_move = SimpleNamespace(slug="bubble")
        child_move = SimpleNamespace(slug="growl")
        replace_move = unittest.mock.Mock()

        child = SimpleNamespace(
            moves=SimpleNamespace(current_moves=[child_move], replace_move=replace_move)
        )
        mother = SimpleNamespace(
            moves=SimpleNamespace(
                current_moves=[shared_move], get_moves=lambda: [shared_move]
            )
        )
        father = SimpleNamespace(
            moves=SimpleNamespace(
                current_moves=[shared_move], get_moves=lambda: [shared_move]
            )
        )

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            side_effect=[shared_move, shared_move],
        ), patch(
            "tuxemon.event.actions.spawn_monster.random.sample",
            return_value=[0],
        ):
            _inherit_parental_moves(child, mother, father)

        replace_move.assert_called_once_with(0, shared_move)


if __name__ == "__main__":
    unittest.main()

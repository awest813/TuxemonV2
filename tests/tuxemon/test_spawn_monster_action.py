# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tuxemon.database.rules import config_monster
from tuxemon.event.actions.spawn_monster import (
    _determine_inherited_ivs,
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

        add_move = unittest.mock.Mock()
        child = SimpleNamespace(
            max_moves=2,
            moves=SimpleNamespace(
                current_moves=[child_move_1, child_move_2],
                add_move=add_move,
                replace_move=replace_move,
            ),
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

        add_move = unittest.mock.Mock()
        child = SimpleNamespace(
            max_moves=1,
            moves=SimpleNamespace(
                current_moves=[child_move],
                add_move=add_move,
                replace_move=replace_move,
            ),
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

    def test_prefers_appending_inherited_move_when_child_has_capacity(self):
        mother_move = SimpleNamespace(slug="water_pulse")
        child_move = SimpleNamespace(slug="quick_attack")
        add_move = unittest.mock.Mock()
        replace_move = unittest.mock.Mock()

        child = SimpleNamespace(
            max_moves=4,
            moves=SimpleNamespace(
                current_moves=[child_move],
                add_move=add_move,
                replace_move=replace_move,
            ),
        )
        mother = SimpleNamespace(
            moves=SimpleNamespace(
                current_moves=[mother_move], get_moves=lambda: [mother_move]
            )
        )
        father = SimpleNamespace(
            moves=SimpleNamespace(current_moves=[], get_moves=lambda: [])
        )

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            return_value=mother_move,
        ):
            _inherit_parental_moves(child, mother, father)

        add_move.assert_called_once_with(mother_move)
        replace_move.assert_not_called()


class TestDetermineInheritedIvs(unittest.TestCase):
    def test_inherits_each_stat_from_a_parent_without_mutation(self):
        min_iv, max_iv = config_monster.iv_range
        mother_ivs = SimpleNamespace(
            hp=min_iv,
            melee=min_iv + 1,
            ranged=min_iv + 2,
            armour=min_iv + 3,
            dodge=min_iv + 4,
            speed=min_iv + 5,
        )
        father_ivs = SimpleNamespace(
            hp=max_iv,
            melee=max_iv,
            ranged=max_iv,
            armour=max_iv,
            dodge=max_iv,
            speed=max_iv,
        )
        mother = SimpleNamespace(individual_values=mother_ivs)
        father = SimpleNamespace(individual_values=father_ivs)

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            side_effect=[
                mother_ivs.armour,
                father_ivs.dodge,
                mother_ivs.hp,
                father_ivs.melee,
                mother_ivs.ranged,
                father_ivs.speed,
            ],
        ), patch(
            "tuxemon.event.actions.spawn_monster.random.random",
            return_value=0.99,
        ):
            child_ivs = _determine_inherited_ivs(mother, father)

        self.assertEqual(child_ivs.armour, mother_ivs.armour)
        self.assertEqual(child_ivs.dodge, father_ivs.dodge)
        self.assertEqual(child_ivs.hp, mother_ivs.hp)
        self.assertEqual(child_ivs.melee, father_ivs.melee)
        self.assertEqual(child_ivs.ranged, mother_ivs.ranged)
        self.assertEqual(child_ivs.speed, father_ivs.speed)

    def test_mutation_is_clamped_to_valid_iv_range(self):
        min_iv, max_iv = config_monster.iv_range
        mother_ivs = SimpleNamespace(
            hp=min_iv,
            melee=min_iv,
            ranged=min_iv,
            armour=max_iv,
            dodge=max_iv,
            speed=max_iv,
        )
        father_ivs = SimpleNamespace(
            hp=min_iv,
            melee=min_iv,
            ranged=min_iv,
            armour=max_iv,
            dodge=max_iv,
            speed=max_iv,
        )
        mother = SimpleNamespace(individual_values=mother_ivs)
        father = SimpleNamespace(individual_values=father_ivs)

        with patch(
            "tuxemon.event.actions.spawn_monster.random.choice",
            side_effect=[
                min_iv,
                -1,
                min_iv,
                -1,
                min_iv,
                -1,
                max_iv,
                1,
                max_iv,
                1,
                max_iv,
                1,
            ],
        ), patch(
            "tuxemon.event.actions.spawn_monster.random.random",
            return_value=0.0,
        ):
            child_ivs = _determine_inherited_ivs(mother, father)

        self.assertEqual(child_ivs.armour, min_iv)
        self.assertEqual(child_ivs.dodge, min_iv)
        self.assertEqual(child_ivs.hp, min_iv)
        self.assertEqual(child_ivs.melee, max_iv)
        self.assertEqual(child_ivs.ranged, max_iv)
        self.assertEqual(child_ivs.speed, max_iv)


if __name__ == "__main__":
    unittest.main()

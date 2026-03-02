# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import tuxemon.database.runtime
from tuxemon.db import MonsterModel


class TestEggHatching(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session.player = MagicMock()
        self.session.player.monsters = []
        self.session.player.party = MagicMock()
        self.session.player.party.add_monster = MagicMock(
            side_effect=lambda m, s: self.session.player.monsters.append(m)
        )
        self.session.client = MagicMock()
        self.session.client.get_state_by_name = MagicMock()

        # Mock DB
        # We replace the _database dict within the existing ModData instance
        self.original_database = tuxemon.database.runtime.db._database
        tuxemon.database.runtime.db._database = {
            "monster": {"hatchling": MagicMock()}  # Presence check
        }

        # Patch lookup to return a proper mock object
        self.lookup_patcher = patch.object(MonsterModel, "lookup")
        self.mock_lookup = self.lookup_patcher.start()

        mock_monster_model = MagicMock(spec=MonsterModel)
        mock_monster_model.slug = "hatchling"
        mock_monster_model.species = "egg"
        mock_monster_model.sprites = MagicMock()
        mock_monster_model.sounds = MagicMock()
        # Add required attributes for Monster.__init__
        mock_monster_model.height = 10.0
        mock_monster_model.weight = 10.0
        mock_monster_model.stage = "basic"
        mock_monster_model.randomly = False
        mock_monster_model.terrains = []
        mock_monster_model.types = []
        mock_monster_model.shape = "shape"
        mock_monster_model.tags = []
        mock_monster_model.catch_rate = 1.0
        mock_monster_model.gender_weights = {"male": 0.5, "female": 0.5}
        mock_monster_model.lower_catch_resistance = 1.0
        mock_monster_model.upper_catch_resistance = 1.0
        mock_monster_model.moveset = []
        mock_monster_model.history = []
        mock_monster_model.evolutions = []
        mock_monster_model.flairs = []
        mock_monster_model.max_moves = 4
        mock_monster_model.txmn_id = 1

        self.mock_lookup.return_value = mock_monster_model

        # Patch Monster.spawn_base to return a mock monster but with our egg attributes
        # We need a partial mock that calls real init or just sets what we need
        # Since Monster.__init__ is complex and depends on many things, let's just mock spawn_base completely
        # as we did before, but ensure it mimics the signature correctly.
        from tuxemon.monster.monster import Monster

        self.original_spawn_base = Monster.spawn_base

        def mock_spawn_base(slug, level, as_egg=False):
            m = MagicMock(spec=Monster)
            m.slug = slug
            m.name = "Hatchling"
            m.is_egg = as_egg
            m.hatch_steps = 2000 if as_egg else 0
            m.steps = 0
            m.status = None
            return m

        Monster.spawn_base = mock_spawn_base

    def tearDown(self):
        tuxemon.database.runtime.db._database = self.original_database
        self.lookup_patcher.stop()
        from tuxemon.monster.monster import Monster

        Monster.spawn_base = self.original_spawn_base

    def test_give_egg(self):
        from tuxemon.event.actions.give_egg import GiveEggAction

        action = GiveEggAction("hatchling", 100)
        action.start(self.session)

        self.assertEqual(len(self.session.player.monsters), 1)
        egg = self.session.player.monsters[0]
        self.assertTrue(egg.is_egg)
        self.assertEqual(egg.hatch_steps, 100)

    def test_egg_hatch_ready_condition(self):
        from tuxemon.event.conditions.egg_hatch_ready import (
            EggHatchReadyCondition,
        )
        from tuxemon.monster.monster import Monster

        monster = Monster.spawn_base("hatchling", 1, as_egg=True)
        monster.hatch_steps = 100
        self.session.player.monsters.append(monster)

        condition = EggHatchReadyCondition()
        self.assertFalse(condition.test(self.session, MagicMock()))

        monster.hatch_steps = 0
        self.assertTrue(condition.test(self.session, MagicMock()))

    def test_walking_decrements_steps(self):
        from tuxemon.monster.listener import monster_update_listener
        from tuxemon.monster.monster import Monster

        monster = Monster.spawn_base("hatchling", 1, as_egg=True)
        monster.hatch_steps = 100

        # monster_update_listener iterates list of monsters passed to it
        monster_update_listener(10, [monster], self.session)

        self.assertEqual(monster.hatch_steps, 90)
        self.assertEqual(monster.steps, 10)

    def test_hatch_egg_action(self):
        from tuxemon.event.actions.hatch_egg import HatchEggAction
        from tuxemon.monster.monster import Monster

        monster = Monster.spawn_base("hatchling", 1, as_egg=True)
        monster.hatch_steps = 0
        self.session.player.monsters.append(monster)

        action = HatchEggAction()
        action.start(self.session)

        self.assertFalse(monster.is_egg)
        self.assertEqual(monster.hatch_steps, 0)
        self.session.client.active_dialog.assert_not_called()  # Simplified check


if __name__ == "__main__":
    unittest.main()

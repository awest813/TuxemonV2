# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for combat state faint-handling logic.

Covers:
- handle_monster_defeat applies faint status when a monster first reaches 0 HP.
- handle_monster_defeat is idempotent: calling it again for an already-fainted
  monster is a no-op so experience is never awarded twice.
"""
import unittest
from unittest.mock import MagicMock

from tuxemon.states.combat_state import CombatState


def _make_combat_state() -> MagicMock:
    """Return a MagicMock that stands in for a CombatState instance."""
    combat_state = MagicMock()
    # remaining_players > 1 so play_outcome_music is not triggered
    combat_state.combat_session.remaining_players = [
        MagicMock(),
        MagicMock(),
    ]
    return combat_state


def _make_monster(is_fainted: bool) -> MagicMock:
    monster = MagicMock()
    monster.status.is_fainted = is_fainted
    return monster


class TestHandleMonsterDefeat(unittest.TestCase):

    def test_applies_faint_status_on_first_defeat(self):
        """handle_monster_defeat should apply faint status the first time."""
        combat_state = _make_combat_state()
        monster = _make_monster(is_fainted=False)

        CombatState.handle_monster_defeat(combat_state, monster)

        monster.status.apply_faint.assert_called_once_with(
            combat_state.session, monster
        )

    def test_removes_monster_actions_on_first_defeat(self):
        """handle_monster_defeat should remove queued actions for the monster."""
        combat_state = _make_combat_state()
        monster = _make_monster(is_fainted=False)

        CombatState.handle_monster_defeat(combat_state, monster)

        combat_state.remove_monster_actions_from_queue.assert_called_once_with(
            monster
        )

    def test_awards_experience_on_first_defeat(self):
        """handle_monster_defeat should award experience the first time."""
        combat_state = _make_combat_state()
        monster = _make_monster(is_fainted=False)

        CombatState.handle_monster_defeat(combat_state, monster)

        combat_state.award_experience_and_money.assert_called_once_with(
            monster
        )

    def test_skips_already_fainted_monster(self):
        """handle_monster_defeat must be a no-op if faint status is already set."""
        combat_state = _make_combat_state()
        monster = _make_monster(is_fainted=True)

        CombatState.handle_monster_defeat(combat_state, monster)

        monster.status.apply_faint.assert_not_called()
        combat_state.remove_monster_actions_from_queue.assert_not_called()
        combat_state.award_experience_and_money.assert_not_called()

    def test_second_call_is_idempotent(self):
        """Calling handle_monster_defeat twice must not double-award experience."""
        combat_state = _make_combat_state()
        monster = _make_monster(is_fainted=False)

        # First call: monster not yet fainted
        CombatState.handle_monster_defeat(combat_state, monster)

        # Simulate that apply_faint was called and the status is now set
        monster.status.is_fainted = True

        # Second call: should be a no-op
        CombatState.handle_monster_defeat(combat_state, monster)

        monster.status.apply_faint.assert_called_once()
        combat_state.award_experience_and_money.assert_called_once()

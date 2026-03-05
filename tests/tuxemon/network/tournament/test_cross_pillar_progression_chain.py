# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Deterministic cross-pillar progression integration tests.

These tests cover campaign -> battle center -> tournament handoffs and
save/load continuity for post-credits progression state.
"""

from __future__ import annotations

import json

from tuxemon.network.tournament.models import Participant, Tournament, TournamentState
from tuxemon.network.tournament.persistence import load_tournament, save_tournament
from tuxemon.world.milestone_tracker import (
    PostgameMilestoneTracker,
    TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS,
)


def _battle_center_access_unlocked(tracker: PostgameMilestoneTracker) -> bool:
    """Campaign gate for battle-center access in post-credits progression."""
    return tracker.is_achieved("story_complete")


def _tournament_access_unlocked(tracker: PostgameMilestoneTracker) -> bool:
    """Combined campaign + post-credits gate for tournament participation."""
    return _battle_center_access_unlocked(tracker) and tracker.tournament_unlocked


def test_story_progression_unlocks_battle_center_access() -> None:
    tracker = PostgameMilestoneTracker(player_id="player_story")

    assert _battle_center_access_unlocked(tracker) is False

    # Post-credits battle-center progression must reject pre-story entries.
    assert tracker.record_battle_center_match(won=True) is False
    assert tracker.battle_center_matches == 0

    # Finishing the story opens battle-center progression.
    tracker.record_story_complete()
    assert _battle_center_access_unlocked(tracker) is True
    assert tracker.record_battle_center_match(won=False) is True
    assert tracker.battle_center_matches == 1


def test_battle_center_outcomes_unlock_tournament_progression() -> None:
    tracker = PostgameMilestoneTracker(player_id="player_battle")
    tracker.record_story_complete()

    outcomes = [True, False, True, True]
    for won in outcomes:
        assert tracker.record_battle_center_match(won=won) is True

    assert tracker.battle_center_matches == len(outcomes)
    assert tracker.battle_center_wins == 3
    assert tracker.tournament_unlocked is True


def test_tournament_participation_respects_campaign_and_postcredits_gates() -> None:
    tracker = PostgameMilestoneTracker(player_id="player_gate")
    tournament = Tournament(id="gate-tournament", name="Gate Cup")
    tournament.transition(TournamentState.REGISTRATION)

    # Locked before story completion.
    assert _tournament_access_unlocked(tracker) is False

    tracker.record_story_complete()
    for _ in range(TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS - 1):
        assert tracker.record_battle_center_match(won=True) is True
    assert _tournament_access_unlocked(tracker) is False

    # Unlocks only after the post-credits win threshold is reached.
    assert tracker.record_battle_center_match(won=True) is True
    assert _tournament_access_unlocked(tracker) is True

    tournament.participants[tracker.player_id] = Participant(
        id=tracker.player_id,
        name="Gated Player",
        registered_at=1.0,
        checked_in=True,
    )
    assert tracker.player_id in tournament.participants


def test_save_load_preserves_cross_pillar_progression_chain(tmp_path) -> None:
    tracker = PostgameMilestoneTracker(player_id="player_save")
    tracker.record_story_complete()
    for _ in range(TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS - 1):
        assert tracker.record_battle_center_match(won=True) is True

    # Save and load tracker state before threshold: tournament still locked.
    tracker_state_path = tmp_path / "tracker_state.json"
    tracker_state_path.write_text(json.dumps(tracker.encode()), encoding="utf-8")

    tracker_loaded = PostgameMilestoneTracker(player_id="player_save")
    tracker_loaded.decode(json.loads(tracker_state_path.read_text(encoding="utf-8")))
    assert tracker_loaded.tournament_unlocked is False

    # Continue progression after load, then save/load tournament payload too.
    assert tracker_loaded.record_battle_center_match(won=True) is True
    assert tracker_loaded.tournament_unlocked is True

    tournament = Tournament(id="persist-tournament", name="Persistence Cup")
    tournament.transition(TournamentState.REGISTRATION)
    tournament.participants[tracker_loaded.player_id] = Participant(
        id=tracker_loaded.player_id,
        name="Persistent Player",
        registered_at=10.0,
        checked_in=True,
    )

    tournament_path = tmp_path / "persist_tournament.json"
    save_tournament(tournament, tournament_path)

    reloaded_tournament = load_tournament(tournament_path)
    assert reloaded_tournament is not None
    assert tracker_loaded.player_id in reloaded_tournament.participants

    # Final save/load round-trip keeps tournament gate and milestone continuity.
    tracker_roundtrip = PostgameMilestoneTracker(player_id="player_save")
    tracker_roundtrip.decode(tracker_loaded.encode())
    assert _tournament_access_unlocked(tracker_roundtrip) is True
    assert tracker_roundtrip.record_tournament_win() is True
    assert tracker_roundtrip.is_achieved("champion_challenger") is True

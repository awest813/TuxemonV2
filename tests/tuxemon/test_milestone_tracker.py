# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for PostgameMilestoneTracker — Hook 4.9 integration.

Covers the milestone tier structure defined in
docs/gold_silver_blueprint.md §5.
"""

from __future__ import annotations

import pytest

from tuxemon.time_hooks import PostgameMilestonePayload, hooks
from tuxemon.world.milestone_tracker import (
    BATTLER_THRESHOLD,
    COMPLETIONIST_DEX_PERCENT,
    PostgameMilestoneTracker,
    TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS,
)


@pytest.fixture(autouse=True)
def clear_hooks():
    hooks.clear()
    yield
    hooks.clear()


@pytest.fixture
def tracker() -> PostgameMilestoneTracker:
    return PostgameMilestoneTracker(player_id="test_player")


# ---------------------------------------------------------------------------
# Tier 0 — story_complete
# ---------------------------------------------------------------------------


def test_story_complete_fires_hook(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_story_complete()

    assert len(fired) == 1
    assert fired[0].milestone_id == "story_complete"
    assert fired[0].player_id == "test_player"


def test_story_complete_only_fires_once(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_story_complete()
    tracker.record_story_complete()

    assert len(fired) == 1


def test_story_complete_is_achieved(tracker: PostgameMilestoneTracker):
    tracker.record_story_complete()
    assert tracker.is_achieved("story_complete") is True


# ---------------------------------------------------------------------------
# Tier 1 — returner (first rematch win)
# ---------------------------------------------------------------------------


def test_returner_fires_on_first_rematch_win(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_rematch_win()

    returner_events = [p for p in fired if p.milestone_id == "returner"]
    assert len(returner_events) == 1


def test_returner_only_fires_once(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_rematch_win()
    tracker.record_rematch_win()

    returner_events = [p for p in fired if p.milestone_id == "returner"]
    assert len(returner_events) == 1


# ---------------------------------------------------------------------------
# Tier 2 — battler (BATTLER_THRESHOLD cumulative rematch wins)
# ---------------------------------------------------------------------------


def test_battler_not_fired_before_threshold(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    for _ in range(BATTLER_THRESHOLD - 1):
        tracker.record_rematch_win()

    battler_events = [p for p in fired if p.milestone_id == "battler"]
    assert battler_events == []


def test_battler_fires_at_threshold(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    for _ in range(BATTLER_THRESHOLD):
        tracker.record_rematch_win()

    battler_events = [p for p in fired if p.milestone_id == "battler"]
    assert len(battler_events) == 1


def test_battler_only_fires_once(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    for _ in range(BATTLER_THRESHOLD + 5):
        tracker.record_rematch_win()

    battler_events = [p for p in fired if p.milestone_id == "battler"]
    assert len(battler_events) == 1


def test_total_rematch_wins_tracked(tracker: PostgameMilestoneTracker):
    tracker.record_rematch_win()
    tracker.record_rematch_win()
    assert tracker.total_rematch_wins == 2


# ---------------------------------------------------------------------------
# Tier 3 — champion_challenger
# ---------------------------------------------------------------------------


def _unlock_tournament_path(tracker: PostgameMilestoneTracker) -> None:
    tracker.record_story_complete()
    for _ in range(TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS):
        tracker.record_battle_center_match(won=True)


def test_tournament_path_stays_locked_before_story_complete(
    tracker: PostgameMilestoneTracker,
):
    accepted = tracker.record_battle_center_match(won=True)
    assert accepted is False
    assert tracker.tournament_unlocked is False


def test_tournament_unlocks_after_battle_center_wins(
    tracker: PostgameMilestoneTracker,
):
    tracker.record_story_complete()
    for _ in range(TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS - 1):
        tracker.record_battle_center_match(won=True)
    assert tracker.tournament_unlocked is False

    tracker.record_battle_center_match(won=True)
    assert tracker.tournament_unlocked is True


def test_tournament_milestone_blocked_until_unlocked(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    accepted = tracker.record_tournament_win()
    assert accepted is False
    assert [p for p in fired if p.milestone_id == "champion_challenger"] == []


def test_champion_challenger_fires_on_tournament_win(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    _unlock_tournament_path(tracker)
    tracker.record_tournament_win()

    cc_events = [p for p in fired if p.milestone_id == "champion_challenger"]
    assert len(cc_events) == 1


def test_champion_challenger_fires_on_ladder_threshold(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    _unlock_tournament_path(tracker)
    tracker.record_ladder_threshold()

    cc_events = [p for p in fired if p.milestone_id == "champion_challenger"]
    assert len(cc_events) == 1


def test_champion_challenger_fires_only_once_across_paths(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    _unlock_tournament_path(tracker)
    tracker.record_tournament_win()
    tracker.record_ladder_threshold()

    cc_events = [p for p in fired if p.milestone_id == "champion_challenger"]
    assert len(cc_events) == 1


# ---------------------------------------------------------------------------
# Tier 4 — completionist
# ---------------------------------------------------------------------------


def test_completionist_not_fired_below_threshold(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_dex_completion(COMPLETIONIST_DEX_PERCENT - 1)

    co_events = [p for p in fired if p.milestone_id == "completionist"]
    assert co_events == []


def test_completionist_fires_at_threshold(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_dex_completion(COMPLETIONIST_DEX_PERCENT)

    co_events = [p for p in fired if p.milestone_id == "completionist"]
    assert len(co_events) == 1


def test_completionist_fires_above_threshold(
    tracker: PostgameMilestoneTracker,
):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_dex_completion(100.0)

    co_events = [p for p in fired if p.milestone_id == "completionist"]
    assert len(co_events) == 1


def test_dex_completion_pct_stored(tracker: PostgameMilestoneTracker):
    tracker.record_dex_completion(75.5)
    assert tracker.dex_completion_pct == 75.5


# ---------------------------------------------------------------------------
# Tier 5 — grand_champion
# ---------------------------------------------------------------------------


def test_grand_champion_fires(tracker: PostgameMilestoneTracker):
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker.record_battle_tower_cleared()

    gc_events = [p for p in fired if p.milestone_id == "grand_champion"]
    assert len(gc_events) == 1


# ---------------------------------------------------------------------------
# encode / decode round-trip
# ---------------------------------------------------------------------------


def test_encode_decode_round_trip(tracker: PostgameMilestoneTracker):
    tracker.record_story_complete()
    for _ in range(BATTLER_THRESHOLD):
        tracker.record_rematch_win()
    for _ in range(TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS):
        tracker.record_battle_center_match(won=True)

    data = tracker.encode()

    tracker2 = PostgameMilestoneTracker(player_id="test_player")
    tracker2.decode(data)

    assert tracker2.is_achieved("story_complete")
    assert tracker2.is_achieved("returner")
    assert tracker2.is_achieved("battler")
    assert tracker2.total_rematch_wins == BATTLER_THRESHOLD
    assert tracker2.tournament_unlocked is True


def test_decode_empty_dict_gives_clean_state(
    tracker: PostgameMilestoneTracker,
):
    tracker.record_story_complete()
    tracker.decode({})
    assert not tracker.is_achieved("story_complete")
    assert tracker.total_rematch_wins == 0


def test_decode_does_not_re_fire_hooks():
    fired: list[PostgameMilestonePayload] = []
    hooks.on_postgame_milestone_reached(fired.append)

    tracker = PostgameMilestoneTracker(player_id="p")
    tracker.decode(
        {"achieved": ["story_complete", "returner"], "total_rematch_wins": 1}
    )

    assert fired == [], "decode() must not re-fire already-achieved milestones"


def test_is_achieved_false_for_unknown_milestone(
    tracker: PostgameMilestoneTracker,
):
    assert tracker.is_achieved("nonexistent") is False

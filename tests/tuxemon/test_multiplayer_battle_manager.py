# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tuxemon.multiplayer_battle_manager import (
    BattleResolution,
    BattleChallengeResult,
    MultiplayerBattleManager,
)


def test_propose_and_fetch_challenges() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()

    result = manager.propose_challenge(challenger, challenged)

    assert result == BattleChallengeResult.SUCCESS
    pending = manager.get_pending_challenges_for_player(challenger)
    assert len(pending) == 1
    assert pending[0].challenged_player_id == challenged
    assert manager.get_received_challenges_for_player(challenged) == pending


def test_reject_self_challenge_and_duplicate() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()

    assert (
        manager.propose_challenge(challenger, challenger)
        == BattleChallengeResult.SELF_CHALLENGE
    )
    assert manager.propose_challenge(challenger, challenged) == (
        BattleChallengeResult.SUCCESS
    )
    assert manager.propose_challenge(challenger, challenged) == (
        BattleChallengeResult.DUPLICATE
    )


def test_cancel_challenge_requires_participant() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    stranger = uuid4()
    manager.propose_challenge(challenger, challenged)
    challenge = manager.pending_challenges[0]

    assert (
        manager.cancel_challenge(
            challenge.challenge_id, requesting_player_id=stranger
        )
        == BattleChallengeResult.UNAUTHORIZED
    )
    assert manager.pending_challenges == [challenge]

    assert (
        manager.cancel_challenge(
            challenge.challenge_id,
            requesting_player_id=challenged,
        )
        == BattleChallengeResult.SUCCESS
    )
    assert manager.pending_challenges == []


def test_accept_reject_and_expired_challenge() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    manager.propose_challenge(challenger, challenged)
    challenge = manager.pending_challenges[0]

    assert (
        manager.accept_challenge(
            challenge.challenge_id, accepting_player_id=challenger
        )
        == BattleChallengeResult.UNAUTHORIZED
    )

    challenge.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    assert (
        manager.accept_challenge(
            challenge.challenge_id, accepting_player_id=challenged
        )
        == BattleChallengeResult.EXPIRED
    )

    manager.propose_challenge(challenger, challenged)
    challenge = manager.pending_challenges[0]
    assert (
        manager.reject_challenge(
            challenge.challenge_id, rejecting_player_id=challenged
        )
        == BattleChallengeResult.REJECTED
    )

    history = manager.get_battle_history_for_player(challenged)
    assert [record.resolution for record in history] == [
        BattleResolution.EXPIRED,
        BattleResolution.REJECTED,
    ]


def test_cancel_adds_history_and_limit_is_enforced() -> None:
    manager = MultiplayerBattleManager()
    manager.max_battle_history_entries = 2
    challenger = uuid4()
    challenged = uuid4()

    manager.propose_challenge(challenger, challenged)
    first = manager.pending_challenges[0]
    manager.cancel_challenge(first.challenge_id, requesting_player_id=challenger)

    manager.propose_challenge(challenger, challenged)
    second = manager.pending_challenges[0]
    manager.reject_challenge(second.challenge_id, rejecting_player_id=challenged)

    manager.propose_challenge(challenger, challenged)
    third = manager.pending_challenges[0]
    manager.accept_challenge(third.challenge_id, accepting_player_id=challenged)

    assert [record.challenge_id for record in manager.battle_history] == [
        second.challenge_id,
        third.challenge_id,
    ]


def test_save_and_load_log_purges_expired() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    manager.default_challenge_ttl_seconds = 45

    manager.propose_challenge(challenger, challenged)
    active = manager.pending_challenges[0]
    manager.reject_challenge(active.challenge_id, rejecting_player_id=challenged)
    manager.propose_challenge(challenger, challenged)
    active = manager.pending_challenges[0]
    expired = active.to_dict() | {
        "challenge_id": str(uuid4()),
        "timestamp": (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat(),
    }

    serialized = manager.save_log()
    serialized["pending_challenges"].append(expired)

    restored = MultiplayerBattleManager()
    restored.load_log(serialized)

    assert restored.default_challenge_ttl_seconds == 45
    assert restored.battle_history[0].resolution == BattleResolution.REJECTED
    assert len(restored.pending_challenges) == 1
    assert restored.pending_challenges[0].challenge_id == active.challenge_id


def test_load_log_completed_battles_compat_and_malformed_entries() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    manager.propose_challenge(challenger, challenged)
    challenge = manager.pending_challenges[0]

    manager.load_log(
        {
            "pending_challenges": [],
            "completed_battles": [
                {
                    "challenge_id": str(challenge.challenge_id),
                    "challenger_player_id": str(challenger),
                    "challenged_player_id": str(challenged),
                    "resolution": BattleResolution.ACCEPTED.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                {"bad": "data"},
                "not-a-record",
            ],
        }
    )

    assert len(manager.battle_history) == 1
    assert manager.battle_history[0].resolution == BattleResolution.ACCEPTED

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tuxemon.multiplayer_battle_manager import (
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


def test_save_and_load_log_purges_expired() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    manager.default_challenge_ttl_seconds = 45

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
    assert len(restored.pending_challenges) == 1
    assert restored.pending_challenges[0].challenge_id == active.challenge_id

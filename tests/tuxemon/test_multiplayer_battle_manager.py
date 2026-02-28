# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tuxemon.multiplayer_battle_manager import (
    BattleResolution,
    BattleChallengeResult,
    MultiplayerBattleManager,
    OnlineActionState,
    TurnSubmissionResult,
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


def test_accept_creates_active_battle_session() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()

    manager.propose_challenge(challenger, challenged)
    challenge = manager.pending_challenges[0]

    result = manager.accept_challenge(
        challenge.challenge_id, accepting_player_id=challenged
    )

    assert result == BattleChallengeResult.SUCCESS
    assert len(manager.active_battle_sessions) == 1
    battle_session = manager.active_battle_sessions[0]
    assert battle_session.challenge_id == challenge.challenge_id
    assert battle_session.challenger_player_id == challenger
    assert battle_session.challenged_player_id == challenged
    assert (
        manager.get_active_battle_session_for_challenge(
            challenge.challenge_id
        )
        == battle_session
    )


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


def test_load_log_skips_malformed_pending_challenges() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    valid_pending = {
        "challenger_player_id": str(challenger),
        "challenged_player_id": str(challenged),
        "challenge_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=1)
        ).isoformat(),
    }

    manager.load_log(
        {
            "pending_challenges": [
                valid_pending,
                {"challenge_id": "invalid"},
                "not-a-challenge",
            ],
        }
    )

    assert len(manager.pending_challenges) == 1
    assert manager.pending_challenges[0].challenge_id.hex == valid_pending["challenge_id"].replace("-", "")


def test_turn_submission_synchronizes_and_increments_turn() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    challenge_id = uuid4()

    battle_session = manager.start_battle_session(
        challenge_id, challenger, challenged
    )

    assert (
        manager.submit_turn_action(
            battle_session.session_id,
            challenger,
            turn=1,
            action={"move": "scratch", "priority": 1, "speed": 10},
        )
        == TurnSubmissionResult.WAITING
    )
    assert (
        manager.submit_turn_action(
            battle_session.session_id,
            challenged,
            turn=1,
            action={"move": "tackle", "priority": 1, "speed": 20},
        )
        == TurnSubmissionResult.SUCCESS
    )
    assert battle_session.current_turn == 2
    assert battle_session.turn_actions == {}


def test_turn_resolution_is_authoritative_and_deterministic() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    battle_session = manager.start_battle_session(uuid4(), challenger, challenged)

    manager.submit_turn_action(
        battle_session.session_id,
        challenger,
        turn=1,
        action={"move": "slow", "priority": 0, "speed": 10},
    )
    events: list[dict[str, object]] = []
    manager.event_bus.subscribe(
        "multiplayer_battle_turn_resolved", lambda payload: events.append(payload)
    )

    manager.submit_turn_action(
        battle_session.session_id,
        challenged,
        turn=1,
        action={"move": "fast", "priority": 1, "speed": 50},
    )

    assert events
    resolved_actions = events[0]["actions"]
    assert resolved_actions[0]["action"]["move"] == "fast"
    assert resolved_actions[1]["action"]["move"] == "slow"
    assert events[0]["conflict_policy"]["authoritative"] == "server"


def test_turn_submission_rejects_wrong_player_turn_and_duplicates() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    battle_session = manager.start_battle_session(uuid4(), challenger, challenged)

    assert (
        manager.submit_turn_action(
            battle_session.session_id,
            uuid4(),
            turn=1,
            action={"move": "scratch"},
        )
        == TurnSubmissionResult.UNAUTHORIZED
    )
    assert (
        manager.submit_turn_action(
            battle_session.session_id,
            challenger,
            turn=2,
            action={"move": "scratch"},
        )
        == TurnSubmissionResult.TURN_MISMATCH
    )
    assert (
        manager.submit_turn_action(
            battle_session.session_id,
            challenger,
            turn=1,
            action={"move": "scratch"},
        )
        == TurnSubmissionResult.WAITING
    )
    assert (
        manager.submit_turn_action(
            battle_session.session_id,
            challenger,
            turn=1,
            action={"move": "growl"},
        )
        == TurnSubmissionResult.DUPLICATE
    )


def test_save_load_and_purge_stale_battle_sessions() -> None:
    manager = MultiplayerBattleManager()
    manager.default_turn_timeout_seconds = 120
    manager.default_reconnect_grace_seconds = 15
    challenger = uuid4()
    challenged = uuid4()
    session = manager.start_battle_session(uuid4(), challenger, challenged)

    manager.set_player_connection_state(
        session.session_id,
        challenger,
        connected=False,
        now=datetime.now(timezone.utc) - timedelta(seconds=30),
    )
    removed = manager.purge_stale_battle_sessions(now=datetime.now(timezone.utc))
    assert removed == 1
    assert manager.active_battle_sessions == []

    manager.start_battle_session(uuid4(), challenger, challenged)
    serialized = manager.save_log()

    restored = MultiplayerBattleManager()
    restored.load_log(serialized)

    assert restored.default_turn_timeout_seconds == 120
    assert restored.default_reconnect_grace_seconds == 15
    assert len(restored.active_battle_sessions) == 1


def test_get_challenge_feedback_for_pending_and_unauthorized() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    stranger = uuid4()
    manager.propose_challenge(challenger, challenged)
    challenge = manager.pending_challenges[0]

    feedback = manager.get_challenge_feedback(challenge.challenge_id, challenger)
    assert feedback.state == OnlineActionState.PENDING
    assert feedback.retryable is False
    assert "pending" in feedback.message.lower()

    unauthorized = manager.get_challenge_feedback(
        challenge.challenge_id, stranger
    )
    assert unauthorized.state == OnlineActionState.FAILED
    assert unauthorized.retryable is False


def test_get_challenge_feedback_for_history_and_missing() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()

    manager.propose_challenge(challenger, challenged)
    accepted = manager.pending_challenges[0]
    manager.accept_challenge(
        accepted.challenge_id, accepting_player_id=challenged
    )
    accepted_feedback = manager.get_challenge_feedback(
        accepted.challenge_id, challenger
    )
    assert accepted_feedback.state == OnlineActionState.ACCEPTED
    assert accepted_feedback.retryable is False

    manager.propose_challenge(challenger, challenged)
    expired = manager.pending_challenges[0]
    expired.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    manager.accept_challenge(
        expired.challenge_id, accepting_player_id=challenged
    )
    expired_feedback = manager.get_challenge_feedback(
        expired.challenge_id, challenger
    )
    assert expired_feedback.state == OnlineActionState.EXPIRED
    assert expired_feedback.retryable is True

    missing_feedback = manager.get_challenge_feedback(uuid4(), challenger)
    assert missing_feedback.state == OnlineActionState.NOT_FOUND
    assert missing_feedback.retryable is True


def test_get_turn_submission_feedback_messages() -> None:
    manager = MultiplayerBattleManager()

    success = manager.get_turn_submission_feedback(TurnSubmissionResult.SUCCESS)
    assert success.state == OnlineActionState.ACCEPTED
    assert success.retryable is False

    waiting = manager.get_turn_submission_feedback(TurnSubmissionResult.WAITING)
    assert waiting.state == OnlineActionState.PENDING
    assert waiting.retryable is False

    not_found = manager.get_turn_submission_feedback(
        TurnSubmissionResult.NOT_FOUND
    )
    assert not_found.state == OnlineActionState.NOT_FOUND
    assert not_found.retryable is True

    expired = manager.get_turn_submission_feedback(TurnSubmissionResult.EXPIRED)
    assert expired.state == OnlineActionState.EXPIRED
    assert expired.retryable is True

    mismatch = manager.get_turn_submission_feedback(
        TurnSubmissionResult.TURN_MISMATCH
    )
    assert mismatch.state == OnlineActionState.FAILED
    assert mismatch.retryable is True

    duplicate = manager.get_turn_submission_feedback(
        TurnSubmissionResult.DUPLICATE
    )
    assert duplicate.state == OnlineActionState.FAILED
    assert duplicate.retryable is False

    unauthorized = manager.get_turn_submission_feedback(
        TurnSubmissionResult.UNAUTHORIZED
    )
    assert unauthorized.state == OnlineActionState.FAILED
    assert unauthorized.retryable is False


def test_get_challenge_action_feedback_messages() -> None:
    manager = MultiplayerBattleManager()

    proposed = manager.get_challenge_action_feedback(
        BattleChallengeResult.SUCCESS,
        action="propose",
    )
    assert proposed.state == OnlineActionState.PENDING
    assert proposed.retryable is False

    accepted = manager.get_challenge_action_feedback(
        BattleChallengeResult.SUCCESS,
        action="accept",
    )
    assert accepted.state == OnlineActionState.ACCEPTED
    assert accepted.retryable is False

    cancelled = manager.get_challenge_action_feedback(
        BattleChallengeResult.SUCCESS,
        action="cancel",
    )
    assert cancelled.state == OnlineActionState.CANCELLED
    assert cancelled.retryable is False

    rejected = manager.get_challenge_action_feedback(
        BattleChallengeResult.REJECTED,
        action="reject",
    )
    assert rejected.state == OnlineActionState.REJECTED
    assert rejected.retryable is True

    duplicate = manager.get_challenge_action_feedback(
        BattleChallengeResult.DUPLICATE,
        action="propose",
    )
    assert duplicate.state == OnlineActionState.FAILED
    assert duplicate.retryable is False

    missing = manager.get_challenge_action_feedback(
        BattleChallengeResult.NOT_FOUND,
        action="cancel",
    )
    assert missing.state == OnlineActionState.NOT_FOUND
    assert missing.retryable is True


def test_get_battle_session_feedback_states() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    stranger = uuid4()
    battle_session = manager.start_battle_session(uuid4(), challenger, challenged)

    active_feedback = manager.get_battle_session_feedback(
        battle_session.session_id, challenger
    )
    assert active_feedback.state == OnlineActionState.PENDING
    assert active_feedback.retryable is False
    assert "submit your action" in active_feedback.message.lower()

    manager.submit_turn_action(
        battle_session.session_id,
        challenger,
        turn=1,
        action={"move": "scratch"},
    )
    waiting_feedback = manager.get_battle_session_feedback(
        battle_session.session_id, challenger
    )
    assert waiting_feedback.state == OnlineActionState.PENDING
    assert waiting_feedback.retryable is False
    assert "waiting for the other player" in waiting_feedback.message.lower()

    unauthorized = manager.get_battle_session_feedback(
        battle_session.session_id, stranger
    )
    assert unauthorized.state == OnlineActionState.FAILED
    assert unauthorized.retryable is False

    missing = manager.get_battle_session_feedback(uuid4(), challenger)
    assert missing.state == OnlineActionState.NOT_FOUND
    assert missing.retryable is True


def test_get_battle_session_feedback_connection_and_timeout() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    battle_session = manager.start_battle_session(uuid4(), challenger, challenged)

    disconnect_now = datetime.now(timezone.utc)
    manager.set_player_connection_state(
        battle_session.session_id,
        challenged,
        connected=False,
        now=disconnect_now,
    )

    waiting_reconnect = manager.get_battle_session_feedback(
        battle_session.session_id,
        challenger,
        now=disconnect_now + timedelta(seconds=5),
    )
    assert waiting_reconnect.state == OnlineActionState.PENDING
    assert waiting_reconnect.retryable is False
    assert "reconnect" in waiting_reconnect.message.lower()

    expired_reconnect = manager.get_battle_session_feedback(
        battle_session.session_id,
        challenger,
        now=disconnect_now
        + timedelta(seconds=battle_session.reconnect_grace_seconds + 1),
    )
    assert expired_reconnect.state == OnlineActionState.EXPIRED
    assert expired_reconnect.retryable is True

    timeout_session = manager.start_battle_session(uuid4(), challenger, challenged)
    timeout_session.last_activity_at = datetime.now(timezone.utc) - timedelta(
        seconds=timeout_session.turn_timeout_seconds + 1
    )
    timed_out_feedback = manager.get_battle_session_feedback(
        timeout_session.session_id,
        challenger,
    )
    assert timed_out_feedback.state == OnlineActionState.EXPIRED
    assert timed_out_feedback.retryable is True


def test_turn_submission_rejects_expired_battle_session() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    battle_session = manager.start_battle_session(uuid4(), challenger, challenged)
    battle_session.last_activity_at = datetime.now(timezone.utc) - timedelta(
        seconds=battle_session.turn_timeout_seconds + 1
    )

    result = manager.submit_turn_action(
        battle_session.session_id,
        challenger,
        turn=1,
        action={"move": "scratch"},
    )

    assert result == TurnSubmissionResult.EXPIRED


def test_load_log_normalizes_active_battle_sessions() -> None:
    manager = MultiplayerBattleManager()
    challenger = uuid4()
    challenged = uuid4()
    valid = manager.start_battle_session(uuid4(), challenger, challenged)
    stale = manager.start_battle_session(uuid4(), challenger, challenged)
    stale.last_activity_at = datetime.now(timezone.utc) - timedelta(
        seconds=stale.turn_timeout_seconds + 1
    )

    serialized = manager.save_log()
    raw_valid = serialized["active_battle_sessions"][0]
    raw_stale = serialized["active_battle_sessions"][1]
    # invalid turn action owner is dropped during normalization
    raw_valid["turn_actions"] = {
        str(uuid4()): {
            "player_id": str(uuid4()),
            "turn": raw_valid["current_turn"],
            "action": {"move": "hack"},
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    serialized["active_battle_sessions"] = [raw_valid, raw_stale]

    restored = MultiplayerBattleManager()
    restored.load_log(serialized)

    assert len(restored.active_battle_sessions) == 1
    restored_valid = restored.active_battle_sessions[0]
    assert restored_valid.challenge_id == valid.challenge_id
    assert restored_valid.turn_actions == {}

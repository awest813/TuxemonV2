# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from tuxemon.event import get_event_bus


def _coerce_utc_timestamp(value: str) -> datetime:
    """Parse timestamp strings and normalize to timezone-aware UTC."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class BattleChallengeResult(Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    EXPIRED = "expired"
    UNAUTHORIZED = "unauthorized"
    SELF_CHALLENGE = "self_challenge"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class BattleResolution(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TurnSubmissionResult(Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    TURN_MISMATCH = "turn_mismatch"
    DUPLICATE = "duplicate"
    WAITING = "waiting"


class OnlineActionState(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"
    NOT_FOUND = "not_found"


@dataclass
class OnlineActionFeedback:
    state: OnlineActionState
    message: str
    retryable: bool


@dataclass
class BattleChallenge:
    challenger_player_id: UUID
    challenged_player_id: UUID
    challenge_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "challenger_player_id": str(self.challenger_player_id),
            "challenged_player_id": str(self.challenged_player_id),
            "challenge_id": str(self.challenge_id),
            "timestamp": self.timestamp.isoformat(),
            "expires_at": (
                self.expires_at.isoformat()
                if self.expires_at is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, str | None]) -> BattleChallenge:
        expires_raw = data.get("expires_at")
        return cls(
            challenger_player_id=UUID(str(data["challenger_player_id"])),
            challenged_player_id=UUID(str(data["challenged_player_id"])),
            challenge_id=UUID(str(data["challenge_id"])),
            timestamp=_coerce_utc_timestamp(str(data["timestamp"])),
            expires_at=(
                _coerce_utc_timestamp(expires_raw)
                if isinstance(expires_raw, str)
                else None
            ),
        )


@dataclass
class BattleRecord:
    challenge_id: UUID
    challenger_player_id: UUID
    challenged_player_id: UUID
    resolution: BattleResolution
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, str]:
        return {
            "challenge_id": str(self.challenge_id),
            "challenger_player_id": str(self.challenger_player_id),
            "challenged_player_id": str(self.challenged_player_id),
            "resolution": self.resolution.value,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, str]) -> BattleRecord:
        return cls(
            challenge_id=UUID(data["challenge_id"]),
            challenger_player_id=UUID(data["challenger_player_id"]),
            challenged_player_id=UUID(data["challenged_player_id"]),
            resolution=BattleResolution(data["resolution"]),
            timestamp=_coerce_utc_timestamp(data["timestamp"]),
        )


@dataclass
class BattleTurnAction:
    player_id: UUID
    turn: int
    action: dict[str, Any]
    submitted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": str(self.player_id),
            "turn": self.turn,
            "action": self.action,
            "submitted_at": self.submitted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BattleTurnAction:
        return cls(
            player_id=UUID(str(data["player_id"])),
            turn=int(data["turn"]),
            action=dict(data["action"]),
            submitted_at=_coerce_utc_timestamp(str(data["submitted_at"])),
        )


@dataclass
class ActiveBattleSession:
    challenge_id: UUID
    challenger_player_id: UUID
    challenged_player_id: UUID
    session_id: UUID = field(default_factory=uuid4)
    current_turn: int = 1
    turn_timeout_seconds: int = 60
    reconnect_grace_seconds: int = 30
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    disconnected_at: dict[str, str | None] = field(default_factory=dict)
    turn_actions: dict[str, BattleTurnAction] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge_id": str(self.challenge_id),
            "challenger_player_id": str(self.challenger_player_id),
            "challenged_player_id": str(self.challenged_player_id),
            "session_id": str(self.session_id),
            "current_turn": self.current_turn,
            "turn_timeout_seconds": self.turn_timeout_seconds,
            "reconnect_grace_seconds": self.reconnect_grace_seconds,
            "created_at": self.created_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "disconnected_at": self.disconnected_at,
            "turn_actions": {
                player_id: action.to_dict()
                for player_id, action in self.turn_actions.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ActiveBattleSession:
        turn_actions: dict[str, BattleTurnAction] = {}
        raw_actions = data.get("turn_actions", {})
        if isinstance(raw_actions, Mapping):
            for player_id, raw_action in raw_actions.items():
                if isinstance(raw_action, Mapping):
                    turn_actions[str(player_id)] = BattleTurnAction.from_dict(
                        raw_action
                    )

        disconnected_at: dict[str, str | None] = {}
        raw_disconnected = data.get("disconnected_at", {})
        if isinstance(raw_disconnected, Mapping):
            for player_id, timestamp in raw_disconnected.items():
                if timestamp is None or isinstance(timestamp, str):
                    disconnected_at[str(player_id)] = timestamp

        return cls(
            challenge_id=UUID(str(data["challenge_id"])),
            challenger_player_id=UUID(str(data["challenger_player_id"])),
            challenged_player_id=UUID(str(data["challenged_player_id"])),
            session_id=UUID(str(data["session_id"])),
            current_turn=int(data.get("current_turn", 1)),
            turn_timeout_seconds=int(data.get("turn_timeout_seconds", 60)),
            reconnect_grace_seconds=int(data.get("reconnect_grace_seconds", 30)),
            created_at=_coerce_utc_timestamp(str(data["created_at"])),
            last_activity_at=_coerce_utc_timestamp(str(data["last_activity_at"])),
            disconnected_at=disconnected_at,
            turn_actions=turn_actions,
        )


class MultiplayerBattleManager:
    """Tracks and resolves online battle challenges between players."""

    def __init__(self) -> None:
        self.pending_challenges: list[BattleChallenge] = []
        self.battle_history: list[BattleRecord] = []
        self.max_battle_history_entries = 100
        self.default_challenge_ttl_seconds = 180
        self.active_battle_sessions: list[ActiveBattleSession] = []
        self.default_turn_timeout_seconds = 60
        self.default_reconnect_grace_seconds = 30
        self.event_bus = get_event_bus()

    def _find_battle_session(
        self, session_id: UUID
    ) -> ActiveBattleSession | None:
        return next(
            (
                battle_session
                for battle_session in self.active_battle_sessions
                if battle_session.session_id == session_id
            ),
            None,
        )

    def purge_stale_battle_sessions(self, now: datetime | None = None) -> int:
        current_time = now or datetime.now(timezone.utc)
        active_sessions = []
        removed = 0

        for battle_session in self.active_battle_sessions:
            timed_out = (
                current_time
                > battle_session.last_activity_at
                + timedelta(seconds=battle_session.turn_timeout_seconds)
            )
            disconnected_timed_out = False
            for timestamp in battle_session.disconnected_at.values():
                if timestamp is None:
                    continue
                disconnected_time = _coerce_utc_timestamp(timestamp)
                if current_time > disconnected_time + timedelta(
                    seconds=battle_session.reconnect_grace_seconds
                ):
                    disconnected_timed_out = True
                    break

            if timed_out or disconnected_timed_out:
                removed += 1
                self.event_bus.publish("multiplayer_battle_session_expired", battle_session)
                continue

            active_sessions.append(battle_session)

        self.active_battle_sessions = active_sessions
        return removed

    def start_battle_session(
        self,
        challenge_id: UUID,
        challenger_player_id: UUID,
        challenged_player_id: UUID,
    ) -> ActiveBattleSession:
        session = ActiveBattleSession(
            challenge_id=challenge_id,
            challenger_player_id=challenger_player_id,
            challenged_player_id=challenged_player_id,
            turn_timeout_seconds=self.default_turn_timeout_seconds,
            reconnect_grace_seconds=self.default_reconnect_grace_seconds,
            disconnected_at={
                str(challenger_player_id): None,
                str(challenged_player_id): None,
            },
        )
        self.active_battle_sessions.append(session)
        self.event_bus.publish("multiplayer_battle_session_started", session)
        return session

    def set_player_connection_state(
        self,
        session_id: UUID,
        player_id: UUID,
        *,
        connected: bool,
        now: datetime | None = None,
    ) -> BattleChallengeResult:
        battle_session = self._find_battle_session(session_id)
        if battle_session is None:
            return BattleChallengeResult.NOT_FOUND

        if player_id not in {
            battle_session.challenger_player_id,
            battle_session.challenged_player_id,
        }:
            return BattleChallengeResult.UNAUTHORIZED

        current_time = now or datetime.now(timezone.utc)
        battle_session.last_activity_at = current_time
        battle_session.disconnected_at[str(player_id)] = (
            None if connected else current_time.isoformat()
        )
        return BattleChallengeResult.SUCCESS

    def submit_turn_action(
        self,
        session_id: UUID,
        player_id: UUID,
        *,
        turn: int,
        action: Mapping[str, Any],
    ) -> TurnSubmissionResult:
        battle_session = self._find_battle_session(session_id)
        if battle_session is None:
            return TurnSubmissionResult.NOT_FOUND

        if player_id not in {
            battle_session.challenger_player_id,
            battle_session.challenged_player_id,
        }:
            return TurnSubmissionResult.UNAUTHORIZED

        if turn != battle_session.current_turn:
            return TurnSubmissionResult.TURN_MISMATCH

        player_key = str(player_id)
        if player_key in battle_session.turn_actions:
            return TurnSubmissionResult.DUPLICATE

        battle_session.turn_actions[player_key] = BattleTurnAction(
            player_id=player_id,
            turn=turn,
            action=dict(action),
        )
        battle_session.last_activity_at = datetime.now(timezone.utc)

        if len(battle_session.turn_actions) < 2:
            return TurnSubmissionResult.WAITING

        actions_in_order = [
            battle_session.turn_actions[key]
            for key in sorted(battle_session.turn_actions.keys())
        ]
        self.event_bus.publish(
            "multiplayer_battle_turn_resolved",
            {
                "session_id": str(battle_session.session_id),
                "turn": battle_session.current_turn,
                "actions": [action.to_dict() for action in actions_in_order],
            },
        )
        battle_session.current_turn += 1
        battle_session.turn_actions = {}
        return TurnSubmissionResult.SUCCESS

    def get_turn_submission_feedback(
        self, submission_result: TurnSubmissionResult
    ) -> OnlineActionFeedback:
        if submission_result == TurnSubmissionResult.SUCCESS:
            return OnlineActionFeedback(
                state=OnlineActionState.ACCEPTED,
                message="Turn submitted. Resolving actions for this round.",
                retryable=False,
            )
        if submission_result == TurnSubmissionResult.WAITING:
            return OnlineActionFeedback(
                state=OnlineActionState.PENDING,
                message="Turn submitted. Waiting for the other player.",
                retryable=False,
            )
        if submission_result == TurnSubmissionResult.NOT_FOUND:
            return OnlineActionFeedback(
                state=OnlineActionState.NOT_FOUND,
                message="Battle session not found. Refresh and reconnect.",
                retryable=True,
            )
        if submission_result == TurnSubmissionResult.TURN_MISMATCH:
            return OnlineActionFeedback(
                state=OnlineActionState.FAILED,
                message="Turn mismatch detected. Sync battle state and try again.",
                retryable=True,
            )
        if submission_result == TurnSubmissionResult.DUPLICATE:
            return OnlineActionFeedback(
                state=OnlineActionState.FAILED,
                message="Turn already submitted for this round.",
                retryable=False,
            )
        return OnlineActionFeedback(
            state=OnlineActionState.FAILED,
            message="You are not authorized to submit turns for this session.",
            retryable=False,
        )

    def _add_battle_record(
        self, challenge: BattleChallenge, resolution: BattleResolution
    ) -> None:
        record = BattleRecord(
            challenge_id=challenge.challenge_id,
            challenger_player_id=challenge.challenger_player_id,
            challenged_player_id=challenge.challenged_player_id,
            resolution=resolution,
        )
        self.battle_history.append(record)

        max_entries = max(1, self.max_battle_history_entries)
        if len(self.battle_history) > max_entries:
            self.battle_history = self.battle_history[-max_entries:]

        self.event_bus.publish("battle_challenge_resolved", record)

    def _is_challenge_expired(
        self, challenge: BattleChallenge, now: datetime | None = None
    ) -> bool:
        if challenge.expires_at is None:
            return False
        current_time = now or datetime.now(timezone.utc)
        return current_time > challenge.expires_at

    def purge_expired_challenges(self, now: datetime | None = None) -> int:
        current_time = now or datetime.now(timezone.utc)
        active_challenges = []
        removed = 0
        for challenge in self.pending_challenges:
            if self._is_challenge_expired(challenge, current_time):
                removed += 1
                self._add_battle_record(challenge, BattleResolution.EXPIRED)
                continue
            active_challenges.append(challenge)
        self.pending_challenges = active_challenges
        return removed

    def get_battle_history_for_player(
        self, player_id: UUID, limit: int | None = None
    ) -> list[BattleRecord]:
        records = [
            record
            for record in self.battle_history
            if record.challenger_player_id == player_id
            or record.challenged_player_id == player_id
        ]
        if limit is not None and limit >= 0:
            return records[-limit:]
        return records

    def get_pending_challenges_for_player(
        self, player_id: UUID
    ) -> list[BattleChallenge]:
        self.purge_expired_challenges()
        return [
            challenge
            for challenge in self.pending_challenges
            if challenge.challenger_player_id == player_id
            or challenge.challenged_player_id == player_id
        ]

    def get_received_challenges_for_player(
        self, player_id: UUID
    ) -> list[BattleChallenge]:
        self.purge_expired_challenges()
        return [
            challenge
            for challenge in self.pending_challenges
            if challenge.challenged_player_id == player_id
        ]

    def get_challenge_feedback(
        self, challenge_id: UUID, player_id: UUID
    ) -> OnlineActionFeedback:
        challenge = self._find_challenge(challenge_id)
        if challenge is not None:
            if player_id not in {
                challenge.challenger_player_id,
                challenge.challenged_player_id,
            }:
                return OnlineActionFeedback(
                    state=OnlineActionState.FAILED,
                    message="You are not authorized to view this battle request.",
                    retryable=False,
                )

            expires_at = challenge.expires_at
            if expires_at is not None:
                seconds_left = max(
                    0,
                    int(
                        (
                            expires_at - datetime.now(timezone.utc)
                        ).total_seconds()
                    ),
                )
                return OnlineActionFeedback(
                    state=OnlineActionState.PENDING,
                    message=(
                        "Battle request is pending. "
                        f"Time remaining: {seconds_left} seconds."
                    ),
                    retryable=False,
                )

            return OnlineActionFeedback(
                state=OnlineActionState.PENDING,
                message="Battle request is pending.",
                retryable=False,
            )

        for record in reversed(self.battle_history):
            if record.challenge_id != challenge_id:
                continue
            if player_id not in {
                record.challenger_player_id,
                record.challenged_player_id,
            }:
                return OnlineActionFeedback(
                    state=OnlineActionState.FAILED,
                    message="You are not authorized to view this battle request.",
                    retryable=False,
                )

            if record.resolution == BattleResolution.ACCEPTED:
                return OnlineActionFeedback(
                    state=OnlineActionState.ACCEPTED,
                    message="Battle request accepted. Preparing battle session.",
                    retryable=False,
                )
            if record.resolution == BattleResolution.EXPIRED:
                return OnlineActionFeedback(
                    state=OnlineActionState.EXPIRED,
                    message="Battle request expired. Send a new request to retry.",
                    retryable=True,
                )
            if record.resolution == BattleResolution.REJECTED:
                return OnlineActionFeedback(
                    state=OnlineActionState.REJECTED,
                    message="Battle request was declined. You can try again.",
                    retryable=True,
                )
            return OnlineActionFeedback(
                state=OnlineActionState.CANCELLED,
                message="Battle request was cancelled.",
                retryable=True,
            )

        return OnlineActionFeedback(
            state=OnlineActionState.NOT_FOUND,
            message="Battle request not found. Please refresh and try again.",
            retryable=True,
        )

    def _find_challenge(self, challenge_id: UUID) -> BattleChallenge | None:
        return next(
            (
                challenge
                for challenge in self.pending_challenges
                if challenge.challenge_id == challenge_id
            ),
            None,
        )

    def _has_duplicate_pending(
        self, challenger_player_id: UUID, challenged_player_id: UUID
    ) -> bool:
        return any(
            challenge.challenger_player_id == challenger_player_id
            and challenge.challenged_player_id == challenged_player_id
            for challenge in self.pending_challenges
        )

    def propose_challenge(
        self,
        challenger_player_id: UUID,
        challenged_player_id: UUID,
        *,
        ttl_seconds: int | None = None,
    ) -> BattleChallengeResult:
        self.purge_expired_challenges()

        if challenger_player_id == challenged_player_id:
            return BattleChallengeResult.SELF_CHALLENGE

        if self._has_duplicate_pending(
            challenger_player_id, challenged_player_id
        ):
            return BattleChallengeResult.DUPLICATE

        challenge = BattleChallenge(
            challenger_player_id=challenger_player_id,
            challenged_player_id=challenged_player_id,
        )
        ttl = (
            self.default_challenge_ttl_seconds
            if ttl_seconds is None
            else ttl_seconds
        )
        challenge.expires_at = challenge.timestamp + timedelta(seconds=ttl)

        self.pending_challenges.append(challenge)
        self.event_bus.publish("battle_challenge_proposed", challenge)
        return BattleChallengeResult.SUCCESS

    def cancel_challenge(
        self, challenge_id: UUID, requesting_player_id: UUID | None = None
    ) -> BattleChallengeResult:
        challenge = self._find_challenge(challenge_id)
        if challenge is None:
            return BattleChallengeResult.NOT_FOUND

        if requesting_player_id is not None and requesting_player_id not in {
            challenge.challenger_player_id,
            challenge.challenged_player_id,
        }:
            return BattleChallengeResult.UNAUTHORIZED

        self.pending_challenges.remove(challenge)
        self._add_battle_record(challenge, BattleResolution.CANCELLED)
        self.event_bus.publish("battle_challenge_cancelled", challenge)
        return BattleChallengeResult.SUCCESS

    def accept_challenge(
        self, challenge_id: UUID, accepting_player_id: UUID | None = None
    ) -> BattleChallengeResult:
        challenge = self._find_challenge(challenge_id)
        if challenge is None:
            return BattleChallengeResult.NOT_FOUND

        if (
            accepting_player_id is not None
            and accepting_player_id != challenge.challenged_player_id
        ):
            return BattleChallengeResult.UNAUTHORIZED

        if self._is_challenge_expired(challenge):
            self.pending_challenges.remove(challenge)
            self._add_battle_record(challenge, BattleResolution.EXPIRED)
            return BattleChallengeResult.EXPIRED

        self.pending_challenges.remove(challenge)
        self._add_battle_record(challenge, BattleResolution.ACCEPTED)
        self.event_bus.publish("battle_challenge_accepted", challenge)
        return BattleChallengeResult.SUCCESS

    def reject_challenge(
        self, challenge_id: UUID, rejecting_player_id: UUID | None = None
    ) -> BattleChallengeResult:
        challenge = self._find_challenge(challenge_id)
        if challenge is None:
            return BattleChallengeResult.NOT_FOUND

        if (
            rejecting_player_id is not None
            and rejecting_player_id != challenge.challenged_player_id
        ):
            return BattleChallengeResult.UNAUTHORIZED

        self.pending_challenges.remove(challenge)
        self._add_battle_record(challenge, BattleResolution.REJECTED)
        self.event_bus.publish("battle_challenge_rejected", challenge)
        return BattleChallengeResult.REJECTED

    def save_log(self) -> dict[str, Any]:
        return {
            "pending_challenges": [
                challenge.to_dict() for challenge in self.pending_challenges
            ],
            "battle_history": [
                record.to_dict() for record in self.battle_history
            ],
            "max_battle_history_entries": self.max_battle_history_entries,
            "default_challenge_ttl_seconds": self.default_challenge_ttl_seconds,
            "active_battle_sessions": [
                battle_session.to_dict()
                for battle_session in self.active_battle_sessions
            ],
            "default_turn_timeout_seconds": self.default_turn_timeout_seconds,
            "default_reconnect_grace_seconds": self.default_reconnect_grace_seconds,
        }

    def load_log(self, data: dict[str, Any]) -> None:
        pending_data = data.get("pending_challenges", [])
        self.pending_challenges = [
            BattleChallenge.from_dict(challenge_data)
            for challenge_data in pending_data
        ]
        raw_history = data.get("battle_history", data.get("completed_battles", []))
        history: list[BattleRecord] = []
        for entry in raw_history:
            if not isinstance(entry, Mapping):
                continue
            try:
                history.append(
                    BattleRecord.from_dict(dict(entry))
                )
            except (KeyError, TypeError, ValueError):
                continue
        self.battle_history = history
        self.max_battle_history_entries = int(
            data.get(
                "max_battle_history_entries",
                self.max_battle_history_entries,
            )
        )
        self.default_challenge_ttl_seconds = int(
            data.get(
                "default_challenge_ttl_seconds",
                self.default_challenge_ttl_seconds,
            )
        )
        raw_sessions = data.get("active_battle_sessions", [])
        sessions: list[ActiveBattleSession] = []
        for session_entry in raw_sessions:
            if not isinstance(session_entry, Mapping):
                continue
            try:
                sessions.append(ActiveBattleSession.from_dict(session_entry))
            except (KeyError, TypeError, ValueError):
                continue

        self.active_battle_sessions = sessions
        self.default_turn_timeout_seconds = int(
            data.get(
                "default_turn_timeout_seconds",
                self.default_turn_timeout_seconds,
            )
        )
        self.default_reconnect_grace_seconds = int(
            data.get(
                "default_reconnect_grace_seconds",
                self.default_reconnect_grace_seconds,
            )
        )
        self.purge_expired_challenges()
        self.purge_stale_battle_sessions()

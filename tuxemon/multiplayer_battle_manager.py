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


class MultiplayerBattleManager:
    """Tracks and resolves online battle challenges between players."""

    def __init__(self) -> None:
        self.pending_challenges: list[BattleChallenge] = []
        self.battle_history: list[BattleRecord] = []
        self.max_battle_history_entries = 100
        self.default_challenge_ttl_seconds = 180
        self.event_bus = get_event_bus()

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
        self.purge_expired_challenges()

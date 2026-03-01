# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from tuxemon.event import get_event_bus

SUPPORTED_BRACKET_SIZES = (8, 16)
MIN_BRACKET_SIZE = 8


def _coerce_utc_timestamp(value: str) -> datetime:
    """Parse timestamp strings and normalize to timezone-aware UTC."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class TournamentStatus(Enum):
    DRAFT = "draft"
    REGISTRATION = "registration"
    CHECKIN = "checkin"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MatchStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    WALKOVER = "walkover"
    CANCELLED = "cancelled"


class TournamentResult(Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID_STATE = "invalid_state"
    REGISTRATION_FULL = "registration_full"
    ALREADY_REGISTERED = "already_registered"
    NOT_REGISTERED = "not_registered"
    ALREADY_CHECKED_IN = "already_checked_in"
    DISQUALIFIED = "disqualified"
    INSUFFICIENT_PLAYERS = "insufficient_players"
    UNAUTHORIZED = "unauthorized"
    DUPLICATE_RESULT = "duplicate_result"
    MATCH_NOT_FOUND = "match_not_found"
    INVALID_WINNER = "invalid_winner"
    INVALID_BRACKET_SIZE = "invalid_bracket_size"


@dataclass
class TournamentPolicy:
    team_size: int = 6
    level_cap: int = 50
    turn_timer_seconds: int = 60
    reconnect_grace_seconds: int = 90
    duplicate_species_clause: bool = True
    no_show_timeout_seconds: int = 180
    min_viable_players: int = 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_size": self.team_size,
            "level_cap": self.level_cap,
            "turn_timer_seconds": self.turn_timer_seconds,
            "reconnect_grace_seconds": self.reconnect_grace_seconds,
            "duplicate_species_clause": self.duplicate_species_clause,
            "no_show_timeout_seconds": self.no_show_timeout_seconds,
            "min_viable_players": self.min_viable_players,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TournamentPolicy:
        return cls(
            team_size=int(data.get("team_size", 6)),
            level_cap=int(data.get("level_cap", 50)),
            turn_timer_seconds=int(data.get("turn_timer_seconds", 60)),
            reconnect_grace_seconds=int(data.get("reconnect_grace_seconds", 90)),
            duplicate_species_clause=bool(
                data.get("duplicate_species_clause", True)
            ),
            no_show_timeout_seconds=int(data.get("no_show_timeout_seconds", 180)),
            min_viable_players=int(data.get("min_viable_players", 8)),
        )


@dataclass
class Participant:
    player_id: UUID
    display_name: str
    registered_at: datetime
    checked_in: bool = False
    seed: int | None = None
    disqualified: bool = False
    disqualified_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": str(self.player_id),
            "display_name": self.display_name,
            "registered_at": self.registered_at.isoformat(),
            "checked_in": self.checked_in,
            "seed": self.seed,
            "disqualified": self.disqualified,
            "disqualified_at": (
                self.disqualified_at.isoformat() if self.disqualified_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Participant:
        disqualified_at_raw = data.get("disqualified_at")
        return cls(
            player_id=UUID(str(data["player_id"])),
            display_name=str(data["display_name"]),
            registered_at=_coerce_utc_timestamp(str(data["registered_at"])),
            checked_in=bool(data.get("checked_in", False)),
            seed=(int(data["seed"]) if data.get("seed") is not None else None),
            disqualified=bool(data.get("disqualified", False)),
            disqualified_at=(
                _coerce_utc_timestamp(disqualified_at_raw)
                if isinstance(disqualified_at_raw, str)
                else None
            ),
        )


@dataclass
class Match:
    match_id: UUID
    round_index: int
    match_index: int
    player_a_id: UUID | None
    player_b_id: UUID | None
    winner_id: UUID | None = None
    resolution_token: str | None = None
    status: MatchStatus = MatchStatus.PENDING
    is_bye: bool = False
    scheduled_at: datetime | None = None
    resolved_at: datetime | None = None
    challenge_correlation_id: str | None = None
    challenge_dispatched_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": str(self.match_id),
            "round_index": self.round_index,
            "match_index": self.match_index,
            "player_a_id": (str(self.player_a_id) if self.player_a_id else None),
            "player_b_id": (str(self.player_b_id) if self.player_b_id else None),
            "winner_id": (str(self.winner_id) if self.winner_id else None),
            "resolution_token": self.resolution_token,
            "status": self.status.value,
            "is_bye": self.is_bye,
            "scheduled_at": (
                self.scheduled_at.isoformat() if self.scheduled_at else None
            ),
            "resolved_at": (
                self.resolved_at.isoformat() if self.resolved_at else None
            ),
            "challenge_correlation_id": self.challenge_correlation_id,
            "challenge_dispatched_at": (
                self.challenge_dispatched_at.isoformat()
                if self.challenge_dispatched_at
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Match:
        return cls(
            match_id=UUID(str(data["match_id"])),
            round_index=int(data["round_index"]),
            match_index=int(data["match_index"]),
            player_a_id=(
                UUID(str(data["player_a_id"])) if data.get("player_a_id") else None
            ),
            player_b_id=(
                UUID(str(data["player_b_id"])) if data.get("player_b_id") else None
            ),
            winner_id=(
                UUID(str(data["winner_id"])) if data.get("winner_id") else None
            ),
            resolution_token=data.get("resolution_token"),
            status=MatchStatus(data.get("status", MatchStatus.PENDING.value)),
            is_bye=bool(data.get("is_bye", False)),
            scheduled_at=(
                _coerce_utc_timestamp(str(data["scheduled_at"]))
                if data.get("scheduled_at")
                else None
            ),
            resolved_at=(
                _coerce_utc_timestamp(str(data["resolved_at"]))
                if data.get("resolved_at")
                else None
            ),
            challenge_correlation_id=data.get("challenge_correlation_id"),
            challenge_dispatched_at=(
                _coerce_utc_timestamp(str(data["challenge_dispatched_at"]))
                if data.get("challenge_dispatched_at")
                else None
            ),
        )


@dataclass
class BracketNode:
    position: int
    round_index: int
    match_index: int
    match_id: UUID | None
    feeds_into: int | None
    slot_a_feeds_from: int | None
    slot_b_feeds_from: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "round_index": self.round_index,
            "match_index": self.match_index,
            "match_id": (str(self.match_id) if self.match_id else None),
            "feeds_into": self.feeds_into,
            "slot_a_feeds_from": self.slot_a_feeds_from,
            "slot_b_feeds_from": self.slot_b_feeds_from,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BracketNode:
        return cls(
            position=int(data["position"]),
            round_index=int(data["round_index"]),
            match_index=int(data["match_index"]),
            match_id=(UUID(str(data["match_id"])) if data.get("match_id") else None),
            feeds_into=(
                int(data["feeds_into"])
                if data.get("feeds_into") is not None
                else None
            ),
            slot_a_feeds_from=(
                int(data["slot_a_feeds_from"])
                if data.get("slot_a_feeds_from") is not None
                else None
            ),
            slot_b_feeds_from=(
                int(data["slot_b_feeds_from"])
                if data.get("slot_b_feeds_from") is not None
                else None
            ),
        )


@dataclass
class Tournament:
    tournament_id: UUID
    name: str
    format: str
    bracket_size: int
    status: TournamentStatus
    policy: TournamentPolicy
    tournament_seed: int
    participants: list[Participant]
    matches: list[Match]
    bracket: list[BracketNode]
    created_at: datetime
    registration_closes_at: datetime | None
    checkin_closes_at: datetime | None
    champion_id: UUID | None = None
    cancel_reason: str | None = None
    admin_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tournament_id": str(self.tournament_id),
            "name": self.name,
            "format": self.format,
            "bracket_size": self.bracket_size,
            "status": self.status.value,
            "policy": self.policy.to_dict(),
            "tournament_seed": self.tournament_seed,
            "participants": [p.to_dict() for p in self.participants],
            "matches": [m.to_dict() for m in self.matches],
            "bracket": [b.to_dict() for b in self.bracket],
            "created_at": self.created_at.isoformat(),
            "registration_closes_at": (
                self.registration_closes_at.isoformat()
                if self.registration_closes_at
                else None
            ),
            "checkin_closes_at": (
                self.checkin_closes_at.isoformat()
                if self.checkin_closes_at
                else None
            ),
            "champion_id": (str(self.champion_id) if self.champion_id else None),
            "cancel_reason": self.cancel_reason,
            "admin_notes": list(self.admin_notes),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Tournament:
        participants: list[Participant] = []
        for p_data in data.get("participants", []):
            if not isinstance(p_data, Mapping):
                continue
            try:
                participants.append(Participant.from_dict(p_data))
            except (KeyError, TypeError, ValueError):
                continue

        matches: list[Match] = []
        for m_data in data.get("matches", []):
            if not isinstance(m_data, Mapping):
                continue
            try:
                matches.append(Match.from_dict(m_data))
            except (KeyError, TypeError, ValueError):
                continue

        bracket: list[BracketNode] = []
        for b_data in data.get("bracket", []):
            if not isinstance(b_data, Mapping):
                continue
            try:
                bracket.append(BracketNode.from_dict(b_data))
            except (KeyError, TypeError, ValueError):
                continue

        return cls(
            tournament_id=UUID(str(data["tournament_id"])),
            name=str(data["name"]),
            format=str(data.get("format", "single_elimination")),
            bracket_size=int(data["bracket_size"]),
            status=TournamentStatus(data["status"]),
            policy=TournamentPolicy.from_dict(data.get("policy", {}) or {}),
            tournament_seed=int(data.get("tournament_seed", 0)),
            participants=participants,
            matches=matches,
            bracket=bracket,
            created_at=_coerce_utc_timestamp(str(data["created_at"])),
            registration_closes_at=(
                _coerce_utc_timestamp(str(data["registration_closes_at"]))
                if data.get("registration_closes_at")
                else None
            ),
            checkin_closes_at=(
                _coerce_utc_timestamp(str(data["checkin_closes_at"]))
                if data.get("checkin_closes_at")
                else None
            ),
            champion_id=(
                UUID(str(data["champion_id"])) if data.get("champion_id") else None
            ),
            cancel_reason=data.get("cancel_reason"),
            admin_notes=list(data.get("admin_notes", [])),
        )


# ---------------------------------------------------------------------------
# Bracket generation helpers
# ---------------------------------------------------------------------------


def _seeding_slot_order(n: int) -> list[int]:
    """Return ordered seed list for a standard single-elimination bracket.

    Produces the classic top-half/bottom-half expansion so that the top
    two seeds cannot meet before the final.  Example for n=8:
    [1, 8, 4, 5, 2, 7, 3, 6]  — pairs are taken as consecutive elements.

    The algorithm is recursive: build the bracket for n//2, then expand
    each seed by appending its complement (n+1-seed) directly after it.
    """
    if n == 2:
        return [1, 2]
    prev = _seeding_slot_order(n // 2)
    result: list[int] = []
    for seed in prev:
        result.append(seed)
        result.append(n + 1 - seed)
    return result


def _round_start_position(bracket_size: int, round_index: int) -> int:
    """Absolute position of the first match in *round_index* (0-based)."""
    return sum(bracket_size // (2 ** (r + 1)) for r in range(round_index))


def _generate_bracket(
    participants: list[Participant],
    bracket_size: int,
    rng: random.Random,
) -> tuple[list[Match], list[BracketNode]]:
    """Build a single-elimination bracket from eligible participants.

    Participants are assigned seeds 1..n using a deterministic RNG key
    (primary sort) with registration timestamp and player_id as stable
    tie-breakers (matching the spec requirement for replay/debug).

    Matches and nodes are returned sorted by (round_index, match_index).
    Round-0 byes are flagged as WALKOVER with winner pre-set; later rounds
    start as PENDING until upstream matches resolve.

    Bye propagation into later rounds is intentionally *not* performed
    here — callers must call ``TournamentManager._advance_winner`` for
    each WALKOVER match after attaching these lists to a Tournament.
    """
    num_rounds = int(math.log2(bracket_size))

    eligible = [p for p in participants if p.checked_in and not p.disqualified]

    # Pre-compute a random key per player so sort order is stable.
    random_keys = [rng.random() for _ in eligible]
    sorted_indices = sorted(
        range(len(eligible)),
        key=lambda i: (
            random_keys[i],
            eligible[i].registered_at,
            str(eligible[i].player_id),
        ),
    )
    sorted_participants = [eligible[i] for i in sorted_indices]

    for seed_num, p in enumerate(sorted_participants, start=1):
        p.seed = seed_num

    seed_to_player: dict[int, UUID | None] = {
        s: None for s in range(1, bracket_size + 1)
    }
    for p in sorted_participants:
        if p.seed is not None and p.seed <= bracket_size:
            seed_to_player[p.seed] = p.player_id

    slot_order = _seeding_slot_order(bracket_size)

    total_matches = bracket_size - 1
    match_ids: list[UUID] = [uuid4() for _ in range(total_matches)]

    matches: list[Match] = []
    bracket: list[BracketNode] = []
    now = datetime.now(timezone.utc)

    for round_idx in range(num_rounds):
        round_match_count = bracket_size // (2 ** (round_idx + 1))
        round_start = _round_start_position(bracket_size, round_idx)

        for match_idx in range(round_match_count):
            pos = round_start + match_idx
            match_id = match_ids[pos]

            if round_idx < num_rounds - 1:
                next_round_start = _round_start_position(
                    bracket_size, round_idx + 1
                )
                feeds_into: int | None = next_round_start + match_idx // 2
            else:
                feeds_into = None

            if round_idx == 0:
                slot_a_feeds_from: int | None = None
                slot_b_feeds_from: int | None = None
                slot_a_seed = slot_order[match_idx * 2]
                slot_b_seed = slot_order[match_idx * 2 + 1]
                player_a_id = seed_to_player.get(slot_a_seed)
                player_b_id = seed_to_player.get(slot_b_seed)
            else:
                prev_round_start = _round_start_position(
                    bracket_size, round_idx - 1
                )
                slot_a_feeds_from = prev_round_start + match_idx * 2
                slot_b_feeds_from = prev_round_start + match_idx * 2 + 1
                player_a_id = None
                player_b_id = None

            is_bye = round_idx == 0 and (
                player_a_id is None or player_b_id is None
            )

            if round_idx == 0:
                if is_bye:
                    status = MatchStatus.WALKOVER
                    winner_id: UUID | None = player_a_id or player_b_id
                    resolved_at: datetime | None = now
                    scheduled_at: datetime | None = None
                else:
                    status = MatchStatus.SCHEDULED
                    winner_id = None
                    resolved_at = None
                    scheduled_at = now
            else:
                status = MatchStatus.PENDING
                winner_id = None
                resolved_at = None
                scheduled_at = None

            matches.append(
                Match(
                    match_id=match_id,
                    round_index=round_idx,
                    match_index=match_idx,
                    player_a_id=player_a_id,
                    player_b_id=player_b_id,
                    winner_id=winner_id,
                    status=status,
                    is_bye=is_bye,
                    scheduled_at=scheduled_at,
                    resolved_at=resolved_at,
                )
            )

            bracket.append(
                BracketNode(
                    position=pos,
                    round_index=round_idx,
                    match_index=match_idx,
                    match_id=match_id,
                    feeds_into=feeds_into,
                    slot_a_feeds_from=slot_a_feeds_from,
                    slot_b_feeds_from=slot_b_feeds_from,
                )
            )

    return matches, bracket


# ---------------------------------------------------------------------------
# Tournament manager
# ---------------------------------------------------------------------------


class TournamentManager:
    """Manages the full lifecycle of online tournaments."""

    def __init__(self) -> None:
        self.tournaments: list[Tournament] = []
        self.event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Internal lookups
    # ------------------------------------------------------------------

    def _find_tournament(self, tournament_id: UUID) -> Tournament | None:
        return next(
            (t for t in self.tournaments if t.tournament_id == tournament_id),
            None,
        )

    @staticmethod
    def _find_participant(
        tournament: Tournament, player_id: UUID
    ) -> Participant | None:
        return next(
            (p for p in tournament.participants if p.player_id == player_id),
            None,
        )

    @staticmethod
    def _find_match(tournament: Tournament, match_id: UUID) -> Match | None:
        return next(
            (m for m in tournament.matches if m.match_id == match_id), None
        )

    @staticmethod
    def _find_node_for_match(
        tournament: Tournament, match_id: UUID
    ) -> BracketNode | None:
        return next(
            (n for n in tournament.bracket if n.match_id == match_id), None
        )

    @staticmethod
    def _find_node_at_position(
        tournament: Tournament, position: int
    ) -> BracketNode | None:
        return next(
            (n for n in tournament.bracket if n.position == position), None
        )

    # ------------------------------------------------------------------
    # Challenge dispatch integration
    # ------------------------------------------------------------------

    @staticmethod
    def _build_match_correlation_id(tournament_id: UUID, match_id: UUID) -> str:
        """Return a stable correlation key for challenge transport wiring."""
        return f"tournament:{tournament_id}:match:{match_id}"

    def mark_match_dispatched(
        self,
        tournament_id: UUID,
        match_id: UUID,
        *,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> TournamentResult:
        """Attach challenge correlation metadata to a scheduled match.

        This operation is idempotent: if the same correlation key has already
        been recorded, SUCCESS is returned with no state mutation.
        """
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND

        match = self._find_match(tournament, match_id)
        if match is None:
            return TournamentResult.MATCH_NOT_FOUND
        if match.status != MatchStatus.SCHEDULED:
            return TournamentResult.INVALID_STATE

        correlation = correlation_id or self._build_match_correlation_id(
            tournament_id, match_id
        )
        if match.challenge_correlation_id == correlation:
            return TournamentResult.SUCCESS
        if match.challenge_correlation_id is not None:
            return TournamentResult.DUPLICATE_RESULT

        match.challenge_correlation_id = correlation
        match.challenge_dispatched_at = now or datetime.now(timezone.utc)
        self.event_bus.publish(
            "tournament_match_dispatched",
            {
                "tournament_id": str(tournament_id),
                "match_id": str(match_id),
                "correlation_id": correlation,
            },
        )
        return TournamentResult.SUCCESS

    # ------------------------------------------------------------------
    # Winner advancement
    # ------------------------------------------------------------------

    def _advance_winner(
        self,
        tournament: Tournament,
        match: Match,
        *,
        now: datetime | None = None,
    ) -> None:
        """Propagate a resolved match's winner into the next bracket node.

        If the match is the championship match (feeds_into is None) the
        tournament is marked COMPLETED and the champion is recorded.
        """
        current_time = now or datetime.now(timezone.utc)

        if match.winner_id is None:
            return

        node = self._find_node_for_match(tournament, match.match_id)
        if node is None:
            return

        if node.feeds_into is None:
            tournament.champion_id = match.winner_id
            tournament.status = TournamentStatus.COMPLETED
            self.event_bus.publish("tournament_completed", tournament)
            return

        next_node = self._find_node_at_position(tournament, node.feeds_into)
        if next_node is None or next_node.match_id is None:
            return

        next_match = self._find_match(tournament, next_node.match_id)
        if next_match is None:
            return

        if next_node.slot_a_feeds_from == node.position:
            next_match.player_a_id = match.winner_id
        elif next_node.slot_b_feeds_from == node.position:
            next_match.player_b_id = match.winner_id

        if (
            next_match.player_a_id is not None
            and next_match.player_b_id is not None
            and next_match.status == MatchStatus.PENDING
        ):
            next_match.status = MatchStatus.SCHEDULED
            next_match.scheduled_at = current_time
            self.event_bus.publish(
                "tournament_match_scheduled",
                {
                    "tournament_id": str(tournament.tournament_id),
                    "match_id": str(next_match.match_id),
                    "round_index": next_match.round_index,
                    "match_index": next_match.match_index,
                },
            )

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def create_tournament(
        self,
        name: str,
        bracket_size: int,
        *,
        policy: TournamentPolicy | None = None,
        registration_closes_at: datetime | None = None,
        checkin_closes_at: datetime | None = None,
        tournament_seed: int | None = None,
    ) -> TournamentResult | Tournament:
        """Create a new tournament in DRAFT status.

        Returns the new ``Tournament`` on success or a ``TournamentResult``
        error value if validation fails.
        """
        if bracket_size not in SUPPORTED_BRACKET_SIZES:
            return TournamentResult.INVALID_BRACKET_SIZE

        seed = (
            tournament_seed
            if tournament_seed is not None
            else int(random.random() * 2**32)
        )

        tournament = Tournament(
            tournament_id=uuid4(),
            name=name,
            format="single_elimination",
            bracket_size=bracket_size,
            status=TournamentStatus.DRAFT,
            policy=policy or TournamentPolicy(),
            tournament_seed=seed,
            participants=[],
            matches=[],
            bracket=[],
            created_at=datetime.now(timezone.utc),
            registration_closes_at=registration_closes_at,
            checkin_closes_at=checkin_closes_at,
        )
        self.tournaments.append(tournament)
        self.event_bus.publish("tournament_created", tournament)
        return tournament

    def open_registration(self, tournament_id: UUID) -> TournamentResult:
        """Transition tournament from DRAFT to REGISTRATION."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.DRAFT:
            return TournamentResult.INVALID_STATE
        tournament.status = TournamentStatus.REGISTRATION
        self.event_bus.publish("tournament_registration_opened", tournament)
        return TournamentResult.SUCCESS

    def register_participant(
        self,
        tournament_id: UUID,
        player_id: UUID,
        display_name: str,
    ) -> TournamentResult:
        """Register a player. Fails if registration is closed or full."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.REGISTRATION:
            return TournamentResult.INVALID_STATE

        existing = self._find_participant(tournament, player_id)
        if existing is not None:
            if existing.disqualified:
                return TournamentResult.DISQUALIFIED
            return TournamentResult.ALREADY_REGISTERED

        active_count = sum(
            1 for p in tournament.participants if not p.disqualified
        )
        if active_count >= tournament.bracket_size:
            return TournamentResult.REGISTRATION_FULL

        participant = Participant(
            player_id=player_id,
            display_name=display_name,
            registered_at=datetime.now(timezone.utc),
        )
        tournament.participants.append(participant)
        self.event_bus.publish(
            "tournament_participant_registered",
            {
                "tournament_id": str(tournament_id),
                "player_id": str(player_id),
            },
        )
        return TournamentResult.SUCCESS

    def close_registration(self, tournament_id: UUID) -> TournamentResult:
        """Transition from REGISTRATION to CHECKIN."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.REGISTRATION:
            return TournamentResult.INVALID_STATE
        tournament.status = TournamentStatus.CHECKIN
        self.event_bus.publish("tournament_checkin_opened", tournament)
        return TournamentResult.SUCCESS

    def check_in_participant(
        self, tournament_id: UUID, player_id: UUID
    ) -> TournamentResult:
        """Check in a registered participant during the CHECKIN phase."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.CHECKIN:
            return TournamentResult.INVALID_STATE

        participant = self._find_participant(tournament, player_id)
        if participant is None:
            return TournamentResult.NOT_REGISTERED
        if participant.disqualified:
            return TournamentResult.DISQUALIFIED
        if participant.checked_in:
            return TournamentResult.ALREADY_CHECKED_IN

        participant.checked_in = True
        self.event_bus.publish(
            "tournament_participant_checked_in",
            {
                "tournament_id": str(tournament_id),
                "player_id": str(player_id),
            },
        )
        return TournamentResult.SUCCESS

    def start_tournament(
        self, tournament_id: UUID, *, now: datetime | None = None
    ) -> TournamentResult:
        """Generate bracket and transition to IN_PROGRESS.

        Participants who did not check in are removed before bracket
        generation. If the number of checked-in players is below
        ``policy.min_viable_players`` the tournament is cancelled.
        """
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.CHECKIN:
            return TournamentResult.INVALID_STATE

        current_time = now or datetime.now(timezone.utc)

        checked_in = [
            p
            for p in tournament.participants
            if p.checked_in and not p.disqualified
        ]

        if len(checked_in) < tournament.policy.min_viable_players:
            tournament.status = TournamentStatus.CANCELLED
            tournament.cancel_reason = (
                f"Insufficient checked-in players: {len(checked_in)} "
                f"(minimum {tournament.policy.min_viable_players})"
            )
            self.event_bus.publish("tournament_cancelled", tournament)
            return TournamentResult.INSUFFICIENT_PLAYERS

        rng = random.Random(tournament.tournament_seed)
        matches, bracket = _generate_bracket(
            tournament.participants, tournament.bracket_size, rng
        )
        tournament.matches = matches
        tournament.bracket = bracket
        tournament.status = TournamentStatus.IN_PROGRESS

        for match in tournament.matches:
            if match.status == MatchStatus.WALKOVER:
                self._advance_winner(tournament, match, now=current_time)

        self.event_bus.publish("tournament_started", tournament)
        return TournamentResult.SUCCESS

    # ------------------------------------------------------------------
    # Match result reporting
    # ------------------------------------------------------------------

    def report_match_result(
        self,
        tournament_id: UUID,
        match_id: UUID,
        winner_id: UUID,
        *,
        resolution_token: str | None = None,
        now: datetime | None = None,
    ) -> TournamentResult:
        """Record a match result and advance the bracket.

        Result ingestion is idempotent: if the same ``resolution_token``
        is submitted for an already-resolved match, SUCCESS is returned
        without mutating state.  A conflicting token on a resolved match
        returns DUPLICATE_RESULT.
        """
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status not in (
            TournamentStatus.IN_PROGRESS,
            TournamentStatus.PAUSED,
        ):
            return TournamentResult.INVALID_STATE

        match = self._find_match(tournament, match_id)
        if match is None:
            return TournamentResult.MATCH_NOT_FOUND

        if match.status in (MatchStatus.COMPLETED, MatchStatus.WALKOVER):
            if (
                resolution_token is not None
                and match.resolution_token == resolution_token
            ):
                return TournamentResult.SUCCESS
            return TournamentResult.DUPLICATE_RESULT

        if match.status != MatchStatus.SCHEDULED:
            return TournamentResult.INVALID_STATE

        if winner_id not in {match.player_a_id, match.player_b_id}:
            return TournamentResult.INVALID_WINNER

        current_time = now or datetime.now(timezone.utc)
        match.winner_id = winner_id
        match.status = MatchStatus.COMPLETED
        match.resolved_at = current_time
        match.resolution_token = resolution_token

        self.event_bus.publish(
            "tournament_match_completed",
            {
                "tournament_id": str(tournament_id),
                "match_id": str(match_id),
                "winner_id": str(winner_id),
            },
        )
        self._advance_winner(tournament, match, now=current_time)
        return TournamentResult.SUCCESS

    def resolve_no_show_timeout(
        self,
        tournament_id: UUID,
        match_id: UUID,
        absent_player_id: UUID,
        *,
        absent_disconnected_at: datetime | None = None,
        now: datetime | None = None,
    ) -> TournamentResult:
        """Resolve a scheduled match when one participant no-shows past policy."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status not in (
            TournamentStatus.IN_PROGRESS,
            TournamentStatus.PAUSED,
        ):
            return TournamentResult.INVALID_STATE

        match = self._find_match(tournament, match_id)
        if match is None:
            return TournamentResult.MATCH_NOT_FOUND
        if match.status != MatchStatus.SCHEDULED:
            return TournamentResult.INVALID_STATE
        if absent_player_id not in {match.player_a_id, match.player_b_id}:
            return TournamentResult.INVALID_WINNER
        if match.scheduled_at is None:
            return TournamentResult.INVALID_STATE

        current_time = now or datetime.now(timezone.utc)
        timeout_at = match.scheduled_at + timedelta(
            seconds=tournament.policy.no_show_timeout_seconds
        )

        if absent_disconnected_at is not None:
            reconnect_deadline = absent_disconnected_at + timedelta(
                seconds=tournament.policy.reconnect_grace_seconds
            )
            if reconnect_deadline > timeout_at:
                timeout_at = reconnect_deadline

        if current_time < timeout_at:
            return TournamentResult.INVALID_STATE

        winner_id = (
            match.player_b_id
            if absent_player_id == match.player_a_id
            else match.player_a_id
        )
        if winner_id is None:
            return TournamentResult.INVALID_WINNER

        match.winner_id = winner_id
        match.status = MatchStatus.WALKOVER
        match.resolved_at = current_time

        self.event_bus.publish(
            "tournament_match_no_show_resolved",
            {
                "tournament_id": str(tournament_id),
                "match_id": str(match_id),
                "winner_id": str(winner_id),
                "absent_player_id": str(absent_player_id),
            },
        )
        self.event_bus.publish(
            "tournament_match_auto_adjudicated",
            {
                "tournament_id": str(tournament_id),
                "match_id": str(match_id),
                "winner_id": str(winner_id),
                "reason": "no_show_timeout",
            },
        )

        self._advance_winner(tournament, match, now=current_time)
        return TournamentResult.SUCCESS

    def force_report_result(
        self,
        tournament_id: UUID,
        match_id: UUID,
        winner_id: UUID,
        *,
        admin: bool = False,
        now: datetime | None = None,
    ) -> TournamentResult:
        """Admin action: force-resolve any match regardless of its status."""
        if not admin:
            return TournamentResult.UNAUTHORIZED

        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status not in (
            TournamentStatus.IN_PROGRESS,
            TournamentStatus.PAUSED,
        ):
            return TournamentResult.INVALID_STATE

        match = self._find_match(tournament, match_id)
        if match is None:
            return TournamentResult.MATCH_NOT_FOUND

        if match.status in (MatchStatus.COMPLETED, MatchStatus.WALKOVER):
            return TournamentResult.DUPLICATE_RESULT

        valid_players = {match.player_a_id, match.player_b_id} - {None}
        if winner_id not in valid_players:
            return TournamentResult.INVALID_WINNER

        current_time = now or datetime.now(timezone.utc)
        match.winner_id = winner_id
        match.status = MatchStatus.COMPLETED
        match.resolved_at = current_time

        self.event_bus.publish(
            "tournament_match_force_reported",
            {
                "tournament_id": str(tournament_id),
                "match_id": str(match_id),
                "winner_id": str(winner_id),
            },
        )
        self._advance_winner(tournament, match, now=current_time)
        return TournamentResult.SUCCESS

    # ------------------------------------------------------------------
    # Admin / moderation actions
    # ------------------------------------------------------------------

    def disqualify_participant(
        self,
        tournament_id: UUID,
        player_id: UUID,
        *,
        admin: bool = False,
        now: datetime | None = None,
    ) -> TournamentResult:
        """Disqualify a participant and auto-advance their opponent.

        Works during REGISTRATION, CHECKIN, IN_PROGRESS, and PAUSED phases.
        """
        if not admin:
            return TournamentResult.UNAUTHORIZED

        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status in (
            TournamentStatus.COMPLETED,
            TournamentStatus.CANCELLED,
        ):
            return TournamentResult.INVALID_STATE

        participant = self._find_participant(tournament, player_id)
        if participant is None:
            return TournamentResult.NOT_REGISTERED
        if participant.disqualified:
            return TournamentResult.DISQUALIFIED

        current_time = now or datetime.now(timezone.utc)
        participant.disqualified = True
        participant.disqualified_at = current_time

        self.event_bus.publish(
            "tournament_participant_disqualified",
            {
                "tournament_id": str(tournament_id),
                "player_id": str(player_id),
            },
        )

        for match in tournament.matches:
            if match.status not in (MatchStatus.SCHEDULED, MatchStatus.PENDING):
                continue
            opponent_id: UUID | None = None
            if match.player_a_id == player_id:
                opponent_id = match.player_b_id
            elif match.player_b_id == player_id:
                opponent_id = match.player_a_id
            if opponent_id is None:
                continue
            match.winner_id = opponent_id
            match.status = MatchStatus.COMPLETED
            match.resolved_at = current_time
            self._advance_winner(tournament, match, now=current_time)

        return TournamentResult.SUCCESS

    def pause_tournament(self, tournament_id: UUID) -> TournamentResult:
        """Admin: pause an in-progress tournament."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.IN_PROGRESS:
            return TournamentResult.INVALID_STATE
        tournament.status = TournamentStatus.PAUSED
        self.event_bus.publish("tournament_paused", tournament)
        return TournamentResult.SUCCESS

    def resume_tournament(self, tournament_id: UUID) -> TournamentResult:
        """Admin: resume a paused tournament."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status != TournamentStatus.PAUSED:
            return TournamentResult.INVALID_STATE
        tournament.status = TournamentStatus.IN_PROGRESS
        self.event_bus.publish("tournament_resumed", tournament)
        return TournamentResult.SUCCESS

    def cancel_tournament(
        self, tournament_id: UUID, *, reason: str = ""
    ) -> TournamentResult:
        """Admin: cancel a tournament and broadcast the reason."""
        tournament = self._find_tournament(tournament_id)
        if tournament is None:
            return TournamentResult.NOT_FOUND
        if tournament.status in (
            TournamentStatus.COMPLETED,
            TournamentStatus.CANCELLED,
        ):
            return TournamentResult.INVALID_STATE
        tournament.status = TournamentStatus.CANCELLED
        tournament.cancel_reason = reason
        self.event_bus.publish("tournament_cancelled", tournament)
        return TournamentResult.SUCCESS

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_log(self) -> dict[str, Any]:
        return {
            "tournaments": [t.to_dict() for t in self.tournaments],
        }

    def load_log(self, data: dict[str, Any]) -> None:
        tournaments: list[Tournament] = []
        for t_data in data.get("tournaments", []):
            if not isinstance(t_data, Mapping):
                continue
            try:
                tournaments.append(Tournament.from_dict(t_data))
            except (KeyError, TypeError, ValueError):
                continue
        self.tournaments = tournaments

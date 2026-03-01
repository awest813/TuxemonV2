from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class TournamentState(str, Enum):
    DRAFT = "draft"
    REGISTRATION = "registration"
    CHECKIN = "checkin"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Participant(BaseModel):
    id: str
    name: str
    registered_at: float
    checked_in: bool = False


class BracketNode(BaseModel):
    id: str
    player1_id: Optional[str] = None
    player2_id: Optional[str] = None
    winner_id: Optional[str] = None
    match_id: Optional[str] = None
    next_node_id: Optional[str] = None


class Match(BaseModel):
    id: str
    node_id: str
    player1_id: str
    player2_id: str
    winner_id: Optional[str] = None
    resolution_token: Optional[str] = None
    status: str = "pending"


class TournamentPolicy(BaseModel):
    min_players: int = 8
    max_players: int = 8
    team_size: int = 6
    level_cap: int = 50
    turn_timer: int = 60
    reconnect_grace: int = 90


class Tournament(BaseModel):
    id: str
    name: str
    state: TournamentState = TournamentState.DRAFT
    policy: TournamentPolicy = Field(default_factory=TournamentPolicy)
    participants: Dict[str, Participant] = Field(default_factory=dict)
    nodes: Dict[str, BracketNode] = Field(default_factory=dict)
    matches: Dict[str, Match] = Field(default_factory=dict)
    seed: Optional[int] = None
    champion_id: Optional[str] = None

    def transition(self, target_state: TournamentState) -> None:
        valid_transitions = {
            TournamentState.DRAFT: [
                TournamentState.REGISTRATION,
                TournamentState.CANCELLED,
            ],
            TournamentState.REGISTRATION: [
                TournamentState.CHECKIN,
                TournamentState.CANCELLED,
            ],
            TournamentState.CHECKIN: [
                TournamentState.IN_PROGRESS,
                TournamentState.CANCELLED,
            ],
            TournamentState.IN_PROGRESS: [
                TournamentState.COMPLETED,
                TournamentState.CANCELLED,
            ],
            TournamentState.COMPLETED: [],
            TournamentState.CANCELLED: [],
        }
        if target_state not in valid_transitions[self.state]:
            raise ValueError(
                f"Cannot transition from {self.state} to {target_state}"
            )
        self.state = target_state

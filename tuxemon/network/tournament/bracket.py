import random
from typing import Dict, List, Optional

from tuxemon.network.tournament.models import (
    BracketNode,
    Match,
    Tournament,
    TournamentState,
)


def _generate_bracket_nodes(bracket_size: int) -> Dict[str, BracketNode]:
    """Generates the structure of a single-elimination bracket."""
    nodes = {}
    total_nodes = bracket_size - 1

    # Generate nodes
    for i in range(1, total_nodes + 1):
        node_id = f"node_{i}"
        nodes[node_id] = BracketNode(id=node_id)

    # Link nodes bottom up
    current_level_nodes = [
        f"node_{i}" for i in range(1, (bracket_size // 2) + 1)
    ]
    next_node_index = (bracket_size // 2) + 1

    while len(current_level_nodes) > 1:
        next_level_nodes = []
        for i in range(0, len(current_level_nodes), 2):
            if i + 1 < len(current_level_nodes):
                parent_id = f"node_{next_node_index}"
                nodes[current_level_nodes[i]].next_node_id = parent_id
                nodes[current_level_nodes[i + 1]].next_node_id = parent_id
                next_level_nodes.append(parent_id)
                next_node_index += 1
            else:
                next_level_nodes.append(current_level_nodes[i])
        current_level_nodes = next_level_nodes

    return nodes


def generate_bracket(tournament: Tournament) -> None:
    """Generates a seeded bracket from checked-in participants."""
    if tournament.state != TournamentState.CHECKIN:
        raise ValueError(
            f"Cannot generate bracket in state {tournament.state}"
        )

    # Ensure seeding determinism
    rng = random.Random(tournament.seed)

    checked_in_players = [
        p for p in tournament.participants.values() if p.checked_in
    ]

    if len(checked_in_players) < tournament.policy.min_players:
        tournament.transition(TournamentState.CANCELLED)
        return

    # We only support exact powers of 2 for now
    bracket_size = tournament.policy.max_players

    # Sort by registration timestamp then by id for tie-breaking
    checked_in_players.sort(key=lambda p: (p.registered_at, p.id))
    players = [p.id for p in checked_in_players]

    # Pad with Byes (None)
    while len(players) < bracket_size:
        players.append(None)  # type: ignore

    # Shuffle for seeding
    rng.shuffle(players)

    tournament.nodes = _generate_bracket_nodes(bracket_size)
    tournament.matches = {}

    # Assign players to the first round nodes
    first_round_nodes = [
        node
        for node in tournament.nodes.values()
        if int(node.id.split("_")[1]) <= bracket_size // 2
    ]

    for i, node in enumerate(first_round_nodes):
        p1 = players[i * 2]
        p2 = players[i * 2 + 1]
        node.player1_id = p1
        node.player2_id = p2

        # Handle byes immediately
        if p1 and not p2:
            _resolve_node(tournament, node.id, p1)
        elif p2 and not p1:
            _resolve_node(tournament, node.id, p2)
        elif not p1 and not p2:
            _resolve_node(tournament, node.id, None)  # Both byes

    _schedule_ready_matches(tournament)


def _schedule_ready_matches(tournament: Tournament) -> None:
    """Creates pending matches for unresolved nodes with both players set."""
    for node in tournament.nodes.values():
        if node.winner_id is not None:
            continue
        if not node.player1_id or not node.player2_id:
            continue
        if node.match_id:
            continue

        match_id = f"match_{node.id}"
        tournament.matches[match_id] = Match(
            id=match_id,
            node_id=node.id,
            player1_id=node.player1_id,
            player2_id=node.player2_id,
        )
        node.match_id = match_id


def get_ready_matches(tournament: Tournament) -> List[Match]:
    """Returns pending matches available for orchestration/service dispatch."""
    return [m for m in tournament.matches.values() if m.status == "pending"]


def _resolve_node(
    tournament: Tournament, node_id: str, winner_id: Optional[str]
) -> None:
    """Advances a winner to the next node in the bracket."""
    node = tournament.nodes[node_id]
    node.winner_id = winner_id

    if not node.next_node_id:
        if winner_id:
            tournament.champion_id = winner_id
            tournament.transition(TournamentState.COMPLETED)
        if node.match_id:
            match = tournament.matches[node.match_id]
            match.status = "completed"
            match.winner_id = winner_id
        return

    next_node = tournament.nodes[node.next_node_id]

    if next_node.player1_id is None:
        next_node.player1_id = winner_id
    elif next_node.player2_id is None:
        next_node.player2_id = winner_id

        # Check if we need to auto-advance the next node due to a bye
        if not next_node.player1_id and next_node.player2_id:
            _resolve_node(tournament, next_node.id, next_node.player2_id)
        elif next_node.player1_id and not next_node.player2_id:
            _resolve_node(tournament, next_node.id, next_node.player1_id)
        elif not next_node.player1_id and not next_node.player2_id:
            _resolve_node(tournament, next_node.id, None)

    if node.match_id:
        match = tournament.matches[node.match_id]
        match.status = "completed"
        match.winner_id = winner_id

    _schedule_ready_matches(tournament)


def process_match_result(
    tournament: Tournament, node_id: str, winner_id: str, resolution_token: str
) -> None:
    """Processes a match result idempotently."""
    node = tournament.nodes[node_id]
    match = tournament.matches.get(node.match_id) if node.match_id else None

    if node.winner_id:
        if node.winner_id != winner_id:
            raise ValueError("Conflicting match result")
        if match and match.resolution_token != resolution_token:
            raise ValueError("Conflicting resolution token")
        return

    if tournament.state != TournamentState.IN_PROGRESS:
        raise ValueError("Tournament is not in progress")

    if winner_id not in [node.player1_id, node.player2_id]:
        raise ValueError("Winner must be a player in the match")

    if match:
        if (
            match.resolution_token is not None
            and match.resolution_token != resolution_token
        ):
            raise ValueError("Conflicting resolution token")
        match.resolution_token = resolution_token

    _resolve_node(tournament, node_id, winner_id)

import pytest

from tuxemon.network.tournament.bracket import (
    generate_bracket,
    process_match_result,
)
from tuxemon.network.tournament.models import (
    Participant,
    Tournament,
    TournamentState,
)


def test_full_bracket_simulation():
    # Setup
    t = Tournament(id="sim1", name="Sim Tourney")
    t.transition(TournamentState.REGISTRATION)

    # Register and Check-in 8 players
    for i in range(8):
        t.participants[f"p{i}"] = Participant(
            id=f"p{i}", name=f"Player {i}", registered_at=i, checked_in=True
        )

    t.transition(TournamentState.CHECKIN)
    t.seed = 12345

    # Generate Bracket
    generate_bracket(t)
    t.transition(TournamentState.IN_PROGRESS)

    assert len(t.nodes) == 7

    # First Round (nodes 1-4)
    for i in range(1, 5):
        node = t.nodes[f"node_{i}"]
        assert node.player1_id is not None
        assert node.player2_id is not None
        assert node.winner_id is None

        # Simulate player 1 winning each match
        process_match_result(t, node.id, node.player1_id, "token")

    # Second Round (nodes 5-6)
    for i in range(5, 7):
        node = t.nodes[f"node_{i}"]
        assert node.player1_id is not None
        assert node.player2_id is not None
        assert node.winner_id is None

        # Simulate player 2 winning
        process_match_result(t, node.id, node.player2_id, "token")

    # Final (node 7)
    node = t.nodes["node_7"]
    assert node.player1_id is not None
    assert node.player2_id is not None
    assert node.winner_id is None

    process_match_result(t, node.id, node.player1_id, "token")

    # Verify completion
    assert t.state == TournamentState.COMPLETED
    assert t.champion_id == node.player1_id


def test_idempotent_result():
    t = Tournament(id="sim2", name="Sim")
    t.transition(TournamentState.REGISTRATION)
    t.participants["p1"] = Participant(
        id="p1", name="P1", registered_at=1, checked_in=True
    )
    t.participants["p2"] = Participant(
        id="p2", name="P2", registered_at=2, checked_in=True
    )
    t.policy.min_players = 2
    t.policy.max_players = 2
    t.transition(TournamentState.CHECKIN)
    t.seed = 1

    generate_bracket(t)
    t.transition(TournamentState.IN_PROGRESS)

    node = t.nodes["node_1"]

    # First result
    process_match_result(t, node.id, node.player1_id, "token1")
    assert node.winner_id == node.player1_id

    # Duplicate result, same winner (idempotent)
    process_match_result(t, node.id, node.player1_id, "token2")
    assert node.winner_id == node.player1_id

    # Conflicting result
    with pytest.raises(ValueError):
        process_match_result(t, node.id, node.player2_id, "token3")

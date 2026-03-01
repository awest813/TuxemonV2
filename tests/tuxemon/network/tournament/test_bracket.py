from tuxemon.network.tournament.bracket import (
    _generate_bracket_nodes,
    generate_bracket,
)
from tuxemon.network.tournament.models import (
    Participant,
    Tournament,
    TournamentState,
)


def test_generate_nodes():
    nodes = _generate_bracket_nodes(8)
    assert len(nodes) == 7

    # Bottom level: nodes 1-4
    for i in range(1, 5):
        assert nodes[f"node_{i}"].next_node_id == f"node_{(i - 1) // 2 + 5}"

    # Semi-finals: nodes 5, 6 -> point to node 7
    assert nodes["node_5"].next_node_id == "node_7"
    assert nodes["node_6"].next_node_id == "node_7"

    # Finals: node 7 has no next
    assert nodes["node_7"].next_node_id is None


def test_generate_bracket_success():
    t = Tournament(id="t1", name="Test")
    t.transition(TournamentState.REGISTRATION)

    # Add 8 players
    for i in range(8):
        t.participants[f"p{i}"] = Participant(
            id=f"p{i}", name=f"Player {i}", registered_at=i, checked_in=True
        )

    t.transition(TournamentState.CHECKIN)
    t.seed = 42

    generate_bracket(t)

    assert len(t.nodes) == 7
    # Since 8 players, no auto-advancements initially
    for i in range(1, 5):
        node = t.nodes[f"node_{i}"]
        assert node.player1_id is not None
        assert node.player2_id is not None
        assert node.winner_id is None


def test_generate_bracket_with_byes():
    t = Tournament(id="t1", name="Test")
    t.transition(TournamentState.REGISTRATION)

    # Add 5 players (3 byes)
    for i in range(5):
        t.participants[f"p{i}"] = Participant(
            id=f"p{i}", name=f"Player {i}", registered_at=i, checked_in=True
        )

    # Minimum players is 8 by default, let's change to 4
    t.policy.min_players = 4
    t.transition(TournamentState.CHECKIN)
    t.seed = 42

    generate_bracket(t)

    assert len(t.nodes) == 7

    # Check that some nodes auto-advanced
    auto_advanced = sum(1 for n in t.nodes.values() if n.winner_id is not None)
    assert auto_advanced > 0


def test_generate_bracket_insufficient_players():
    t = Tournament(id="t1", name="Test")
    t.transition(TournamentState.REGISTRATION)

    for i in range(3):  # Below default min of 8
        t.participants[f"p{i}"] = Participant(
            id=f"p{i}", name=f"Player {i}", registered_at=i, checked_in=True
        )

    t.transition(TournamentState.CHECKIN)

    generate_bracket(t)

    assert t.state == TournamentState.CANCELLED

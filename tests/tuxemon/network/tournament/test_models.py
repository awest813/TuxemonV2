import pytest

from tuxemon.network.tournament.models import (
    Participant,
    Tournament,
    TournamentState,
)


def test_tournament_creation():
    t = Tournament(id="t1", name="Test Tourney")
    assert t.state == TournamentState.DRAFT
    assert t.policy.min_players == 8
    assert t.policy.team_size == 6


def test_valid_state_transitions():
    t = Tournament(id="t1", name="Test Tourney")
    t.transition(TournamentState.REGISTRATION)
    assert t.state == TournamentState.REGISTRATION
    t.transition(TournamentState.CHECKIN)
    assert t.state == TournamentState.CHECKIN
    t.transition(TournamentState.IN_PROGRESS)
    assert t.state == TournamentState.IN_PROGRESS
    t.transition(TournamentState.COMPLETED)
    assert t.state == TournamentState.COMPLETED


def test_invalid_state_transitions():
    t = Tournament(id="t1", name="Test Tourney")
    with pytest.raises(ValueError):
        t.transition(TournamentState.IN_PROGRESS)


def test_cancellation():
    for state in [
        TournamentState.DRAFT,
        TournamentState.REGISTRATION,
        TournamentState.CHECKIN,
        TournamentState.IN_PROGRESS,
    ]:
        t = Tournament(id="t1", name="Test Tourney")
        t.state = state
        t.transition(TournamentState.CANCELLED)
        assert t.state == TournamentState.CANCELLED


def test_add_participant():
    t = Tournament(id="t1", name="Test Tourney")
    p = Participant(id="p1", name="Player 1", registered_at=100.0)
    t.participants["p1"] = p
    assert "p1" in t.participants
    assert not t.participants["p1"].checked_in

    t.participants["p1"].checked_in = True
    assert t.participants["p1"].checked_in

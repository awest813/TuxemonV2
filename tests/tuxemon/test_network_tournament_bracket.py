from tuxemon.network.tournament.bracket import (
    generate_bracket,
    get_ready_matches,
    process_match_result,
)
from tuxemon.network.tournament.models import (
    Participant,
    Tournament,
    TournamentPolicy,
    TournamentState,
)


def _make_tournament(*, min_players: int = 8, max_players: int = 8) -> Tournament:
    return Tournament(
        id="t-1",
        name="Online Cup",
        state=TournamentState.CHECKIN,
        seed=77,
        policy=TournamentPolicy(min_players=min_players, max_players=max_players),
    )


def _add_checked_in_players(tournament: Tournament, count: int) -> None:
    for i in range(count):
        pid = f"player-{i + 1}"
        tournament.participants[pid] = Participant(
            id=pid,
            name=f"Player {i + 1}",
            registered_at=float(i),
            checked_in=True,
        )


def test_generate_bracket_transitions_to_in_progress_and_schedules_matches() -> None:
    tournament = _make_tournament(min_players=8, max_players=8)
    _add_checked_in_players(tournament, 8)

    generate_bracket(tournament)

    assert tournament.state == TournamentState.IN_PROGRESS
    ready_matches = get_ready_matches(tournament)
    assert len(ready_matches) == 4


def test_process_match_result_is_usable_after_generation() -> None:
    tournament = _make_tournament(min_players=8, max_players=8)
    _add_checked_in_players(tournament, 8)

    generate_bracket(tournament)

    ready_match = get_ready_matches(tournament)[0]
    process_match_result(
        tournament,
        node_id=ready_match.node_id,
        winner_id=ready_match.player1_id,
        resolution_token="token-1",
    )

    match_after = tournament.matches[ready_match.id]
    assert match_after.status == "completed"
    assert match_after.winner_id == ready_match.player1_id


def test_generate_bracket_cancels_when_minimum_players_not_met() -> None:
    tournament = _make_tournament(min_players=8, max_players=8)
    _add_checked_in_players(tournament, 7)

    generate_bracket(tournament)

    assert tournament.state == TournamentState.CANCELLED

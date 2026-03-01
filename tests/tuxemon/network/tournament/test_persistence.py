from tuxemon.network.tournament.models import (
    Participant,
    Tournament,
    TournamentState,
)
from tuxemon.network.tournament.persistence import (
    load_tournament,
    save_tournament,
)


def test_save_and_load(tmp_path):
    t = Tournament(id="t1", name="Test Tourney")
    t.transition(TournamentState.REGISTRATION)
    t.participants["p1"] = Participant(
        id="p1", name="P1", registered_at=100.0, checked_in=True
    )
    t.seed = 42

    file_path = tmp_path / "t1.json"

    save_tournament(t, file_path)

    assert file_path.exists()

    loaded_t = load_tournament(file_path)

    assert loaded_t is not None
    assert loaded_t.id == "t1"
    assert loaded_t.name == "Test Tourney"
    assert loaded_t.state == TournamentState.REGISTRATION
    assert "p1" in loaded_t.participants
    assert loaded_t.participants["p1"].checked_in
    assert loaded_t.seed == 42

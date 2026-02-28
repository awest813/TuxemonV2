from types import SimpleNamespace
from unittest.mock import patch

from tuxemon.network.networking import EventData, EventType
from tuxemon.states.world_state import WorldState


def make_world_state() -> WorldState:
    state = WorldState.__new__(WorldState)
    state.client = SimpleNamespace()
    return state


def test_handle_interaction_duel_invite_opens_dialog() -> None:
    state = make_world_state()
    event_data = EventData(
        type=EventType.CLIENT_INTERACTION,
        event_number=1,
        cuuid="remote-a",
        interaction="DUEL",
    )
    registry = {"remote-a": {"sprite": SimpleNamespace(name="Rival")}}

    with patch("tuxemon.network.networking.update_client") as mock_update, patch(
        "tuxemon.states.world_state.open_dialog"
    ) as mock_dialog, patch(
        "tuxemon.states.world_state.T.translate",
        side_effect=lambda key: key,
    ), patch(
        "tuxemon.states.world_state.T.format",
        side_effect=lambda key, params: f"{key}:{params['name']}",
    ):
        state.handle_interaction(event_data, registry)

    mock_update.assert_called_once()
    mock_dialog.assert_called_once_with(
        state.client,
        [
            "multiplayer_duel_invite_received:Rival",
            "multiplayer_duel_invite_hint",
        ],
    )


def test_handle_interaction_ignores_unknown_client() -> None:
    state = make_world_state()
    event_data = EventData(
        type=EventType.CLIENT_INTERACTION,
        event_number=1,
        cuuid="missing",
        interaction="DUEL",
    )

    with patch("tuxemon.network.networking.update_client") as mock_update, patch(
        "tuxemon.states.world_state.open_dialog"
    ) as mock_dialog:
        state.handle_interaction(event_data, {})

    mock_update.assert_not_called()
    mock_dialog.assert_not_called()

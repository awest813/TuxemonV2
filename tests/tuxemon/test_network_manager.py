from unittest.mock import MagicMock, patch

from tuxemon.network.manager import NetworkManager


def make_manager() -> tuple[NetworkManager, MagicMock]:
    parent = MagicMock()
    parent.get_map_name.return_value = "test_map"
    parent.npc_manager = MagicMock()
    manager = NetworkManager(parent)
    return manager, parent


def test_update_delegates_to_active_client() -> None:
    manager, parent = make_manager()
    client = MagicMock()
    client.listening = True
    client.registry = {"abc": {"sprite": MagicMock()}}
    client.consume_feedback.return_value = []
    manager.client = client

    manager.update(0.016)

    client.update.assert_called_once()
    parent.npc_manager.add_clients_to_map.assert_called_once_with(
        client.registry, "test_map"
    )


def test_update_opens_dialog_for_queued_feedback() -> None:
    manager, parent = make_manager()
    client = MagicMock()
    client.listening = False
    client.consume_feedback.return_value = [
        ("multiplayer_connect_failed", "multiplayer_retry_hint")
    ]
    manager.client = client

    with patch("tuxemon.network.manager.open_dialog") as mock_dialog, patch(
        "tuxemon.network.manager.T.translate",
        side_effect=lambda key: key,
    ):
        manager.update(0.016)

    mock_dialog.assert_called_once_with(
        parent,
        ["multiplayer_connect_failed", "multiplayer_retry_hint"],
    )


def test_update_skips_dialog_when_no_feedback() -> None:
    manager, _ = make_manager()
    client = MagicMock()
    client.listening = False
    client.consume_feedback.return_value = []
    manager.client = client

    with patch("tuxemon.network.manager.open_dialog") as mock_dialog:
        manager.update(0.016)

    mock_dialog.assert_not_called()

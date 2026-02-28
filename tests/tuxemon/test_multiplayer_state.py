from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from tuxemon.multiplayer_battle_manager import MultiplayerBattleManager
from tuxemon.states.multiplayer import MultiplayerMenu, MultiplayerSelect


class DummyClient:
    def __init__(self):
        self.popped_state = None

    def pop_state(self, state):
        self.popped_state = state


class DummyNetworkClient:
    def __init__(self):
        self.server_list = ["Local Test Server"]
        self.available_games = [("127.0.0.1", 40081)]
        self.connected_to = None

    def connect_to_host(self, ip, port):
        self.connected_to = (ip, port)


class DummyMenuItem:
    def __init__(self, image, game_object, description, game_object_menu):
        self.image = image
        self.game_object = game_object
        self.description = description
        self.game_object_menu = game_object_menu
        self.enabled = True


def make_state() -> MultiplayerSelect:
    state = MultiplayerSelect.__new__(MultiplayerSelect)
    state.client = DummyClient()
    state.network = SimpleNamespace(client=DummyNetworkClient())
    state.shadow_text = lambda text: text
    return state


def test_initialize_items_builds_join_entries():
    state = make_state()

    with patch("tuxemon.states.multiplayer.MenuItem", DummyMenuItem):
        items = list(state.initialize_items())

    assert len(items) == 1
    assert items[0].game_object == ("127.0.0.1", 40081)
    assert items[0].description == "Local Test Server"
    assert callable(items[0].game_object_menu)


def test_join_selected_server_connects_and_closes_menu():
    state = make_state()

    state._join_selected_server(("127.0.0.1", 40081))

    assert state.network.client.connected_to == ("127.0.0.1", 40081)
    assert state.client.popped_state is state


def test_initialize_items_disables_menu_when_server_data_is_out_of_sync():
    state = make_state()
    state.network.client.available_games = []

    with patch("tuxemon.states.multiplayer.MenuItem", DummyMenuItem):
        items = list(state.initialize_items())

    assert len(items) == 1
    assert items[0].enabled is False


class DummyMenuNetworkClient(DummyNetworkClient):
    def __init__(self):
        super().__init__()
        self.selected_game = None


class DummyMenuClient:
    def __init__(self, manager=None):
        self.dialogs = []
        self.pushed_state = None
        self.push_kwargs = {}
        self.multiplayer_battle_manager = manager or MultiplayerBattleManager()

    def push_state(self, state, **kwargs):
        self.pushed_state = state
        self.push_kwargs = kwargs


def make_menu_state(
    is_host: bool = False, manager: MultiplayerBattleManager | None = None
) -> MultiplayerMenu:
    state = MultiplayerMenu.__new__(MultiplayerMenu)
    state.client = DummyMenuClient(manager=manager)
    state.network = SimpleNamespace(
        client=DummyMenuNetworkClient(),
        is_host=lambda: is_host,
    )
    state._last_challenge_id = None
    return state


def test_join_warns_when_hosting():
    state = make_menu_state(is_host=True)

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.join()

    assert state.network.client.connected_to is None
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_join_unavailable_host"]
    )


def test_join_warns_when_no_server_selected():
    state = make_menu_state()

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.join()

    assert state.network.client.connected_to is None
    mock_dialog.assert_called_once_with(
        state.client,
        ["multiplayer_join_missing_target", "multiplayer_retry_hint"],
    )


def test_join_connects_and_shows_connecting_status():
    state = make_menu_state()
    state.network.client.selected_game = ("127.0.0.1", 40081)

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.join()

    assert state.network.client.connected_to == ("127.0.0.1", 40081)
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_connecting_status"]
    )


def test_join_last_server_uses_previous_selection():
    state = make_menu_state()
    state.network.client.selected_game = ("127.0.0.1", 40081)

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.join_last_server()

    assert state.network.client.connected_to == ("127.0.0.1", 40081)
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_connecting_status"]
    )


def test_join_last_server_warns_when_no_previous_selection():
    state = make_menu_state()

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.join_last_server()

    assert state.network.client.connected_to is None
    mock_dialog.assert_called_once_with(
        state.client,
        ["multiplayer_join_missing_target", "multiplayer_retry_hint"],
    )


def test_join_by_ip_pushes_input_menu_with_callback():
    state = make_menu_state()

    with patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.join_by_ip()

    assert state.client.pushed_state == "InputMenu"
    assert state.client.push_kwargs["prompt"] == "multiplayer_join_prompt"
    assert callable(state.client.push_kwargs["callback"])


def test_join_by_ip_callback_parses_host_and_connects():
    state = make_menu_state()

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state._join_by_ip_input(" 127.0.0.1:40123 ")

    assert state.network.client.selected_game == ("127.0.0.1", 40123)
    assert state.network.client.connected_to == ("127.0.0.1", 40123)
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_connecting_status"]
    )


def test_join_by_ip_callback_uses_default_port_when_omitted():
    state = make_menu_state()

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state._join_by_ip_input("example.local")

    assert state.network.client.selected_game == ("example.local", 40081)
    assert state.network.client.connected_to == ("example.local", 40081)
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_connecting_status"]
    )


def test_join_by_ip_callback_shows_retry_on_invalid_target():
    state = make_menu_state()

    with patch("tuxemon.states.multiplayer.open_dialog") as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state._join_by_ip_input("127.0.0.1:notaport")

    assert state.network.client.selected_game is None
    assert state.network.client.connected_to is None
    mock_dialog.assert_called_once_with(
        state.client,
        ["multiplayer_join_missing_target", "multiplayer_retry_hint"],
    )


def test_challenge_by_uuid_pushes_input_menu_with_callback():
    state = make_menu_state()

    with patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ):
        state.challenge_by_uuid()

    assert state.client.pushed_state == "InputMenu"
    assert state.client.push_kwargs["prompt"] == "multiplayer_challenge_prompt"
    assert callable(state.client.push_kwargs["callback"])


def test_challenge_by_uuid_callback_shows_retry_on_invalid_uuid():
    manager = MultiplayerBattleManager()
    state = make_menu_state(manager=manager)
    player_id = uuid4()
    fake_local_session = SimpleNamespace(
        has_player=lambda: True,
        player=SimpleNamespace(instance_id=player_id),
    )

    with patch("tuxemon.states.multiplayer.local_session", fake_local_session), patch(
        "tuxemon.states.multiplayer.open_dialog"
    ) as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ), patch(
        "tuxemon.states.multiplayer.T.format",
        side_effect=lambda key, params: f"{key}:{params}",
    ):
        state._challenge_by_uuid_input("not-a-uuid")

    assert manager.pending_challenges == []
    mock_dialog.assert_called_once_with(
        state.client,
        ["multiplayer_invalid_player_uuid", "multiplayer_retry_hint"],
    )


def test_challenge_by_uuid_callback_creates_pending_challenge():
    manager = MultiplayerBattleManager()
    state = make_menu_state(manager=manager)
    player_id = uuid4()
    challenged_id = uuid4()
    fake_local_session = SimpleNamespace(
        has_player=lambda: True,
        player=SimpleNamespace(instance_id=player_id),
    )

    with patch("tuxemon.states.multiplayer.local_session", fake_local_session), patch(
        "tuxemon.states.multiplayer.open_dialog"
    ) as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ), patch(
        "tuxemon.states.multiplayer.T.format",
        side_effect=lambda key, params: f"{key}:{params}",
    ):
        state._challenge_by_uuid_input(str(challenged_id))

    assert len(manager.pending_challenges) == 1
    challenge = manager.pending_challenges[0]
    assert challenge.challenger_player_id == player_id
    assert challenge.challenged_player_id == challenged_id
    assert state._last_challenge_id == challenge.challenge_id
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_feedback_challenge_sent"]
    )


def test_accept_latest_challenge_starts_battle_session():
    manager = MultiplayerBattleManager()
    state = make_menu_state(manager=manager)
    player_id = uuid4()
    challenger = uuid4()
    fake_local_session = SimpleNamespace(
        has_player=lambda: True,
        player=SimpleNamespace(instance_id=player_id),
    )
    manager.propose_challenge(challenger, player_id)
    challenge = manager.pending_challenges[0]

    with patch("tuxemon.states.multiplayer.local_session", fake_local_session), patch(
        "tuxemon.states.multiplayer.open_dialog"
    ) as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ), patch(
        "tuxemon.states.multiplayer.T.format",
        side_effect=lambda key, params: f"{key}:{params}",
    ):
        state.accept_latest_challenge()

    assert manager.pending_challenges == []
    assert len(manager.active_battle_sessions) == 1
    assert state._last_challenge_id == challenge.challenge_id
    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_feedback_challenge_accepted"]
    )


def test_check_active_battle_status_warns_without_active_session():
    manager = MultiplayerBattleManager()
    state = make_menu_state(manager=manager)
    player_id = uuid4()
    fake_local_session = SimpleNamespace(
        has_player=lambda: True,
        player=SimpleNamespace(instance_id=player_id),
    )

    with patch("tuxemon.states.multiplayer.local_session", fake_local_session), patch(
        "tuxemon.states.multiplayer.open_dialog"
    ) as mock_dialog, patch(
        "tuxemon.states.multiplayer.T.translate",
        side_effect=lambda key: key,
    ), patch(
        "tuxemon.states.multiplayer.T.format",
        side_effect=lambda key, params: f"{key}:{params}",
    ):
        state.check_active_battle_status()

    mock_dialog.assert_called_once_with(
        state.client, ["multiplayer_no_active_battle"]
    )

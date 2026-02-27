from types import SimpleNamespace
from unittest.mock import patch

from tuxemon.states.multiplayer import MultiplayerSelect


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

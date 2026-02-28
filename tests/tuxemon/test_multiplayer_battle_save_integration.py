# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from types import SimpleNamespace
from unittest.mock import MagicMock

from tuxemon.save import get_save_data
from tuxemon.save_state import NPCState, SaveData, SessionSave, WorldSave
from tuxemon.session import Session


class DummyScreenshot:
    def get_width(self) -> int:
        return 1

    def get_height(self) -> int:
        return 1


def test_get_save_data_includes_multiplayer_battles(monkeypatch) -> None:
    player_state = NPCState(player_name="Player")
    world_state = WorldSave()
    session_state = SessionSave(uuid="abc")
    multiplayer_log = {
        "pending_challenges": [],
        "default_challenge_ttl_seconds": 180,
    }

    session = SimpleNamespace(
        player=SimpleNamespace(get_state=MagicMock(return_value=player_state)),
        world=SimpleNamespace(get_state=MagicMock(return_value=world_state)),
        get_state=MagicMock(return_value=session_state),
        client=SimpleNamespace(
            npc_manager=SimpleNamespace(
                get_persistent_npc_states=MagicMock(return_value=[])
            ),
            shop_manager=SimpleNamespace(
                dump_to_dict=MagicMock(return_value={"shop": {}})
            ),
            multiplayer_battle_manager=SimpleNamespace(
                save_log=MagicMock(return_value=multiplayer_log)
            ),
        ),
    )

    monkeypatch.setattr(
        "tuxemon.save.capture_screenshot", lambda _s: DummyScreenshot()
    )
    monkeypatch.setattr("tuxemon.save.tobytes", lambda _img, _fmt: b"rgb")

    save_data = get_save_data(session)

    assert save_data.multiplayer_battles == multiplayer_log


def test_session_load_state_restores_multiplayer_log() -> None:
    session = Session()
    session._player = SimpleNamespace(set_state=MagicMock())
    session._world = SimpleNamespace(set_state=MagicMock())

    multiplayer_manager = SimpleNamespace(load_log=MagicMock())
    session._client = SimpleNamespace(
        shop_manager=SimpleNamespace(load_from_dict=MagicMock()),
        multiplayer_battle_manager=multiplayer_manager,
        npc_manager=SimpleNamespace(load_persistent_npc_states=MagicMock()),
    )

    save_data = SaveData(
        npc_state=NPCState(),
        world_state=WorldSave(),
        session_state=SessionSave(),
        shop_stock={"shop": {}},
        multiplayer_battles={
            "pending_challenges": [],
            "default_challenge_ttl_seconds": 90,
        },
    )

    session.load_state(save_data)

    multiplayer_manager.load_log.assert_called_once_with(
        save_data.multiplayer_battles
    )

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import json
from pathlib import Path

from tuxemon import save
from tuxemon.save_state import NPCState, SaveData, SessionSave, WorldSave
from tuxemon.save_upgrader import SAVE_VERSION, upgrade_save


def _campaign_npc_state() -> dict[str, object]:
    return {
        "player_name": "ImporterTester",
        "player_slug": "player",
        "current_map": "campaign/maps/start.tmx",
        "tile_pos": [3, 7],
        "facing": "down",
        "monsters": [],
        "items": [],
        "tuxepedia": {},
        "game_variables": {
            "campaign_id": "imported_alpha",
            "campaign_story_flag": "met_professor",
        },
        "money": {"money": 100, "bank_account": 5, "bills": {}},
        "monster_boxes": {},
        "item_boxes": {},
        "relationships": {},
        "appearance": {
            "sprite_name": "adventurer",
            "combat_sheet": "adventurer",
        },
    }


def test_campaign_import_roundtrip_save_and_reload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(save.config, "save_method", "json")
    monkeypatch.setattr(save.config, "compress_save", None)

    save_path = tmp_path / "slot1.save"
    original = SaveData(
        screenshot=None,
        screenshot_width=None,
        screenshot_height=None,
        time="2026-07-11 12:34",
        version=SAVE_VERSION,
        npc_state=NPCState(**_campaign_npc_state()),
        world_state=WorldSave(menu_flags={"menu_save": True}),
        session_state=SessionSave(uuid="session-1", total_playtime=90.0),
        shop_stock={"campaign_shop": {"potion": 3}},
        multiplayer_battles={},
        persistent_state=[],
    )

    save.save(original, save_path)
    reloaded = save.load(save_path)

    assert reloaded is not None
    assert reloaded.version == SAVE_VERSION
    assert reloaded.npc_state is not None
    assert reloaded.npc_state.game_variables["campaign_id"] == "imported_alpha"
    assert reloaded.world_state is not None
    assert reloaded.world_state.menu_flags["menu_save"] is True


def test_mixed_version_campaign_save_upgrade_preserves_state() -> None:
    mixed_version_import = {
        "screenshot": None,
        "screenshot_width": 1,
        "screenshot_height": 1,
        "time": "2026-06-01 08:00",
        "version": 1,
        "npc_state": {
            **_campaign_npc_state(),
            "contacts": {"quest_giver": "met"},
            "money": {"player": 250, "bank_account": 10, "bill_tax": 2},
        },
        "world_state": {"menu_flags": {"menu_load": True}},
        "session_state": {"uuid": "abc", "total_playtime": 5.0},
        "shop_stock": {},
        "multiplayer_battles": {},
        "persistent_state": [],
    }

    upgraded = upgrade_save(mixed_version_import)

    assert upgraded["version"] == SAVE_VERSION
    assert upgraded["npc_state"]["relationships"] == {
        "quest_giver": {"relationship_type": "unknown"}
    }
    assert upgraded["npc_state"]["money"] == {
        "money": 250,
        "bank_account": 10,
        "bills": {"bill_tax": {"amount": 2}},
    }
    assert upgraded["world_state"] == {"menu_flags": {"menu_load": True}}
    assert upgraded["session_state"] == {"uuid": "abc", "total_playtime": 5.0}


def test_migration_failure_creates_backup_and_returns_none(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    monkeypatch.setattr(save.config, "save_method", "json")
    monkeypatch.setattr(save.config, "compress_save", None)

    broken_save_path = tmp_path / "broken.save"
    broken_payload = {
        "screenshot": None,
        "screenshot_width": 1,
        "screenshot_height": 1,
        "time": "2026-06-01 08:00",
        "version": 1,
        "npc_state": {
            "monsters": [],
            "items": [],
            "money": {"player": 100},
            "monster_boxes": {},
            "item_boxes": {},
            "game_variables": {},
            # Missing tuxepedia triggers migration failure in v1 -> v2 upgrader.
        },
    }
    broken_save_path.write_text(json.dumps(broken_payload), encoding="utf-8")

    loaded = save.load(broken_save_path)

    assert loaded is None
    backups = list(tmp_path.glob("broken.save.migration_failed_*.bak"))
    assert len(backups) == 1
    assert "Failed to migrate save" in caplog.text
    assert "Backup created" in caplog.text

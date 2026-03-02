# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Save compatibility test matrix.

Regression tests for old/new save migrations around trade and multiplayer
logs, including malformed-history fixtures to preserve tolerant loading.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from tuxemon.multiplayer_battle_manager import (
    BattleResolution,
    MultiplayerBattleManager,
)
from tuxemon.save_state import SaveData
from tuxemon.save_upgrader import SAVE_VERSION, upgrade_save
from tuxemon.trade_manager import TradeManager

# ---------------------------------------------------------------------------
# Fixtures: canonical save data at various schema versions
# ---------------------------------------------------------------------------


def _minimal_npc_state(**overrides):
    base = {
        "player_name": "Tester",
        "current_map": "test_map.tmx",
        "tile_pos": [5, 5],
        "facing": "down",
        "monsters": [],
        "items": [],
        "tuxepedia": {},
        "game_variables": {},
        "money": {"money": 100, "bank_account": 0, "bills": {}},
        "monster_boxes": {},
        "item_boxes": {},
        "relationships": {},
        "appearance": {
            "sprite_name": "adventurer",
            "combat_sheet": "adventurer",
        },
    }
    base.update(overrides)
    return base


def _v3_save_data(**overrides):
    """Build a version-3 save with defaults and optional overrides."""
    data = {
        "screenshot": None,
        "screenshot_width": None,
        "screenshot_height": None,
        "time": "2026-01-15 12:00",
        "version": 3,
        "npc_state": _minimal_npc_state(),
        "world_state": {},
        "session_state": {"uuid": "abc", "start_time": None, "duration": 0},
        "shop_stock": {},
        "multiplayer_battles": {},
        "persistent_state": [],
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Test: save upgrader preserves version and applies fixes
# ---------------------------------------------------------------------------


class TestSaveUpgrader:
    def test_v0_save_upgrades_to_current(self):
        old_save = {
            "screenshot": None,
            "screenshot_width": 1,
            "screenshot_height": 1,
            "time": "2024-01-01 00:00",
            "version": 0,
            "player_name": "Old Player",
            "tile_pos": [0, 0],
            "facing": "down",
            "monsters": [],
            "items": [],
            "tuxepedia": {},
            "game_variables": {},
            "money": {"player": 500},
            "monster_boxes": {},
            "item_boxes": {},
            "contacts": {},
            "teleport_faint": {},
        }
        upgraded = upgrade_save(old_save)
        assert upgraded["version"] == SAVE_VERSION
        assert "npc_state" in upgraded

    def test_current_version_save_unchanged(self):
        save = _v3_save_data()
        upgraded = upgrade_save(save)
        assert upgraded["version"] == SAVE_VERSION
        assert upgraded["npc_state"]["player_name"] == "Tester"

    def test_monster_rename_applied(self):
        save = _v3_save_data()
        save["npc_state"]["monsters"] = [
            {"slug": "axylightl", "name": "Axylightl", "moves": []},
        ]
        save["npc_state"]["tuxepedia"] = {
            "axylightl": {"status": "caught", "appearance_count": 1}
        }
        upgraded = upgrade_save(save)
        assert upgraded["npc_state"]["monsters"][0]["slug"] == "axolightl"
        assert "axolightl" in upgraded["npc_state"]["tuxepedia"]
        assert "axylightl" not in upgraded["npc_state"]["tuxepedia"]

    def test_technique_rename_applied(self):
        save = _v3_save_data()
        save["npc_state"]["monsters"] = [
            {"slug": "tux", "name": "Tux", "moves": [{"slug": "venom"}]},
        ]
        upgraded = upgrade_save(save)
        assert (
            upgraded["npc_state"]["monsters"][0]["moves"][0]["slug"]
            == "caustic_spray"
        )


# ---------------------------------------------------------------------------
# Test: SaveData model tolerates missing optional fields
# ---------------------------------------------------------------------------


class TestSaveDataModel:
    def test_missing_multiplayer_battles_defaults(self):
        data = _v3_save_data()
        del data["multiplayer_battles"]
        save = SaveData(**data)
        assert save.multiplayer_battles == {}

    def test_missing_shop_stock_defaults(self):
        data = _v3_save_data()
        del data["shop_stock"]
        save = SaveData(**data)
        assert save.shop_stock == {}

    def test_missing_persistent_state_defaults(self):
        data = _v3_save_data()
        del data["persistent_state"]
        save = SaveData(**data)
        assert save.persistent_state == []

    def test_null_world_and_session_state(self):
        data = _v3_save_data()
        data["world_state"] = None
        data["session_state"] = None
        save = SaveData(**data)
        assert save.world_state is None
        assert save.session_state is None


# ---------------------------------------------------------------------------
# Test: trade log save/load compatibility matrix
# ---------------------------------------------------------------------------


@pytest.fixture
def npc_manager():
    npc = MagicMock()
    npc.get_monster_owner.return_value = None
    npc.get_monster_by_iid.return_value = None
    return npc


class TestTradeLogCompatibility:
    def test_empty_trade_log(self, npc_manager):
        manager = TradeManager(npc_manager)
        manager.load_log({})
        assert manager.global_trade_log == []
        assert manager.pending_offers == []

    def test_trade_log_with_valid_history(self, npc_manager):
        now = datetime.now(timezone.utc)
        manager = TradeManager(npc_manager)
        manager.load_log(
            {
                "trade_history": [
                    {
                        "from_player": "Alice",
                        "to_player": "Bob",
                        "from_player_id": str(uuid4()),
                        "to_player_id": str(uuid4()),
                        "monster_given": "alpha",
                        "monster_received": "beta",
                        "monster_given_id": str(uuid4()),
                        "monster_received_id": str(uuid4()),
                        "timestamp": now.isoformat(),
                    }
                ],
                "pending_offers": [],
            }
        )
        assert len(manager.global_trade_log) == 1
        assert manager.global_trade_log[0].from_player == "Alice"

    def test_trade_log_with_malformed_entries_skipped(self, npc_manager):
        now = datetime.now(timezone.utc)
        valid = {
            "from_player": "Carol",
            "to_player": "Dave",
            "from_player_id": str(uuid4()),
            "to_player_id": str(uuid4()),
            "monster_given": "gamma",
            "monster_received": "delta",
            "monster_given_id": str(uuid4()),
            "monster_received_id": str(uuid4()),
            "timestamp": now.isoformat(),
        }
        malformed_entries = [
            "not_a_dict",
            42,
            None,
            {"incomplete": True},
            {"from_player": "X"},
            valid,
        ]
        manager = TradeManager(npc_manager)
        manager.load_log({"trade_history": malformed_entries})
        assert len(manager.global_trade_log) == 1
        assert manager.global_trade_log[0].from_player == "Carol"

    def test_trade_log_with_naive_timestamps(self, npc_manager):
        naive_ts = datetime(2025, 6, 15, 10, 30, 0).isoformat()
        record = {
            "from_player": "Eve",
            "to_player": "Frank",
            "from_player_id": str(uuid4()),
            "to_player_id": str(uuid4()),
            "monster_given": "zeta",
            "monster_received": "eta",
            "monster_given_id": str(uuid4()),
            "monster_received_id": str(uuid4()),
            "timestamp": naive_ts,
        }
        manager = TradeManager(npc_manager)
        manager.load_log({"trade_history": [record]})
        assert len(manager.global_trade_log) == 1
        assert manager.global_trade_log[0].timestamp.tzinfo is not None

    def test_pending_offers_malformed_skipped(self, npc_manager):
        now = datetime.now(timezone.utc)
        valid_offer = {
            "proposing_player_id": str(uuid4()),
            "proposing_monster_id": str(uuid4()),
            "receiving_player_id": str(uuid4()),
            "requested_monster_id": str(uuid4()),
            "offer_id": str(uuid4()),
            "timestamp": now.isoformat(),
            "expires_at": (now + timedelta(minutes=5)).isoformat(),
        }
        manager = TradeManager(npc_manager)
        manager.load_log(
            {
                "pending_offers": [
                    valid_offer,
                    "garbage",
                    {"offer_id": "bad-uuid"},
                    None,
                ],
            }
        )
        assert len(manager.pending_offers) == 1

    def test_trade_log_roundtrip(self, npc_manager):
        """Full save → load → save roundtrip preserves data."""
        now = datetime.now(timezone.utc)
        manager = TradeManager(npc_manager)
        manager.global_trade_log.append(
            __import__(
                "tuxemon.trade_manager", fromlist=["TradeRecord"]
            ).TradeRecord(
                from_player="Ash",
                to_player="Gary",
                from_player_id=uuid4(),
                to_player_id=uuid4(),
                monster_given="pikachu",
                monster_received="eevee",
                monster_given_id=uuid4(),
                monster_received_id=uuid4(),
                timestamp=now,
            )
        )
        saved = manager.save_log()
        new_manager = TradeManager(npc_manager)
        new_manager.load_log(saved)
        re_saved = new_manager.save_log()
        assert len(re_saved["trade_history"]) == 1
        assert re_saved["trade_history"][0]["from_player"] == "Ash"


# ---------------------------------------------------------------------------
# Test: multiplayer battle log save/load compatibility matrix
# ---------------------------------------------------------------------------


class TestMultiplayerBattleLogCompatibility:
    def test_empty_battle_log(self):
        manager = MultiplayerBattleManager()
        manager.load_log({})
        assert manager.pending_challenges == []
        assert manager.battle_history == []
        assert manager.active_battle_sessions == []

    def test_legacy_completed_battles_key(self):
        """Older saves used 'completed_battles' instead of 'battle_history'."""
        challenger = uuid4()
        challenged = uuid4()
        now = datetime.now(timezone.utc)
        manager = MultiplayerBattleManager()
        manager.load_log(
            {
                "pending_challenges": [],
                "completed_battles": [
                    {
                        "challenge_id": str(uuid4()),
                        "challenger_player_id": str(challenger),
                        "challenged_player_id": str(challenged),
                        "resolution": BattleResolution.ACCEPTED.value,
                        "timestamp": now.isoformat(),
                    }
                ],
            }
        )
        assert len(manager.battle_history) == 1
        assert (
            manager.battle_history[0].resolution == BattleResolution.ACCEPTED
        )

    def test_malformed_pending_challenges_skipped(self):
        valid = {
            "challenger_player_id": str(uuid4()),
            "challenged_player_id": str(uuid4()),
            "challenge_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=3)
            ).isoformat(),
        }
        manager = MultiplayerBattleManager()
        manager.load_log(
            {
                "pending_challenges": [
                    valid,
                    "not-a-dict",
                    {"challenge_id": "bad"},
                    None,
                    42,
                ],
            }
        )
        assert len(manager.pending_challenges) == 1

    def test_malformed_battle_history_skipped(self):
        valid = {
            "challenge_id": str(uuid4()),
            "challenger_player_id": str(uuid4()),
            "challenged_player_id": str(uuid4()),
            "resolution": BattleResolution.REJECTED.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        manager = MultiplayerBattleManager()
        manager.load_log(
            {
                "battle_history": [
                    valid,
                    {"bad": "data"},
                    "garbage",
                    99,
                ],
            }
        )
        assert len(manager.battle_history) == 1
        assert (
            manager.battle_history[0].resolution == BattleResolution.REJECTED
        )

    def test_expired_challenges_purged_on_load(self):
        now = datetime.now(timezone.utc)
        active = {
            "challenger_player_id": str(uuid4()),
            "challenged_player_id": str(uuid4()),
            "challenge_id": str(uuid4()),
            "timestamp": now.isoformat(),
            "expires_at": (now + timedelta(minutes=5)).isoformat(),
        }
        expired = {
            "challenger_player_id": str(uuid4()),
            "challenged_player_id": str(uuid4()),
            "challenge_id": str(uuid4()),
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "expires_at": (now - timedelta(minutes=5)).isoformat(),
        }
        manager = MultiplayerBattleManager()
        manager.load_log({"pending_challenges": [active, expired]})
        assert len(manager.pending_challenges) == 1

    def test_stale_battle_sessions_purged_on_load(self):
        challenger = uuid4()
        challenged = uuid4()
        now = datetime.now(timezone.utc)
        stale_ts = (now - timedelta(minutes=10)).isoformat()
        fresh_ts = now.isoformat()

        fresh_session = {
            "challenge_id": str(uuid4()),
            "challenger_player_id": str(challenger),
            "challenged_player_id": str(challenged),
            "session_id": str(uuid4()),
            "current_turn": 1,
            "turn_timeout_seconds": 60,
            "reconnect_grace_seconds": 30,
            "created_at": fresh_ts,
            "last_activity_at": fresh_ts,
            "disconnected_at": {},
            "turn_actions": {},
        }
        stale_session = {
            "challenge_id": str(uuid4()),
            "challenger_player_id": str(challenger),
            "challenged_player_id": str(challenged),
            "session_id": str(uuid4()),
            "current_turn": 3,
            "turn_timeout_seconds": 60,
            "reconnect_grace_seconds": 30,
            "created_at": stale_ts,
            "last_activity_at": stale_ts,
            "disconnected_at": {},
            "turn_actions": {},
        }

        manager = MultiplayerBattleManager()
        manager.load_log(
            {
                "active_battle_sessions": [fresh_session, stale_session],
            }
        )
        assert len(manager.active_battle_sessions) == 1

    def test_battle_log_roundtrip(self):
        """Full save → load → save roundtrip preserves data."""
        manager = MultiplayerBattleManager()
        challenger = uuid4()
        challenged = uuid4()
        manager.propose_challenge(challenger, challenged)
        challenge = manager.pending_challenges[0]
        manager.accept_challenge(
            challenge.challenge_id, accepting_player_id=challenged
        )

        saved = manager.save_log()
        restored = MultiplayerBattleManager()
        restored.load_log(saved)
        re_saved = restored.save_log()

        assert len(re_saved["battle_history"]) == 1
        assert len(re_saved["active_battle_sessions"]) == 1

    def test_config_values_persist(self):
        manager = MultiplayerBattleManager()
        manager.default_challenge_ttl_seconds = 42
        manager.default_turn_timeout_seconds = 99
        manager.default_reconnect_grace_seconds = 7
        manager.max_battle_history_entries = 50

        saved = manager.save_log()
        restored = MultiplayerBattleManager()
        restored.load_log(saved)

        assert restored.default_challenge_ttl_seconds == 42
        assert restored.default_turn_timeout_seconds == 99
        assert restored.default_reconnect_grace_seconds == 7
        assert restored.max_battle_history_entries == 50

    def test_naive_timestamps_coerced_to_utc(self):
        naive_ts = "2025-06-15T10:30:00"
        manager = MultiplayerBattleManager()
        manager.load_log(
            {
                "battle_history": [
                    {
                        "challenge_id": str(uuid4()),
                        "challenger_player_id": str(uuid4()),
                        "challenged_player_id": str(uuid4()),
                        "resolution": BattleResolution.ACCEPTED.value,
                        "timestamp": naive_ts,
                    }
                ],
            }
        )
        assert len(manager.battle_history) == 1
        assert manager.battle_history[0].timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Test: combined trade + battle data in SaveData model
# ---------------------------------------------------------------------------


class TestCombinedSaveData:
    def test_save_data_with_trade_and_battle_logs(self, npc_manager):
        now = datetime.now(timezone.utc)
        trade_log = {
            "trade_history": [
                {
                    "from_player": "A",
                    "to_player": "B",
                    "from_player_id": str(uuid4()),
                    "to_player_id": str(uuid4()),
                    "monster_given": "x",
                    "monster_received": "y",
                    "monster_given_id": str(uuid4()),
                    "monster_received_id": str(uuid4()),
                    "timestamp": now.isoformat(),
                }
            ],
            "pending_offers": [],
        }
        battle_log = {
            "pending_challenges": [],
            "battle_history": [
                {
                    "challenge_id": str(uuid4()),
                    "challenger_player_id": str(uuid4()),
                    "challenged_player_id": str(uuid4()),
                    "resolution": "accepted",
                    "timestamp": now.isoformat(),
                }
            ],
            "active_battle_sessions": [],
        }

        save = SaveData(
            **_v3_save_data(
                multiplayer_battles=battle_log,
            )
        )

        trade_manager = TradeManager(npc_manager)
        trade_manager.load_log(trade_log)
        assert len(trade_manager.global_trade_log) == 1

        battle_manager = MultiplayerBattleManager()
        battle_manager.load_log(save.multiplayer_battles)
        assert len(battle_manager.battle_history) == 1

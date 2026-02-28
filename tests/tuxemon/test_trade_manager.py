# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from tuxemon.db import SeenStatus
from tuxemon.trade_manager import (
    TradeActionState,
    TradeManager,
    TradeRecord,
    TradeResult,
)


@pytest.fixture
def npc_manager():
    npc = MagicMock()
    owners = {}

    def get_owner(monster):
        if hasattr(monster, "_owner"):
            return monster._owner
        return owners.get(monster.instance_id)

    npc.get_monster_owner.side_effect = get_owner
    npc.get_monster_by_iid.side_effect = lambda iid: None

    return npc


@pytest.fixture
def manager(npc_manager):
    return TradeManager(npc_manager)


class MockPlayer:
    def __init__(self, name):
        self.name = name
        self.instance_id = uuid4()
        self.party = MagicMock()
        self.tuxepedia = MagicMock()


class MockMonster:
    def __init__(self, name, slug, owner):
        self.name = name
        self.slug = slug
        self.instance_id = uuid4()
        self.level = 5
        self._owner = owner

    def get_owner(self):
        return self._owner

    def set_owner(self, new_owner):
        self._owner = new_owner

    def set_acquisition(self, acquisition):
        self.acquisition = acquisition


@pytest.fixture
def players_and_monsters():
    player_a = MockPlayer("Better")
    player_b = MockPlayer("Call")
    monster_a = MockMonster("Flamey", "flamey_slug", player_a)
    monster_b = MockMonster("Splashy", "splashy_slug", player_b)
    player_a.party.monsters = [monster_a]
    player_b.party.monsters = [monster_b]
    return player_a, player_b, monster_a, monster_b


def test_execute_trade_success(manager, players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    result = manager.execute_trade(monster_a, monster_b)
    assert result == TradeResult.SUCCESS
    assert len(manager.global_trade_log) == 2


def test_execute_trade_same_owner(manager, players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    monster_b._owner = player_a
    result = manager.execute_trade(monster_a, monster_b)
    assert result == TradeResult.SAME_OWNER


def test_execute_trade_monster_not_found(manager, players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    player_a.party.monsters = []
    result = manager.execute_trade(monster_a, monster_b)
    assert result == TradeResult.NOT_FOUND


@pytest.fixture
def sample_record(players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    return TradeRecord(
        from_player="Better",
        to_player="Call",
        from_player_id=player_a.instance_id,
        to_player_id=player_b.instance_id,
        monster_given="flamey_slug",
        monster_received="splashy_slug",
        monster_given_id=monster_a.instance_id,
        monster_received_id=monster_b.instance_id,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Better", True),
        ("Call", True),
        ("Saul", False),
    ],
)
def test_was_traded_with_player(manager, sample_record, query, expected):
    manager.global_trade_log.append(sample_record)
    assert manager.was_traded_with_player(query) is expected


@pytest.mark.parametrize(
    "slug,expected",
    [
        ("flamey_slug", True),
        ("splashy_slug", True),
        ("leafy_slug", False),
    ],
)
def test_was_traded_for_monster(manager, sample_record, slug, expected):
    manager.global_trade_log.append(sample_record)
    assert manager.was_traded_for_monster(slug) is expected


def test_get_trade_history(manager, sample_record):
    manager.global_trade_log.append(sample_record)
    lineage = manager.get_trade_history()
    assert len(lineage) == 1
    assert "Better traded flamey_slug for splashy_slug" in lineage[0]


def test_save_and_load_log(manager, npc_manager, sample_record):
    manager.global_trade_log.append(sample_record)
    saved = manager.save_log()
    new_manager = TradeManager(npc_manager)
    new_manager.event_bus = MagicMock()
    new_manager.load_log(saved)
    assert len(new_manager.global_trade_log) == 1
    assert new_manager.global_trade_log[0].from_player == "Better"


def test_save_and_load_log_persists_pending_offers_and_ttl(
    manager, npc_manager, players_and_monsters
):
    _, player_b, monster_a, monster_b = players_and_monsters
    manager.default_offer_ttl_seconds = 123
    manager.propose_trade(monster_a, monster_b, expires_in_seconds=123)

    saved = manager.save_log()
    new_manager = TradeManager(npc_manager)
    new_manager.event_bus = MagicMock()
    new_manager.load_log(saved)

    assert new_manager.default_offer_ttl_seconds == 123
    received = new_manager.get_received_offers_for_player(player_b.instance_id)
    assert len(received) == 1
    assert received[0].requested_monster_id == monster_b.instance_id


def test_load_log_purges_expired_pending_offers(manager, npc_manager):
    now = datetime.now(timezone.utc)
    valid_offer = {
        "proposing_player_id": str(uuid4()),
        "proposing_monster_id": str(uuid4()),
        "receiving_player_id": str(uuid4()),
        "requested_monster_id": str(uuid4()),
        "offer_id": str(uuid4()),
        "timestamp": now.isoformat(),
        "expires_at": (now + timedelta(minutes=1)).isoformat(),
    }
    expired_offer = {
        "proposing_player_id": str(uuid4()),
        "proposing_monster_id": str(uuid4()),
        "receiving_player_id": str(uuid4()),
        "requested_monster_id": str(uuid4()),
        "offer_id": str(uuid4()),
        "timestamp": now.isoformat(),
        "expires_at": (now - timedelta(minutes=1)).isoformat(),
    }

    new_manager = TradeManager(npc_manager)
    new_manager.load_log(
        {
            "trade_history": [],
            "pending_offers": [valid_offer, expired_offer],
        }
    )

    assert len(new_manager.pending_offers) == 1
    assert new_manager.pending_offers[0].offer_id.hex == UUID(
        valid_offer["offer_id"]
    ).hex


def test_load_log_skips_malformed_trade_history_and_pending_offers(
    manager, npc_manager
):
    now = datetime.now(timezone.utc)
    valid_record = {
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
    valid_offer = {
        "proposing_player_id": str(uuid4()),
        "proposing_monster_id": str(uuid4()),
        "receiving_player_id": str(uuid4()),
        "requested_monster_id": str(uuid4()),
        "offer_id": str(uuid4()),
        "timestamp": now.isoformat(),
        "expires_at": (now + timedelta(minutes=1)).isoformat(),
    }

    manager.load_log(
        {
            "trade_history": [valid_record, {"bad": "entry"}, "nope"],
            "pending_offers": [valid_offer, {"offer_id": "invalid"}, 99],
        }
    )

    assert len(manager.global_trade_log) == 1
    assert manager.global_trade_log[0].from_player == "Alice"
    assert len(manager.pending_offers) == 1
    assert manager.pending_offers[0].offer_id == UUID(valid_offer["offer_id"])


def test_accept_trade_expired_offer(
    manager, npc_manager, players_and_monsters
):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    all_monsters = [monster_a, monster_b]
    npc_manager.get_monster_by_iid.side_effect = lambda iid: next(
        (m for m in all_monsters if m.instance_id == iid), None
    )
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]
    offer.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = manager.accept_trade(offer.offer_id)
    assert result == TradeResult.EXPIRED
    assert offer not in manager.pending_offers


def test_accept_trade_missing_monster(
    manager, npc_manager, players_and_monsters
):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    all_monsters = [monster_a, monster_b]
    npc_manager.get_monster_by_iid.side_effect = lambda iid: next(
        (m for m in all_monsters if m.instance_id == iid), None
    )
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]
    player_a.party.monsters = []
    player_b.party.monsters = []
    result = manager.accept_trade(offer.offer_id)
    assert result == TradeResult.NOT_FOUND


def test_accept_trade_nonexistent_offer(manager):
    fake_id = uuid4()
    result = manager.accept_trade(fake_id)
    assert result == TradeResult.NOT_FOUND


def test_propose_trade_sets_default_expiry(manager, players_and_monsters):
    player_a, _, monster_a, monster_b = players_and_monsters
    result = manager.propose_trade(monster_a, monster_b)

    assert result == TradeResult.SUCCESS
    offer = manager.pending_offers[0]
    assert offer.expires_at is not None
    delta = offer.expires_at - offer.timestamp
    assert int(delta.total_seconds()) == manager.default_offer_ttl_seconds
    offers = manager.get_pending_offers_for_player(player_a.instance_id)
    assert offer in offers


def test_purge_expired_offers_removes_only_expired(
    manager, players_and_monsters
):
    player_a, _, monster_a, monster_b = players_and_monsters
    manager.propose_trade(monster_a, monster_b, expires_in_seconds=1)
    manager.propose_trade(monster_a, monster_b, expires_in_seconds=60)

    now = datetime.now(timezone.utc) + timedelta(seconds=2)
    removed = manager.purge_expired_offers(now)

    assert removed == 1
    assert len(manager.pending_offers) == 1
    offers = manager.get_pending_offers_for_player(player_a.instance_id)
    assert len(offers) == 1


def test_get_received_offers_for_player(manager, players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    manager.propose_trade(monster_a, monster_b)

    received = manager.get_received_offers_for_player(player_b.instance_id)

    assert len(received) == 1
    assert received[0].receiving_player_id == player_b.instance_id
    assert (
        manager.get_received_offers_for_player(player_a.instance_id) == []
    )


def test_cancel_trade_offer_success(manager, players_and_monsters):
    player_a, _, monster_a, monster_b = players_and_monsters
    manager.event_bus = MagicMock()
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]
    manager.event_bus.publish.reset_mock()

    result = manager.cancel_trade_offer(
        offer.offer_id, requesting_player_id=player_a.instance_id
    )

    assert result == TradeResult.SUCCESS
    assert manager.pending_offers == []
    manager.event_bus.publish.assert_called_once_with(
        "trade_offer_cancelled", offer
    )


def test_cancel_trade_offer_unauthorized(manager, players_and_monsters):
    _, _, monster_a, monster_b = players_and_monsters
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]

    result = manager.cancel_trade_offer(
        offer.offer_id, requesting_player_id=uuid4()
    )

    assert result == TradeResult.UNAUTHORIZED
    assert offer in manager.pending_offers


def test_accept_trade_unauthorized_actor(
    manager, npc_manager, players_and_monsters
):
    player_a, _, monster_a, monster_b = players_and_monsters
    all_monsters = [monster_a, monster_b]
    npc_manager.get_monster_by_iid.side_effect = lambda iid: next(
        (m for m in all_monsters if m.instance_id == iid), None
    )
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]

    result = manager.accept_trade(
        offer.offer_id, accepting_player_id=player_a.instance_id
    )

    assert result == TradeResult.UNAUTHORIZED
    assert offer in manager.pending_offers


def test_reject_trade_offer_success(manager, players_and_monsters):
    _, player_b, monster_a, monster_b = players_and_monsters
    manager.event_bus = MagicMock()
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]
    manager.event_bus.publish.reset_mock()

    result = manager.reject_trade_offer(
        offer.offer_id, rejecting_player_id=player_b.instance_id
    )

    assert result == TradeResult.REJECTED
    assert manager.pending_offers == []
    manager.event_bus.publish.assert_called_once_with(
        "trade_offer_rejected", offer
    )


def test_reject_trade_offer_unauthorized(manager, players_and_monsters):
    player_a, _, monster_a, monster_b = players_and_monsters
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]

    result = manager.reject_trade_offer(
        offer.offer_id, rejecting_player_id=player_a.instance_id
    )

    assert result == TradeResult.UNAUTHORIZED
    assert offer in manager.pending_offers




def test_get_trade_action_feedback_messages(manager):
    success = manager.get_trade_action_feedback(TradeResult.SUCCESS, "accept")
    assert success.state == TradeActionState.ACCEPTED
    assert success.retryable is False
    assert "completed successfully" in success.message.lower()

    rejected = manager.get_trade_action_feedback(
        TradeResult.REJECTED, "reject"
    )
    assert rejected.state == TradeActionState.REJECTED
    assert rejected.retryable is True

    expired = manager.get_trade_action_feedback(TradeResult.EXPIRED, "accept")
    assert expired.state == TradeActionState.EXPIRED
    assert expired.retryable is True

    missing = manager.get_trade_action_feedback(TradeResult.NOT_FOUND, "accept")
    assert missing.state == TradeActionState.NOT_FOUND
    assert missing.retryable is True

    same_owner = manager.get_trade_action_feedback(
        TradeResult.SAME_OWNER, "propose"
    )
    assert same_owner.state == TradeActionState.FAILED
    assert same_owner.retryable is False

    unauthorized = manager.get_trade_action_feedback(
        TradeResult.UNAUTHORIZED, "cancel"
    )
    assert unauthorized.state == TradeActionState.FAILED
    assert unauthorized.retryable is False


def test_get_trade_offer_feedback_states(manager, players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]

    pending = manager.get_trade_offer_feedback(
        offer.offer_id, player_a.instance_id
    )
    assert pending.state == TradeActionState.PENDING
    assert pending.retryable is False

    unauthorized = manager.get_trade_offer_feedback(offer.offer_id, uuid4())
    assert unauthorized.state == TradeActionState.FAILED
    assert unauthorized.retryable is False

    offer.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = manager.get_trade_offer_feedback(
        offer.offer_id, player_b.instance_id
    )
    assert expired.state == TradeActionState.EXPIRED
    assert expired.retryable is True

    missing = manager.get_trade_offer_feedback(uuid4(), player_a.instance_id)
    assert missing.state == TradeActionState.NOT_FOUND
    assert missing.retryable is True

def test_get_trade_history_filtered(manager, sample_record):
    manager.global_trade_log.append(sample_record)
    lineage = manager.get_trade_history(player_name="Better")

    assert len(lineage) == 1
    assert "Better traded flamey_slug" in lineage[0]


def test_execute_trade_updates_party_and_ownership(
    manager, players_and_monsters
):
    player_a, player_b, monster_a, monster_b = players_and_monsters

    player_a.party.remove_monster = MagicMock()
    player_b.party.remove_monster = MagicMock()
    player_a.party.insert_monster_to_party = MagicMock()
    player_b.party.insert_monster_to_party = MagicMock()
    result = manager.execute_trade(monster_a, monster_b)
    assert result == TradeResult.SUCCESS

    player_a.party.remove_monster.assert_called_once_with(monster_a)
    player_b.party.remove_monster.assert_called_once_with(monster_b)
    player_a.party.insert_monster_to_party.assert_called_once()
    player_b.party.insert_monster_to_party.assert_called_once()


def test_execute_trade_updates_tuxepedia(manager, players_and_monsters):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    manager.execute_trade(monster_a, monster_b)
    player_a.tuxepedia.register_caught.assert_called_once_with(monster_b.slug)
    player_b.tuxepedia.register_caught.assert_called_once_with(monster_a.slug)


def test_execute_trade_publishes_event(manager, players_and_monsters):
    manager.event_bus = MagicMock()
    player_a, player_b, monster_a, monster_b = players_and_monsters
    manager.execute_trade(monster_a, monster_b)
    manager.event_bus.publish.assert_called_once()
    event_name, payload = manager.event_bus.publish.call_args[0]
    assert event_name == "trade_completed"
    assert len(payload) == 2


def test_accept_trade_invalid_ownership_change(
    manager, npc_manager, players_and_monsters
):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    all_monsters = [monster_a, monster_b]
    npc_manager.get_monster_by_iid.side_effect = lambda iid: next(
        (m for m in all_monsters if m.instance_id == iid), None
    )
    manager.propose_trade(monster_a, monster_b)
    offer = manager.pending_offers[0]
    monster_a.set_owner(player_b)
    result = manager.accept_trade(offer.offer_id)
    assert result == TradeResult.NOT_FOUND


def test_execute_scripted_trade_success(
    manager, npc_manager, players_and_monsters, monkeypatch
):
    player_a, player_b, monster_a, monster_b = players_and_monsters

    # Scripted trade creates a new monster via Monster.spawn_base
    class FakeNewMonster(MockMonster):
        def __init__(self):
            super().__init__("NewMon", "new_slug", player_a)

    fake_mon = FakeNewMonster()
    monkeypatch.setattr(
        "tuxemon.trade_manager.Monster.spawn_base",
        lambda slug, level: fake_mon,
    )
    player_a.party.replace_monster = MagicMock(return_value=True)
    result = manager.execute_scripted_trade(monster_a, "new_slug")
    assert result == TradeResult.SUCCESS
    player_a.party.replace_monster.assert_called_once_with(monster_a, fake_mon)
    assert fake_mon.acquisition is not None
    player_a.tuxepedia.register_caught.assert_called_once_with("new_slug")
    assert len(manager.global_trade_log) == 1
    record = manager.global_trade_log[0]
    assert record.monster_given == monster_a.slug
    assert record.monster_received == "new_slug"


def test_execute_scripted_trade_missing_player(
    manager, npc_manager, players_and_monsters
):
    player_a, player_b, monster_a, monster_b = players_and_monsters
    npc_manager.get_monster_owner.side_effect = lambda m: None
    result = manager.execute_scripted_trade(monster_a, "new_slug")
    assert result == TradeResult.NOT_FOUND
    assert manager.global_trade_log == []


def test_execute_scripted_trade_replace_failure(
    manager, npc_manager, players_and_monsters, monkeypatch
):
    player_a, player_b, monster_a, monster_b = players_and_monsters

    class FakeNewMonster(MockMonster):
        def __init__(self):
            super().__init__("NewMon", "new_slug", player_a)

    fake_mon = FakeNewMonster()
    monkeypatch.setattr(
        "tuxemon.trade_manager.Monster.spawn_base",
        lambda slug, level: fake_mon,
    )
    player_a.party.replace_monster = MagicMock(return_value=False)
    result = manager.execute_scripted_trade(monster_a, "new_slug")
    assert result == TradeResult.NOT_FOUND
    assert manager.global_trade_log == []


def test_load_log_supports_naive_offer_timestamps(manager, npc_manager):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    naive_now = now.replace(tzinfo=None)
    offer = {
        "proposing_player_id": str(uuid4()),
        "proposing_monster_id": str(uuid4()),
        "receiving_player_id": str(uuid4()),
        "requested_monster_id": str(uuid4()),
        "offer_id": str(uuid4()),
        "timestamp": naive_now.isoformat(),
        "expires_at": (naive_now + timedelta(minutes=1)).isoformat(),
    }

    new_manager = TradeManager(npc_manager)
    new_manager.load_log({"trade_history": [], "pending_offers": [offer]})

    assert len(new_manager.pending_offers) == 1
    assert new_manager.pending_offers[0].timestamp.tzinfo is not None
    assert new_manager.pending_offers[0].expires_at is not None
    assert new_manager.pending_offers[0].expires_at.tzinfo is not None


def test_load_log_supports_naive_trade_record_timestamp(manager, npc_manager):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    record = {
        "from_player": "Better",
        "to_player": "Call",
        "from_player_id": str(uuid4()),
        "to_player_id": str(uuid4()),
        "monster_given": "flamey_slug",
        "monster_received": "splashy_slug",
        "monster_given_id": str(uuid4()),
        "monster_received_id": str(uuid4()),
        "timestamp": now.replace(tzinfo=None).isoformat(),
    }

    new_manager = TradeManager(npc_manager)
    new_manager.load_log({"trade_history": [record], "pending_offers": []})

    assert len(new_manager.global_trade_log) == 1
    assert new_manager.global_trade_log[0].timestamp.tzinfo is not None

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Tests for the phone-rematch integration layer."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tuxemon.phone_rematch import (
    PhoneCallType,
    PhoneNotification,
    PhoneRematchBridge,
)
from tuxemon.trainer_rematch import TrainerRematchManager


@pytest.fixture
def rematch_manager() -> TrainerRematchManager:
    return TrainerRematchManager(default_cooldown=100)


@pytest.fixture
def relationships() -> MagicMock:
    rel = MagicMock()
    rel.get_all_connections.return_value = {}
    return rel


@pytest.fixture
def bridge(rematch_manager, relationships) -> PhoneRematchBridge:
    return PhoneRematchBridge(rematch_manager, relationships)


class TestPhoneNotification:
    def test_to_dict(self):
        notif = PhoneNotification(
            npc_slug="rival",
            call_type=PhoneCallType.REMATCH_AVAILABLE,
            message_key="phone_rematch_available",
            format_params={"trainer": "rival"},
        )
        data = notif.to_dict()
        assert data["npc_slug"] == "rival"
        assert data["call_type"] == "rematch_available"
        assert data["message_key"] == "phone_rematch_available"


class TestRematchNotifications:
    def test_no_notifications_when_no_contacts(self, bridge, rematch_manager):
        rematch_manager.record_defeat("rival", now=0.0)
        notifs = bridge.get_rematch_notifications(now=200.0)
        assert notifs == []

    def test_no_notifications_during_cooldown(
        self, bridge, rematch_manager, relationships
    ):
        rematch_manager.record_defeat("rival", now=0.0)
        relationships.get_all_connections.return_value = {
            "rival": MagicMock()
        }
        notifs = bridge.get_rematch_notifications(now=50.0)
        assert notifs == []

    def test_notification_when_available_and_contact(
        self, bridge, rematch_manager, relationships
    ):
        rematch_manager.record_defeat("rival", now=0.0)
        relationships.get_all_connections.return_value = {
            "rival": MagicMock()
        }
        notifs = bridge.get_rematch_notifications(now=200.0)
        assert len(notifs) == 1
        assert notifs[0].npc_slug == "rival"
        assert notifs[0].call_type == PhoneCallType.REMATCH_AVAILABLE

    def test_only_contacts_get_notifications(
        self, bridge, rematch_manager, relationships
    ):
        rematch_manager.record_defeat("rival", now=0.0)
        rematch_manager.record_defeat("stranger", now=0.0)
        relationships.get_all_connections.return_value = {
            "rival": MagicMock()
        }
        notifs = bridge.get_rematch_notifications(now=200.0)
        assert len(notifs) == 1
        assert notifs[0].npc_slug == "rival"

    def test_multiple_contacts_with_rematches(
        self, bridge, rematch_manager, relationships
    ):
        rematch_manager.record_defeat("rival", now=0.0)
        rematch_manager.record_defeat("gym_leader", now=0.0)
        relationships.get_all_connections.return_value = {
            "rival": MagicMock(),
            "gym_leader": MagicMock(),
        }
        notifs = bridge.get_rematch_notifications(now=200.0)
        assert len(notifs) == 2
        slugs = {n.npc_slug for n in notifs}
        assert slugs == {"rival", "gym_leader"}

    def test_notification_includes_scaling_info(
        self, bridge, rematch_manager, relationships
    ):
        rematch_manager.record_defeat("rival", now=0.0)
        rematch_manager.record_defeat("rival", now=50.0)
        relationships.get_all_connections.return_value = {
            "rival": MagicMock()
        }
        notifs = bridge.get_rematch_notifications(now=200.0)
        assert len(notifs) == 1
        assert notifs[0].format_params["rematch_number"] == "3"
        assert notifs[0].format_params["level_bonus"] == "6"


class TestGameplayTips:
    def test_generate_tip_with_contacts(self, bridge, relationships):
        relationships.get_all_connections.return_value = {
            "friend": MagicMock()
        }
        tip = bridge.generate_random_tip()
        assert tip is not None
        assert tip.call_type == PhoneCallType.ITEM_TIP
        assert tip.npc_slug == "friend"

    def test_no_tip_without_contacts(self, bridge):
        tip = bridge.generate_random_tip()
        assert tip is None


class TestEncounterAlerts:
    def test_generate_alert_with_contacts(self, bridge, relationships):
        relationships.get_all_connections.return_value = {
            "scout": MagicMock()
        }
        alert = bridge.generate_encounter_alert(location="route5")
        assert alert is not None
        assert alert.call_type == PhoneCallType.ENCOUNTER_ALERT
        assert alert.format_params["location"] == "route5"

    def test_no_alert_without_contacts(self, bridge):
        alert = bridge.generate_encounter_alert()
        assert alert is None


class TestAllNotifications:
    def test_includes_rematch_notifications(
        self, bridge, rematch_manager, relationships
    ):
        rematch_manager.record_defeat("rival", now=0.0)
        relationships.get_all_connections.return_value = {
            "rival": MagicMock()
        }
        notifs = bridge.get_all_notifications(now=200.0)
        rematch_notifs = [
            n for n in notifs
            if n.call_type == PhoneCallType.REMATCH_AVAILABLE
        ]
        assert len(rematch_notifs) == 1

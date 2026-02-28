# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Phone-rematch integration layer.

Connects the trainer rematch system with the phone contact/relationship
system so that trainers registered as contacts can notify the player
about rematch availability and provide gameplay tips.

This module bridges:
- TrainerRematchManager: tracks rematch availability and scaling
- Relationships: tracks NPC contact connections
- EventBus: publishes phone notification events
"""
from __future__ import annotations

import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuxemon.relationship import Relationships
    from tuxemon.trainer_rematch import TrainerRematchManager

logger = logging.getLogger(__name__)


class PhoneCallType:
    REMATCH_AVAILABLE = "rematch_available"
    ITEM_TIP = "item_tip"
    ENCOUNTER_ALERT = "encounter_alert"
    GREETING = "greeting"


@dataclass
class PhoneNotification:
    """A phone notification from an NPC contact."""

    npc_slug: str
    call_type: str
    message_key: str
    format_params: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "npc_slug": self.npc_slug,
            "call_type": self.call_type,
            "message_key": self.message_key,
            "format_params": self.format_params,
        }


ITEM_TIP_POOL = [
    "phone_tip_potion",
    "phone_tip_capture",
    "phone_tip_status",
    "phone_tip_type_advantage",
]

ENCOUNTER_ALERT_POOL = [
    "phone_alert_rare_sighting",
    "phone_alert_swarm",
    "phone_alert_weather_change",
]


class PhoneRematchBridge:
    """
    Generates phone notifications from rematch availability and contacts.

    This class is stateless and queries the rematch manager and
    relationships on each call to produce fresh notifications.
    """

    def __init__(
        self,
        rematch_manager: TrainerRematchManager,
        relationships: Relationships,
    ) -> None:
        self.rematch_manager = rematch_manager
        self.relationships = relationships

    def get_rematch_notifications(
        self, now: float | None = None
    ) -> list[PhoneNotification]:
        """
        Generate rematch-available notifications for contacts
        who are also tracked as defeated trainers.
        """
        available = set(self.rematch_manager.get_available_rematches(now=now))
        contacts = set(self.relationships.get_all_connections().keys())
        eligible = available & contacts

        notifications: list[PhoneNotification] = []
        for slug in sorted(eligible):
            rematch_count = self.rematch_manager.get_rematch_count(slug)
            level_bonus = self.rematch_manager.get_level_bonus(slug)
            notifications.append(
                PhoneNotification(
                    npc_slug=slug,
                    call_type=PhoneCallType.REMATCH_AVAILABLE,
                    message_key="phone_rematch_available",
                    format_params={
                        "trainer": slug,
                        "rematch_number": str(rematch_count + 1),
                        "level_bonus": str(level_bonus),
                    },
                )
            )

        return notifications

    def generate_random_tip(
        self, contact_slugs: Sequence[str] | None = None
    ) -> PhoneNotification | None:
        """
        Generate a random gameplay tip from a random contact.
        """
        contacts = contact_slugs or list(
            self.relationships.get_all_connections().keys()
        )
        if not contacts:
            return None

        npc_slug = random.choice(contacts)
        tip_key = random.choice(ITEM_TIP_POOL)
        return PhoneNotification(
            npc_slug=npc_slug,
            call_type=PhoneCallType.ITEM_TIP,
            message_key=tip_key,
            format_params={"trainer": npc_slug},
        )

    def generate_encounter_alert(
        self, contact_slugs: Sequence[str] | None = None,
        location: str = "",
    ) -> PhoneNotification | None:
        """
        Generate a rare encounter alert from a random contact.
        """
        contacts = contact_slugs or list(
            self.relationships.get_all_connections().keys()
        )
        if not contacts:
            return None

        npc_slug = random.choice(contacts)
        alert_key = random.choice(ENCOUNTER_ALERT_POOL)
        return PhoneNotification(
            npc_slug=npc_slug,
            call_type=PhoneCallType.ENCOUNTER_ALERT,
            message_key=alert_key,
            format_params={"trainer": npc_slug, "location": location},
        )

    def get_all_notifications(
        self, now: float | None = None
    ) -> list[PhoneNotification]:
        """
        Get all pending notifications: rematches first, then optional
        tips or alerts if contacts exist.
        """
        notifications = self.get_rematch_notifications(now=now)

        contacts = list(self.relationships.get_all_connections().keys())
        if contacts and random.random() < 0.3:
            tip = self.generate_random_tip(contacts)
            if tip:
                notifications.append(tip)

        return notifications

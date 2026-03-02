# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Event Adventure starter template.

A linear event-driven campaign with time-gated content and scripted story beats.
Designed for narrative-focused creators who want to tell a story through
triggered events and world-variable gating.

Content generated:
  maps/
    village_start.tmx     — Opening village (start map)
    forest_path.tmx       — Forest route with time-gated encounter tables
    ancient_shrine.tmx    — Story climax location (time-gated access)
  scripts/
    main_intro.json       — Opening cutscene
    shrine_guardian.json  — Guardian NPC encountered at shrine
    dawn_event.json       — Event fires at dawn each day
  locale/
    en_US.ini
"""
from __future__ import annotations

from pathlib import Path

from tuxemon.campaign.templates._base import CampaignTemplate


class EventAdventureTemplate(CampaignTemplate):
    """
    Linear event-driven campaign with time-gated content.

    Matches the ``event_adventure`` template ID in the wizard.
    """

    def __init__(self) -> None:
        super().__init__(
            name="event_adventure",
            display_name="Event Adventure",
            description=(
                "A linear, story-focused campaign driven by scripted events "
                "and time-gated content. No free exploration — every step is "
                "authored."
            ),
            features=[
                "Scripted story with world-variable gating",
                "Time-gated encounter tables (dawn/night only monsters)",
                "Day-change event script fires every morning",
                "Shrine guardian NPC with branching outcome",
                "Locale file with 15+ narrative string keys",
            ],
        )

    def apply(
        self,
        scaffold_root: Path,
        campaign_id: str,
        campaign_name: str,
        author: str,
    ) -> list[Path]:
        maps_dir = scaffold_root / "maps"
        scripts_dir = scaffold_root / "scripts"
        locale_dir = scaffold_root / "locale"
        written: list[Path] = []

        # ------------------------------------------------------------------
        # Village (start map)
        # ------------------------------------------------------------------
        spawn = self._spawn_event(oid=1, x=80, y=120)
        elder_npc = self._npc_event(oid=2, script_id="main_intro", x=80, y=60)
        forest_trans = self._transition_event(
            oid=3, target_map="maps/forest_path.tmx", x=160, y=10
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "village_start",
                width=18,
                height=14,
                events_xml="\n  ".join([spawn, elder_npc, forest_trans]),
            )
        )

        # ------------------------------------------------------------------
        # Forest path — time-gated encounters
        # ------------------------------------------------------------------
        enc_day = self._encounter_event(
            oid=1,
            monster_ids=["porcupinito", "iguana_evo"],
            x=0,
            y=0,
            w=160,
            h=200,
        )
        enc_dawn_only = self._encounter_event(
            oid=2,
            monster_ids=["mistwing", "ghostrion"],
            x=160,
            y=0,
            w=120,
            h=200,
        )
        spawn_forest = self._spawn_event(oid=3, x=10, y=100)
        shrine_trans = self._transition_event(
            oid=4, target_map="maps/ancient_shrine.tmx", x=300, y=100
        )
        village_back = self._transition_event(
            oid=5, target_map="maps/village_start.tmx", x=10, y=10
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "forest_path",
                width=24,
                height=18,
                events_xml="\n  ".join(
                    [enc_day, enc_dawn_only, spawn_forest, shrine_trans, village_back]
                ),
            )
        )

        # ------------------------------------------------------------------
        # Ancient shrine — story climax
        # ------------------------------------------------------------------
        spawn_shrine = self._spawn_event(oid=1, x=80, y=160)
        guardian = self._npc_event(
            oid=2, script_id="shrine_guardian", x=80, y=50
        )
        forest_back = self._transition_event(
            oid=3, target_map="maps/forest_path.tmx", x=80, y=180
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "ancient_shrine",
                width=12,
                height=14,
                events_xml="\n  ".join([spawn_shrine, guardian, forest_back]),
            )
        )

        # ------------------------------------------------------------------
        # Scripts
        # ------------------------------------------------------------------
        written.append(
            self._write_script(
                scripts_dir,
                "main_intro",
                description=(
                    "Opening cutscene: village elder tells the player about "
                    "the ancient shrine."
                ),
                trigger_type="game_start",
                action_type="dialog",
                action_args={"text_key": "story.elder_intro"},
            )
        )

        written.append(
            self._write_script(
                scripts_dir,
                "shrine_guardian",
                description=(
                    "The guardian of the ancient shrine challenges the player."
                ),
                trigger_type="map_zone_enter",
                action_type="dialog",
                action_args={"text_key": "story.guardian_challenge"},
            )
        )

        written.append(
            self._write_script(
                scripts_dir,
                "dawn_event",
                description=(
                    "Fires every morning at dawn. Sets world variables and "
                    "hints at time-sensitive content."
                ),
                trigger_type="day_change",
                action_type="dialog",
                action_args={"text_key": "world.dawn_message"},
            )
        )

        # ------------------------------------------------------------------
        # Locale
        # ------------------------------------------------------------------
        written.append(
            self._write_locale(
                locale_dir,
                strings={
                    "story.elder_intro": (
                        "Long ago, an ancient shrine was sealed deep in the forest. "
                        "Only a true trainer can unlock its secrets."
                    ),
                    "story.elder_hint": (
                        "Explore the forest path. But beware — the forest "
                        "changes at dawn."
                    ),
                    "story.guardian_challenge": (
                        "You have reached the shrine. To pass, you must "
                        "prove your worth in battle!"
                    ),
                    "story.guardian_victory": (
                        "You have proven yourself. The shrine's blessing is yours."
                    ),
                    "story.guardian_defeat": (
                        "The shrine remains sealed. Train harder and return."
                    ),
                    "world.dawn_message": (
                        "A new day dawns. The forest awakens with new mysteries..."
                    ),
                    "world.night_hint": (
                        "Strange creatures appear in the darkness. "
                        "Venture out if you dare."
                    ),
                    "encounter.mistwing_rare": (
                        "A rare mistwing appears in the morning mist!"
                    ),
                    "npc.villager_hello": "Good day, traveler!",
                    "npc.villager_hint": (
                        "They say the shrine guardian only appears to those "
                        "who have proved themselves worthy."
                    ),
                    "system.day_counter": "Day {day} of your journey.",
                    "system.first_day": "Your adventure begins today!",
                },
            )
        )

        return written

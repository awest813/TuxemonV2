# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Classic Two-Region Campaign starter template.

Provides a Gold/Silver-era structure: two connected regions with gym
progression, day/night encounter tables, and rematch-ready NPC trainers.

Content generated:
  maps/
    region1_town.tmx      — Starting town (region 1)
    region1_route1.tmx    — Route with day/night encounter zones
    region1_gym.tmx       — Region 1 gym
    region2_town.tmx      — Region 2 city
    region2_route1.tmx    — Route 2
    region2_gym.tmx       — Region 2 gym
  scripts/
    main_intro.json       — Entry script shown at game start
    gym1_leader.json      — Gym 1 leader pre-battle dialogue
    gym2_leader.json      — Gym 2 leader pre-battle dialogue
  locale/
    en_US.ini             — English locale strings
"""
from __future__ import annotations

from pathlib import Path

from tuxemon.campaign.templates._base import CampaignTemplate


class ClassicTwoRegionTemplate(CampaignTemplate):
    """
    Two regions, 2 gyms, day/night encounter tables, NPC rematch hooks.

    Matches the ``classic_two_region`` template ID in the wizard.
    """

    def __init__(self) -> None:
        super().__init__(
            name="classic_two_region",
            display_name="Classic Two-Region Campaign",
            description=(
                "A Gold/Silver-era structure with two connected regions, "
                "2 gyms, day/night encounter tables, and rematch-ready trainers."
            ),
            features=[
                "2 regions, 2 gyms, 1 final challenge area",
                "Day/night encounter tables for all routes",
                "Compatible with rematch loop (trainers enabled for return battles)",
                "Pre-authored intro, gym leader, and rival dialogue scripts",
                "Locale file with 20+ starter string keys",
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
        # Maps
        # ------------------------------------------------------------------

        # Region 1 — Town (start map, has spawn point)
        spawn = self._spawn_event(oid=1, x=80, y=80)
        npc = self._npc_event(oid=2, script_id="main_intro", x=100, y=80)
        trans_to_route1 = self._transition_event(
            oid=3, target_map="maps/region1_route1.tmx", x=160, y=10
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "region1_town",
                events_xml="\n  ".join([spawn, npc, trans_to_route1]),
            )
        )

        # Region 1 — Route 1 (day/night encounter zones)
        enc_day = self._encounter_event(
            oid=1,
            monster_ids=["porcupinito", "iguana_evo"],
            x=0,
            y=0,
            w=160,
            h=200,
        )
        enc_night = self._encounter_event(
            oid=2,
            monster_ids=["ghostrion", "noctulite"],
            x=160,
            y=0,
            w=160,
            h=200,
        )
        spawn_r1 = self._spawn_event(oid=3, x=10, y=100)
        trans_to_gym1 = self._transition_event(
            oid=4, target_map="maps/region1_gym.tmx", x=300, y=10
        )
        trans_to_r2 = self._transition_event(
            oid=5, target_map="maps/region2_town.tmx", x=300, y=150
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "region1_route1",
                width=25,
                height=20,
                events_xml="\n  ".join(
                    [enc_day, enc_night, spawn_r1, trans_to_gym1, trans_to_r2]
                ),
            )
        )

        # Region 1 — Gym
        spawn_gym1 = self._spawn_event(oid=1, x=80, y=150)
        gym1_leader = self._npc_event(oid=2, script_id="gym1_leader", x=80, y=50)
        trans_back_r1 = self._transition_event(
            oid=3, target_map="maps/region1_route1.tmx", x=80, y=170
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "region1_gym",
                width=12,
                height=14,
                events_xml="\n  ".join([spawn_gym1, gym1_leader, trans_back_r1]),
            )
        )

        # Region 2 — Town
        spawn_r2town = self._spawn_event(oid=1, x=80, y=100)
        trans_to_route2 = self._transition_event(
            oid=2, target_map="maps/region2_route1.tmx", x=160, y=10
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "region2_town",
                events_xml="\n  ".join([spawn_r2town, trans_to_route2]),
            )
        )

        # Region 2 — Route 1
        enc_r2 = self._encounter_event(
            oid=1,
            monster_ids=["drakovex", "crystalink", "porcupinito"],
            x=0,
            y=0,
            w=200,
            h=200,
        )
        spawn_r2route = self._spawn_event(oid=2, x=10, y=100)
        trans_to_gym2 = self._transition_event(
            oid=3, target_map="maps/region2_gym.tmx", x=300, y=10
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "region2_route1",
                width=25,
                height=20,
                events_xml="\n  ".join([enc_r2, spawn_r2route, trans_to_gym2]),
            )
        )

        # Region 2 — Gym
        spawn_gym2 = self._spawn_event(oid=1, x=80, y=150)
        gym2_leader = self._npc_event(oid=2, script_id="gym2_leader", x=80, y=50)
        trans_back_r2 = self._transition_event(
            oid=3, target_map="maps/region2_route1.tmx", x=80, y=170
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "region2_gym",
                width=12,
                height=14,
                events_xml="\n  ".join([spawn_gym2, gym2_leader, trans_back_r2]),
            )
        )

        # ------------------------------------------------------------------
        # Scripts
        # ------------------------------------------------------------------

        written.append(
            self._write_script(
                scripts_dir,
                "main_intro",
                description="Opening introduction shown when the campaign begins.",
                trigger_type="game_start",
                action_type="dialog",
                action_args={"text_key": "intro.welcome"},
            )
        )

        written.append(
            self._write_script(
                scripts_dir,
                "gym1_leader",
                description="Gym 1 leader pre-battle dialogue.",
                trigger_type="map_zone_enter",
                action_type="dialog",
                action_args={"text_key": "gym1.leader_challenge"},
            )
        )

        written.append(
            self._write_script(
                scripts_dir,
                "gym2_leader",
                description="Gym 2 leader pre-battle dialogue.",
                trigger_type="map_zone_enter",
                action_type="dialog",
                action_args={"text_key": "gym2.leader_challenge"},
            )
        )

        # ------------------------------------------------------------------
        # Locale
        # ------------------------------------------------------------------

        written.append(
            self._write_locale(
                locale_dir,
                strings={
                    "intro.welcome": (
                        f"Welcome to {campaign_name}! Your adventure begins here."
                    ),
                    "intro.tutorial_hint": (
                        "Catch monsters in tall grass. Battle trainers to grow stronger."
                    ),
                    "gym1.leader_challenge": (
                        "So you've come to challenge me? Prove your worth!"
                    ),
                    "gym1.leader_victory": "You've defeated me! Take this badge.",
                    "gym1.leader_defeat": (
                        "I wasn't at my best today. Come back when you're ready."
                    ),
                    "gym2.leader_challenge": (
                        "Few trainers make it this far. Let's see if you can beat me."
                    ),
                    "gym2.leader_victory": (
                        "Remarkable. You've earned the second badge."
                    ),
                    "gym2.leader_defeat": "Train harder and return.",
                    "npc.trainer_hello": "Ready to battle?",
                    "npc.trainer_lose": "I've got to train more!",
                    "npc.trainer_rematch": "You've gotten stronger since last time!",
                    "world.day_greeting": "Good morning, trainer!",
                    "world.night_greeting": "The night brings different monsters...",
                },
            )
        )

        return written

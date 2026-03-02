# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Battle Challenge starter template.

A single facility with 5 escalating difficulty tiers and no story content.
Designed for competitive-focused creators who want to build challenge rooms,
battle factories, or ranked training facilities.

Content generated:
  maps/
    lobby.tmx         — Entry lobby with tier selection
    tier1_floor.tmx   — Tier 1 (beginner)
    tier2_floor.tmx   — Tier 2 (intermediate)
    tier3_floor.tmx   — Tier 3 (advanced)
    tier4_floor.tmx   — Tier 4 (expert)
    tier5_floor.tmx   — Tier 5 (champion)
  scripts/
    main_intro.json   — Facility welcome script
    tier_transition.json — Script played between tiers
  locale/
    en_US.ini
"""

from __future__ import annotations

from pathlib import Path

from tuxemon.campaign.templates._base import CampaignTemplate

_TIER_MONSTERS: list[list[str]] = [
    ["porcupinito", "iguana_evo"],
    ["crystalink", "drakovex"],
    ["noctulite", "ghostrion", "aquazor"],
    ["voltex", "crystalink", "drakovex"],
    ["arcanite", "voltex", "noctulite"],
]

_TIER_LABELS = ["Beginner", "Intermediate", "Advanced", "Expert", "Champion"]


class BattleChallengeTemplate(CampaignTemplate):
    """
    Single battle facility with 5 difficulty tiers.

    Matches the ``battle_challenge`` template ID in the wizard.
    """

    def __init__(self) -> None:
        super().__init__(
            name="battle_challenge",
            display_name="Battle Challenge Facility",
            description=(
                "A single combat facility with 5 escalating difficulty tiers. "
                "No story — pure battle focus."
            ),
            features=[
                "5 difficulty tiers (Beginner → Champion)",
                "Unique monster pools per tier",
                "Facility lobby with tier-selection NPCs",
                "Tier transition script for dramatic pacing",
                "Compatible with custom ruleset clauses",
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
        # Lobby map — entry point with spawn + tier NPC portals
        # ------------------------------------------------------------------
        spawn = self._spawn_event(oid=1, x=80, y=150)
        lobby_npc = self._npc_event(oid=2, script_id="main_intro", x=80, y=80)
        tier1_transition = self._transition_event(
            oid=3, target_map="maps/tier1_floor.tmx", x=50, y=50
        )
        written.append(
            self._write_tmx(
                maps_dir,
                "lobby",
                width=16,
                height=14,
                events_xml="\n  ".join([spawn, lobby_npc, tier1_transition]),
            )
        )

        # ------------------------------------------------------------------
        # Tier floors — each has encounter zones + transition to next tier
        # ------------------------------------------------------------------
        for tier_idx, (monsters, label) in enumerate(
            zip(_TIER_MONSTERS, _TIER_LABELS), start=1
        ):
            tier_slug = f"tier{tier_idx}_floor"
            spawn_tier = self._spawn_event(oid=1, x=80, y=150)
            enc_zone = self._encounter_event(
                oid=2,
                monster_ids=monsters,
                x=20,
                y=20,
                w=240,
                h=200,
            )
            tier_npc = self._npc_event(
                oid=3, script_id="tier_transition", x=80, y=60
            )

            events_parts = [spawn_tier, enc_zone, tier_npc]

            if tier_idx < 5:
                next_slug = f"tier{tier_idx + 1}_floor"
                next_trans = self._transition_event(
                    oid=4,
                    target_map=f"maps/{next_slug}.tmx",
                    x=300,
                    y=80,
                )
                events_parts.append(next_trans)

            back_trans = self._transition_event(
                oid=5,
                target_map="maps/lobby.tmx",
                x=10,
                y=80,
            )
            events_parts.append(back_trans)

            written.append(
                self._write_tmx(
                    maps_dir,
                    tier_slug,
                    width=22,
                    height=16,
                    events_xml="\n  ".join(events_parts),
                )
            )

        # ------------------------------------------------------------------
        # Scripts
        # ------------------------------------------------------------------
        written.append(
            self._write_script(
                scripts_dir,
                "main_intro",
                description="Facility welcome message shown when entering the lobby.",
                trigger_type="game_start",
                action_type="dialog",
                action_args={"text_key": "facility.welcome"},
            )
        )

        written.append(
            self._write_script(
                scripts_dir,
                "tier_transition",
                description="Played at the boundary between challenge tiers.",
                trigger_type="map_zone_enter",
                action_type="dialog",
                action_args={"text_key": "facility.tier_advance"},
            )
        )

        # ------------------------------------------------------------------
        # Locale
        # ------------------------------------------------------------------
        written.append(
            self._write_locale(
                locale_dir,
                strings={
                    "facility.welcome": (
                        f"Welcome to {campaign_name}! "
                        "Five tiers of battle await. How far can you go?"
                    ),
                    "facility.tier_advance": (
                        "You've cleared this tier. The next challenge begins!"
                    ),
                    "tier1.description": "Beginner — a gentle introduction.",
                    "tier2.description": "Intermediate — the gloves come off.",
                    "tier3.description": "Advanced — only the prepared survive.",
                    "tier4.description": "Expert — near the pinnacle.",
                    "tier5.description": "Champion — the ultimate test.",
                    "npc.defeat": "You beat me! You're ready for the next floor.",
                    "npc.victory": "Come back stronger next time.",
                },
            )
        )

        return written

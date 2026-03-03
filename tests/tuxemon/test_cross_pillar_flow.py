# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Integration tests for cross-pillar flows.

Covers Phase 5.1 (Beta Hardening — Stability and Regression Coverage):
  campaign install → battle center matchmaking → tournament progression

These tests exercise the handoff between the three pillars:
1. A campaign is imported (CampaignImporter) and linted (CampaignLinter).
2. Players who finished the campaign join the battle center (LobbyManager).
3. Matched players advance into a tournament (TournamentManager).
4. Economy reward flows are validated end-to-end (EconomyBalanceAnalyzer).
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

import yaml

from tuxemon.battle_center.lobby import LobbyManager, LobbyStatus
from tuxemon.battle_center.matchmaking import MatchmakingEngine
from tuxemon.campaign.importer import CampaignImporter
from tuxemon.campaign.linter import CampaignLinter
from tuxemon.economy.progression_balance import (
    EconomyBalanceAnalyzer,
    EconomyBalancePolicy,
    RewardFlow,
)
from tuxemon.tournament_manager import (
    TournamentManager,
    TournamentResult,
    TournamentStatus,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_VALID_MANIFEST = {
    "id": "cross_pillar_test",
    "name": "Cross-Pillar Test Campaign",
    "version": "1.0.0",
    "author": "Integration Tester",
    "engine_min_version": "0.4.35",
    "description": "Campaign used for cross-pillar integration tests.",
    "start_map": "maps/start.tmx",
    "entry_script": "intro",
}

_MINIMAL_TMX = """\
<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" width="5" height="5" tilewidth="16" tileheight="16"
     nextlayerid="3" nextobjectid="3">
 <properties>
  <property name="slug" value="start"/>
 </properties>
 <layer id="1" name="ground" width="5" height="5">
  <data encoding="csv">1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1</data>
 </layer>
 <objectgroup id="2" name="Events">
  <object id="1" type="spawn_point" x="32" y="32" width="16" height="16"/>
 </objectgroup>
</map>
"""

_INTRO_SCRIPT = {
    "id": "intro",
    "triggers": [{"type": "game_start", "args": {}}],
    "nodes": [
        {
            "id": "n1",
            "action": "dialog",
            "args": {"text_key": "welcome"},
            "next": None,
            "branches": {},
        }
    ],
}


def _make_capsule(tmp_path: Path) -> Path:
    """Build a minimal valid .capsule archive and return its path."""
    buf = io.BytesIO()
    cid = _VALID_MANIFEST["id"]
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{cid}/campaign.yaml", yaml.dump(_VALID_MANIFEST))
        zf.writestr(f"{cid}/maps/start.tmx", _MINIMAL_TMX)
        zf.writestr(f"{cid}/scripts/intro.json", json.dumps(_INTRO_SCRIPT))
    capsule = tmp_path / f"{cid}.capsule"
    capsule.write_bytes(buf.getvalue())
    return capsule


def _make_valid_campaign_dir(tmp_path: Path) -> Path:
    """Write a valid campaign directory (no archive) for direct linting."""
    cdir = tmp_path / _VALID_MANIFEST["id"]
    (cdir / "maps").mkdir(parents=True)
    (cdir / "scripts").mkdir(parents=True)
    (cdir / "campaign.yaml").write_text(yaml.dump(_VALID_MANIFEST))
    (cdir / "maps" / "start.tmx").write_text(_MINIMAL_TMX)
    (cdir / "scripts" / "intro.json").write_text(json.dumps(_INTRO_SCRIPT))
    return cdir


# ---------------------------------------------------------------------------
# Pillar 1 → 2: campaign import + linting
# ---------------------------------------------------------------------------


class TestCampaignImportAndLint:
    """A campaign must import cleanly before players can enter the battle center."""

    def test_valid_capsule_installs_and_lints_clean(self, tmp_path: Path):
        capsule = _make_capsule(tmp_path)
        install_dir = tmp_path / "installed"

        importer = CampaignImporter()
        result = importer.install(capsule, install_dir)

        assert result.success, result.human_summary()
        assert result.install_dir is not None
        assert (result.install_dir / "campaign.yaml").exists()

        # Linting the installed campaign must also pass
        linter = CampaignLinter()
        report = linter.lint(result.install_dir)
        assert report.passed, report.format_human()

    def test_overwrite_removes_stale_files(self, tmp_path: Path):
        """Reinstalling with overwrite=True must not leave stale files behind."""
        capsule = _make_capsule(tmp_path)
        install_dir = tmp_path / "installed"

        importer = CampaignImporter()
        importer.install(capsule, install_dir)

        # Plant a stale file that is NOT in the archive
        stale = install_dir / _VALID_MANIFEST["id"] / "stale_artifact.txt"
        stale.write_text("should be removed on reinstall")
        assert stale.exists()

        # Reinstall with overwrite=True
        result = importer.install(capsule, install_dir, overwrite=True)
        assert result.success, result.human_summary()

        # Stale file must be gone
        assert not stale.exists(), "Stale file survived overwrite reinstall"

    def test_lint_hints_present_for_blocking_failure(self, tmp_path: Path):
        """Blocking lint failures for known check_ids must include a hint."""
        # Missing campaign.yaml → manifest_missing check
        bad_dir = tmp_path / "bad_campaign"
        bad_dir.mkdir()

        linter = CampaignLinter()
        report = linter.lint(bad_dir)

        assert not report.passed
        blocking_with_hints = [i for i in report.blocking if i.hint]
        assert blocking_with_hints, (
            "Expected at least one blocking issue with a hint, got: "
            + str([i.check_id for i in report.blocking])
        )

    def test_lint_json_includes_hint_field(self, tmp_path: Path):
        """The JSON report must include the hint field for every issue."""
        import json as _json

        bad_dir = tmp_path / "no_manifest"
        bad_dir.mkdir()

        linter = CampaignLinter()
        report = linter.lint(bad_dir)
        parsed = _json.loads(report.to_json())

        for issue in parsed["issues"]:
            assert "hint" in issue, f"hint key missing from issue: {issue}"


# ---------------------------------------------------------------------------
# Pillar 2: battle center matchmaking
# ---------------------------------------------------------------------------


class TestBattleCenterMatchmaking:
    """Players who completed a campaign enter the battle center queue."""

    def test_two_players_matched_after_campaign(self):
        lobby = LobbyManager()
        engine = MatchmakingEngine(lobby)

        # Simulate two players entering the battle center after campaign play
        lobby.join_queue("alice", ruleset="default", format="single")
        lobby.join_queue("bob", ruleset="default", format="single")

        matches = engine.run_cycle()

        assert len(matches) == 1
        assert set(matches[0]) == {"alice", "bob"}
        assert lobby.get_status("alice") == LobbyStatus.MATCHED
        assert lobby.get_status("bob") == LobbyStatus.MATCHED

    def test_incompatible_rulesets_not_matched(self):
        lobby = LobbyManager()
        engine = MatchmakingEngine(lobby)

        lobby.join_queue("alice", ruleset="no_items", format="single")
        lobby.join_queue("bob", ruleset="default", format="single")

        matches = engine.run_cycle()
        assert matches == []

    def test_cancel_removes_player_from_queue(self):
        lobby = LobbyManager()

        lobby.join_queue("alice")
        assert lobby.queue_size() == 1

        lobby.cancel("alice")
        assert lobby.queue_size() == 0
        assert lobby.get_status("alice") == LobbyStatus.CANCELLED


# ---------------------------------------------------------------------------
# Pillar 2 → 3: battle center match → tournament entry
# ---------------------------------------------------------------------------


class TestBattleCenterToTournament:
    """Matched battle center players can enter a tournament."""

    def _register_n(self, manager: TournamentManager, tid, n: int) -> list:
        pids = []
        for i in range(n):
            pid = uuid4()
            r = manager.register_participant(tid, pid, f"Player{i + 1}")
            assert r == TournamentResult.SUCCESS
            pids.append(pid)
        return pids

    def test_matched_players_register_for_tournament(self):
        lobby = LobbyManager()
        engine = MatchmakingEngine(lobby)

        lobby.join_queue("alice", ruleset="default", format="single")
        lobby.join_queue("bob", ruleset="default", format="single")
        engine.run_cycle()

        assert lobby.get_status("alice") == LobbyStatus.MATCHED
        assert lobby.get_status("bob") == LobbyStatus.MATCHED

        # Both matched players may now register for a tournament
        mgr = TournamentManager()
        t = mgr.create_tournament("Beta Cup", 8, tournament_seed=1)
        assert hasattr(t, "tournament_id")
        mgr.open_registration(t.tournament_id)

        for name in ("alice", "bob"):
            r = mgr.register_participant(t.tournament_id, uuid4(), name)
            assert r == TournamentResult.SUCCESS

    def test_full_8player_tournament_reaches_in_progress(self):
        mgr = TournamentManager()
        t = mgr.create_tournament("Full Beta Cup", 8, tournament_seed=7)
        assert hasattr(t, "tournament_id")

        mgr.open_registration(t.tournament_id)
        pids = self._register_n(mgr, t.tournament_id, 8)

        # Move to check-in
        r = mgr.close_registration(t.tournament_id)
        assert r == TournamentResult.SUCCESS

        for pid in pids:
            mgr.check_in_participant(t.tournament_id, pid)

        # Start the tournament
        r = mgr.start_tournament(t.tournament_id)
        assert r == TournamentResult.SUCCESS
        assert t.status == TournamentStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# Pillar 3 — economy reward flows across pillars
# ---------------------------------------------------------------------------


class TestCrossPillarEconomyFlows:
    """Economy reward flows from all three pillars must stay within policy."""

    def test_combined_reward_flows_within_policy(self):
        policy = EconomyBalancePolicy(
            max_daily_coins=6000,
            max_source_share=0.65,
            max_exploit_risk_weighted=0.45,
        )
        analyzer = EconomyBalanceAnalyzer(policy)

        report = analyzer.analyze(
            [
                RewardFlow(
                    "campaign_quests",
                    coins_per_event=200,
                    events_per_hour=2.0,
                    max_events_per_day=10,
                    exploit_risk=0.10,
                ),
                RewardFlow(
                    "battle_center",
                    coins_per_event=150,
                    events_per_hour=2.0,
                    max_events_per_day=8,
                    exploit_risk=0.20,
                ),
                RewardFlow(
                    "casino",
                    coins_per_event=50,
                    events_per_hour=3.0,
                    max_events_per_day=15,
                    exploit_risk=0.30,
                ),
                RewardFlow(
                    "tournament_prize",
                    coins_per_event=500,
                    events_per_hour=0.1,
                    max_events_per_day=1,
                    exploit_risk=0.05,
                ),
            ],
            active_hours=2.0,
        )

        assert report.total_daily_coins > 0
        assert report.warnings == (), (
            f"Economy balance warnings: {report.warnings}"
        )

    def test_casino_dominant_share_triggers_warning(self):
        policy = EconomyBalancePolicy(
            max_daily_coins=10000,
            max_source_share=0.50,
        )
        analyzer = EconomyBalanceAnalyzer(policy)

        report = analyzer.analyze(
            [
                RewardFlow(
                    "casino",
                    coins_per_event=300,
                    events_per_hour=4.0,
                    max_events_per_day=30,
                    exploit_risk=0.4,
                ),
                RewardFlow(
                    "campaign_quests",
                    coins_per_event=10,
                    events_per_hour=1.0,
                    max_events_per_day=3,
                    exploit_risk=0.05,
                ),
            ],
            active_hours=2.0,
        )

        assert any(
            "dominant_source_share_exceeded" in w for w in report.warnings
        ), f"Expected dominant source warning, got: {report.warnings}"

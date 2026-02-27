from pathlib import Path

from tuxemon.fork_status import (
    RoadmapProgress,
    collect_progress_counts,
    collect_roadmap_progress,
)


def test_collect_progress_counts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "mods/tuxemon/db/monster").mkdir(parents=True)
    (root / "mods/tuxemon/db/technique").mkdir(parents=True)
    (root / "mods/tuxemon/db/item").mkdir(parents=True)
    (root / "mods/tuxemon/db/npc").mkdir(parents=True)
    (root / "mods/tuxemon/maps").mkdir(parents=True)
    (root / "mods/tuxemon/l18n/en_US").mkdir(parents=True)

    (root / "mods/tuxemon/db/monster/a.json").write_text("{}", encoding="utf-8")
    (root / "mods/tuxemon/db/technique/b.json").write_text("{}", encoding="utf-8")
    (root / "mods/tuxemon/db/item/c.json").write_text("{}", encoding="utf-8")
    (root / "mods/tuxemon/db/npc/d.json").write_text("{}", encoding="utf-8")
    (root / "mods/tuxemon/maps/e.tmx").write_text("", encoding="utf-8")
    (root / "mods/tuxemon/l18n/en_US/messages.po").write_text(
        "msgid ''", encoding="utf-8"
    )

    counts = collect_progress_counts(root)

    assert counts.monsters == 1
    assert counts.techniques == 1
    assert counts.items == 1
    assert counts.npcs == 1
    assert counts.maps == 1
    assert counts.locales == 1


def test_collect_roadmap_progress(tmp_path: Path) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text(
        """# Roadmap\n- [x] Done\n- [ ] Todo\n  - [X] Nested done\n""",
        encoding="utf-8",
    )

    progress = collect_roadmap_progress(roadmap)

    assert progress == RoadmapProgress(completed=2, total=3)

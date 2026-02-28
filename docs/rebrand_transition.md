# OpenCapsuleMon Rebrand Transition Guide

This document defines how we move from historical **Tuxemon** naming to
**OpenCapsuleMon** naming without breaking existing workflows.

## Naming Conventions During Transition

Use this table when deciding what names to use in code, docs, and tooling.

| Area | Preferred name now | Keep compatibility alias? | Notes |
| --- | --- | --- | --- |
| Player-facing docs and announcements | OpenCapsuleMon | Yes | Mention Tuxemon lineage once where useful. |
| Runtime CLI entrypoint | `run_tuxemon.py` | N/A | Keep stable until CLI rename milestone. |
| Python package/module paths | `tuxemon.*` | N/A | Preserve imports until package migration phase. |
| Save-data keys and serialized payloads | Existing Tuxemon-compatible keys | Yes | Add migration/upgrader rules before key changes. |
| Internal architecture docs | OpenCapsuleMon terminology with Tuxemon aliases | Yes | Prefer transition-safe wording: "OpenCapsuleMon (tuxemon module)". |

### Transition-safe wording examples

- "OpenCapsuleMon battle engine (`tuxemon.battle`)"
- "OpenCapsuleMon launcher (`run_tuxemon.py`)"
- "OpenCapsuleMon content packs (mods format inherited from Tuxemon)"

## Staged Compatibility-First Migration Plan

### Phase A: Documentation and Messaging (active)

1. Use OpenCapsuleMon name in README, roadmap, and contributor messaging.
2. Keep references to current executable/module names where commands are shown.
3. Require PRs that touch naming to include a "Rebrand impact" note.

### Phase B: Runtime Alias Introduction

1. Add optional OpenCapsuleMon-named launch aliases while keeping existing
   commands functional.
2. Log deprecation notices only after aliases have existed for at least one
   stable release.

### Phase C: Package/Module Rename Preparation

1. Introduce compatibility import shims for moved modules.
2. Provide one full release cycle where old import paths continue to work.
3. Remove shims only after deprecation window and migration notes are published.

### Phase D: Cleanup

1. Remove deprecated aliases.
2. Simplify docs to OpenCapsuleMon-only naming.
3. Keep historical reference notes for contributors working with old branches.

## Deprecation Window Policy

- Minimum deprecation window: **1 stable release cycle**.
- Breaking rename PRs must include:
  - migration instructions,
  - compatibility coverage details,
  - save/load impact summary (if applicable).

## Release Notes and PR Messaging Baseline

### Release notes

Each release note should include:

1. One-line OpenCapsuleMon project summary.
2. Upstream attribution note (Tuxemon lineage).
3. Compatibility notes for renamed commands, paths, or save keys.

### Pull requests

When opening a PR that changes naming or contributor-facing wording, include:

- **Rebrand impact:** what changed for users/contributors.
- **Compatibility impact:** what old names still work.
- **Follow-up needed:** planned future rename steps, if any.

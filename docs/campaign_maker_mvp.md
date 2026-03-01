# Campaign Maker MVP

## Document Status

- Status: Published (Phase 1)
- Scope: MVP creator workflow scope, UX wireflow, and schema constraints for creator-facing forms

---

## 1. Purpose

The Campaign Maker is a first-party toolset that lets non-programmer users create, validate, and export full OpenCapsuleMon campaigns. The MVP ships with Phase 3 (see ROADMAP.md) but the discovery, scope, and schema constraints are defined here in Phase 1 so engineering and content design can proceed in parallel.

---

## 2. Creator Personas

| Persona | Background | Goal |
|---|---|---|
| **Casual Mapper** | Familiar with RPG Maker or Tiled; no programming experience. | Build a short 1–2 region campaign with original monsters and maps. |
| **Content Remixer** | Has played existing mods; wants to modify encounter tables and NPC scripts. | Adjust an existing campaign without breaking its structure. |
| **Competitive Designer** | Familiar with tournament rules; wants to build a challenge-focused campaign with custom clauses. | Ship a campaign oriented around battle facility content and specific rulesets. |

---

## 3. MVP Scope (Creator Workflows)

The MVP supports the following creator workflows. Items marked **required** must ship in Phase 3; items marked **stretch** are optional.

### Workflow A — New Campaign Setup (Required)

1. Creator launches the Campaign Maker tool.
2. Creator completes a guided **New Campaign Wizard** (see §5 for wireflow).
3. Wizard validates all required fields and generates a campaign directory with scaffold files.
4. Campaign is immediately openable in the editor.

### Workflow B — Map Authoring (Required)

1. Creator opens or creates a map in the integrated Tiled-based editor.
2. Encounter table editor lets creator assign monsters to zones with optional time/season restrictions.
3. Creator places NPC markers and assigns dialogue scripts from a searchable script library.
4. Creator saves the map; validator runs automatically and reports blocking errors before save completes.

### Workflow C — Event and Quest Authoring (Required)

1. Creator uses a visual event graph to connect trigger conditions to actions.
2. Triggers: map zone enter, item use, dialogue choice, time-based, battle outcome.
3. Actions: set world variable, spawn NPC, open shop, start battle, play cutscene, award item.
4. Creator can reference monsters, items, trainers, and world variables from dropdown lists (no raw IDs needed).

### Workflow D — Campaign Packaging and Export (Required)

1. Creator clicks "Build Campaign."
2. Builder validates the full campaign (see §6 for validator rules).
3. If valid: produces a single `.capsule` archive file (ZIP with manifest).
4. If invalid: shows a human-readable error report grouped by severity (blocking / warning / info).
5. Creator shares the `.capsule` file or publishes to the community mod index (future Phase).

### Workflow E — Campaign Import and Compatibility Check (Required)

1. Player or creator opens the game and selects "Import Campaign."
2. Engine runs compatibility check against current engine version.
3. Compatible: campaign is installed and available.
4. Incompatible: engine shows specific incompatibilities and links to migration guide.

### Workflow F — Template-Based Starter Campaigns (Stretch)

- Three first-party starter templates bundled with the tool:
  - `classic_two_region` — Two connected regions with gym progression.
  - `battle_challenge` — Single facility with 5 difficulty tiers; no story.
  - `event_adventure` — Linear event-driven campaign with time-gated content.

---

## 4. Schema Constraints

### 4.1 Campaign Manifest (`campaign.yaml`)

Every campaign must include a `campaign.yaml` at its root. Required fields:

```yaml
# campaign.yaml
id: "my_campaign_id"           # str: lowercase, alphanumeric, underscores only; globally unique
name: "My Campaign Name"       # str: display name, 3–80 characters
version: "1.0.0"               # str: semver
author: "Creator Name"         # str: 1–60 characters
engine_min_version: "0.4.35"   # str: semver; minimum engine version required
description: "..."             # str: 10–500 characters
start_map: "region1/start.tmx" # str: path relative to campaign root; file must exist
entry_script: "main_intro"     # str: script ID; must exist in scripts/

# Optional fields:
tags: ["adventure", "time-aware"]   # list[str]: discovery/filter tags
license: "CC-BY-SA-4.0"            # str: SPDX license identifier
language: "en_US"                   # str: primary locale code
```

Validation rules:
- `id` must match pattern `^[a-z][a-z0-9_]{2,63}$`.
- `version` must be valid semver (`MAJOR.MINOR.PATCH`).
- `engine_min_version` must be ≤ current engine version at import time.
- `start_map` must resolve to an existing `.tmx` file within the campaign directory.
- `entry_script` must resolve to a known script ID in `scripts/`.

### 4.2 Map File Constraints

Maps must pass the following checks before a campaign can be built:

| Check | Severity | Rule |
|---|---|---|
| `map_id_unique` | Blocking | No two maps within the campaign may share the same ID. |
| `spawn_point_exists` | Blocking | Every map that is a `start_map` or transition target must have at least one `spawn_point` object. |
| `transition_target_valid` | Blocking | Every map transition tile must reference a target map that exists in the campaign. |
| `encounter_zone_valid` | Blocking | Every encounter zone must reference at least one valid monster ID. |
| `npc_script_valid` | Blocking | Every NPC with a dialogue assignment must reference a script ID that exists in `scripts/`. |
| `layer_naming_convention` | Warning | Map layers should follow `day_*` / `night_*` naming for time-aware layers. |
| `orphan_layer` | Info | Layers with no tiles are informational (not blocking). |

### 4.3 Monster Reference Constraints

| Check | Severity | Rule |
|---|---|---|
| `monster_id_valid` | Blocking | Every monster ID referenced in encounter tables must resolve to a known monster (campaign-defined or engine-bundled). |
| `monster_level_range` | Warning | Encounter levels should be within 5 levels of the zone's suggested level range (if defined in the campaign manifest). |
| `time_restriction_valid` | Blocking | Time restriction tokens must be one of: `dawn`, `morning`, `afternoon`, `dusk`, `night`, `day`, `any`. |
| `season_restriction_valid` | Blocking | Season restriction tokens must be: `spring`, `summer`, `autumn`, `winter`. |
| `weekday_restriction_valid` | Blocking | Weekday restriction tokens must be full lowercase English weekday names. |

### 4.4 Script Constraints

| Check | Severity | Rule |
|---|---|---|
| `script_id_unique` | Blocking | No two scripts may share the same ID within a campaign. |
| `script_action_valid` | Blocking | Every action node in a script must reference a known action type. |
| `script_variable_defined` | Warning | World variables referenced in conditions should be initialized before first use. |
| `script_loop_detected` | Blocking | Circular script references (script A calls script B which calls script A) are not allowed. |
| `localization_key_defined` | Warning | String keys used in dialogue actions should have entries in the campaign's locale file. |

### 4.5 Campaign-Level Constraints

| Check | Severity | Rule |
|---|---|---|
| `start_map_reachable` | Blocking | The `start_map` must be reachable from the campaign entry point without completing any battles or quests. |
| `no_unreachable_maps` | Warning | Every map in the campaign should be reachable from the start map (orphan map detection). |
| `ruleset_valid` | Blocking | Campaign ruleset overrides (if present) must pass `BattleRules` Pydantic validation. |
| `weekly_event_ids_unique` | Blocking | Weekly event IDs must be unique within the campaign. |
| `trainer_ids_unique` | Blocking | Trainer IDs must be unique within the campaign. |

---

## 5. UX Wireflow — New Campaign Wizard

The wizard collects campaign metadata and generates scaffold files. It has 4 steps.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 1 of 4 — Campaign Identity                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Campaign ID*    [my_first_campaign___________]  (lowercase, no spaces)     │
│  Campaign Name*  [My First Campaign____________]                             │
│  Author*         [Your Name____________________]                             │
│  Description*    [                                                ]          │
│                  [                                                ]          │
│                                                                             │
│  ✓ ID is available          ✓ Name is valid                                 │
│                                                                             │
│                                            [Cancel]  [Next →]              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 2 of 4 — Starting Point                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Start from:                                                                │
│    ○ Blank campaign  (empty maps and scripts folder)                        │
│    ● Template        ▼ [Classic Two-Region Campaign_____]                   │
│                                                                             │
│  Template preview:                                                          │
│    • 2 regions, 8 gyms, 1 final boss                                       │
│    • 50 pre-placed NPC trainers with authored dialogue                     │
│    • Day/night encounter tables for all routes                              │
│    • Compatible with rematch loop (trainers enabled for phone)             │
│                                                                             │
│                                       [← Back]  [Cancel]  [Next →]        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3 of 4 — Rules and Difficulty                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Default difficulty   ○ Easy  ● Normal  ○ Hard  ○ Challenge                │
│                                                                             │
│  Optional rules:                                                            │
│    [ ] Enable permadeath (fainted monsters cannot be revived)              │
│    [ ] Enable Nuzlocke mode (first encounter per zone only)                │
│                                                                             │
│  Battle clauses (active for all campaign battles):                         │
│    [✓] Duplicate species clause                                             │
│    [ ] Sleep limit clause                                                   │
│    [ ] OHKO ban                                                             │
│                                                                             │
│                                       [← Back]  [Cancel]  [Next →]        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 4 of 4 — Review and Create                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Campaign ID:        my_first_campaign                                      │
│  Campaign Name:      My First Campaign                                      │
│  Author:             Your Name                                              │
│  Template:           Classic Two-Region Campaign                            │
│  Difficulty:         Normal                                                 │
│  Permadeath:         No                                                     │
│  Active Clauses:     duplicate_species                                      │
│                                                                             │
│  Output directory:   ~/campaigns/my_first_campaign/                         │
│                                                                             │
│  ✓ All fields valid. Ready to create campaign.                             │
│                                                                             │
│                                       [← Back]  [Cancel]  [Create ✓]      │
└─────────────────────────────────────────────────────────────────────────────┘
```

After "Create":
1. Campaign directory is created at the output path.
2. `campaign.yaml` is written with the configured values.
3. Template files are copied (if template selected).
4. Editor opens with the new campaign loaded.
5. A "Getting Started" checklist panel is shown:
   - [ ] Place your first spawn point on the start map.
   - [ ] Add at least one wild encounter zone.
   - [ ] Write your intro script.
   - [ ] Add your first NPC trainer.

---

## 6. Prototype — Validator-Backed Wizard

The wizard prototype is implemented in `tuxemon/campaign/wizard.py`. It:

1. Accepts wizard step inputs as Pydantic models.
2. Validates each step before allowing progression to the next.
3. Produces a `CampaignManifest` from the final step.
4. Generates the scaffold directory structure from a manifest.

See `tuxemon/campaign/` for the implementation and `tests/tuxemon/campaign/` for the test suite.

---

## 7. Out of Scope for MVP

The following are explicitly out of scope for the Campaign Maker MVP:

- **Visual map painter** — The MVP uses Tiled as the map editor; a custom in-engine map painter is Phase 3.3+.
- **Online publishing** — Campaign upload/distribution is a future community feature; the MVP exports to a local file only.
- **Multiplayer campaign co-op** — Campaigns are single-player; online battle/trading features are independent pillars.
- **Audio composition tools** — Creators bring their own audio files; the MVP does not include an audio editor.
- **Advanced scripting IDE** — The MVP uses a visual event graph; a text-based scripting IDE is stretch/Phase 3+.

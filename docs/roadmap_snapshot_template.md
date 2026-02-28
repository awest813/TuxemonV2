# Roadmap Snapshot — [Month Year]

## Status

- **Date**: YYYY-MM-DD
- **Branch**: `[branch_name]`
- **Commit**: `[short_hash]`
- **Roadmap completion**: XX/YY milestones

## Content Snapshot

Run `python run_tuxemon.py --status` and paste output:

```
Monsters: NNN | Techniques: NNN | Items: NNN | NPCs: NNN | Maps: NNN | Localizations: NN
```

## Balance Snapshot

Run `python scripts/balance_report.py` and note any flags:

```
Balance flags: N
- [list any flags]
```

## Validation Status

```bash
python -m tuxemon.database.content_validator        # Cross-references: PASS/FAIL
python -m tuxemon.database.content_validator --strict # Locale coverage: PASS/FAIL
pytest tests                                         # Test suite: PASS/FAIL (N tests)
```

## Changes Since Last Snapshot

### Completed
- [ ] Item 1
- [ ] Item 2

### In Progress
- [ ] Item 1

### Deferred / Descoped
- [ ] Item 1 (reason)

## Next Priorities

1. Priority 1
2. Priority 2
3. Priority 3

## Known Issues

- Issue 1 (link to GitHub issue if applicable)

---

*This snapshot follows the cadence established in ROADMAP.md Phase 4. Generate a new snapshot at the start of each month or after significant milestones.*

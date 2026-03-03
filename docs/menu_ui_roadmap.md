# Menu & UI Systems Roadmap

This roadmap covers the evolution of the menu system (`tuxemon/menu/`) and UI system (`tuxemon/ui/`) in OpenCapsuleMon. It is organized by phases, with each phase building on the previous one.

---

## Current State (Baseline)

### What Works

- **Menu system** supports two paradigms: sprite-based `Menu[T]` (legacy) and widget-based `PygameMenuState` (pygame-menu-ce).
- **MenuController** provides safe state machine transitions with logging for invalid operations.
- **Cursor navigation** with animated movement, repeat-on-hold, and touch/mouse support.
- **Dialog system** with character-by-character animation, split-line alerts, and queued messages.
- **Combat HUD** with YAML-driven layouts, HP/EXP bars, status icons, and text overlays.
- **Text rendering** with shadow text, alignment, overflow handling, and multiline wrapping.
- **Quantity menus** for buying/selling items with price/cost display.
- **Text formatting** with dynamic placeholder replacement (player data, monster stats, game variables).
- **Pagination** for both text and generic item lists.
- **Input system** with character sets, variants, and character limits.
- **Test coverage:** 4026+ passing tests including 217+ tests specifically for menu/UI components.

### Recent Fixes (This Overhaul)

| Fix | File | Description |
|-----|------|-------------|
| `get_open_slot` return type | `combat_hud.py` | Returns `None` when all slots occupied instead of silently returning 0 |
| Text formatter replacement loop | `text_formatter.py` | Fixed bug where intermediate replacements were lost; moved `import re` to module level |
| Font size cache bound | `draw.py` | Cache now clears at 4096 entries to prevent unbounded memory growth |
| RuntimeError message | `draw.py` | Fixed two-arg `RuntimeError` to use f-string |
| Label data safety | `combat_text_display.py` | Uses `dict.get()` to avoid `KeyError` on missing label keys |
| MonsterSpriteMap docstring | `combat_monsters.py` | Fixed misleading docstring (returns None, does not raise) |
| CombatLayoutManager encapsulation | `combat_hud.py` | Added `get_monster_ui()` and `iter_monster_ui()` public API |
| StatusIconManager encapsulation | `combat_status.py` | Migrated from `_monster_ui` direct access to public API |
| TextAnimationManager API | `combat_notifier.py` | Added `pending_xp_duration` property and `consume_pending_xp_duration()` method |
| SwapTracker reset | `combat_swap.py` | Added `reset_all()` for clearing persistent blocks on battle end |
| MenuController helpers | `controller.py` | Added `is_opening()` and `is_closing()` state queries |
| Duplicate test name | `test_ui_graphic_box.py` | Fixed `test_init_with_custom_grid_size` duplicate |
| Invalid grid_size test | `test_ui_graphic_box.py` | Fixed test using unsupported grid_size=4 |

### New Tests Added

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_menu_controller.py` | 26 | Full MenuController state machine lifecycle |
| `test_menu_formatter.py` | 11 | CurrencyFormatter and QuantityFormatter |
| `test_menu_events.py` | 8 | PlayerInput → pygame.Event mapping |
| `test_menu_input.py` | 18 | InputController and CharacterSetManager |
| `test_combat_swap.py` | 11 | SwapTracker blocking and reset logic |
| `test_combat_notifier.py` | 11 | TextAnimationManager queuing and XP duration |
| `test_combat_zone.py` | 10 | CombatZone screen zone classification |
| `test_ui_paginator.py` | 12 | Generic Paginator operations |
| `test_ui_text_paginator.py` | 6 | TextPaginator wrapping and splitting |
| `test_ui_draw_cache.py` | 7 | Font size cache bounds and eviction |

---

## Phase 1 — Polish and Reliability (Short-term)

### 1.1 Input Handling Robustness
-- [x] Add dead-zone handling for analog stick inputs in `MenuInputHandler`.
  - `tuxemon/menu/input_handler.py` — `MenuInputHandler.ANALOG_DEAD_ZONE = 0.25` constant; `_is_analog_deadzone()` filters float axis values below the threshold in `_valid_press()`.
- [x] Support configurable repeat delay and interval per menu type.
  - `MenuInputHandler(menu, repeat_delay=…, repeat_interval=…)` constructor parameters override the class-level defaults without changing existing call sites.
  - `PygameMenuInputHandler(state, repeat_delay=…)` likewise accepts a per-instance override.
- [x] Add accessibility option for single-press-only navigation (no hold repeat).
  - `single_press_only=True` on both `MenuInputHandler` and `PygameMenuInputHandler` disables hold-repeat entirely; only initial key-down events trigger cursor movement or updates.
- [x] Test cursor wrapping behavior (first item → last item and vice versa).
  - `tests/tuxemon/test_menu_input_robustness.py` — `test_cursor_wraps_from_last_to_first`, `test_cursor_wraps_from_first_to_last`.

### 1.2 Dialog System Improvements
- [ ] Add rich text support (bold, italic, color inline markers) in `TextArea`.
- [ ] Support portrait/avatar display alongside dialog text.
- [x] Add dialog history/log accessible via a button press.
  - `tuxemon/ui/dialog_history.py` — `DialogHistory` (bounded `deque`-backed log of `DialogEntry` records; configurable `max_entries`, FIFO eviction).
  - `tuxemon/states/dialog_state.py` — `DialogState` accepts optional `history: DialogHistory` and `speaker: str | None`; every call to `next_text()` records the shown text via `history.record(text, speaker=speaker)`.
- [x] Implement auto-advance option for dialogs (timed progression).
  - Already implemented in `DialogState` via `close_after` + `per_line_timeout` parameters.
- [ ] Add sound effects per character during text animation.

### 1.3 Text Rendering Quality
- [x] Implement `TextOverflow.SHRINK` (dynamic font size reduction to fit bounds).
  - `tuxemon/ui/draw.py` — `_find_shrink_font()` steps the font size down from the original until the text fits within the target rect, or falls back to `min_font_size`. `iter_render_text()` applies it when `overflow_behavior=TextOverflow.SHRINK`.
- [x] Add text outline rendering as an alternative to drop shadow.
  - `tuxemon/ui/text_renderer.py` — `TextRenderer.outline_text()` renders 8-directional stroke outlines then composites the foreground on top; configurable `outline_color` and `outline_width`.
- [ ] Support right-to-left (RTL) text layout for Arabic/Hebrew localization.
- [x] Optimize `font_size_cache` with LRU eviction instead of full clear.
  - `tuxemon/ui/draw.py` — `font_size_cache` is now an `OrderedDict`; `get_text_size()` promotes accessed entries to most-recently-used and evicts only the single oldest entry when the cache is full (instead of clearing everything).

### 1.4 Combat HUD Polish
- [x] Add HP bar drain animation (smooth decrease instead of instant).
  - `tuxemon/ui/bar_animator.py` — `HpBarAnimator` with frame-rate-independent drain and ghost-bar overlay (amber residual shows old HP level immediately on damage while bar drains).
  - `tuxemon/ui/combat_bars.py` — `CombatBars` now owns `HpBarAnimator` per monster; `update(dt)` advances animators each frame; `draw_bars()` renders ghost layer then active bar.
- [x] Add EXP bar fill animation (smooth increase on level-up).
  - `ExpBarAnimator` in `bar_animator.py` supports normal fill and level-up wrap-around (fill-to-max → reset-to-zero → fill-to-new-progress) with configurable delay and fill speed.
- [ ] Support dynamic HUD resizing for different screen resolutions.
- [x] Add weather/terrain indicator to combat HUD.
  - `tuxemon/ui/combat_overlay.py` — `WeatherTerrainIndicator` tracks active weather and terrain tokens, remaining turns, and exposes a `changed` flag for efficient HUD re-renders. `WeatherTerrainState` snapshot dataclass surfaces `has_effect` and `display_token` helpers.
- [x] Add turn counter display.
  - `tuxemon/ui/combat_overlay.py` — `TurnCounter` tracks current (1-based) turn and total completed turns; `next_turn()` advances and `reset()` restores initial state.

### 1.5 Error Handling and Logging
- [x] Audit all `except Exception` blocks and narrow to specific exceptions.
  - `tuxemon/menu/alert.py` — narrowed `StopIteration` to its own `except` clause in `animate_text` and `dump_remaining_text`; remaining `except Exception` guards are appropriate for untrusted caller callbacks.
- [x] Add structured logging context (menu name, state, action) to all log messages.
  - `tuxemon/menu/alert.py` — log messages now include `message=%r`, `text=%r`, and action context.
  - `tuxemon/menu/input_handler.py` — log messages now include `button=%r` and handler context string.
  - `tuxemon/states/dialog_state.py` — on_complete callback log includes descriptive context.
- [ ] Add metrics collection for menu navigation patterns (debug builds only).

---

## Phase 2 — Accessibility and UX (Medium-term)

### 2.1 Accessibility Features
- [ ] High-contrast mode for all menu elements.
- [ ] Configurable font size multiplier (beyond `large_gui` toggle).
- [ ] Screen reader support via text-to-speech integration.
- [ ] Color-blind friendly HP bar colors (configurable palette).
- [ ] Keyboard shortcut overlay for all menu actions.

### 2.2 Menu Navigation UX
- [ ] Breadcrumb trail for nested menu navigation.
- [ ] Menu transition animations (slide, fade) between states.
- [ ] Recent/favorite items quick-access in menus.
- [ ] Search/filter functionality for large menu lists (item menu, monster menu).
- [ ] Tooltips and help text on hover/focus.

### 2.3 Touch and Controller UX
- [ ] Swipe gesture support for menu navigation.
- [ ] Controller button prompts (Xbox/PlayStation/Switch icons).
- [ ] Touch-friendly scaling for mobile platforms.
- [ ] Haptic feedback integration with rumble system.

### 2.4 Localization Support
- [ ] Complete RTL layout support for all menu elements.
- [ ] Dynamic text wrapping that handles CJK characters correctly.
- [ ] Locale-aware number and currency formatting.
- [ ] Font fallback chains for scripts not covered by primary font.

---

## Phase 3 — Architecture Evolution (Long-term)

### 3.1 Unified Menu Framework
- [ ] Evaluate unifying `Menu[T]` and `PygameMenuState` into a single menu API.
- [ ] Design a declarative menu definition format (YAML/JSON-driven menus).
- [ ] Implement hot-reload for menu layouts during development.
- [ ] Add menu profiling tools (render time, input latency).

### 3.2 Component Architecture
- [ ] Extract reusable UI components (buttons, sliders, checkboxes) into a component library.
- [ ] Implement a layout engine (flexbox-like) for responsive positioning.
- [ ] Add theming engine for per-mod visual customization.
- [ ] Support animated backgrounds and particle effects in menus.

### 3.3 Combat UI Architecture
- [ ] Support 3v3 and 4v4 battle layouts (currently limited to 1v1 and 2v2).
- [ ] Add spectator-optimized HUD layout.
- [ ] Support picture-in-picture for simultaneous battles.
- [ ] Add damage number pop-ups and hit effect indicators.
- [ ] Implement timeline/turn-order display.

### 3.4 Campaign Maker Integration
- [ ] Provide a visual menu editor for campaign creators.
- [ ] Support custom dialog styles per NPC/event.
- [ ] Allow campaigns to define custom menu layouts and themes.
- [ ] Add preview mode for custom dialogs during campaign editing.

### 3.5 Online Play UI
- [ ] Tournament bracket visualization.
- [ ] Lobby/waiting room menu with player list and chat.
- [ ] Match-found notification and accept/decline dialog.
- [ ] Spectator controls overlay.
- [ ] Online casino game selection menu.

---

## Phase 4 — Performance and Testing (Ongoing)

### 4.1 Performance
- [ ] Profile menu render pipeline and identify bottlenecks.
- [ ] Implement sprite batching for menu elements.
- [ ] Add GPU-accelerated text rendering option.
- [ ] Reduce Surface allocations in animation loops.

### 4.2 Test Coverage Goals
- [ ] Achieve 90%+ line coverage for `tuxemon/menu/` and `tuxemon/ui/`.
- [ ] Add integration tests that exercise full menu lifecycles (open → navigate → select → close).
- [ ] Add visual regression tests for key menu screens.
- [ ] Add property-based tests for text wrapping and pagination edge cases.
- [ ] Add fuzz testing for text formatter placeholder replacement.

### 4.3 Documentation
- [ ] Auto-generate API docs for all public menu/UI classes.
- [ ] Add visual diagrams for state machine transitions.
- [ ] Create a menu/UI style guide for contributors.
- [ ] Add annotated screenshots for each menu type.

---

## Priority Matrix

| Priority | Items | Rationale |
|----------|-------|-----------|
| **P0 — Critical** | HP bar animation, error handling audit, accessibility font scaling | Directly impacts player experience |
| **P1 — Important** | Dialog portraits, touch UX, RTL support, search/filter | Needed for content expansion and localization |
| **P2 — Valuable** | Unified framework, component library, campaign maker integration | Architecture quality and creator tooling |
| **P3 — Nice-to-have** | Particle effects, GPU rendering, spectator UI | Polish for advanced features |

---

## Definition of Done for Roadmap Items

A roadmap item is complete when:

1. Implementation is merged and passes all tests.
2. Existing tests are not broken.
3. New behavior has dedicated tests.
4. READMEs are updated if public API changes.
5. No regressions in menu navigation or dialog display.
6. Accessibility features are verified with at least one non-default configuration.
7. Performance is comparable or better than before the change.

---

## Dependencies and Constraints

- **pygame-menu-ce** version compatibility must be maintained for `PygameMenuState`.
- **Display scaling** must work correctly at all supported resolutions (the `ScalingStrategy` API).
- **Mod compatibility** — menu/UI changes must not break existing mod content or save files.
- **Localization** — all user-facing text must go through the translation system.
- **Platform support** — menus must work on desktop (keyboard+mouse), controller, and touch inputs.

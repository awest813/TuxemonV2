# UI System (`tuxemon/ui/`)

The UI system provides all visual components for rendering text, dialog boxes, combat HUDs, progress bars, status icons, and layout management in OpenCapsuleMon. It works alongside the menu system (`tuxemon/menu/`) to deliver the complete user interface.

---

## Architecture Overview

```
tuxemon/ui/
├── Text Rendering
│   ├── text.py               # TextArea (animated text display), MultilineTextRenderer, draw_text()
│   ├── text_renderer.py      # TextRenderer (shadow text rendering)
│   ├── text_alignment.py     # DialogPosition, HorizontalAlignment, VerticalAlignment enums
│   ├── text_formatter.py     # TextFormatter (placeholder replacement for dialog text)
│   ├── text_paginator.py     # TextPaginator (text wrapping and page splitting)
│   └── draw.py               # Low-level text rendering: iter_render_text, overflow, alignment, caching
│
├── Dialog & Display
│   ├── dialogue.py           # Dialog rect calculation, DialogueStyleCache
│   ├── graphic_box.py        # GraphicBox (bordered window rendering), TileLayout
│   ├── input_display.py      # InputDisplay (text input prompt UI)
│   ├── cipher_processor.py   # CipherProcessor (encoded text with unlockable letters)
│   └── paginator.py          # Generic Paginator for item lists
│
├── Combat UI
│   ├── combat_hud.py         # CombatLayoutManager, MonsterUI, Side enum
│   ├── combat_bars.py        # CombatBars (HP/EXP bar management per monster)
│   ├── combat_layout.py      # LayoutRepository, LayoutSelector, LayoutManager (YAML-driven)
│   ├── combat_status.py      # StatusIconManager (status effect icons)
│   ├── combat_monsters.py    # MonsterSpriteMap (entity→sprite mapping)
│   ├── combat_text_display.py# CombatTextDisplay (HUD text overlay)
│   ├── combat_notifier.py    # TextAnimationManager, CombatNotifier (message queue)
│   ├── combat_zone.py        # CombatZone (screen zone classification)
│   ├── combat_swap.py        # SwapTracker (monster swap blocking)
│   └── method_animation.py   # MethodAnimationCache (technique/status animation sprites)
│
├── Menu Integration
│   └── menu_options.py       # MenuOptions, ChoiceOption (menu choice management)
│
└── __init__.py
```

---

## Text Rendering Pipeline

### TextRenderer (text_renderer.py)

The foundational text rendering class. Renders text with a drop shadow.

```python
renderer = TextRenderer(scaling=ctx.scaling, font_color=(255, 255, 255))
surface = renderer.shadow_text("Hello World")
```

### TextArea (text.py)

An animated text display area. Characters appear one at a time (typewriter effect) when `animated=True`.

**Key properties:**
- `text` — setting this triggers animation or immediate rendering.
- `drawing_text` — True while animation is in progress.
- Supports horizontal/vertical alignment and overflow behavior.
- Implements `__iter__` / `__next__` for character-by-character stepping.

### MultilineTextRenderer (text.py)

Wraps text into multiple lines and renders each line as a Surface.

### draw_text() (text.py)

High-level function for drawing text onto a surface within a rect, handling wrapping and alignment.

### iter_render_text() (draw.py)

Low-level generator that yields `RenderedChar` objects for each character/token/line. Supports three render modes:
- `CHARACTER` — character by character (default)
- `TOKEN` — word by word
- `LINE` — line by line

### TextOverflow (draw.py)

Controls what happens when text exceeds its bounding rect:

| Mode | Behavior |
|------|----------|
| `CLIP` | Truncates silently |
| `ELLIPSIS` | Adds "…" at truncation point |
| `EXPAND` | Allows overflow (scrollable views) |
| `WRAP` | Moves overflow text to next line |
| `SHRINK` | Reserved for future font-size reduction |

### Font Size Cache (draw.py)

`get_text_size()` caches font measurements to avoid repeated calls to `Font.size()`. The cache is bounded at 4096 entries and resets when full.

---

## Dialog System

### calc_dialog_rect() (dialogue.py)

Calculates a dialog box rect on screen with support for 10 positioning modes:

`TOP`, `BOTTOM`, `CENTER`, `TOPLEFT`, `TOPRIGHT`, `BOTTOMLEFT`, `BOTTOMRIGHT`, `LEFT`, `RIGHT`, `AT_TARGET`

Dialog size scales based on the `large_gui` config setting.

### DialogueStyleCache (dialogue.py)

Caches `DialogueModel` lookups from the database for efficient repeated access during dialog rendering. Supports preloading multiple styles.

---

## GraphicBox (graphic_box.py)

Renders bordered windows using a 3x3 tileset (corners, edges, center).

### TileLayout

Extracts a grid of named tiles (`nw`, `n`, `ne`, `w`, `c`, `e`, `sw`, `s`, `se`) from a border image.

---

## Combat UI Components

### CombatLayoutManager (combat_hud.py)

Central manager for battle positioning:
- Assigns monsters to sides (PLAYER/OPPONENT) and slot indices.
- Maps monsters to layout keys (e.g., "home", "home0", "home1").
- Manages HUD sprite assignments.
- Provides `get_monster_ui()` and `iter_monster_ui()` for public access to per-monster UI state.

**`MonsterUI` dataclass:** Holds `slot_index`, `layout_key`, `hud_sprite`, `status_icons`, `feet_pos` for each active monster.

### CombatBars (combat_bars.py)

Manages HP and EXP bar instances per monster. Creates bars lazily on first access.

### LayoutManager (combat_layout.py)

YAML-driven layout system:
1. `LayoutRepository` — loads and caches raw layout coordinates from YAML.
2. `LayoutSelector` — selects the correct layout group by player index.
3. `LayoutRectFactory` — converts coordinate tuples to `pygame.Rect` objects.
4. `LayoutManager` — combines all three for a unified API.

### StatusIconManager (combat_status.py)

Handles creation, caching, and updating of status effect icons:
- Creates icon sprites at positions derived from layout data.
- Caches icons by `(icon_filename, position)` to avoid reloading.
- Supports icon animation (fade in/out).
- Uses public `CombatLayoutManager` API for encapsulation.

### MonsterSpriteMap (combat_monsters.py)

Simple entity→sprite mapping with add, get, remove, and position update operations.

### CombatTextDisplay (combat_text_display.py)

Draws dynamic text (name, level, status) onto monster HUD sprites with a translucent background strip for readability.

### TextAnimationManager / CombatNotifier (combat_notifier.py)

**TextAnimationManager:** Manages a queue of timed text animations for combat messages.
- Computes animation duration based on message length.
- Supports XP message aggregation and pending duration tracking via `pending_xp_duration` property.

**CombatNotifier:** Coordinates message display with player input blocking.
- `show_message_and_wait_for_input()` — displays a message and optionally pushes a WaitForInputState.
- `trigger_xp_and_wait_for_input()` — triggers XP animation and schedules input blocking.

### CombatZone (combat_zone.py)

Classifies screen positions into horizontal (LEFT/CENTER/RIGHT) and vertical (TOP/CENTER/BOTTOM) zones. Used for determining animation directions.

### SwapTracker (combat_swap.py)

Tracks monster swap state during combat:
- `register()` — marks a monster as swapped this turn.
- `block_swap()` — blocks swapping with a reason (temporary or persistent).
- `clear()` — resets turn-specific state and temporary blocks.
- `reset_all()` — clears everything including persistent blocks (battle end).

### MethodAnimationCache (method_animation.py)

Caches animation sprites for techniques, statuses, and items by `(slug, flipped)` key.

---

## Menu Integration

### MenuOptions / ChoiceOption (menu_options.py)

- `ChoiceOption` — dataclass representing a single menu choice with key, display text, and action callback.
- `MenuOptions` — collection with add/remove/replace/filter/sort/group operations.
- `create_choice_options()` — builds options from a mapping of actions.
- `create_yes_no_options()` — convenience for Yes/No dialogs.

---

## TextFormatter (text_formatter.py)

Replaces placeholders in dialog text with dynamic values at runtime.

**Built-in placeholders:**
- `${{name}}`, `${{NAME}}` — player name
- `${{money}}`, `${{money_formatted}}` — wallet balance
- `${{today}}`, `${{birthdate}}` — dates
- `${{map_name}}`, `${{map_desc}}` — current map info
- `${{monster_N_name}}`, `${{monster_N_level}}`, etc. — party monster attributes
- `${{var:key}}`, `${{msgid:key}}` — game variables
- Unit conversions (metric/imperial) for steps, weight, height

**Custom placeholders:** Register via `register_replacement("${{custom}}", lambda: "value")`.

---

## Configuration

| Setting | Source | Description |
|---------|--------|-------------|
| `dialog_speed` | `user_config.py` | Text animation speed |
| `large_gui` | `user_config.py` | Larger fonts and dialog boxes |
| `dialog_box_style` | `user_config.py` | Dialog box visual style |
| `menu_border` | `user_config.py` | Border tileset for windows |
| `menu_cursor` | `user_config.py` | Cursor arrow image |
| `menu_sound` | `user_config.py` | Selection sound effect |
| `unit_measure` | `user_config.py` | Metric or imperial units |

---

## Testing

UI tests are located in `tests/tuxemon/`:

| Test File | Coverage Area |
|-----------|---------------|
| `test_ui_text_renderer.py` | TextRenderer shadow text rendering |
| `test_ui_text_renderer_multiline.py` | MultilineTextRenderer line wrapping |
| `test_ui_draw_methods.py` | iter_render_text, alignment, wrapping utilities |
| `test_ui_draw_cache.py` | Font size cache bounds and eviction |
| `test_ui_overflow_handler.py` | OverflowHandler behavior for all overflow modes |
| `test_ui_dialogue.py` | Dialog rect calculation for all positions |
| `test_ui_graphic_box.py` | TileLayout, GraphicBox rendering |
| `test_ui_menu_options.py` | MenuOptions and ChoiceOption operations |
| `test_ui_combat_layout.py` | LayoutRepository, LayoutSelector, LayoutManager |
| `test_ui_paginator.py` | Generic Paginator item pagination |
| `test_ui_text_paginator.py` | TextPaginator text wrapping and pagination |
| `test_combat_ui.py` | CombatBars HP/EXP bar management |
| `test_combat_swap.py` | SwapTracker swap blocking logic |
| `test_combat_notifier.py` | TextAnimationManager queuing and timing |
| `test_combat_zone.py` | CombatZone screen zone classification |

Run UI tests:

```bash
python3 -m pytest tests/tuxemon/test_ui_*.py tests/tuxemon/test_combat_*.py -v
```

---

## Design Principles

1. **Separation of concerns:** Menu logic (state, input, cursor) is separate from UI rendering (text, bars, boxes).
2. **Encapsulation:** Combat UI components access layout data through public APIs (`get_monster_ui()`, `iter_monster_ui()`), not internal state.
3. **Caching:** Font sizes, graphics, and animation sprites are cached to minimize I/O and computation.
4. **Configurability:** Visual appearance is driven by user settings and mod data, not hardcoded values.
5. **Testability:** All components are designed for unit testing without requiring a running game instance.

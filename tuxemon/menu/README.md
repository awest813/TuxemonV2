# Menu System (`tuxemon/menu/`)

The menu system provides the core infrastructure for all in-game menus, dialog boxes, quantity selectors, and interactive overlays in OpenCapsuleMon. It supports both the legacy sprite-based `Menu` class and the modern `pygame-menu-ce`-backed `PygameMenuState`.

---

## Architecture Overview

```
tuxemon/menu/
├── menu.py            # Menu, PygameMenuState, PopUpMenu base classes
├── controller.py      # MenuController state machine (CLOSED → OPENING → NORMAL → DISABLED → CLOSING)
├── cursor.py          # MenuCursor sprite and MenuCursorController
├── input_handler.py   # MenuInputHandler (legacy), PygameMenuInputHandler (pygame-menu)
├── interface.py       # MenuItem, Bar, HpBar, ExpBar
├── theme.py           # Tuxemon theme and sound engine for pygame-menu
├── alert.py           # AlertManager for queued text alerts and split-line dialogs
├── quantity.py        # QuantityMenu, QuantityAndPriceMenu, QuantityAndCostMenu
├── formatter.py       # CurrencyFormatter, QuantityFormatter
├── input.py           # InputController, CharacterSetManager, NameDataLoader
├── events.py          # PlayerInput → pygame.Event adapter
└── __init__.py
```

---

## Core Components

### `Menu[T]` (menu.py)

The primary sprite-based menu class. All classic menus (world menu, monster menu, combat menu, shop menus) inherit from this.

**Key features:**
- Generic type `T` represents the game object or callback attached to each menu item.
- Supports column layouts, cursor navigation, borders, background images, and transparency.
- Anchoring system for positioning relative to screen coordinates.
- Open/close animations via `animate_open()` / `animate_close()`.
- Invalidation-based layout: call `invalidate_layout()` to schedule re-arrangement on the next `draw()`.
- Input handling delegated to `MenuInputHandler`.

**Lifecycle:**
1. `__init__` → loads fonts, graphics, sounds, creates input handler and cursor controller.
2. `resume()` → transitions from CLOSED → OPENING → NORMAL, plays open animation.
3. User interacts → `process_event()` → `MenuInputHandler.handle_event()`.
4. `close()` → transitions to CLOSING, plays close animation, pops state.
5. `shutdown()` → clears sprites and breaks cyclical references.

### `PygameMenuState` (menu.py)

Wraps `pygame-menu-ce` for more complex menu layouts (scrollable lists, widgets, forms).

**Key features:**
- Uses `pygame_menu.Menu` under the hood.
- Theming via `get_theme()` (TuxemonArrowSelection for cursor).
- Input handled by `PygameMenuInputHandler`.
- Supports custom background images via `_setup_theme()`.

### `PopUpMenu[T]` (menu.py)

A `Menu` subclass with a scale-up animation on open.

---

### `MenuController` (controller.py)

A finite state machine managing menu lifecycle transitions:

```
CLOSED ──open()──→ OPENING ──set_normal()──→ NORMAL ──disable()──→ DISABLED
                                              │                       │
                                              ├──close()──→ CLOSING   ├──enable()──→ NORMAL
                                              │                       ├──close()──→ CLOSING
                                              └──────────────────────────────────→ reset() → CLOSED
```

**State queries:**
- `is_closed()`, `is_opening()`, `is_enabled()`, `is_disabled()`, `is_closing()`, `is_interactive()`

Invalid transitions are logged as warnings and safely ignored (no exceptions).

---

### `MenuCursor` / `MenuCursorController` (cursor.py)

- `MenuCursor` is a `Sprite` representing the selection arrow.
- `MenuCursorController` manages visibility, animated movement between items, and focus state changes.
- Margin calculation uses ratios to adapt cursor offset to different display scales.

---

### `MenuInputHandler` (input_handler.py)

Handles player input for the sprite-based `Menu`:

| Input | Action |
|-------|--------|
| A / SELECT | Confirm selection → `on_menu_selection()` |
| B / BACK / MENU_CANCEL | Close menu (if `escape_key_exits`) |
| UP / DOWN / LEFT / RIGHT | Move cursor with repeat-on-hold support |
| MOUSELEFT | Touch/click selection (if `touch_aware`) |

**Repeat behavior:** After `REPEAT_DELAY` (0.5s), cursor movement repeats every `REPEAT_INTERVAL` (0.08s).

### `PygameMenuInputHandler` (input_handler.py)

Converts `PlayerInput` events to `pygame.Event` objects and feeds them to the `pygame-menu` update loop. Directional buttons support held-repeat; other buttons require a fresh press.

---

### `MenuItem[T]` (interface.py)

A generic selectable item within a menu. Each item has:
- `image` (Surface) — visual representation
- `label` (str) — display text
- `description` (str) — tooltip text
- `game_object` (T) — callback or linked object triggered on selection
- `enabled` — whether the item is interactable
- `in_focus` — whether the cursor is currently on this item
- `metadata` — arbitrary dict for extension

### `Bar`, `HpBar`, `ExpBar` (interface.py)

Progress bars for HP and EXP display in the combat HUD.

- `Bar` is the base class with clamped value (0.0–1.0), border graphics, and a gloss overlay.
- `HpBar` changes color based on HP percentage: green (>50%), yellow (>20%), red (≤20%).
- `ExpBar` uses a consistent blue fill.
- Graphics are cached per border filename to avoid repeated disk loads.

---

### `AlertManager` (alert.py)

Manages a queue of text alert messages for dialog boxes.

**Features:**
- Queued alerts: multiple messages are processed in order.
- Split-line support: long messages can be split by newlines and advanced one line at a time.
- Character-by-character animation with configurable speed.
- Callbacks on alert completion.
- Event bus integration: publishes `DIALOG_STARTED` events.

---

### `QuantityMenu` / `QuantityAndPriceMenu` / `QuantityAndCostMenu` (quantity.py)

Specialized menus for selecting quantities (e.g., buying/selling items).

- UP/DOWN changes by 1, LEFT/RIGHT changes by 10.
- Hold-repeat support for rapid adjustment.
- Optional price/cost display with currency formatting.
- Shows wallet balance when buying/selling.

---

### Formatters (formatter.py)

- `CurrencyFormatter` — formats monetary values with configurable symbol, position, and width.
- `QuantityFormatter` — formats quantity values (e.g., "x 5").

---

### Input System (input.py)

- `InputController` — manages a text input field with character limit, backspace, clear, and direct override.
- `CharacterSetManager` — manages character sets for text input menus, including variant characters (e.g., accented letters).
- `NameDataLoader` — loads random NPC names from YAML files by gender and language.

---

### Event Adapter (events.py)

`playerinput_to_event()` converts `PlayerInput` button presses to `pygame.Event` objects for consumption by `pygame-menu-ce`. Maps directional buttons, confirm (A → RETURN), and cancel (B/BACK → ESCAPE).

---

### Theme (theme.py)

`get_theme()` creates and caches the default Tuxemon `pygame-menu` theme:
- Border and background from the configured `menu_border` asset.
- `TuxemonArrowSelection` renders the cursor arrow alongside selected widgets.
- Font sizes, colors, and shadow settings from `tuxemon.platform.const.graphics`.

`get_sound_engine()` creates and caches the menu selection sound engine.

---

## Configuration

Menu appearance is controlled by settings in `tuxemon/config.py` and `tuxemon/user_config.py`:

| Setting | Description |
|---------|-------------|
| `menu_sound` | Sound file played on menu selection |
| `menu_border` | Border tileset image for menu windows |
| `menu_cursor` | Cursor arrow image |
| `dialog_speed` | Speed of text animation in dialogs |
| `large_gui` | Increases font sizes and dialog heights for accessibility |
| `locale.font_file` | TTF font file for menu text |

---

## Testing

Menu system tests are located in `tests/tuxemon/`:

| Test File | Coverage Area |
|-----------|---------------|
| `test_menu_controller.py` | MenuController state machine transitions |
| `test_menu_cursor.py` | MenuCursorController visibility, movement, focus |
| `test_menu_input_handler1.py` | MenuInputHandler event handling |
| `test_menu_input_handler2.py` | PygameMenuInputHandler event handling |
| `test_interface_menu_item.py` | MenuItem properties and behavior |
| `test_menu_formatter.py` | CurrencyFormatter, QuantityFormatter |
| `test_menu_events.py` | PlayerInput → pygame.Event conversion |
| `test_menu_input.py` | InputController, CharacterSetManager |

Run menu tests:

```bash
python3 -m pytest tests/tuxemon/test_menu_*.py tests/tuxemon/test_interface_menu_item.py -v
```

---

## Extending the Menu System

### Adding a New Menu State

1. Create a new file in `tuxemon/states/` (e.g., `my_menu.py`).
2. Subclass `Menu[Callable[[], object]]` for sprite-based menus, or `PygameMenuState` for widget-based menus.
3. Override `initialize_items()` to populate menu entries.
4. Override `on_menu_selection()` if you need custom selection behavior.
5. Register the state name in the state manager.

### Adding a New Menu Item Type

Subclass `MenuItem[T]` and override `update_image()` for custom rendering.

### Custom Animations

Override `animate_open()` and `animate_close()` in your menu subclass. Return an `Animation` object to schedule callbacks on completion.

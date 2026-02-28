"""Static game constants for colors, asset paths, and font sizes."""

# Asset Paths
GFX_HP_BAR: str = "gfx/ui/monster/hp_bar.png"
GFX_XP_BAR: str = "gfx/ui/monster/exp_bar.png"
MISSING_IMAGE: str = "gfx/sprites/battle/missing.png"

# ── Color Palette ─────────────────────────────────────────────────────
# Primary monster-bar colors
HP_COLOR_FG = (56, 212, 92)  # vibrant green (higher saturation, clearer)
HP_COLOR_BG = (220, 50, 50)  # softer red (less eye-straining than pure red)
XP_COLOR_FG = (64, 180, 240)  # sky blue (more legible than washed cyan)
XP_COLOR_BG = None

# HP bar dynamic tier colors (used by HpBar.get_fill_color)
HP_TIER_HIGH = (72, 208, 104)  # green — above 50%
HP_TIER_MID = (240, 188, 56)  # amber — 20%-50%
HP_TIER_LOW = (216, 72, 72)  # soft red — below 20%

# EXP bar fill color
XP_FILL_COLOR = (96, 176, 240)  # polished sky-blue fill

# Base colors
BLACK_COLOR = (0, 0, 0)
WHITE_COLOR = (255, 255, 255)
RED_COLOR = (255, 0, 0)
GREEN_COLOR = (0, 255, 0)
FUCHSIA_COLOR = (255, 0, 255)
SEA_BLUE_COLOR = (0, 105, 148)
DARKGRAY_COLOR = (169, 169, 169)
DIMGRAY_COLOR = (105, 105, 105)
TRANSPARENT_COLOR = (255, 255, 255, 0)

# UI surface colors
BACKGROUND_COLOR = (244, 244, 240)  # warm off-white (less sterile than pure gray)
FONT_COLOR = (16, 16, 24)  # near-black with slight warmth
FONT_SHADOW_COLOR = (176, 176, 184)  # neutral mid-gray shadow
UNAVAILABLE_COLOR = (200, 200, 204)  # disabled item gray
UNAVAILABLE_COLOR_SHOP = (64, 64, 68)  # shop-unavailable dark gray

# Scrollbar
SCROLLBAR_COLOR = (228, 236, 240)  # light cool-gray track
SCROLLBAR_SLIDER_COLOR = (160, 208, 216)  # teal-tinted slider

# Gradient Paths
GRAD_BLACK: str = "gfx/ui/background/gradient_black.png"
GRAD_BLUE: str = "gfx/ui/background/gradient_blue.png"
GRAD_BROWN: str = "gfx/ui/background/gradient_brown.png"
GRAD_GREEN: str = "gfx/ui/background/gradient_green.png"
GRAD_ORANGE: str = "gfx/ui/background/gradient_orange.png"
GRAD_RED: str = "gfx/ui/background/gradient_red.png"
GRAD_VIOLET: str = "gfx/ui/background/gradient_violet.png"
GRAD_YELLOW: str = "gfx/ui/background/gradient_yellow.png"

# Background Paths
TUX_GENERIC: str = "gfx/ui/background/tux_generic.png"
TUX_INFO: str = "gfx/ui/background/tux_info.png"
TECH_INFO: str = "gfx/ui/background/tech_info.png"
ITEM_MENU: str = "gfx/ui/item/item_menu_bg.png"
INDIV_INFO: str = "gfx/ui/background/passportbackground.png"
PYGAME_LOGO: str = "gfx/ui/intro/pygame_logo.png"
CREATIVE_COMMONS: str = "gfx/ui/intro/creative_commons.png"
BG_PLAYER1: str = "gfx/ui/background/player_info.png"
BG_PLAYER2: str = "gfx/ui/background/player_info1.png"
BG_PARTY: str = "gfx/ui/background/player_info2.png"
BG_ITEMS_BACKPACK: str = "gfx/ui/item/backpack.png"
BG_MONSTERS: str = "gfx/ui/monster/monster_menu_bg.png"

# Background paths per state (using gradients)
BG_MINIGAME: str = GRAD_BLUE
BG_MISSIONS: str = GRAD_BLUE
BG_PC_KENNEL: str = GRAD_BLUE
BG_PC_LOCKER: str = GRAD_BLUE
BG_PHONE: str = GRAD_BLUE
BG_PHONE_BANKING: str = GRAD_BLUE
BG_PHONE_CONTACTS: str = GRAD_BLUE
BG_PHONE_MAP: str = GRAD_BLUE
BG_PHONE_RENAMING: str = GRAD_BLUE
BG_START_SCREEN: str = GRAD_BLUE
BG_JOURNAL: str = TUX_GENERIC
BG_JOURNAL_CHOICE: str = TUX_GENERIC
BG_JOURNAL_INFO: str = TUX_INFO
BG_MONSTER_INFO: str = TUX_INFO
BG_ITEMS: str = ITEM_MENU
BG_MOVES: str = ITEM_MENU

# Font Sizes
# Relative size indices that are multiplied by the display scale factor
# to produce final pixel sizes.  Bump by +1 when ``large_gui`` is active.
FONT_SIZE_SMALLER = 3  # fine print, labels
FONT_SIZE_SMALL = 4  # secondary text, descriptions
FONT_SIZE = 5  # default body text
FONT_SIZE_BIG = 6  # headings, menu titles
FONT_SIZE_BIGGER = 7  # prominent headings
FONT_SIZE_BIGGEST = 8  # splash / title screen

# Line spacing applied between text lines (scaled at render time)
DEFAULT_LINE_SPACING = 10
# Menu widget padding (horizontal, vertical) in unscaled pixels
MENU_WIDGET_PADDING = (12, 22)

# Gloss overlay alpha values for bar rendering
BAR_GLOSS_ALPHA = 30
BAR_HIGHLIGHT_ALPHA = 50

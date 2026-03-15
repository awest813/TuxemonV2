## 2024-03-24 - QuantityMenu Confirm Interaction with SELECT Intention
**Learning:** `QuantityMenu` was missing the ability to confirm selections with `intentions.SELECT`, whereas general menus support it. This caused inconsistent behavior for users relying on alternative input methods mapped to the generic `SELECT` intention.
**Action:** Updated `QuantityMenu.process_event` to accept both `buttons.A` and `intentions.SELECT` for confirming a quantity selection, ensuring consistent input handling across the UI.
## 2024-05-18 - [Disabled Menu Item States]
**Learning:** Pygame sprites representing menu items didn't have visual cues when disabled, relying only on lack of interaction. Setting image alpha provides immediate visual feedback.
**Action:** Apply alpha transparency (128) to disabled surfaces for all custom UI sprites.
## 2024-05-20 - Adding Support for Intentions in Generic D-Pad Controls
**Learning:** Hardcoding standard controller inputs like `buttons.UP` and `buttons.DOWN` is inflexible and prevents custom or mapped inputs from working smoothly. Adding checks for corresponding intentions (e.g., `intentions.UP`) immediately improves accessibility for players relying on alternative input methods.
**Action:** When evaluating or modifying UI interaction logic (like `QuantityMenu._update_quantity` or `MenuInputHandler._handle_cursor`), always consider whether the check allows generic intentions alongside raw hardware buttons.

## 2024-05-22 - Visual Focus States for Menu Items
**Learning:** `MenuItem` sprites lacked a visual indicator when they were focused (relying solely on an external cursor or other hints). Applying a subtle brightening effect using `BLEND_RGB_ADD` significantly improves keyboard and gamepad navigation feedback.
**Action:** When implementing or modifying custom UI sprites that support an `in_focus` state, ensure that focus is communicated visually (e.g., through brightness, scale, or a highlight) to aid accessibility.
## 2026-03-15 - Added Visual Focus State Updates for MenuItem
**Learning:** The `MenuItem` custom UI sprite lacked an explicit visual update when its `in_focus` property was set via its property setter, unlike `enabled`. This caused keyboard/gamepad navigation to sometimes not reflect the focus state immediately, relying on the state update to trigger elsewhere.
**Action:** When creating or modifying properties on a UI sprite (like `in_focus` or `enabled`) that affect visual representation (e.g. using `BLEND_RGB_ADD` or setting alpha), always ensure the property setter checks for a change and calls `self.update_image()` to immediately reflect the new state.

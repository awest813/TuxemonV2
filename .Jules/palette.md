## 2024-03-24 - QuantityMenu Confirm Interaction with SELECT Intention
**Learning:** `QuantityMenu` was missing the ability to confirm selections with `intentions.SELECT`, whereas general menus support it. This caused inconsistent behavior for users relying on alternative input methods mapped to the generic `SELECT` intention.
**Action:** Updated `QuantityMenu.process_event` to accept both `buttons.A` and `intentions.SELECT` for confirming a quantity selection, ensuring consistent input handling across the UI.
## 2024-05-18 - [Disabled Menu Item States]
**Learning:** Pygame sprites representing menu items didn't have visual cues when disabled, relying only on lack of interaction. Setting image alpha provides immediate visual feedback.
**Action:** Apply alpha transparency (128) to disabled surfaces for all custom UI sprites.
## 2024-05-20 - Adding Support for Intentions in Generic D-Pad Controls
**Learning:** Hardcoding standard controller inputs like `buttons.UP` and `buttons.DOWN` is inflexible and prevents custom or mapped inputs from working smoothly. Adding checks for corresponding intentions (e.g., `intentions.UP`) immediately improves accessibility for players relying on alternative input methods.
**Action:** When evaluating or modifying UI interaction logic (like `QuantityMenu._update_quantity` or `MenuInputHandler._handle_cursor`), always consider whether the check allows generic intentions alongside raw hardware buttons.

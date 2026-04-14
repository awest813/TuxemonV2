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
## 2024-05-24 - Support Intentions in Pygame-Menu Event Adapter
**Learning:** Modern menus built with `pygame-menu-ce` rely on `playerinput_to_event` (via `_EVENT_MAP` in `tuxemon/menu/events.py`) to convert game `PlayerInput` into native `pygame.Event` objects. This map only checked physical `buttons` (e.g. `buttons.UP`, `buttons.A`), which broke navigation for users who remapped controls to generic `intentions` (like `intentions.UP`, `intentions.SELECT`).
**Action:** When creating adapters or bridging game input to third-party UI libraries, always map abstract `intentions` alongside literal `buttons` so alternative/custom control schemes still function correctly.
## 2026-03-20 - Adding Auditory Feedback to Quantity Changes
**Learning:**  lacked auditory feedback when changing the quantity via D-pad/intentions, unlike standard  interactions. This reduced accessibility and UI consistency.
**Action:** When implementing new UI elements or inputs that change state, verify that  (or the equivalent sound hook) is fired appropriately on state change to ensure intuitive and consistent feedback.

## 2024-05-25 - Adding Auditory Feedback to Quantity Changes
**Learning:** `QuantityMenu` lacked auditory feedback when changing the quantity via D-pad/intentions, unlike standard `Menu` interactions. This reduced accessibility and UI consistency.
**Action:** When implementing new UI elements or inputs that change state, verify that `self.menu_select_sound.play()` (or the equivalent sound hook) is fired appropriately on state change to ensure intuitive and consistent feedback.
## 2026-03-25 - [Audio Feedback for Custom Text Inputs]
**Learning:** In Pygame custom text input states (e.g., `InputMenu`), users may not perceive interactive actions like typing, backspacing, submitting, or generating random text as successful without audio feedback, particularly when visual updates are subtle. Auditory cues enhance UX and improve accessibility confirmation.
**Action:** Ensure custom interactive menus trigger standard UI auditory feedback (`self.menu_select_sound.play()`) on successful state changes.

## 2024-05-26 - [Audio Feedback for Invalid Inputs]
**Learning:** When users interact with text input fields (like `InputMenu`) and hit boundaries such as a character limit, missing auditory feedback can leave them confused about why their input was rejected. A distinct auditory cue for failure states clearly signals to the user that their action was invalid.
**Action:** When implementing input limits or validation, always provide distinct auditory feedback (like an error beep) for rejected inputs to communicate failure states effectively.
## 2024-04-10 - Add error sounds for invalid actions in InputMenu
**Learning:** In Pygame UI, it is an important UX and accessibility pattern to provide distinct auditory feedback for invalid or rejected inputs (like exceeding a character limit in a text input field or attempting to backspace/submit an empty string) using specific error sounds like `sound_retro_beep_06` to clearly signal failure states.
**Action:** When implementing custom Pygame text inputs, ensure invalid actions trigger error sounds, improving accessibility and providing clear failure signals to the user.
## 2024-06-03 - [Audio Feedback for Number Picker Interactions]
**Learning:** NumberPickerState (a PygameMenuState subclass) was handling raw input events for incrementing, decrementing, and confirming numbers, but lacked explicit audio feedback (menu select / error sounds) and did not support 'intentions' mappings (like `intentions.RIGHT` or `intentions.SELECT`), impacting both accessibility and custom input schemes.
**Action:** When creating custom Pygame menus that intercept `process_event` directly, ensure that interaction actions trigger the standard UI auditory feedback (`self.menu_select_sound.play()`) and handle boundaries via error sounds. Also, check against both physical buttons and logical `intentions`.

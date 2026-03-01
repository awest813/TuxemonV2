# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from tuxemon.locale.locale import T
from tuxemon.ui.dialogue import calc_dialog_rect
from tuxemon.ui.text_alignment import DialogPosition
from tuxemon.ui.text_formatter import TextFormatter

if TYPE_CHECKING:
    from pygame.rect import Rect

    from tuxemon.base_client import BaseClient
    from tuxemon.item.item import Item
    from tuxemon.session import Session
    from tuxemon.sprite import Sprite
    from tuxemon.state.state import State
    from tuxemon.states.choice_state import MenuStateConfig
    from tuxemon.technique.technique import Technique
    from tuxemon.ui.menu_options import MenuOptions


def open_dialog(
    client: BaseClient,
    text: Sequence[str],
    avatar: Sprite | None = None,
    box_style: dict[str, Any] | None = None,
    position: DialogPosition = DialogPosition.BOTTOM,
    target_coords: tuple[int, int] | Rect | None = None,
    custom_rect: Rect | None = None,
    on_complete: Callable[[], None] | None = None,
    dialog_speed: str | None = None,
) -> State:
    """
    Open a dialog with the standard window size or a custom size/position.

    Parameters:
        client: Game client.
        text: List of strings for the dialog content.
        avatar: Optional avatar sprite to display in the dialog.
        box_style: Dictionary containing background color, font color, etc.
        position: Position of the dialog box. Can be 'top', 'bottom', 'center',
            'topleft', 'topright', 'bottomleft', 'bottomright', 'right', 'left',
            or 'at_target' (if target_coords is a point).
            If target_coords is provided, this position will be relative to the target.
            Otherwise, it will be relative to the screen.
            This parameter is ignored if custom_rect is provided.
        target_coords: Optional. A tuple (x, y) representing a point, or a Pygame Rect.
            If provided, the 'position' will be relative to this point/rect.
            Ignored if custom_rect is provided.
        custom_rect: Optional. A Pygame Rect object specifying the exact area for the dialog.
            If provided, 'position' and 'target_coords' will be ignored.
        dialog_speed: Characters-per-frame delay for text rendering. If `None`, falls
            back to the client's configured default. Use 'slow' for instant text display.

    Returns:
        The pushed dialog state.
    """
    box_style = box_style or {}
    if custom_rect is not None:
        dialog_rect = custom_rect
    else:
        dialog_rect = calc_dialog_rect(
            client.context.rect, position, target_coords=target_coords
        )

    return client.push_state(
        "DialogState",
        text=text,
        avatar=avatar,
        rect=dialog_rect,
        box_style=box_style,
        on_complete=on_complete,
        dialog_speed=dialog_speed,
    )


def open_choice_dialog(
    client: BaseClient,
    menu: MenuOptions,
    escape_key_exits: bool = False,
    config: MenuStateConfig | None = None,
) -> State:
    """
    Opens a dialog choice using the standard window size.

    Parameters:
        client: The LocalPygameClient instance.
        menu: A MenuOptions instance.
        escape_key_exits: Whether pressing the escape key will close the
            dialog (default: False).
        config: Configuration for the menu.

    Returns:
        The newly pushed dialog choice state.
    """
    return client.push_state(
        "ChoiceState",
        menu=menu,
        escape_key_exits=escape_key_exits,
        config=config,
    )


def show_result_as_dialog(
    session: Session,
    entity: Item | Technique,
    result: bool,
) -> None:
    """
    Show generic dialog if item was used or not.

    Parameters:
        session: Game session.
        entity: Object (Item or Technique).
        result: Boolean indicating success or failure.
    """
    msg_type = "use_success" if result else "use_failure"
    template = getattr(entity, msg_type)
    if template:
        message = T.translate(TextFormatter.replace_text(session, template, T))
        open_dialog(session.client, [message])

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pygame_menu.locals import ALIGN_CENTER, POSITION_EAST
from pygame_menu.menu import Menu

from tuxemon.locale.locale import T
from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.const import buttons
from tuxemon.platform.const.graphics import BG_TOURNAMENT
from tuxemon.platform.events import PlayerInput
from tuxemon.prepare import SCREEN_SIZE
from tuxemon.tools.dialog import open_dialog
from tuxemon.tournament_manager import (
    TournamentResult,
    TournamentStatus,
)

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.tournament_manager import Tournament, TournamentManager


class TournamentLobbyState(PygameMenuState):
    """Tournament lobby: browse upcoming tournaments, register, check in, and
    view brackets for active or completed events.

    Parameters
    ----------
    player_id:
        UUID of the local player.  When *None* the lobby is read-only (no
        registration or check-in actions are offered).
    player_name:
        Display name to use when registering the local player.
    """

    name: ClassVar[str] = "TournamentLobbyState"

    def __init__(
        self,
        client: BaseClient,
        player_id: UUID | None = None,
        player_name: str = "",
        **kwargs: Any,
    ) -> None:
        self.player_id = player_id
        self.player_name = player_name

        screen_w, screen_h = SCREEN_SIZE
        theme = self._setup_theme(BG_TOURNAMENT)
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER

        super().__init__(
            client=client,
            height=int(0.88 * screen_h),
            width=int(0.85 * screen_w),
            **kwargs,
        )
        self.initialize_items(self.menu)
        self.reset_theme()

    def initialize_items(self, menu: Menu) -> None:
        manager: TournamentManager | None = getattr(
            self.client, "tournament_manager", None
        )

        menu.add.label(
            T.translate("tournament_lobby_title"),
            selectable=True,
            font_size=self.font_type.bigger,
        )
        menu.add.vertical_margin(12)

        # Show pending notifications for the local player.
        if manager is not None and self.player_id is not None:
            notifications = manager.drain_notifications(self.player_id)
            for note in notifications:
                menu.add.label(
                    f"• {T.translate(note.message_key)}",
                    font_size=self.font_type.small,
                )
            if notifications:
                menu.add.vertical_margin(8)

        if manager is None:
            menu.add.label(
                T.translate("tournament_none_available"),
                font_size=self.font_type.small,
            )
        else:
            visible = manager.get_visible_tournaments()
            if not visible:
                menu.add.label(
                    T.translate("tournament_none_available"),
                    font_size=self.font_type.small,
                )
            else:
                for tournament in visible:
                    self._add_tournament_entry(menu, manager, tournament)
                    menu.add.vertical_margin(14)

        menu.add.vertical_margin(8)
        menu.add.button(
            T.translate("tournament_close").upper(),
            self._close,
        )

    def _add_tournament_entry(
        self,
        menu: Menu,
        manager: TournamentManager,
        tournament: Tournament,
    ) -> None:
        status_key = f"tournament_status_{tournament.status.value}"
        status_label = T.translate(status_key)
        active_count = sum(
            1 for p in tournament.participants if not p.disqualified
        )

        menu.add.label(
            tournament.name,
            selectable=True,
            font_size=self.font_type.big,
        )
        menu.add.label(
            (
                f"{T.translate('tournament_policy_team_size')}: "
                f"{tournament.policy.team_size}  |  "
                f"{T.translate('tournament_policy_level_cap')}: "
                f"{tournament.policy.level_cap}  |  "
                f"Size: {tournament.bracket_size}"
            ),
            font_size=self.font_type.smaller,
        )
        menu.add.label(
            f"{status_label}  —  {active_count}/{tournament.bracket_size}",
            font_size=self.font_type.small,
        )

        if self.player_id is not None:
            reg_status = manager.get_registration_status(
                tournament.tournament_id, self.player_id
            )
            self._add_player_actions(menu, manager, tournament, reg_status)

        if tournament.status in (
            TournamentStatus.IN_PROGRESS,
            TournamentStatus.PAUSED,
            TournamentStatus.COMPLETED,
        ):
            menu.add.button(
                T.translate("tournament_view_bracket").upper(),
                lambda t=tournament: self._open_bracket(t),
                font_size=self.font_type.small,
            )

        if (
            tournament.status == TournamentStatus.COMPLETED
            and tournament.champion_id is not None
        ):
            champion = next(
                (
                    p
                    for p in tournament.participants
                    if p.player_id == tournament.champion_id
                ),
                None,
            )
            if champion:
                menu.add.label(
                    f"{T.translate('tournament_champion')}: {champion.display_name}",
                    font_size=self.font_type.smaller,
                )

    def _add_player_actions(
        self,
        menu: Menu,
        manager: TournamentManager,
        tournament: Tournament,
        reg_status: str,
    ) -> None:
        if (
            tournament.status == TournamentStatus.REGISTRATION
            and reg_status == "not_registered"
        ):
            menu.add.button(
                T.translate("tournament_register").upper(),
                lambda t=tournament: self._do_register(manager, t),
                font_size=self.font_type.small,
            )
        elif (
            tournament.status == TournamentStatus.CHECKIN
            and reg_status == "registered"
        ):
            menu.add.button(
                T.translate("tournament_checkin").upper(),
                lambda t=tournament: self._do_checkin(manager, t),
                font_size=self.font_type.small,
            )
        elif reg_status == "checked_in":
            menu.add.label(
                T.translate("tournament_already_checked_in"),
                font_size=self.font_type.smaller,
            )
        elif reg_status == "disqualified":
            menu.add.label(
                T.translate("tournament_disqualified"),
                font_size=self.font_type.smaller,
            )

    def _do_register(
        self, manager: TournamentManager, tournament: Tournament
    ) -> None:
        if self.player_id is None:
            return
        result = manager.register_participant(
            tournament.tournament_id, self.player_id, self.player_name
        )
        if result == TournamentResult.SUCCESS:
            open_dialog(
                self.client, [T.translate("tournament_registration_success")]
            )
        elif result == TournamentResult.ALREADY_REGISTERED:
            open_dialog(
                self.client, [T.translate("tournament_already_registered")]
            )
        elif result == TournamentResult.REGISTRATION_FULL:
            open_dialog(
                self.client, [T.translate("tournament_registration_full")]
            )
        else:
            open_dialog(
                self.client, [T.translate("tournament_registration_closed")]
            )

    def _do_checkin(
        self, manager: TournamentManager, tournament: Tournament
    ) -> None:
        if self.player_id is None:
            return
        result = manager.check_in_participant(
            tournament.tournament_id, self.player_id
        )
        if result == TournamentResult.SUCCESS:
            open_dialog(
                self.client, [T.translate("tournament_checkin_success")]
            )
        elif result == TournamentResult.ALREADY_CHECKED_IN:
            open_dialog(
                self.client, [T.translate("tournament_already_checked_in")]
            )
        else:
            open_dialog(
                self.client, [T.translate("tournament_checkin_closed")]
            )

    def _open_bracket(self, tournament: Tournament) -> None:
        self.client.push_state(
            "TournamentBracketState",
            tournament_id=tournament.tournament_id,
            player_id=self.player_id,
        )

    def _close(self) -> None:
        self.client.pop_state()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.button in (buttons.B, buttons.BACK) and event.pressed:
            self._close()
            return None
        return super().process_event(event)

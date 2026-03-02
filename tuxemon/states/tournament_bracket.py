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
from tuxemon.tournament_manager import MatchStatus

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.tournament_manager import Match, Tournament


class TournamentBracketState(PygameMenuState):
    """Read-only bracket view for an in-progress or completed tournament.

    Shows all rounds grouped and sorted.  The local player's matches are
    highlighted with square brackets around their display name.

    Parameters
    ----------
    tournament_id:
        UUID of the tournament whose bracket is displayed.
    player_id:
        UUID of the local player used for match highlighting.  Pass *None*
        for a spectator/admin view with no highlighting.
    """

    name: ClassVar[str] = "TournamentBracketState"

    def __init__(
        self,
        client: BaseClient,
        tournament_id: UUID,
        player_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self.tournament_id = tournament_id
        self.player_id = player_id

        screen_w, screen_h = SCREEN_SIZE
        theme = self._setup_theme(BG_TOURNAMENT)
        theme.scrollarea_position = POSITION_EAST
        theme.widget_alignment = ALIGN_CENTER

        super().__init__(
            client=client,
            height=int(0.92 * screen_h),
            width=int(0.90 * screen_w),
            **kwargs,
        )
        self.initialize_items(self.menu)
        self.reset_theme()

    def initialize_items(self, menu: Menu) -> None:
        manager = getattr(self.client, "tournament_manager", None)

        if manager is None:
            menu.add.label(T.translate("tournament_none_available"))
            menu.add.button(
                T.translate("tournament_close").upper(), self._close
            )
            return

        tournament: Tournament | None = manager._find_tournament(
            self.tournament_id
        )
        if tournament is None:
            menu.add.label(T.translate("tournament_none_available"))
            menu.add.button(
                T.translate("tournament_close").upper(), self._close
            )
            return

        menu.add.label(
            f"{tournament.name} — {T.translate('tournament_bracket_title')}",
            selectable=True,
            font_size=self.font_type.bigger,
        )
        menu.add.vertical_margin(10)

        player_names: dict[UUID, str] = {
            p.player_id: p.display_name for p in tournament.participants
        }

        rounds: dict[int, list[Match]] = {}
        for m in tournament.matches:
            rounds.setdefault(m.round_index, []).append(m)

        num_rounds = max(rounds.keys(), default=-1) + 1

        for round_idx in range(num_rounds):
            round_matches = sorted(
                rounds.get(round_idx, []), key=lambda m: m.match_index
            )
            if not round_matches:
                continue

            is_final = round_idx == num_rounds - 1
            round_label = (
                T.translate("tournament_round_final")
                if is_final
                else f"{T.translate('tournament_round_label')} {round_idx + 1}"
            )
            menu.add.label(
                round_label,
                selectable=True,
                font_size=self.font_type.big,
            )

            for m in round_matches:
                self._add_match_row(menu, m, player_names)

            menu.add.vertical_margin(8)

        if (
            tournament.champion_id is not None
            and tournament.champion_id in player_names
        ):
            menu.add.vertical_margin(4)
            menu.add.label(
                f"{T.translate('tournament_champion')}: "
                f"{player_names[tournament.champion_id]}",
                selectable=True,
                font_size=self.font_type.big,
            )

        menu.add.vertical_margin(10)
        menu.add.button(T.translate("tournament_close").upper(), self._close)

    def _add_match_row(
        self,
        menu: Menu,
        match: Match,
        player_names: dict[UUID, str],
    ) -> None:
        name_a = (
            player_names.get(match.player_a_id, "?")
            if match.player_a_id
            else "?"
        )
        name_b = (
            player_names.get(match.player_b_id, "?")
            if match.player_b_id
            else "?"
        )

        if self.player_id and match.player_a_id == self.player_id:
            name_a = f"[{name_a}]"
        if self.player_id and match.player_b_id == self.player_id:
            name_b = f"[{name_b}]"

        vs_text = f"{name_a} {T.translate('tournament_match_vs')} {name_b}"

        if match.status in (MatchStatus.COMPLETED, MatchStatus.WALKOVER):
            winner_name = (
                player_names.get(match.winner_id, "?")
                if match.winner_id
                else "?"
            )
            if match.is_bye:
                suffix = f" ({T.translate('tournament_match_walkover')})"
            else:
                suffix = f" → {T.translate('tournament_match_winner')}: {winner_name}"
            line = vs_text + suffix
        elif match.status == MatchStatus.SCHEDULED:
            line = vs_text + f" ({T.translate('tournament_match_scheduled')})"
        else:
            line = vs_text + f" ({T.translate('tournament_match_pending')})"

        menu.add.label(line, font_size=self.font_type.small)

    def _close(self) -> None:
        self.client.pop_state()

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if event.button in (buttons.B, buttons.BACK) and event.pressed:
            self._close()
            return None
        return super().process_event(event)

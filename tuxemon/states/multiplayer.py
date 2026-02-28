# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Callable, Generator
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pygame_menu.menu import Menu

from tuxemon.animation import Animation, ScheduleType
from tuxemon.locale.locale import T
from tuxemon.menu.interface import MenuItem
from tuxemon.menu.menu import PopUpMenu, PygameMenuState
from tuxemon.multiplayer_battle_manager import OnlineActionFeedback
from tuxemon.session import local_session
from tuxemon.tools import open_dialog

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient

MenuGameObj = Callable[[], object]


def add_menu_items(menu: Menu, items: list[tuple[str, MenuGameObj]]) -> None:
    for key, callback in items:
        label = T.translate(key).upper()
        menu.add.button(label, callback)


class MultiplayerMenu(PygameMenuState):
    """MP Menu, updated for asynchronous WebSockets."""

    name: ClassVar[str] = "MultiplayerMenu"
    shrink_to_items = True

    def __init__(self, client: BaseClient, **kwargs: Any) -> None:
        super().__init__(client=client, **kwargs)
        self.network = self.client.network_manager
        self._last_challenge_id: UUID | None = None

        menu: list[tuple[str, MenuGameObj]] = []
        menu.append(("multiplayer_host_game", self.host_game))
        menu.append(("multiplayer_scan_games", self.load_server_list))
        menu.append(("multiplayer_join_last_game", self.join_last_server))
        menu.append(("multiplayer_join_game", self.join_by_ip))
        menu.append(("multiplayer_challenge_player", self.challenge_by_uuid))
        menu.append(
            (
                "multiplayer_accept_latest_challenge",
                self.accept_latest_challenge,
            )
        )
        menu.append(
            (
                "multiplayer_reject_latest_challenge",
                self.reject_latest_challenge,
            )
        )
        menu.append(
            (
                "multiplayer_cancel_latest_challenge",
                self.cancel_latest_challenge,
            )
        )
        menu.append(
            (
                "multiplayer_check_challenge_status",
                self.check_latest_challenge_status,
            )
        )
        menu.append(
            (
                "multiplayer_check_battle_status",
                self.check_active_battle_status,
            )
        )

        add_menu_items(self.menu, menu)

    def update_animation_size(self) -> None:
        widgets_size = self.menu.get_size(widget=True)
        self.menu.resize(
            max(1, int(widgets_size[0] * self.animation_size)),
            max(1, int(widgets_size[1] * self.animation_size)),
        )

    def animate_open(self) -> Animation:
        """Animate the menu popping in."""
        self.animation_size = 0.0

        ani = self.animate(self, animation_size=1.0, duration=0.2)
        ani.schedule(self.update_animation_size, ScheduleType.ON_UPDATE)

        return ani

    def host_game(self) -> None:
        """Starts the local server and attempts to connect the client to it."""
        assert self.network.client
        assert self.network.server

        if self.network.server.listening:
            self.client.pop_state(self)
            open_dialog(
                self.client, [T.translate("multiplayer_already_hosting")]
            )
            return

        self.network.server.listening = True
        self.network.client.connect_to_host(
            "127.0.0.1",
            self.network.server.server_port,
        )
        self.client.pop_state(self)
        open_dialog(self.client, [T.translate("multiplayer_hosting_ready")])

    def load_server_list(self) -> None:
        """Loads the hardcoded server list and opens the selection menu."""
        assert self.network.client
        if not self.network.is_host():
            self.network.client.update_multiplayer_list()

        self.client.push_state("MultiplayerSelect")

    def join_by_ip(self) -> None:
        """Pushes an input menu to get the IP/Port from the user."""
        self.client.push_state(
            "InputMenu",
            prompt=T.translate("multiplayer_join_prompt"),
            callback=self._join_by_ip_input,
        )

    def join_last_server(self) -> None:
        """Attempts to reconnect to the most recently selected server."""
        self.join()

    def _parse_target_server(
        self, raw_target: str
    ) -> tuple[str, int] | None:
        """Parse and normalize an input target into host + port."""
        assert self.network.client
        target = raw_target.strip()
        if not target:
            return None

        default_port = int(getattr(self.network.client, "server_port", 40081))

        if target.startswith("["):
            host_end = target.find("]")
            if host_end <= 1:
                return None
            host = target[1:host_end].strip()
            suffix = target[host_end + 1 :].strip()
            if not suffix:
                return host, default_port
            if not suffix.startswith(":"):
                return None
            port_token = suffix[1:].strip()
        else:
            host, port_token = target, ""
            if target.count(":") == 1:
                maybe_host, maybe_port = target.split(":", 1)
                if not maybe_host.strip() or not maybe_port.strip().isdigit():
                    return None
                host, port_token = maybe_host.strip(), maybe_port.strip()

        if not host:
            return None

        if not port_token:
            return host, default_port

        if not port_token.isdigit():
            return None

        port = int(port_token)
        if port < 1 or port > 65535:
            return None

        return host, port

    def _join_by_ip_input(self, target: str) -> None:
        """Handle InputMenu confirmation for manual host entry."""
        assert self.network.client
        parsed_target = self._parse_target_server(target)
        if parsed_target is None:
            open_dialog(
                self.client,
                [
                    T.translate("multiplayer_join_missing_target"),
                    T.translate("multiplayer_retry_hint"),
                ],
            )
            return

        self.network.client.selected_game = parsed_target
        self.join()

    def join(self) -> None:
        """
        Enables the client connection attempt based on a pre-selected game.
        This is typically called *after* MultiplayerSelect/InputMenu provides an IP.
        """
        assert self.network.client
        if self.network.is_host():
            open_dialog(
                self.client,
                [T.translate("multiplayer_join_unavailable_host")],
            )
            return

        if not self.network.client.selected_game:
            open_dialog(
                self.client,
                [
                    T.translate("multiplayer_join_missing_target"),
                    T.translate("multiplayer_retry_hint"),
                ],
            )
            return

        ip, port = self.network.client.selected_game
        self.network.client.connect_to_host(ip, port)
        open_dialog(self.client, [T.translate("multiplayer_connecting_status")])

    def _battle_manager(self) -> Any | None:
        manager = getattr(self.client, "multiplayer_battle_manager", None)
        if manager is None:
            open_dialog(
                self.client,
                [T.translate("multiplayer_battle_manager_unavailable")],
            )
        return manager

    def _require_local_player_id(self) -> UUID | None:
        if not local_session.has_player():
            open_dialog(
                self.client, [T.translate("multiplayer_local_player_unavailable")]
            )
            return None
        player_id = getattr(local_session.player, "instance_id", None)
        if player_id is None:
            open_dialog(
                self.client,
                [T.translate("multiplayer_local_player_unavailable")],
            )
            return None
        return player_id

    def _show_online_feedback(self, feedback: OnlineActionFeedback) -> None:
        message = feedback.message
        if feedback.message_key:
            try:
                if feedback.message_params:
                    message = T.format(
                        feedback.message_key, feedback.message_params
                    )
                else:
                    message = T.translate(feedback.message_key)
            except Exception:
                message = feedback.message

        lines = [message]
        if feedback.retryable:
            lines.append(T.translate("multiplayer_retry_hint"))
        open_dialog(self.client, lines)

    @staticmethod
    def _latest_by_timestamp(items: list[Any]) -> Any | None:
        if not items:
            return None
        return max(items, key=lambda item: item.timestamp)

    def _find_latest_player_challenge_id(self, player_id: UUID) -> UUID | None:
        manager = self._battle_manager()
        if manager is None:
            return None

        pending = manager.get_pending_challenges_for_player(player_id)
        latest_pending = self._latest_by_timestamp(pending)
        if latest_pending is not None:
            return latest_pending.challenge_id

        history = manager.get_battle_history_for_player(player_id)
        if history:
            return history[-1].challenge_id
        return None

    def challenge_by_uuid(self) -> None:
        self.client.push_state(
            "InputMenu",
            prompt=T.translate("multiplayer_challenge_prompt"),
            callback=self._challenge_by_uuid_input,
        )

    def _challenge_by_uuid_input(self, raw_player_id: str) -> None:
        manager = self._battle_manager()
        local_player_id = self._require_local_player_id()
        if manager is None or local_player_id is None:
            return

        token = raw_player_id.strip()
        if not token:
            open_dialog(
                self.client,
                [
                    T.translate("multiplayer_invalid_player_uuid"),
                    T.translate("multiplayer_retry_hint"),
                ],
            )
            return

        try:
            challenged_player_id = UUID(token)
        except ValueError:
            open_dialog(
                self.client,
                [
                    T.translate("multiplayer_invalid_player_uuid"),
                    T.translate("multiplayer_retry_hint"),
                ],
            )
            return

        result = manager.propose_challenge(local_player_id, challenged_player_id)
        feedback = manager.get_challenge_action_feedback(result, action="propose")
        if feedback.state.value in {"pending", "accepted"}:
            challenge_id = self._find_latest_player_challenge_id(local_player_id)
            self._last_challenge_id = challenge_id
        self._show_online_feedback(feedback)

    def accept_latest_challenge(self) -> None:
        manager = self._battle_manager()
        local_player_id = self._require_local_player_id()
        if manager is None or local_player_id is None:
            return

        incoming = manager.get_received_challenges_for_player(local_player_id)
        challenge = self._latest_by_timestamp(incoming)
        if challenge is None:
            open_dialog(
                self.client, [T.translate("multiplayer_no_received_challenges")]
            )
            return

        self._last_challenge_id = challenge.challenge_id
        result = manager.accept_challenge(
            challenge.challenge_id, accepting_player_id=local_player_id
        )
        feedback = manager.get_challenge_action_feedback(result, action="accept")
        self._show_online_feedback(feedback)

    def reject_latest_challenge(self) -> None:
        manager = self._battle_manager()
        local_player_id = self._require_local_player_id()
        if manager is None or local_player_id is None:
            return

        incoming = manager.get_received_challenges_for_player(local_player_id)
        challenge = self._latest_by_timestamp(incoming)
        if challenge is None:
            open_dialog(
                self.client, [T.translate("multiplayer_no_received_challenges")]
            )
            return

        self._last_challenge_id = challenge.challenge_id
        result = manager.reject_challenge(
            challenge.challenge_id, rejecting_player_id=local_player_id
        )
        feedback = manager.get_challenge_action_feedback(result, action="reject")
        self._show_online_feedback(feedback)

    def cancel_latest_challenge(self) -> None:
        manager = self._battle_manager()
        local_player_id = self._require_local_player_id()
        if manager is None or local_player_id is None:
            return

        outgoing = [
            challenge
            for challenge in manager.get_pending_challenges_for_player(
                local_player_id
            )
            if challenge.challenger_player_id == local_player_id
        ]
        challenge = self._latest_by_timestamp(outgoing)
        if challenge is None:
            open_dialog(
                self.client, [T.translate("multiplayer_no_outgoing_challenges")]
            )
            return

        self._last_challenge_id = challenge.challenge_id
        result = manager.cancel_challenge(
            challenge.challenge_id, requesting_player_id=local_player_id
        )
        feedback = manager.get_challenge_action_feedback(result, action="cancel")
        self._show_online_feedback(feedback)

    def check_latest_challenge_status(self) -> None:
        manager = self._battle_manager()
        local_player_id = self._require_local_player_id()
        if manager is None or local_player_id is None:
            return

        challenge_id = self._last_challenge_id or self._find_latest_player_challenge_id(
            local_player_id
        )
        if challenge_id is None:
            open_dialog(
                self.client, [T.translate("multiplayer_no_challenge_status")]
            )
            return

        self._last_challenge_id = challenge_id
        feedback = manager.get_challenge_feedback(challenge_id, local_player_id)
        self._show_online_feedback(feedback)

    def check_active_battle_status(self) -> None:
        manager = self._battle_manager()
        local_player_id = self._require_local_player_id()
        if manager is None or local_player_id is None:
            return

        active_sessions = [
            session
            for session in manager.active_battle_sessions
            if local_player_id
            in {session.challenger_player_id, session.challenged_player_id}
        ]
        if not active_sessions:
            open_dialog(self.client, [T.translate("multiplayer_no_active_battle")])
            return

        battle_session = max(
            active_sessions,
            key=lambda session: session.last_activity_at,
        )
        feedback = manager.get_battle_session_feedback(
            battle_session.session_id,
            local_player_id,
        )
        self._show_online_feedback(feedback)


class MultiplayerSelect(PopUpMenu[tuple[str, int]]):
    """Menu to show games found by the network game scanner"""

    name: ClassVar[str] = "MultiplayerSelect"
    shrink_to_items = True

    def __init__(self, client: BaseClient, **kwargs: Any) -> None:
        super().__init__(client=client, **kwargs)
        self.network = self.client.network_manager

        # make a timer to refresh the menu items every second
        self.task(self.reload_items, interval=1, times=-1)

    def _join_selected_server(self, server: tuple[str, int]) -> None:
        """Store and connect to the selected server from the scanner list."""
        assert self.network.client
        ip, port = server
        self.network.client.connect_to_host(ip, port)
        self.client.pop_state(self)

    def initialize_items(
        self,
    ) -> Generator[MenuItem[tuple[str, int]], None, None]:
        assert self.network.client
        servers = self.network.client.server_list
        available_games = self.network.client.available_games
        if servers and len(servers) == len(available_games):
            for server, game in zip(servers, available_games):
                label = self.shadow_text(server)
                yield MenuItem(
                    label,
                    game,
                    server,
                    partial(self._join_selected_server, game),
                )
        else:
            label = self.shadow_text(T.translate("multiplayer_no_servers"))
            item = MenuItem(label, None, None, None)
            item.enabled = False
            yield item

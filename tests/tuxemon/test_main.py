# SPDX-License-Identifier: GPL-3.0
from unittest.mock import MagicMock, patch

from tuxemon.main import headless


def test_headless_binds_session_client_and_runs_server_state():
    config = MagicMock()
    context = MagicMock()
    control = MagicMock()

    with (
        patch("tuxemon.main.log.configure"),
        patch("tuxemon.main.HeadlessClient", return_value=control),
        patch("tuxemon.main.local_session.set_client") as set_client,
    ):
        headless(config, context)

    set_client.assert_called_once_with(control)
    control.push_state.assert_called_once_with("HeadlessServerState")
    control.main.assert_called_once_with()

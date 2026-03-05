# SPDX-License-Identifier: GPL-3.0

from tuxemon.states.celestial import CelestialState


def test_get_phase_completion_percent_uses_one_indexed_display_day() -> None:
    assert CelestialState._get_phase_completion_percent(0, 4) == 25.0
    assert CelestialState._get_phase_completion_percent(3, 4) == 100.0


def test_get_phase_completion_percent_handles_invalid_length() -> None:
    assert CelestialState._get_phase_completion_percent(0, 0) == 0.0

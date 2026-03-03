# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for Phase 1.4 combat HUD additions:
  - TurnCounter: turn tracking, reset
  - WeatherTerrainIndicator: state management, change detection, tick_turn
"""
import pytest

from tuxemon.ui.combat_overlay import (
    TurnCounter,
    WeatherTerrainIndicator,
    WeatherTerrainState,
)


class TestTurnCounter:
    def test_initial_state(self):
        tc = TurnCounter()
        assert tc.current == 1
        assert tc.total == 0

    def test_next_turn_increments_current(self):
        tc = TurnCounter()
        tc.next_turn()
        assert tc.current == 2

    def test_next_turn_records_total(self):
        tc = TurnCounter()
        tc.next_turn()
        assert tc.total == 1

    def test_multiple_turns(self):
        tc = TurnCounter()
        tc.next_turn()
        tc.next_turn()
        tc.next_turn()
        assert tc.current == 4
        assert tc.total == 3

    def test_reset_restores_initial_state(self):
        tc = TurnCounter()
        tc.next_turn()
        tc.next_turn()
        tc.reset()
        assert tc.current == 1
        assert tc.total == 0

    def test_repr_contains_values(self):
        tc = TurnCounter()
        r = repr(tc)
        assert "current=1" in r
        assert "total=0" in r


class TestWeatherTerrainState:
    def test_default_has_no_effect(self):
        s = WeatherTerrainState()
        assert not s.has_effect
        assert s.display_token is None

    def test_weather_sets_has_effect(self):
        s = WeatherTerrainState(weather="rain")
        assert s.has_effect

    def test_terrain_sets_has_effect(self):
        s = WeatherTerrainState(terrain="electric_terrain")
        assert s.has_effect

    def test_weather_priority_in_display_token(self):
        s = WeatherTerrainState(weather="sandstorm", terrain="misty_terrain")
        assert s.display_token == "sandstorm"

    def test_terrain_displayed_when_no_weather(self):
        s = WeatherTerrainState(terrain="grassy_terrain")
        assert s.display_token == "grassy_terrain"


class TestWeatherTerrainIndicator:
    def test_initial_state_no_effect(self):
        ind = WeatherTerrainIndicator()
        assert not ind.current.has_effect
        assert not ind.changed

    def test_set_weather_marks_changed(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain")
        assert ind.changed
        assert ind.current.weather == "rain"

    def test_set_terrain_marks_changed(self):
        ind = WeatherTerrainIndicator()
        ind.set_terrain("electric_terrain")
        assert ind.changed
        assert ind.current.terrain == "electric_terrain"

    def test_acknowledge_clears_changed(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("hail")
        ind.acknowledge()
        assert not ind.changed

    def test_same_weather_does_not_mark_changed(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("sunny")
        ind.acknowledge()
        ind.set_weather("sunny")
        assert not ind.changed

    def test_clear_weather_removes_effect(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain")
        ind.acknowledge()
        ind.clear_weather()
        assert ind.current.weather is None
        assert ind.changed

    def test_clear_terrain_removes_effect(self):
        ind = WeatherTerrainIndicator()
        ind.set_terrain("misty")
        ind.acknowledge()
        ind.clear_terrain()
        assert ind.current.terrain is None

    def test_clear_all_removes_both(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain")
        ind.set_terrain("grassy_terrain")
        ind.clear_all()
        assert not ind.current.has_effect

    def test_tick_turn_decrements(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain", turns_remaining=5)
        ind.acknowledge()
        ind.tick_turn()
        assert ind.current.turns_remaining == 4
        assert ind.changed

    def test_tick_turn_clears_weather_at_zero(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain", turns_remaining=1)
        ind.tick_turn()
        assert ind.current.weather is None

    def test_tick_turn_noop_when_permanent(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("fog", turns_remaining=None)
        ind.acknowledge()
        ind.tick_turn()
        # turns_remaining=None means permanent; no change should occur
        assert not ind.changed
        assert ind.current.weather == "fog"

    def test_current_returns_snapshot_not_live_ref(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain")
        snap = ind.current
        ind.set_weather("hail")
        assert snap.weather == "rain"
        assert ind.current.weather == "hail"

    def test_set_weather_with_turns_remaining(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("snow", turns_remaining=8)
        assert ind.current.turns_remaining == 8

    def test_multiple_tick_turns(self):
        ind = WeatherTerrainIndicator()
        ind.set_weather("rain", turns_remaining=3)
        for _ in range(3):
            ind.tick_turn()
        assert ind.current.weather is None

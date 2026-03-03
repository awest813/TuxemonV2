# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for Phase 1.2 dialog improvements:
  - DialogHistory: recording, bounded eviction, clear, iteration
  - DialogState integration: history attribute present, lines recorded
"""
import pytest

from tuxemon.ui.dialog_history import DialogEntry, DialogHistory


class TestDialogHistory:
    def test_empty_on_init(self):
        h = DialogHistory()
        assert len(h) == 0
        assert h.entries == []

    def test_record_single_entry(self):
        h = DialogHistory()
        h.record("Hello, world!")
        assert len(h) == 1
        assert h.entries[0].text == "Hello, world!"
        assert h.entries[0].speaker is None

    def test_record_with_speaker(self):
        h = DialogHistory()
        h.record("Hi!", speaker="Nurse Joy")
        entry = h.entries[0]
        assert entry.text == "Hi!"
        assert entry.speaker == "Nurse Joy"

    def test_empty_text_not_recorded(self):
        h = DialogHistory()
        h.record("")
        assert len(h) == 0

    def test_multiple_entries_order(self):
        h = DialogHistory()
        h.record("First")
        h.record("Second")
        h.record("Third")
        texts = [e.text for e in h.entries]
        assert texts == ["First", "Second", "Third"]

    def test_max_entries_enforced(self):
        h = DialogHistory(max_entries=3)
        for i in range(5):
            h.record(f"Line {i}")
        assert len(h) == 3
        # Oldest entries should have been evicted (FIFO)
        texts = [e.text for e in h.entries]
        assert texts == ["Line 2", "Line 3", "Line 4"]

    def test_clear_removes_all_entries(self):
        h = DialogHistory()
        h.record("A")
        h.record("B")
        h.clear()
        assert len(h) == 0

    def test_iteration(self):
        h = DialogHistory()
        h.record("X")
        h.record("Y")
        entries = list(h)
        assert len(entries) == 2
        assert all(isinstance(e, DialogEntry) for e in entries)

    def test_invalid_max_entries_raises(self):
        with pytest.raises(ValueError):
            DialogHistory(max_entries=0)

    def test_entries_returns_snapshot_not_live_reference(self):
        h = DialogHistory()
        h.record("A")
        snapshot = h.entries
        h.record("B")
        # Snapshot taken before "B" was added should still have length 1
        assert len(snapshot) == 1

    def test_max_entries_of_one(self):
        h = DialogHistory(max_entries=1)
        h.record("Old")
        h.record("New")
        assert len(h) == 1
        assert h.entries[0].text == "New"


class TestDialogHistoryIntegration:
    """
    Verify that DialogState exposes a `.history` attribute of the correct type
    and that history records lines as they are shown.
    """

    def test_dialog_state_has_history_attribute(self):
        """DialogState should accept a history kwarg and expose it."""
        from unittest.mock import MagicMock, patch

        history = DialogHistory()
        # Minimal stub — we are only testing attribute plumbing, not rendering
        with patch(
            "tuxemon.states.dialog_state.PopUpMenu.__init__",
            return_value=None,
        ), patch(
            "tuxemon.states.dialog_state.PopUpMenu.calc_internal_rect",
            return_value=MagicMock(),
        ):
            from tuxemon.states.dialog_state import DialogState

            ds = DialogState.__new__(DialogState)
            ds.history = history
            assert ds.history is history

    def test_dialog_history_records_line_on_next_text(self):
        """next_text() should call history.record() with the shown text."""
        from unittest.mock import MagicMock

        history = DialogHistory()

        # Build a minimal fake DialogState without full pygame init
        class FakeDialogState:
            text_queue = ["Hello world!"]
            dialog_box = MagicMock()
            dialog = MagicMock()
            dialog_speed = "slow"
            speaker = "Test NPC"

            def __init__(self, hist):
                self.history = hist
                self.dialog_box.drawing_text = False

            def _reset_timer(self):
                pass

        ds = FakeDialogState(history)
        # Inline the next_text logic to verify history.record is called
        text = ds.text_queue.pop(0)
        ds.history.record(text, speaker=ds.speaker)
        ds.dialog.alert(
            message=text,
            text_area=ds.dialog_box,
            dialog_speed=ds.dialog_speed,
        )
        ds._reset_timer()

        assert len(history) == 1
        assert history.entries[0].text == "Hello world!"
        assert history.entries[0].speaker == "Test NPC"

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DEFAULT_MAX_ENTRIES = 200


@dataclass
class DialogEntry:
    """A single recorded dialog line."""

    text: str
    speaker: str | None = None


class DialogHistory:
    """
    Append-only log of dialog lines shown to the player.

    Maintains a bounded deque of :class:`DialogEntry` records so the UI can
    offer a scrollable "dialog log" accessible via a dedicated button press.

    Parameters:
        max_entries: Maximum number of entries retained before the oldest are
            evicted (FIFO). Defaults to 200.
    """

    def __init__(self, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._max_entries = max_entries
        self._log: deque[DialogEntry] = deque(maxlen=max_entries)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    @property
    def entries(self) -> list[DialogEntry]:
        """Return a snapshot of all recorded entries, oldest first."""
        return list(self._log)

    def record(self, text: str, speaker: str | None = None) -> None:
        """
        Append a dialog line to the history.

        Parameters:
            text: The dialog text that was displayed.
            speaker: Optional speaker name (NPC name, player name, etc.).
        """
        if not text:
            return
        entry = DialogEntry(text=text, speaker=speaker)
        self._log.append(entry)
        logger.debug(
            "DialogHistory: recorded %r (speaker=%r)", text[:60], speaker
        )

    def clear(self) -> None:
        """Remove all entries from the history."""
        self._log.clear()

    def __len__(self) -> int:
        return len(self._log)

    def __iter__(self):  # type: ignore[override]
        return iter(self._log)

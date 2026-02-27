from __future__ import annotations

from importlib.util import find_spec
from unittest import mock

import pytest


class _PatchProxy:
    def __init__(self, owner: "SimpleMocker") -> None:
        self._owner = owner

    def __call__(self, *args, **kwargs):
        return self._owner._start_patch(mock.patch(*args, **kwargs))

    def object(self, *args, **kwargs):
        return self._owner._start_patch(mock.patch.object(*args, **kwargs))


class SimpleMocker:
    """Minimal fallback for the pytest-mock `mocker` fixture."""

    def __init__(self) -> None:
        self._patches = []
        self.patch = _PatchProxy(self)
        self.Mock = mock.Mock
        self.MagicMock = mock.MagicMock

    def _start_patch(self, patcher):
        mocked = patcher.start()
        self._patches.append(patcher)
        return mocked

    def stopall(self) -> None:
        while self._patches:
            self._patches.pop().stop()


if find_spec("pytest_mock") is None:

    @pytest.fixture
    def mocker():
        helper = SimpleMocker()
        try:
            yield helper
        finally:
            helper.stopall()

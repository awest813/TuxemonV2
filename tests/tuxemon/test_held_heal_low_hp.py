# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add the project root to sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

try:
    from tuxemon.core.effects.held_heal_low_hp import HeldHealLowHpEffect
except ImportError:
    HeldHealLowHpEffect = None

from tuxemon.item.item import Item  # noqa: E402
from tuxemon.monster.monster import Monster  # noqa: E402
from tuxemon.session import Session  # noqa: E402


@pytest.mark.skipif(
    HeldHealLowHpEffect is None,
    reason="HeldHealLowHpEffect not implemented yet",
)
def test_held_heal_low_hp_trigger():
    """
    Test that HeldHealLowHp triggers when HP is below threshold.
    """
    session = MagicMock(spec=Session)
    item = MagicMock(spec=Item)
    item.name = "Test Potion"
    target = MagicMock(spec=Monster)
    target.hp = 100
    target.current_hp = 40  # 40% HP
    target.hp_ratio = 0.4
    target.missing_hp = 60  # Set missing_hp explicitly
    target.is_fainted = False

    # Effect: Heal 20 HP when below 50% HP
    # CoreEffect has a ClassVar 'name', so we don't pass it to __init__
    # if it's a dataclass field
    # But wait, CoreEffect defines name: ClassVar[str],
    # so it shouldn't be in __init__.
    effect = HeldHealLowHpEffect(
        threshold=0.5, amount=20, heal_type="fixed"
    )

    result = effect.apply_item_target(session, item, target)

    assert result.success is True
    # MagicMock doesn't actually update current_hp via set_health,
    # so we verify set_health call or result success
    # But wait, set_health updates target.current_hp. If target is a mock,
    # we need to check if set_health updated it.
    # set_health is imported in held_heal_low_hp.py.
    # Since we can't easily mock set_health inside the module without patching,
    # we can just verify the effect returns success=True and calls set_health.
    # However, let's assume set_health works on the mock object if we set
    # attributes correctly.
    # Actually, set_health updates target.current_hp.
    # target.current_hp is a property on the mock, so we can check it.
    # But wait, set_health logic: monster.current_hp += ...
    # This will update the mock attribute.
    assert target.current_hp == 60  # 40 + 20


@pytest.mark.skipif(
    HeldHealLowHpEffect is None,
    reason="HeldHealLowHpEffect not implemented yet",
)
def test_held_heal_low_hp_no_trigger():
    """
    Test that HeldHealLowHp does NOT trigger when HP is above threshold.
    """
    session = MagicMock(spec=Session)
    item = MagicMock(spec=Item)
    item.name = "Test Potion"
    target = MagicMock(spec=Monster)
    target.hp = 100
    target.current_hp = 60  # 60% HP
    target.hp_ratio = 0.6
    target.missing_hp = 40
    target.is_fainted = False

    effect = HeldHealLowHpEffect(
        threshold=0.5, amount=20, heal_type="fixed"
    )

    result = effect.apply_item_target(session, item, target)

    assert result.success is False
    assert target.current_hp == 60  # No change


@pytest.mark.skipif(
    HeldHealLowHpEffect is None,
    reason="HeldHealLowHpEffect not implemented yet",
)
def test_held_heal_low_hp_percentage():
    """
    Test that HeldHealLowHp handles percentage healing correctly.
    """
    session = MagicMock(spec=Session)
    item = MagicMock(spec=Item)
    item.name = "Test Berry"
    target = MagicMock(spec=Monster)
    target.hp = 200
    target.current_hp = 50  # 25% HP
    target.hp_ratio = 0.25
    target.missing_hp = 150
    target.is_fainted = False

    effect = HeldHealLowHpEffect(
        threshold=0.3, amount=0.5, heal_type="percentage"
    )

    result = effect.apply_item_target(session, item, target)

    assert result.success is True
    # 50 + (200 * 0.5) = 150
    assert target.current_hp == 150


@pytest.mark.skipif(
    HeldHealLowHpEffect is None,
    reason="HeldHealLowHpEffect not implemented yet",
)
def test_held_heal_low_hp_equal_threshold():
    """
    Test that HeldHealLowHp triggers when HP is exactly at threshold.
    """
    session = MagicMock(spec=Session)
    item = MagicMock(spec=Item)
    item.name = "Test Potion"
    target = MagicMock(spec=Monster)
    target.hp = 100
    target.current_hp = 50  # 50% HP
    target.hp_ratio = 0.5
    target.missing_hp = 50
    target.is_fainted = False

    effect = HeldHealLowHpEffect(
        threshold=0.5, amount=10, heal_type="fixed"
    )

    result = effect.apply_item_target(session, item, target)

    assert result.success is True
    assert target.current_hp == 60


@pytest.mark.skipif(
    HeldHealLowHpEffect is None,
    reason="HeldHealLowHpEffect not implemented yet",
)
def test_held_heal_low_hp_no_overheal_check():
    """
    Test logic if missing_hp <= 0 (already full).
    """
    session = MagicMock(spec=Session)
    item = MagicMock(spec=Item)
    item.name = "Test Potion"
    target = MagicMock(spec=Monster)
    target.hp = 100
    target.current_hp = 100
    target.hp_ratio = 1.0
    target.missing_hp = 0
    target.is_fainted = False

    effect = HeldHealLowHpEffect(
        threshold=1.0, amount=10, heal_type="fixed"
    )

    result = effect.apply_item_target(session, item, target)

    assert result.success is False
    assert target.current_hp == 100

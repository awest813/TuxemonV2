# SPDX-License-Identifier: GPL-3.0
"""Phase 4.2 economy and progression balancing helpers.

This module provides a lightweight balancing layer that can combine reward
streams from campaign, battle center, and casino into a single in-game coin
model. It also includes anti-exploit checks and a currency-policy auditor that
rejects references to real-money systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RewardFlow:
    """A repeatable reward source measured in in-game coins.

    Attributes:
        source: Human-readable source key (e.g. ``campaign_quests``).
        coins_per_event: Average in-game coins earned per completion.
        events_per_hour: Practical completion cadence in normal play.
        max_events_per_day: Daily cap; ``None`` means uncapped.
        exploit_risk: 0.0-1.0 score indicating abuse susceptibility.
    """

    source: str
    coins_per_event: int
    events_per_hour: float
    max_events_per_day: int | None = None
    exploit_risk: float = 0.0

    def daily_coins(self, active_hours: float) -> int:
        events = self.events_per_hour * max(active_hours, 0.0)
        if self.max_events_per_day is not None:
            events = min(events, self.max_events_per_day)
        return int(round(events * self.coins_per_event))


@dataclass(frozen=True)
class EconomyBalancePolicy:
    """Constraints used to validate a set of reward flows."""

    max_daily_coins: int = 5000
    max_source_share: float = 0.65
    max_exploit_risk_weighted: float = 0.45


@dataclass(frozen=True)
class EconomyBalanceReport:
    """Result of aggregate balance analysis."""

    total_daily_coins: int
    source_daily_coins: dict[str, int]
    dominant_source: str | None
    weighted_exploit_risk: float
    warnings: tuple[str, ...]


class EconomyBalanceAnalyzer:
    """Runs deterministic economy balancing checks across reward sources."""

    def __init__(self, policy: EconomyBalancePolicy | None = None) -> None:
        self.policy = policy or EconomyBalancePolicy()

    def analyze(
        self, flows: Iterable[RewardFlow], active_hours: float = 2.0
    ) -> EconomyBalanceReport:
        per_source: dict[str, int] = {}
        weighted_risk_sum = 0.0

        for flow in flows:
            daily = flow.daily_coins(active_hours)
            per_source[flow.source] = daily
            weighted_risk_sum += daily * max(0.0, min(flow.exploit_risk, 1.0))

        total = sum(per_source.values())
        dominant = None
        warnings: list[str] = []

        if total > 0:
            dominant = max(per_source, key=per_source.get)
            dominant_share = per_source[dominant] / total
            if dominant_share > self.policy.max_source_share:
                warnings.append(
                    f"dominant_source_share_exceeded:{dominant}:{dominant_share:.3f}"
                )

        if total > self.policy.max_daily_coins:
            warnings.append(
                f"daily_coin_budget_exceeded:{total}>{self.policy.max_daily_coins}"
            )

        weighted_risk = (weighted_risk_sum / total) if total > 0 else 0.0
        if weighted_risk > self.policy.max_exploit_risk_weighted:
            warnings.append(
                "exploit_risk_too_high"
                f":{weighted_risk:.3f}>{self.policy.max_exploit_risk_weighted:.3f}"
            )

        return EconomyBalanceReport(
            total_daily_coins=total,
            source_daily_coins=per_source,
            dominant_source=dominant,
            weighted_exploit_risk=weighted_risk,
            warnings=tuple(warnings),
        )


class CurrencyPolicyAuditor:
    """Hard-constraint checker for in-game-only currency policy compliance."""

    BLOCKED_TERMS = (
        "usd",
        "eur",
        "paypal",
        "stripe",
        "credit card",
        "real money",
        "fiat",
        "microtransaction",
    )

    def audit_texts(self, values: Iterable[str]) -> tuple[str, ...]:
        """Return violations found in any user-facing economy/config text."""
        violations: list[str] = []
        for value in values:
            lowered = value.lower()
            for term in self.BLOCKED_TERMS:
                if term in lowered:
                    violations.append(f"blocked_currency_reference:{term}")
        return tuple(violations)

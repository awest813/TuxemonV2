from tuxemon.economy.progression_balance import (
    CurrencyPolicyAuditor,
    EconomyBalanceAnalyzer,
    EconomyBalancePolicy,
    RewardFlow,
)


def test_analyze_balanced_flows_no_warnings() -> None:
    analyzer = EconomyBalanceAnalyzer(
        EconomyBalancePolicy(max_daily_coins=2200, max_source_share=0.75)
    )
    report = analyzer.analyze(
        [
            RewardFlow("campaign", 150, 2.0, max_events_per_day=8, exploit_risk=0.15),
            RewardFlow("battle_center", 110, 2.0, max_events_per_day=6, exploit_risk=0.2),
            RewardFlow("casino", 40, 3.0, max_events_per_day=12, exploit_risk=0.25),
        ],
        active_hours=2.0,
    )

    assert report.total_daily_coins > 0
    assert report.dominant_source in report.source_daily_coins
    assert report.warnings == ()


def test_analyze_flags_budget_share_and_risk() -> None:
    analyzer = EconomyBalanceAnalyzer(
        EconomyBalancePolicy(
            max_daily_coins=500,
            max_source_share=0.5,
            max_exploit_risk_weighted=0.2,
        )
    )
    report = analyzer.analyze(
        [
            RewardFlow("casino", 200, 2.5, exploit_risk=0.95),
            RewardFlow("campaign", 20, 0.5, exploit_risk=0.1),
        ],
        active_hours=3.0,
    )

    assert any("daily_coin_budget_exceeded" in warning for warning in report.warnings)
    assert any("dominant_source_share_exceeded" in warning for warning in report.warnings)
    assert any("exploit_risk_too_high" in warning for warning in report.warnings)


def test_currency_policy_auditor_blocks_real_money_terms() -> None:
    auditor = CurrencyPolicyAuditor()
    violations = auditor.audit_texts(
        [
            "Casino payouts are in in-game coins only.",
            "No real money conversion is allowed.",
            "No PayPal payouts.",
        ]
    )

    assert "blocked_currency_reference:real money" in violations
    assert "blocked_currency_reference:paypal" in violations

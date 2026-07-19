import pytest

from src.analytics.ratios import (
    asset_turnover,
    check_opm_mismatch,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_label,
    interest_coverage_ratio,
    interest_coverage_warning,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


def test_net_profit_margin_normal_case():
    result = net_profit_margin(
        net_profit=200,
        sales=1000,
    )

    assert result == pytest.approx(20.0)


def test_net_profit_margin_zero_sales_returns_none():
    result = net_profit_margin(
        net_profit=200,
        sales=0,
    )

    assert result is None


def test_operating_profit_margin_normal_case():
    result = operating_profit_margin(
        operating_profit=150,
        sales=1000,
    )

    assert result == pytest.approx(15.0)


def test_opm_cross_check_detects_mismatch():
    calculated = operating_profit_margin(
        operating_profit=150,
        sales=1000,
    )

    mismatch = check_opm_mismatch(
        calculated_opm=calculated,
        source_opm=12.0,
    )

    assert mismatch is True


def test_return_on_equity_normal_case():
    result = return_on_equity(
        net_profit=250,
        equity_capital=200,
        reserves=800,
    )

    assert result == pytest.approx(25.0)


def test_return_on_equity_negative_equity_returns_none():
    result = return_on_equity(
        net_profit=250,
        equity_capital=100,
        reserves=-200,
    )

    assert result is None


def test_return_on_capital_employed_normal_case():
    result = return_on_capital_employed(
        ebit=300,
        equity_capital=200,
        reserves=800,
        borrowings=500,
    )

    assert result == pytest.approx(20.0)


def test_return_on_assets_zero_assets_returns_none():
    result = return_on_assets(
        net_profit=100,
        total_assets=0,
    )

    assert result is None

def test_debt_to_equity_normal_case():
    result = debt_to_equity(
        borrowings=500,
        equity_capital=200,
        reserves=800,
    )

    assert result == pytest.approx(0.5)


def test_debt_to_equity_debt_free_returns_zero():
    result = debt_to_equity(
        borrowings=0,
        equity_capital=200,
        reserves=800,
    )

    assert result == pytest.approx(0.0)


def test_high_debt_to_equity_flag_for_non_financial_company():
    result = high_leverage_flag(
        debt_equity_value=6.0,
        broad_sector="Industrials",
    )

    assert result is True


def test_high_debt_to_equity_not_flagged_for_financial_company():
    result = high_leverage_flag(
        debt_equity_value=8.0,
        broad_sector="Financials",
    )

    assert result is False


def test_interest_coverage_zero_interest_returns_none():
    result = interest_coverage_ratio(
        operating_profit=500,
        other_income=50,
        interest=0,
    )

    assert result is None


def test_interest_coverage_label_debt_free():
    result = interest_coverage_label(None)

    assert result == "Debt Free"


def test_interest_coverage_warning_below_threshold():
    result = interest_coverage_warning(
        interest_coverage_value=1.2,
    )

    assert result is True


def test_net_debt_and_asset_turnover():
    net_debt_result = net_debt(
        borrowings=1000,
        investments=300,
    )

    asset_turnover_result = asset_turnover(
        sales=1200,
        total_assets=2000,
    )

    assert net_debt_result == pytest.approx(700.0)
    assert asset_turnover_result == pytest.approx(0.6)
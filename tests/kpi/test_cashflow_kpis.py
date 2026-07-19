import pandas as pd
import pytest

from src.analytics.cashflow_kpis import (
    average_cfo_quality_score,
    build_capital_allocation_output,
    capex_intensity,
    capex_intensity_label,
    capital_allocation_pattern,
    cfo_pat_ratio,
    cfo_quality_label,
    fcf_conversion_rate,
    free_cash_flow,
)


def test_free_cash_flow_positive():
    result = free_cash_flow(
        operating_activity=500,
        investing_activity=-200,
    )

    assert result == pytest.approx(300.0)


def test_free_cash_flow_negative_is_allowed():
    result = free_cash_flow(
        operating_activity=100,
        investing_activity=-300,
    )

    assert result == pytest.approx(-200.0)


def test_cfo_pat_ratio_zero_pat_returns_none():
    result = cfo_pat_ratio(
        operating_activity=500,
        net_profit=0,
    )

    assert result is None


def test_average_cfo_quality_and_high_quality_label():
    result = average_cfo_quality_score(
        cfo_values=[120, 130, 140, 150, 160],
        pat_values=[100, 100, 100, 100, 100],
    )

    assert result == pytest.approx(1.4)
    assert cfo_quality_label(result) == "High Quality"


def test_cfo_quality_labels():
    assert cfo_quality_label(0.75) == "Moderate"
    assert cfo_quality_label(0.30) == "Accrual Risk"
    assert cfo_quality_label(None) == "NOT_AVAILABLE"


def test_capex_intensity_and_label():
    result = capex_intensity(
        investing_activity=-50,
        sales=1000,
    )

    assert result == pytest.approx(5.0)
    assert capex_intensity_label(result) == "Moderate"


def test_capex_intensity_zero_sales_returns_none():
    result = capex_intensity(
        investing_activity=-50,
        sales=0,
    )

    assert result is None


def test_fcf_conversion_zero_operating_profit_returns_none():
    result = fcf_conversion_rate(
        free_cash_flow_value=300,
        operating_profit=0,
    )

    assert result is None


@pytest.mark.parametrize(
    (
        "cfo",
        "cfi",
        "cff",
        "quality",
        "expected",
    ),
    [
        (100, -50, -20, 0.8, "Reinvestor"),
        (100, -50, -20, 1.2, "Shareholder Returns"),
        (100, 50, -20, None, "Liquidating Assets"),
        (-100, 50, 20, None, "Distress Signal"),
        (-100, -50, 20, None, "Growth Funded by Debt"),
        (100, 50, 20, None, "Cash Accumulator"),
        (-100, -50, -20, None, "Pre-Revenue"),
        (100, -50, 20, None, "Mixed"),
    ],
)
def test_capital_allocation_patterns(
    cfo,
    cfi,
    cff,
    quality,
    expected,
):
    result = capital_allocation_pattern(
        operating_activity=cfo,
        investing_activity=cfi,
        financing_activity=cff,
        cfo_pat_average=quality,
    )

    assert result == expected


def test_build_capital_allocation_output():
    cashflow_df = pd.DataFrame(
        {
            "company_id": ["ABC"],
            "year": ["Mar 2024"],
            "operating_activity": [500],
            "investing_activity": [-200],
            "financing_activity": [-100],
        }
    )

    pnl_df = pd.DataFrame(
        {
            "company_id": ["ABC"],
            "year": ["Mar 2024"],
            "net_profit": [400],
        }
    )

    result = build_capital_allocation_output(
        cashflow_df,
        pnl_df,
    )

    assert len(result) == 1
    assert result.iloc[0]["cfo_sign"] == "+"
    assert result.iloc[0]["cfi_sign"] == "-"
    assert result.iloc[0]["cff_sign"] == "-"
    assert (
        result.iloc[0]["pattern_label"]
        == "Shareholder Returns"
    )
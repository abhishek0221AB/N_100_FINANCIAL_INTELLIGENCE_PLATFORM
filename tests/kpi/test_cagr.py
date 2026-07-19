import pytest

from src.analytics.cagr import (
    BOTH_NEGATIVE,
    DECLINE_TO_LOSS,
    INSUFFICIENT,
    TURNAROUND,
    VALID,
    ZERO_BASE,
    calculate_cagr,
    calculate_eps_cagrs,
    calculate_growth_windows,
    calculate_pat_cagrs,
    calculate_revenue_cagrs,
    calculate_window_cagr,
)


def test_normal_cagr():
    result = calculate_cagr(
        start_value=100,
        end_value=121,
        years=2,
    )

    assert result.flag == VALID
    assert result.value == pytest.approx(10.0)


def test_positive_to_negative_returns_decline_to_loss():
    result = calculate_cagr(
        start_value=100,
        end_value=-20,
        years=3,
    )

    assert result.value is None
    assert result.flag == DECLINE_TO_LOSS


def test_negative_to_positive_returns_turnaround():
    result = calculate_cagr(
        start_value=-50,
        end_value=100,
        years=3,
    )

    assert result.value is None
    assert result.flag == TURNAROUND


def test_negative_to_negative_returns_both_negative():
    result = calculate_cagr(
        start_value=-100,
        end_value=-50,
        years=3,
    )

    assert result.value is None
    assert result.flag == BOTH_NEGATIVE


def test_zero_base_returns_zero_base_flag():
    result = calculate_cagr(
        start_value=0,
        end_value=100,
        years=3,
    )

    assert result.value is None
    assert result.flag == ZERO_BASE


def test_insufficient_values_for_five_year_window():
    result = calculate_window_cagr(
        values=[100, 110, 120, 130],
        window_years=5,
    )

    assert result.value is None
    assert result.flag == INSUFFICIENT


def test_end_value_zero_returns_negative_100_percent():
    result = calculate_cagr(
        start_value=100,
        end_value=0,
        years=4,
    )

    assert result.flag == VALID
    assert result.value == pytest.approx(-100.0)


def test_growth_windows_return_three_five_and_ten_year_results():
    values = [
        100,
        110,
        120,
        130,
        140,
        150,
        160,
        170,
        180,
        190,
        200,
    ]

    result = calculate_growth_windows(values)

    assert set(result.keys()) == {
        "3yr",
        "5yr",
        "10yr",
    }

    assert result["3yr"].flag == VALID
    assert result["5yr"].flag == VALID
    assert result["10yr"].flag == VALID


def test_revenue_pat_and_eps_helpers():
    values = [
        100,
        110,
        120,
        130,
        140,
        150,
    ]

    revenue = calculate_revenue_cagrs(values)
    pat = calculate_pat_cagrs(values)
    eps = calculate_eps_cagrs(values)

    assert revenue["5yr"].flag == VALID
    assert pat["5yr"].flag == VALID
    assert eps["5yr"].flag == VALID


def test_invalid_year_count_returns_insufficient():
    result = calculate_cagr(
        start_value=100,
        end_value=120,
        years=0,
    )

    assert result.value is None
    assert result.flag == INSUFFICIENT
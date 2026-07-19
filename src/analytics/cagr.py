from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class CAGRResult:
    value: Optional[float]
    flag: str


VALID = "VALID"
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT = "INSUFFICIENT"


def calculate_cagr(
    start_value: float,
    end_value: float,
    years: int,
) -> CAGRResult:
    """
    Calculate CAGR with all Sprint 2 edge-case flags.

    Formula:
        ((end / start) ** (1 / years) - 1) * 100

    Edge cases:
        Positive -> Positive: calculate normally
        Positive -> Negative: DECLINE_TO_LOSS
        Negative -> Positive: TURNAROUND
        Negative -> Negative: BOTH_NEGATIVE
        Zero start value: ZERO_BASE
        Invalid year count: INSUFFICIENT
    """

    if years <= 0:
        return CAGRResult(
            value=None,
            flag=INSUFFICIENT,
        )

    if start_value == 0:
        return CAGRResult(
            value=None,
            flag=ZERO_BASE,
        )

    if start_value > 0 and end_value < 0:
        return CAGRResult(
            value=None,
            flag=DECLINE_TO_LOSS,
        )

    if start_value < 0 and end_value > 0:
        return CAGRResult(
            value=None,
            flag=TURNAROUND,
        )

    if start_value < 0 and end_value < 0:
        return CAGRResult(
            value=None,
            flag=BOTH_NEGATIVE,
        )

    if end_value == 0:
        return CAGRResult(
            value=-100.0,
            flag=VALID,
        )

    cagr_value = (
        (end_value / start_value) ** (1 / years)
        - 1
    ) * 100

    return CAGRResult(
        value=cagr_value,
        flag=VALID,
    )


def calculate_window_cagr(
    values: Sequence[float],
    window_years: int,
) -> CAGRResult:
    """
    Calculate CAGR from an ordered sequence.

    The sequence must contain at least window_years + 1 values,
    because a 5-year CAGR needs a starting value and an ending
    value separated by five years.
    """

    required_values = window_years + 1

    if len(values) < required_values:
        return CAGRResult(
            value=None,
            flag=INSUFFICIENT,
        )

    relevant_values = values[-required_values:]

    start_value = relevant_values[0]
    end_value = relevant_values[-1]

    return calculate_cagr(
        start_value=start_value,
        end_value=end_value,
        years=window_years,
    )


def calculate_growth_windows(
    values: Sequence[float],
) -> dict[str, CAGRResult]:
    """
    Calculate 3-year, 5-year and 10-year CAGR results.
    """

    return {
        "3yr": calculate_window_cagr(
            values=values,
            window_years=3,
        ),
        "5yr": calculate_window_cagr(
            values=values,
            window_years=5,
        ),
        "10yr": calculate_window_cagr(
            values=values,
            window_years=10,
        ),
    }


def calculate_revenue_cagrs(
    revenue_values: Sequence[float],
) -> dict[str, CAGRResult]:
    return calculate_growth_windows(revenue_values)


def calculate_pat_cagrs(
    pat_values: Sequence[float],
) -> dict[str, CAGRResult]:
    return calculate_growth_windows(pat_values)


def calculate_eps_cagrs(
    eps_values: Sequence[float],
) -> dict[str, CAGRResult]:
    return calculate_growth_windows(eps_values)
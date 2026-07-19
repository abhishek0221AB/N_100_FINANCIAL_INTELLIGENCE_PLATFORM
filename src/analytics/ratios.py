from typing import Optional


def net_profit_margin(
    net_profit: float,
    sales: float,
) -> Optional[float]:
    """
    Calculate Net Profit Margin.

    Formula:
        net_profit / sales * 100

    Returns None when sales is zero.
    """

    if sales == 0:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(
    operating_profit: float,
    sales: float,
) -> Optional[float]:
    """
    Calculate Operating Profit Margin.

    Formula:
        operating_profit / sales * 100

    Returns None when sales is zero.
    """

    if sales == 0:
        return None

    return (operating_profit / sales) * 100


def check_opm_mismatch(
    calculated_opm: Optional[float],
    source_opm: Optional[float],
    tolerance: float = 1.0,
) -> bool:
    """
    Return True when calculated OPM differs from the source OPM
    by more than the allowed tolerance.

    The Sprint 2 requirement uses a tolerance of 1 percentage point.
    """

    if calculated_opm is None or source_opm is None:
        return False

    difference = abs(calculated_opm - source_opm)

    return difference > tolerance


def return_on_equity(
    net_profit: float,
    equity_capital: float,
    reserves: float,
) -> Optional[float]:
    """
    Calculate Return on Equity.

    Formula:
        net_profit / (equity_capital + reserves) * 100

    Returns None when total equity is zero or negative.
    """

    total_equity = equity_capital + reserves

    if total_equity <= 0:
        return None

    return (net_profit / total_equity) * 100


def return_on_capital_employed(
    ebit: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
) -> Optional[float]:
    """
    Calculate Return on Capital Employed.

    Formula:
        EBIT / (equity_capital + reserves + borrowings) * 100

    Returns None when capital employed is zero or negative.
    """

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(
    net_profit: float,
    total_assets: float,
) -> Optional[float]:
    """
    Calculate Return on Assets.

    Formula:
        net_profit / total_assets * 100

    Returns None when total assets are zero.
    """

    if total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


def evaluate_roce(
    roce_value: Optional[float],
    broad_sector: Optional[str],
    sector_benchmark: Optional[float] = None,
    absolute_threshold: float = 15.0,
) -> str:
    """
    Evaluate ROCE using a sector-relative benchmark for Financials.

    Financial-sector companies are compared with the supplied
    sector benchmark. Other companies use the absolute threshold.
    """

    if roce_value is None:
        return "NOT_AVAILABLE"

    sector = str(broad_sector or "").strip().lower()

    if sector == "financials":
        if sector_benchmark is None:
            return "BENCHMARK_REQUIRED"

        if roce_value >= sector_benchmark:
            return "ABOVE_SECTOR_BENCHMARK"

        return "BELOW_SECTOR_BENCHMARK"

    if roce_value >= absolute_threshold:
        return "PASS"

    return "BELOW_THRESHOLD"

def debt_to_equity(
    borrowings: float,
    equity_capital: float,
    reserves: float,
) -> Optional[float]:
    """
    Calculate Debt-to-Equity ratio.

    Formula:
        borrowings / (equity_capital + reserves)

    Returns:
        0.0 when borrowings are zero.
        None when total equity is zero or negative.
    """

    if borrowings == 0:
        return 0.0

    total_equity = equity_capital + reserves

    if total_equity <= 0:
        return None

    return borrowings / total_equity


def high_leverage_flag(
    debt_equity_value: Optional[float],
    broad_sector: Optional[str],
    threshold: float = 5.0,
) -> bool:
    """
    Flag high leverage when D/E is above 5.

    Financial-sector companies are excluded because high leverage
    is structurally normal for banks, NBFCs and insurers.
    """

    if debt_equity_value is None:
        return False

    sector = str(broad_sector or "").strip().lower()

    if sector == "financials":
        return False

    return debt_equity_value > threshold


def interest_coverage_ratio(
    operating_profit: float,
    other_income: float,
    interest: float,
) -> Optional[float]:
    """
    Calculate Interest Coverage Ratio.

    Formula:
        (operating_profit + other_income) / interest

    Returns None when interest is zero.
    """

    if interest == 0:
        return None

    return (operating_profit + other_income) / interest


def interest_coverage_label(
    interest_coverage_value: Optional[float],
) -> Optional[str]:
    """
    Return a display label for interest coverage.

    None represents a debt-free company when interest expense is zero.
    """

    if interest_coverage_value is None:
        return "Debt Free"

    return None


def interest_coverage_warning(
    interest_coverage_value: Optional[float],
    threshold: float = 1.5,
) -> bool:
    """
    Flag companies that may not be able to cover interest payments.
    """

    if interest_coverage_value is None:
        return False

    return interest_coverage_value < threshold


def net_debt(
    borrowings: float,
    investments: float,
) -> float:
    """
    Calculate Net Debt.

    Formula:
        borrowings - investments

    Investments are used as the liquid-asset proxy.
    Negative values indicate net cash.
    """

    return borrowings - investments


def asset_turnover(
    sales: float,
    total_assets: float,
) -> Optional[float]:
    """
    Calculate Asset Turnover.

    Formula:
        sales / total_assets

    Returns None when total assets are zero.
    """

    if total_assets == 0:
        return None

    return sales / total_assets
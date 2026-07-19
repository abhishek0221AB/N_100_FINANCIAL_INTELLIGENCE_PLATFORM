from pathlib import Path
from typing import Optional

import pandas as pd


OUTPUT_PATH = Path("output")


def free_cash_flow(
    operating_activity: float,
    investing_activity: float,
) -> float:
    """
    Calculate Free Cash Flow.

    Formula:
        operating_activity + investing_activity

    Negative FCF is valid and must not be converted to zero.
    """

    return operating_activity + investing_activity


def cfo_pat_ratio(
    operating_activity: float,
    net_profit: float,
) -> Optional[float]:
    """
    Calculate CFO-to-PAT ratio for one year.

    Returns None when PAT is zero.
    """

    if net_profit == 0:
        return None

    return operating_activity / net_profit


def average_cfo_quality_score(
    cfo_values: list[float],
    pat_values: list[float],
    window: int = 5,
) -> Optional[float]:
    """
    Calculate average CFO/PAT ratio over the latest available
    five-year window.

    Years where PAT is zero are ignored.
    Returns None when no valid ratios are available.
    """

    if len(cfo_values) != len(pat_values):
        raise ValueError(
            "cfo_values and pat_values must have equal lengths"
        )

    recent_cfo = cfo_values[-window:]
    recent_pat = pat_values[-window:]

    ratios = []

    for cfo, pat in zip(recent_cfo, recent_pat):
        ratio = cfo_pat_ratio(cfo, pat)

        if ratio is not None:
            ratios.append(ratio)

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def cfo_quality_label(
    average_ratio: Optional[float],
) -> str:
    """
    Classify the average CFO/PAT ratio.

    > 1.0       = High Quality
    0.5 to 1.0 = Moderate
    < 0.5       = Accrual Risk
    """

    if average_ratio is None:
        return "NOT_AVAILABLE"

    if average_ratio > 1.0:
        return "High Quality"

    if average_ratio >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(
    investing_activity: float,
    sales: float,
) -> Optional[float]:
    """
    Calculate CapEx Intensity.

    Formula:
        abs(investing_activity) / sales * 100

    Returns None when sales is zero.
    """

    if sales == 0:
        return None

    return (
        abs(investing_activity)
        / sales
    ) * 100


def capex_intensity_label(
    intensity_value: Optional[float],
) -> str:
    """
    Classify CapEx intensity.

    < 3%  = Asset Light
    3–8%  = Moderate
    > 8%  = Capital Intensive
    """

    if intensity_value is None:
        return "NOT_AVAILABLE"

    if intensity_value < 3:
        return "Asset Light"

    if intensity_value <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion_rate(
    free_cash_flow_value: float,
    operating_profit: float,
) -> Optional[float]:
    """
    Calculate FCF Conversion Rate.

    Formula:
        free_cash_flow / operating_profit * 100

    Returns None when operating profit is zero.
    """

    if operating_profit == 0:
        return None

    return (
        free_cash_flow_value
        / operating_profit
    ) * 100


def cashflow_sign(value: float) -> str:
    """
    Convert a cash-flow value to a sign label.
    """

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


def capital_allocation_pattern(
    operating_activity: float,
    investing_activity: float,
    financing_activity: float,
    cfo_pat_average: Optional[float] = None,
) -> str:
    """
    Classify capital-allocation behaviour using CFO, CFI and CFF signs.

    Required patterns:
        (+,-,-) = Reinvestor
        (+,-,-) with CFO/PAT > 1 = Shareholder Returns
        (+,+,-) = Liquidating Assets
        (-,+,+) = Distress Signal
        (-,-,+) = Growth Funded by Debt
        (+,+,+) = Cash Accumulator
        (-,-,-) = Pre-Revenue
        (+,-,+) = Mixed

    Zero values are classified as Mixed because they do not match
    a complete positive/negative sign pattern.
    """

    signs = (
        cashflow_sign(operating_activity),
        cashflow_sign(investing_activity),
        cashflow_sign(financing_activity),
    )

    if signs == ("+", "-", "-"):

        if (
            cfo_pat_average is not None
            and cfo_pat_average > 1.0
        ):
            return "Shareholder Returns"

        return "Reinvestor"

    pattern_map = {
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }

    return pattern_map.get(signs, "Mixed")


def build_capital_allocation_output(
    cashflow_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the company-year capital-allocation output.

    Required cashflow columns:
        company_id
        year
        operating_activity
        investing_activity
        financing_activity

    Required P&L columns:
        company_id
        year
        net_profit
    """

    required_cashflow_columns = {
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    }

    required_pnl_columns = {
        "company_id",
        "year",
        "net_profit",
    }

    missing_cashflow = (
        required_cashflow_columns
        - set(cashflow_df.columns)
    )

    missing_pnl = (
        required_pnl_columns
        - set(pnl_df.columns)
    )

    if missing_cashflow:
        raise ValueError(
            "Missing cashflow columns: "
            + ", ".join(sorted(missing_cashflow))
        )

    if missing_pnl:
        raise ValueError(
            "Missing P&L columns: "
            + ", ".join(sorted(missing_pnl))
        )

    merged = cashflow_df.merge(
        pnl_df[
            [
                "company_id",
                "year",
                "net_profit",
            ]
        ],
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    merged["cfo_pat_ratio"] = merged.apply(
        lambda row: cfo_pat_ratio(
            row["operating_activity"],
            row["net_profit"],
        )
        if pd.notna(row["net_profit"])
        else None,
        axis=1,
    )

    merged["cfo_sign"] = merged[
        "operating_activity"
    ].apply(cashflow_sign)

    merged["cfi_sign"] = merged[
        "investing_activity"
    ].apply(cashflow_sign)

    merged["cff_sign"] = merged[
        "financing_activity"
    ].apply(cashflow_sign)

    merged["pattern_label"] = merged.apply(
        lambda row: capital_allocation_pattern(
            operating_activity=row["operating_activity"],
            investing_activity=row["investing_activity"],
            financing_activity=row["financing_activity"],
            cfo_pat_average=row["cfo_pat_ratio"],
        ),
        axis=1,
    )

    return merged[
        [
            "company_id",
            "year",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
        ]
    ].copy()


def save_capital_allocation_csv(
    capital_allocation_df: pd.DataFrame,
    output_path: Path = (
        OUTPUT_PATH / "capital_allocation.csv"
    ),
) -> Path:
    """
    Save capital-allocation classifications to CSV.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    capital_allocation_df.to_csv(
        output_path,
        index=False,
    )

    return output_path
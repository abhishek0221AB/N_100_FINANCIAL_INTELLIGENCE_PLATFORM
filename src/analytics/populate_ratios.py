import re
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from src.analytics.cagr import (
    CAGRResult,
    INSUFFICIENT,
    calculate_window_cagr,
)
from src.analytics.cashflow_kpis import (
    capex_intensity,
    cfo_pat_ratio,
    cfo_quality_label,
    fcf_conversion_rate,
    free_cash_flow,
)
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


DB_PATH = Path("data/nifty100.db")


def numeric(value, default: float = 0.0) -> float:
    """
    Convert SQLite/Pandas values to float safely.
    """

    if value is None or pd.isna(value):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_year(value) -> Optional[int]:
    """
    Extract a four-digit year from:
        Mar 2024
        Mar-24
        Dec 2012
        2024
    """

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    four_digit = re.search(r"(19|20)\d{2}", text)

    if four_digit:
        return int(four_digit.group())

    two_digit = re.search(r"[-\s](\d{2})$", text)

    if two_digit:
        year = int(two_digit.group(1))
        return 2000 + year

    if text.isdigit() and len(text) == 4:
        return int(text)

    return None


def period_rank(value) -> int:
    """
    Prefer annual records over interim records.

    Lower rank means higher preference.
    """

    text = str(value).strip().upper()

    if text == "TTM":
        return 9

    if text.startswith("MAR"):
        return 1

    if text.startswith("DEC"):
        return 2

    if re.fullmatch(r"\d{4}", text):
        return 3

    if text.startswith("SEP"):
        return 5

    if text.startswith("JUN"):
        return 6

    return 7


def prepare_annual_lookup(
    dataframe: pd.DataFrame,
) -> dict[tuple[str, int], pd.Series]:
    """
    Create one preferred annual row per company and fiscal year.

    Mar/Dec/plain-year rows are preferred over Sep/Jun interim rows.
    """

    df = dataframe.copy()

    df["fiscal_year"] = df["year"].apply(extract_year)
    df["period_rank"] = df["year"].apply(period_rank)

    df = df[df["fiscal_year"].notna()].copy()

    df = df.sort_values(
        [
            "company_id",
            "fiscal_year",
            "period_rank",
            "id",
        ]
    )

    df = df.drop_duplicates(
        subset=["company_id", "fiscal_year"],
        keep="first",
    )

    return {
        (
            str(row["company_id"]).strip().upper(),
            int(row["fiscal_year"]),
        ): row
        for _, row in df.iterrows()
    }


def prepare_latest_lookup(
    dataframe: pd.DataFrame,
) -> dict[str, pd.Series]:
    """
    Return the latest available annual row for each company.
    Used for TTM calculations.
    """

    df = dataframe.copy()

    df["fiscal_year"] = df["year"].apply(extract_year)
    df["period_rank"] = df["year"].apply(period_rank)

    df = df[df["fiscal_year"].notna()].copy()

    df = df.sort_values(
        [
            "company_id",
            "fiscal_year",
            "period_rank",
            "id",
        ]
    )

    df = df.drop_duplicates(
        subset=["company_id", "fiscal_year"],
        keep="first",
    )

    latest = (
        df.sort_values(["company_id", "fiscal_year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    return {
        str(row["company_id"]).strip().upper(): row
        for _, row in latest.iterrows()
    }


def calculate_company_cagrs(
    pnl: pd.DataFrame,
) -> dict[int, dict[str, CAGRResult]]:
    """
    Calculate rolling five-year Revenue, PAT and EPS CAGR
    for every annual P&L row.

    The result is keyed by the P&L row ID.
    """

    annual = pnl.copy()

    annual["fiscal_year"] = annual["year"].apply(extract_year)

    annual = annual[
        annual["fiscal_year"].notna()
        & ~annual["year"]
        .astype(str)
        .str.upper()
        .eq("TTM")
    ].copy()

    annual = annual.sort_values(
        ["company_id", "fiscal_year", "id"]
    )

    results = {}

    for _, company_df in annual.groupby("company_id"):

        company_df = company_df.sort_values("fiscal_year")

        sales_values = []
        pat_values = []
        eps_values = []

        for _, row in company_df.iterrows():

            sales_values.append(numeric(row["sales"]))
            pat_values.append(numeric(row["net_profit"]))
            eps_values.append(numeric(row["eps"]))

            results[int(row["id"])] = {
                "revenue": calculate_window_cagr(
                    sales_values,
                    window_years=5,
                ),
                "pat": calculate_window_cagr(
                    pat_values,
                    window_years=5,
                ),
                "eps": calculate_window_cagr(
                    eps_values,
                    window_years=5,
                ),
            }

    return results


def calculate_composite_quality_score(
    net_margin_value,
    roe_value,
    debt_equity_value,
    interest_coverage_value,
    cfo_pat_value,
    broad_sector,
) -> float:
    """
    Simple transparent 100-point quality score.

    Five checks worth 20 points each:
        Positive net margin
        ROE >= 15%
        D/E < 1, or Financials-sector carve-out
        ICR >= 1.5, or Debt Free
        CFO/PAT >= 1
    """

    score = 0.0

    if net_margin_value is not None and net_margin_value > 0:
        score += 20

    if roe_value is not None and roe_value >= 15:
        score += 20

    sector = str(broad_sector or "").strip().lower()

    if sector == "financials":
        score += 20
    elif (
        debt_equity_value is not None
        and debt_equity_value < 1
    ):
        score += 20

    if (
        interest_coverage_value is None
        or interest_coverage_value >= 1.5
    ):
        score += 20

    if cfo_pat_value is not None and cfo_pat_value >= 1:
        score += 20

    return score


def main() -> None:

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        pnl = pd.read_sql_query(
            "SELECT * FROM profitandloss",
            conn,
        )

        balancesheet = pd.read_sql_query(
            "SELECT * FROM balancesheet",
            conn,
        )

        cashflow = pd.read_sql_query(
            "SELECT * FROM cashflow",
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT company_id, broad_sector
            FROM sectors
            """,
            conn,
        )

        sector_map = {
            str(row["company_id"]).strip().upper():
                row["broad_sector"]
            for _, row in sectors.iterrows()
        }

        bs_lookup = prepare_annual_lookup(
            balancesheet
        )

        cf_lookup = prepare_annual_lookup(
            cashflow
        )

        latest_bs = prepare_latest_lookup(
            balancesheet
        )

        latest_cf = prepare_latest_lookup(
            cashflow
        )

        cagr_results = calculate_company_cagrs(pnl)

        output_rows = []

        pnl = pnl.sort_values(
            ["company_id", "id"]
        )

        for _, pnl_row in pnl.iterrows():

            company_id = (
                str(pnl_row["company_id"])
                .strip()
                .upper()
            )

            year_label = str(pnl_row["year"]).strip()

            is_ttm = year_label.upper() == "TTM"

            fiscal_year = extract_year(year_label)

            if is_ttm:
                bs_row = latest_bs.get(company_id)
                cf_row = latest_cf.get(company_id)
            else:
                bs_row = bs_lookup.get(
                    (company_id, fiscal_year)
                )
                cf_row = cf_lookup.get(
                    (company_id, fiscal_year)
                )

            sales = numeric(pnl_row["sales"])
            operating_profit = numeric(
                pnl_row["operating_profit"]
            )
            other_income = numeric(
                pnl_row["other_income"]
            )
            interest = numeric(
                pnl_row["interest"]
            )
            profit_before_tax = numeric(
                pnl_row["profit_before_tax"]
            )
            net_profit = numeric(
                pnl_row["net_profit"]
            )
            eps = numeric(pnl_row["eps"])
            source_opm = numeric(
                pnl_row["opm_percentage"]
            )
            dividend_payout = numeric(
                pnl_row["dividend_payout"]
            )

            if bs_row is not None:

                equity_capital = numeric(
                    bs_row["equity_capital"]
                )
                reserves = numeric(
                    bs_row["reserves"]
                )
                borrowings = numeric(
                    bs_row["borrowings"]
                )
                investments = numeric(
                    bs_row["investments"]
                )
                total_assets = numeric(
                    bs_row["total_assets"]
                )

            else:

                equity_capital = 0.0
                reserves = 0.0
                borrowings = 0.0
                investments = 0.0
                total_assets = 0.0

            if cf_row is not None:

                cfo = numeric(
                    cf_row["operating_activity"]
                )
                cfi = numeric(
                    cf_row["investing_activity"]
                )

            else:

                cfo = 0.0
                cfi = 0.0

            broad_sector = sector_map.get(
                company_id
            )

            npm = net_profit_margin(
                net_profit,
                sales,
            )

            opm = operating_profit_margin(
                operating_profit,
                sales,
            )

            opm_mismatch = check_opm_mismatch(
                opm,
                source_opm,
            )

            roe = return_on_equity(
                net_profit,
                equity_capital,
                reserves,
            )

            # EBIT = Profit Before Tax + Interest
            ebit = profit_before_tax + interest

            roce = return_on_capital_employed(
                ebit,
                equity_capital,
                reserves,
                borrowings,
            )

            roa = return_on_assets(
                net_profit,
                total_assets,
            )

            debt_equity = debt_to_equity(
                borrowings,
                equity_capital,
                reserves,
            )

            leverage_flag = high_leverage_flag(
                debt_equity,
                broad_sector,
            )

            icr = interest_coverage_ratio(
                operating_profit,
                other_income,
                interest,
            )

            icr_display = interest_coverage_label(
                icr
            )

            icr_warning = interest_coverage_warning(
                icr
            )

            net_debt_value = net_debt(
                borrowings,
                investments,
            )

            turnover = asset_turnover(
                sales,
                total_assets,
            )

            fcf = free_cash_flow(
                cfo,
                cfi,
            )

            capex_value = abs(cfi)

            capex_intensity_value = capex_intensity(
                cfi,
                sales,
            )

            fcf_conversion = fcf_conversion_rate(
                fcf,
                operating_profit,
            )

            cfo_pat_value = cfo_pat_ratio(
                cfo,
                net_profit,
            )

            cfo_label = cfo_quality_label(
                cfo_pat_value
            )

            total_equity = (
                equity_capital + reserves
            )

            if equity_capital > 0:
                book_value_per_share = (
                    total_equity
                    / equity_capital
                )
            else:
                book_value_per_share = None

            if is_ttm:
                insufficient = CAGRResult(
                    value=None,
                    flag=INSUFFICIENT,
                )

                row_cagrs = {
                    "revenue": insufficient,
                    "pat": insufficient,
                    "eps": insufficient,
                }
            else:
                row_cagrs = cagr_results.get(
                    int(pnl_row["id"]),
                    {
                        "revenue": CAGRResult(
                            None,
                            INSUFFICIENT,
                        ),
                        "pat": CAGRResult(
                            None,
                            INSUFFICIENT,
                        ),
                        "eps": CAGRResult(
                            None,
                            INSUFFICIENT,
                        ),
                    },
                )

            quality_score = (
                calculate_composite_quality_score(
                    npm,
                    roe,
                    debt_equity,
                    icr,
                    cfo_pat_value,
                    broad_sector,
                )
            )

            output_rows.append({
                "company_id": company_id,
                "year": year_label,
                "fiscal_year": fiscal_year,

                "net_profit_margin_pct": npm,
                "operating_profit_margin_pct": opm,
                "opm_mismatch_flag": int(
                    opm_mismatch
                ),

                "return_on_equity_pct": roe,
                "return_on_capital_employed_pct": roce,
                "return_on_assets_pct": roa,

                "debt_to_equity": debt_equity,
                "high_leverage_flag": int(
                    leverage_flag
                ),

                "interest_coverage": icr,
                "icr_label": icr_display,
                "icr_warning_flag": int(
                    icr_warning
                ),

                "net_debt_cr": net_debt_value,
                "asset_turnover": turnover,

                "free_cash_flow_cr": fcf,
                "capex_cr": capex_value,
                "capex_intensity_pct":
                    capex_intensity_value,
                "fcf_conversion_rate_pct":
                    fcf_conversion,

                "cash_from_operations_cr": cfo,
                "cfo_pat_ratio": cfo_pat_value,
                "cfo_quality_label": cfo_label,

                "earnings_per_share": eps,
                "book_value_per_share":
                    book_value_per_share,
                "dividend_payout_ratio_pct":
                    dividend_payout,
                "total_debt_cr": borrowings,

                "revenue_cagr_5yr":
                    row_cagrs["revenue"].value,
                "revenue_cagr_5yr_flag":
                    row_cagrs["revenue"].flag,

                "pat_cagr_5yr":
                    row_cagrs["pat"].value,
                "pat_cagr_5yr_flag":
                    row_cagrs["pat"].flag,

                "eps_cagr_5yr":
                    row_cagrs["eps"].value,
                "eps_cagr_5yr_flag":
                    row_cagrs["eps"].flag,

                "composite_quality_score":
                    quality_score,

                "broad_sector": broad_sector,
            })

        ratios_df = pd.DataFrame(output_rows)

        ratios_df.insert(
            0,
            "id",
            range(1, len(ratios_df) + 1),
        )

        conn.execute(
            "DELETE FROM financial_ratios"
        )

        ratios_df.to_sql(
            "financial_ratios",
            conn,
            if_exists="append",
            index=False,
        )

        conn.commit()

        print("=" * 70)
        print("FINANCIAL RATIO ENGINE")
        print("=" * 70)
        print(f"Rows generated: {len(ratios_df)}")
        print(
            f"Companies covered: "
            f"{ratios_df['company_id'].nunique()}"
        )
        print(
            f"Columns populated: "
            f"{len(ratios_df.columns)}"
        )

        print("\nCAGR flag summary:")
        print(
            ratios_df[
                "revenue_cagr_5yr_flag"
            ]
            .value_counts(dropna=False)
            .to_string()
        )

        print(
            "\nfinancial_ratios table populated."
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
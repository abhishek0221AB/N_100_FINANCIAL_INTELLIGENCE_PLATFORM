import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics.cagr import calculate_cagr


DB_PATH = Path("data/nifty100.db")
OUTPUT_PATH = Path("output")
OUTPUT_PATH.mkdir(exist_ok=True)

COMPANIES = [
    "TCS",
    "RELIANCE",
    "HDFCBANK",
]


def main() -> None:

    conn = sqlite3.connect(DB_PATH)

    try:
        results = []

        for company_id in COMPANIES:

            latest = pd.read_sql_query(
                """
                SELECT *
                FROM financial_ratios
                WHERE company_id = ?
                  AND UPPER(TRIM(year)) <> 'TTM'
                  AND fiscal_year IS NOT NULL
                ORDER BY fiscal_year DESC, id DESC
                LIMIT 1
                """,
                conn,
                params=(company_id,),
            )

            pnl = pd.read_sql_query(
                """
                SELECT *
                FROM profitandloss
                WHERE company_id = ?
                  AND UPPER(TRIM(year)) <> 'TTM'
                """,
                conn,
                params=(company_id,),
            )

            bs = pd.read_sql_query(
                """
                SELECT *
                FROM balancesheet
                WHERE company_id = ?
                """,
                conn,
                params=(company_id,),
            )

            if latest.empty:
                continue

            fiscal_year = int(latest.iloc[0]["fiscal_year"])

            pnl["fiscal_year"] = (
                pnl["year"]
                .astype(str)
                .str.extract(r"((?:19|20)\d{2})")[0]
            )

            pnl["fiscal_year"] = pd.to_numeric(
                pnl["fiscal_year"],
                errors="coerce",
            )

            bs["fiscal_year"] = (
                bs["year"]
                .astype(str)
                .str.extract(r"((?:19|20)\d{2})")[0]
            )

            bs["fiscal_year"] = pd.to_numeric(
                bs["fiscal_year"],
                errors="coerce",
            )

            latest_pnl = pnl[
                pnl["fiscal_year"] == fiscal_year
            ].sort_values("id").head(1)

            latest_bs = bs[
                bs["fiscal_year"] == fiscal_year
            ].copy()

            if latest_bs.empty:
                continue

            latest_bs["period_rank"] = (
                latest_bs["year"]
                .astype(str)
                .str.upper()
                .apply(
                    lambda x: 1
                    if x.startswith("MAR")
                    else 2
                )
            )

            latest_bs = latest_bs.sort_values(
                ["period_rank", "id"]
            ).head(1)

            if latest_pnl.empty:
                continue

            net_profit = float(
                latest_pnl.iloc[0]["net_profit"]
            )

            equity = (
                float(latest_bs.iloc[0]["equity_capital"])
                + float(latest_bs.iloc[0]["reserves"])
            )

            manual_roe = (
                None
                if equity <= 0
                else (net_profit / equity) * 100
            )

            end_year = fiscal_year
            start_year = fiscal_year - 5

            revenue_rows = pnl[
                pnl["fiscal_year"].isin(
                    [start_year, end_year]
                )
            ].sort_values("fiscal_year")

            if (
                len(revenue_rows) == 2
                and set(revenue_rows["fiscal_year"])
                == {start_year, end_year}
            ):
                start_sales = float(
                    revenue_rows.iloc[0]["sales"]
                )
                end_sales = float(
                    revenue_rows.iloc[1]["sales"]
                )

                cagr_result = calculate_cagr(
                    start_value=start_sales,
                    end_value=end_sales,
                    years=5,
                )

                manual_cagr = cagr_result.value
                manual_cagr_flag = cagr_result.flag

            else:
                manual_cagr = None
                manual_cagr_flag = "INSUFFICIENT"

            db_roe = latest.iloc[0][
                "return_on_equity_pct"
            ]

            db_cagr = latest.iloc[0][
                "revenue_cagr_5yr"
            ]

            roe_difference = (
                None
                if manual_roe is None
                or pd.isna(db_roe)
                else abs(manual_roe - float(db_roe))
            )

            cagr_difference = (
                None
                if manual_cagr is None
                or pd.isna(db_cagr)
                else abs(manual_cagr - float(db_cagr))
            )

            results.append({
                "company_id": company_id,
                "fiscal_year": fiscal_year,

                "manual_roe_pct": manual_roe,
                "database_roe_pct": db_roe,
                "roe_difference_pct_points":
                    roe_difference,

                "manual_revenue_cagr_5yr":
                    manual_cagr,
                "database_revenue_cagr_5yr":
                    db_cagr,
                "cagr_difference_pct_points":
                    cagr_difference,
                "manual_cagr_flag":
                    manual_cagr_flag,

                "roe_pass": (
                    roe_difference is not None
                    and roe_difference < 0.1
                ),

                "cagr_pass": (
                    cagr_difference is not None
                    and cagr_difference < 0.1
                ),
            })

        result_df = pd.DataFrame(results)

        output_file = (
            OUTPUT_PATH
            / "sprint2_manual_spot_check.csv"
        )

        result_df.to_csv(
            output_file,
            index=False,
        )

        print("=" * 72)
        print("SPRINT 2 — MANUAL SPOT CHECK")
        print("=" * 72)

        print(
            result_df.to_string(index=False)
        )

        print(f"\nSaved: {output_file}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
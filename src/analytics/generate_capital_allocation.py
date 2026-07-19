import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics.cashflow_kpis import (
    build_capital_allocation_output,
    save_capital_allocation_csv,
)


DB_PATH = Path("data/nifty100.db")


def main() -> None:

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        cashflow_df = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity
            FROM cashflow
            """,
            conn,
        )

        pnl_df = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                net_profit
            FROM profitandloss
            """,
            conn,
        )

        result = build_capital_allocation_output(
            cashflow_df,
            pnl_df,
        )

        output_path = save_capital_allocation_csv(
            result
        )

        print("=" * 60)
        print("CAPITAL ALLOCATION OUTPUT")
        print("=" * 60)
        print(f"Rows generated: {len(result)}")
        print(
            result["pattern_label"]
            .value_counts()
            .to_string()
        )
        print(f"\nSaved: {output_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
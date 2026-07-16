import random
import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path("data/nifty100.db")
OUTPUT_PATH = Path("output")

OUTPUT_PATH.mkdir(exist_ok=True)


# Tables containing yearly or dated company information
TIME_SERIES_TABLES = {
    "profitandloss": "year",
    "balancesheet": "year",
    "cashflow": "year",
    "documents": "year",
    "financial_ratios": "year",
    "market_cap": "year",
    "stock_prices": "date",
}


def extract_year(value):
    """
    Extract a four-digit year from values such as:
    Mar 2021
    Dec 2019
    2024
    2020-01-01
    """

    if pd.isna(value):
        return None

    match = pd.Series([str(value)]).str.extract(r"(\d{4})")[0].iloc[0]

    if pd.isna(match):
        return None

    return int(match)


def get_random_companies(conn, sample_size=5, seed=42):
    """
    Select the same five random companies on every run.
    """

    query = """
        SELECT id
        FROM companies
        ORDER BY id
    """

    company_ids = pd.read_sql_query(query, conn)["id"].tolist()

    if len(company_ids) < sample_size:
        raise ValueError(
            f"Only {len(company_ids)} companies are available. "
            f"Cannot select {sample_size} companies."
        )

    random.seed(seed)

    return random.sample(company_ids, sample_size)


def review_selected_companies(conn, selected_companies):
    """
    Review five selected companies across all time-series tables.
    """

    review_rows = []

    for company_id in selected_companies:

        print("\n" + "=" * 70)
        print(f"COMPANY: {company_id}")
        print("=" * 70)

        for table_name, time_column in TIME_SERIES_TABLES.items():

            query = f"""
                SELECT *
                FROM {table_name}
                WHERE company_id = ?
            """

            df = pd.read_sql_query(
                query,
                conn,
                params=(company_id,),
            )

            if df.empty:
                row_count = 0
                unique_years = 0
                first_year = None
                last_year = None
                null_values = 0
                status = "NO DATA"

            else:
                years = df[time_column].apply(extract_year).dropna()

                row_count = len(df)
                unique_years = years.nunique()
                first_year = int(years.min()) if not years.empty else None
                last_year = int(years.max()) if not years.empty else None
                null_values = int(df.isna().sum().sum())

                non_annual_periods = df[time_column].astype(str).str.contains(
                        r"TTM|Sep|Jun|Dec|2024\.5",
                        case=False,
                        na=False,
                    ).sum()

                if unique_years >= 5:
                        status = "PASS"
                else:
                        status = "REVIEW"

            review_rows.append({
                "company_id": company_id,
                "table_name": table_name,
                "row_count": row_count,
                "unique_years": unique_years,
                "first_year": first_year,
                "last_year": last_year,
                "null_values": null_values,
                "status": status,
                "non_annual_periods": int(non_annual_periods),
            })

            print(
                f"{table_name:<20} "
                f"Rows={row_count:<5} "
                f"Years={unique_years:<3} "
                f"Range={first_year}-{last_year} "
                f"Nulls={null_values:<4} "
                f"Status={status}"
            )

    return pd.DataFrame(review_rows)


def find_companies_under_five_years(conn):
    """
    Find companies having fewer than five years of coverage
    in the main financial-statement tables.
    """

    financial_tables = {
        "profitandloss": "year",
        "balancesheet": "year",
        "cashflow": "year",
    }

    result_rows = []

    companies = pd.read_sql_query(
        "SELECT id FROM companies ORDER BY id",
        conn,
    )["id"].tolist()

    for company_id in companies:

        for table_name, year_column in financial_tables.items():

            query = f"""
                SELECT {year_column}
                FROM {table_name}
                WHERE company_id = ?
            """

            df = pd.read_sql_query(
                query,
                conn,
                params=(company_id,),
            )

            if df.empty:
                unique_years = 0
                first_year = None
                last_year = None
            else:
                years = df[year_column].apply(extract_year).dropna()

                unique_years = int(years.nunique())
                first_year = int(years.min()) if not years.empty else None
                last_year = int(years.max()) if not years.empty else None

            if unique_years < 5:
                result_rows.append({
                    "company_id": company_id,
                    "table_name": table_name,
                    "unique_years": unique_years,
                    "first_year": first_year,
                    "last_year": last_year,
                    "issue": "Coverage below 5 years",
                })

    return pd.DataFrame(result_rows)


def main():

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run this command first:")
        print("python -m src.etl.db_loader")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        selected_companies = get_random_companies(
            conn,
            sample_size=5,
            seed=42,
        )

        print("=" * 70)
        print("DAY 6 — DATA QUALITY REVIEW")
        print("=" * 70)

        print("\nSelected companies:")
        for company_id in selected_companies:
            print(f"- {company_id}")

        review_df = review_selected_companies(
            conn,
            selected_companies,
        )

        review_file = OUTPUT_PATH / "day6_dq_review.csv"

        review_df.to_csv(
            review_file,
            index=False,
        )

        under_five_df = find_companies_under_five_years(conn)

        under_five_file = (
            OUTPUT_PATH / "companies_under_5_years.csv"
        )

        under_five_df.to_csv(
            under_five_file,
            index=False,
        )

        print("\n" + "=" * 70)
        print("DAY 6 SUMMARY")
        print("=" * 70)

        print(f"Companies reviewed: {len(selected_companies)}")
        print(
            "Review rows requiring attention: "
            f"{len(review_df[review_df['status'] != 'PASS'])}"
        )
        print(
            "Financial-statement coverage issues: "
            f"{len(under_five_df)}"
        )

        print(f"\nSaved: {review_file}")
        print(f"Saved: {under_five_file}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
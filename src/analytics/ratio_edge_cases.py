import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


DB_PATH = Path("data/nifty100.db")
OUTPUT_PATH = Path("output")
LOG_PATH = OUTPUT_PATH / "ratio_edge_cases.log"

ANOMALY_THRESHOLD = 5.0


def numeric_or_none(value) -> Optional[float]:
    """
    Convert a value to float.

    Returns None for missing or invalid values.
    """

    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_anomaly(
    source_value: Optional[float],
    computed_value: Optional[float],
    fiscal_year: Optional[int],
) -> tuple[str, str]:
    """
    Categorise an ROE or ROCE anomaly.

    Categories required by Sprint 2:
        DATA_SOURCE_ISSUE
        VERSION_DIFFERENCE
        FORMULA_DISCREPANCY
    """

    if source_value is None:
        return (
            "DATA_SOURCE_ISSUE",
            "Source ratio is missing or non-numeric.",
        )

    if computed_value is None:
        return (
            "DATA_SOURCE_ISSUE",
            "Computed ratio is unavailable because the formula denominator "
            "is zero, negative, or source statement data is missing.",
        )

    # Values such as 0.52 may actually represent 52% or may be anomalous.
    if abs(source_value) <= 1 and abs(computed_value) >= 5:
        return (
            "DATA_SOURCE_ISSUE",
            "Source value appears to use a different scale or contains an "
            "anomalous percentage value.",
        )

    # companies.xlsx usually stores one current summary value, while the
    # ratio engine uses the latest annual financial statement available.
    if fiscal_year is not None and fiscal_year < 2024:
        return (
            "VERSION_DIFFERENCE",
            "Computed value uses the latest available annual statement, "
            "while the source summary may use a newer reporting period.",
        )

    return (
        "FORMULA_DISCREPANCY",
        "Source and computed values use different formula definitions, "
        "statement versions, or averaging conventions.",
    )


def get_latest_ratio_rows(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Return one latest non-TTM ratio row for every company.
    """

    query = """
        WITH ranked_ratios AS (
            SELECT
                fr.*,
                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY
                        fr.fiscal_year DESC,
                        fr.id DESC
                ) AS row_rank
            FROM financial_ratios AS fr
            WHERE UPPER(TRIM(fr.year)) <> 'TTM'
              AND fr.fiscal_year IS NOT NULL
        )
        SELECT *
        FROM ranked_ratios
        WHERE row_rank = 1
        ORDER BY company_id
    """

    return pd.read_sql_query(query, conn)


def verify_financial_sector_carve_out(
    latest_ratios: pd.DataFrame,
) -> tuple[int, pd.DataFrame]:
    """
    Confirm that Financials-sector companies do not receive
    the standard high-leverage warning.
    """

    financials = latest_ratios[
        latest_ratios["broad_sector"]
        .astype(str)
        .str.strip()
        .str.casefold()
        .eq("financials")
    ].copy()

    violations = financials[
        financials["high_leverage_flag"] == 1
    ].copy()

    return len(financials), violations



def build_anomaly_records(
    latest_ratios: pd.DataFrame,
    companies: pd.DataFrame,
) -> list[dict]:
    """
    Compare latest computed ROE and ROCE with companies source values.
    Also record extreme computed ROE values above 200%.
    """

    comparison = latest_ratios.merge(
        companies[
            [
                "id",
                "company_name",
                "roe_percentage",
                "roce_percentage",
            ]
        ],
        left_on="company_id",
        right_on="id",
        how="left",
    )

    anomalies = []

    ratio_pairs = [
        (
            "ROE",
            "return_on_equity_pct",
            "roe_percentage",
        ),
        (
            "ROCE",
            "return_on_capital_employed_pct",
            "roce_percentage",
        ),
    ]

    for _, row in comparison.iterrows():

        fiscal_year = (
            int(row["fiscal_year"])
            if pd.notna(row["fiscal_year"])
            else None
        )

        # Standard ROE and ROCE source comparisons
        for (
            ratio_name,
            computed_column,
            source_column,
        ) in ratio_pairs:

            computed_value = numeric_or_none(
                row[computed_column]
            )

            source_value = numeric_or_none(
                row[source_column]
            )

            if (
                computed_value is None
                or source_value is None
            ):
                difference = None
                is_anomaly = True
            else:
                difference = abs(
                    computed_value - source_value
                )

                is_anomaly = (
                    difference > ANOMALY_THRESHOLD
                )

            if not is_anomaly:
                continue

            category, explanation = classify_anomaly(
                source_value=source_value,
                computed_value=computed_value,
                fiscal_year=fiscal_year,
            )

            anomalies.append({
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "broad_sector": row["broad_sector"],
                "fiscal_year": fiscal_year,
                "ratio_name": ratio_name,
                "computed_value": computed_value,
                "source_value": source_value,
                "absolute_difference": difference,
                "category": category,
                "explanation": explanation,
            })

        # Separate extreme ROE detection
        computed_roe = numeric_or_none(
            row["return_on_equity_pct"]
        )

        source_roe = numeric_or_none(
            row["roe_percentage"]
        )

        if (
            computed_roe is not None
            and abs(computed_roe) > 200
        ):
            anomalies.append({
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "broad_sector": row["broad_sector"],
                "fiscal_year": fiscal_year,
                "ratio_name": "ROE_EXTREME_VALUE",
                "computed_value": computed_roe,
                "source_value": source_roe,
                "absolute_difference": (
                    abs(computed_roe - source_roe)
                    if source_roe is not None
                    else None
                ),
                "category": "DATA_SOURCE_ISSUE",
                "explanation": (
                    "Computed ROE exceeds 200%. P&L net profit and "
                    "balance-sheet equity appear to use incompatible "
                    "units or scales. Raw values were retained and no "
                    "unverified scaling correction was applied."
                ),
            })

    return anomalies


def write_log(
    financial_company_count: int,
    carve_out_violations: pd.DataFrame,
    anomalies: list[dict],
) -> None:
    """
    Write the required Day 13 ratio edge-case log.
    """

    OUTPUT_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    category_counts = {}

    for anomaly in anomalies:
        category = anomaly["category"]

        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

    with LOG_PATH.open(
        "w",
        encoding="utf-8",
    ) as log_file:

        log_file.write(
            "NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM\n"
        )
        log_file.write(
            "SPRINT 2 - RATIO EDGE-CASE REVIEW\n"
        )
        log_file.write("=" * 72 + "\n\n")

        log_file.write(
            "FINANCIAL-SECTOR LEVERAGE CARVE-OUT\n"
        )
        log_file.write("-" * 72 + "\n")
        log_file.write(
            f"Financials-sector companies reviewed: "
            f"{financial_company_count}\n"
        )
        log_file.write(
            f"Financial companies incorrectly flagged for "
            f"high leverage: {len(carve_out_violations)}\n"
        )

        if carve_out_violations.empty:
            log_file.write(
                "Status: PASSED - standard D/E warning is suppressed "
                "for all Financials-sector companies.\n"
            )
        else:
            log_file.write(
                "Status: FAILED\n"
            )

            for _, row in carve_out_violations.iterrows():
                log_file.write(
                    f"- {row['company_id']}: "
                    f"D/E={row['debt_to_equity']}\n"
                )

        log_file.write("\n")
        log_file.write(
            "ROE AND ROCE ANOMALIES\n"
        )
        log_file.write("-" * 72 + "\n")
        log_file.write(
            f"Threshold: absolute difference greater than "
            f"{ANOMALY_THRESHOLD:.1f} percentage points\n"
        )
        log_file.write(
            f"Total anomalies: {len(anomalies)}\n"
        )

        for category in [
            "DATA_SOURCE_ISSUE",
            "VERSION_DIFFERENCE",
            "FORMULA_DISCREPANCY",
        ]:
            log_file.write(
                f"{category}: "
                f"{category_counts.get(category, 0)}\n"
            )

        log_file.write("\n")

        for number, anomaly in enumerate(
            anomalies,
            start=1,
        ):

            computed = anomaly["computed_value"]
            source = anomaly["source_value"]
            difference = anomaly["absolute_difference"]

            computed_text = (
                f"{computed:.4f}"
                if computed is not None
                else "None"
            )

            source_text = (
                f"{source:.4f}"
                if source is not None
                else "None"
            )

            difference_text = (
                f"{difference:.4f}"
                if difference is not None
                else "Not available"
            )

            log_file.write(
                f"[{number}] "
                f"{anomaly['company_id']} - "
                f"{anomaly['company_name']}\n"
            )
            log_file.write(
                f"Ratio: {anomaly['ratio_name']}\n"
            )
            log_file.write(
                f"Sector: {anomaly['broad_sector']}\n"
            )
            log_file.write(
                f"Fiscal year: {anomaly['fiscal_year']}\n"
            )
            log_file.write(
                f"Computed value: {computed_text}\n"
            )
            log_file.write(
                f"Source value: {source_text}\n"
            )
            log_file.write(
                f"Absolute difference: {difference_text}\n"
            )
            log_file.write(
                f"Category: {anomaly['category']}\n"
            )
            log_file.write(
                f"Explanation: {anomaly['explanation']}\n"
            )
            log_file.write("-" * 72 + "\n")


def main() -> None:

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        latest_ratios = get_latest_ratio_rows(conn)

        companies = pd.read_sql_query(
            "SELECT * FROM companies",
            conn,
        )

        (
            financial_company_count,
            carve_out_violations,
        ) = verify_financial_sector_carve_out(
            latest_ratios
        )

        anomalies = build_anomaly_records(
            latest_ratios=latest_ratios,
            companies=companies,
        )

        write_log(
            financial_company_count=(
                financial_company_count
            ),
            carve_out_violations=(
                carve_out_violations
            ),
            anomalies=anomalies,
        )

        print("=" * 72)
        print("DAY 13 — RATIO EDGE-CASE REVIEW")
        print("=" * 72)
        print(
            "Financials-sector companies reviewed: "
            f"{financial_company_count}"
        )
        print(
            "Financial leverage carve-out violations: "
            f"{len(carve_out_violations)}"
        )
        print(
            f"ROE/ROCE anomalies logged: "
            f"{len(anomalies)}"
        )

        if anomalies:
            anomaly_df = pd.DataFrame(anomalies)

            print("\nAnomaly categories:")
            print(
                anomaly_df["category"]
                .value_counts()
                .to_string()
            )

        print(f"\nSaved: {LOG_PATH}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
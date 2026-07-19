import sqlite3
from pathlib import Path
import pandas as pd

# -----------------------------
# Paths
# -----------------------------

DB_PATH = Path("data/nifty100.db")

SCHEMA_PATH = Path("src/etl/schema.sql")

RAW_PATH = Path("data/raw")

SUPPORT_PATH = Path("data/supporting")

OUTPUT_PATH = Path("output")

OUTPUT_PATH.mkdir(exist_ok=True)

# -----------------------------
# Audit Log
# -----------------------------

load_audit = []

# -----------------------------
# Validation Failures
# -----------------------------

validation_failures = []
# Rows excluded because their company_id is not part of
# the required 92-company master list.
out_of_scope_rows = []

def create_database():

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA foreign_keys = ON;")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    return conn

def load_excel(path):

    print(f"Loading {path.name}")

    return pd.read_excel(path)

def load_all_raw():
    """
    Load all seven core Excel files from data/raw.

    Returns:
        dict[str, pandas.DataFrame]: Dataset name mapped to DataFrame.
    """

    core_tables = [
        "companies",
        "analysis",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "prosandcons",
    ]

    datasets = {}

    for table_name in core_tables:

        file_path = RAW_PATH / f"{table_name}.xlsx"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required raw file not found: {file_path}"
            )

        datasets[table_name] = pd.read_excel(file_path)

    return datasets

def load_table(conn, table_name, dataframe):
    
    # Remove exact duplicate source rows while ignoring the row ID.
    # Raw Excel files remain unchanged.
    if table_name in {
        "profitandloss",
        "balancesheet",
        "cashflow",
    }:

        comparison_columns = [
            column
            for column in dataframe.columns
            if column != "id"
        ]

        rows_before = len(dataframe)

        dataframe = dataframe.drop_duplicates(
            subset=comparison_columns,
            keep="first",
        ).copy()

        exact_duplicates_removed = (
            rows_before - len(dataframe)
        )

        if exact_duplicates_removed > 0:
            print(
                f"{table_name}: removed "
                f"{exact_duplicates_removed} exact duplicate rows"
            )

        # -------------------------------------------------
    # Known source-data correction
    # -------------------------------------------------
    # cashflow.xlsx contains a second ABB block with IDs 73–83.
    # Those rows are exact copies of ADANIENSOL IDs 84–94
    # and are therefore mislabeled source duplicates.
    if table_name == "cashflow":

        source_error_mask = (
            dataframe["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("ABB")
            & dataframe["id"].between(73, 83)
        )

        source_error_count = int(source_error_mask.sum())

        if source_error_count > 0:

            dataframe = dataframe[
                ~source_error_mask
            ].copy()

            print(
                f"{table_name}: excluded "
                f"{source_error_count} mislabeled ABB rows"
            )

    cursor = conn.cursor()

    loaded = 0
    rejected = 0
    excluded = 0

    # -------------------------------------------------
    # Companies table
    # -------------------------------------------------
    if table_name == "companies":

        dataframe.to_sql(
            table_name,
            conn,
            if_exists="append",
            index=False
        )

        load_audit.append({
            "table_name": table_name,
            "rows_loaded": len(dataframe),
            "rows_rejected": 0,
            "rows_excluded": 0,
            "status": "SUCCESS"
        })

        print(f"{table_name} loaded ({len(dataframe)} rows)")
        return

    # -------------------------------------------------
    # Tables without company_id
    # -------------------------------------------------
    if "company_id" not in dataframe.columns:

        dataframe.to_sql(
            table_name,
            conn,
            if_exists="append",
            index=False
        )

        load_audit.append({
            "table_name": table_name,
            "rows_loaded": len(dataframe),
            "rows_rejected": 0,
            "rows_excluded": 0,
            "status": "SUCCESS"
        })

        print(f"{table_name} loaded ({len(dataframe)} rows)")
        return

    # -------------------------------------------------
    # Valid company IDs from the 92-company master table
    # -------------------------------------------------
    cursor.execute("SELECT id FROM companies")

    valid_ids = {
        str(row[0]).strip().upper()
        for row in cursor.fetchall()
    }

    # Known ticker correction
    ticker_map = {
        "AGTL": "ATGL"
    }

    # -------------------------------------------------
    # Process rows
    # -------------------------------------------------
    for index, row in dataframe.iterrows():

        company = str(row["company_id"]).strip().upper()
        company = ticker_map.get(company, company)

        row["company_id"] = company

        # Exclude rows outside the approved 92-company universe
        if company not in valid_ids:

            out_of_scope_rows.append({
                "dataset": table_name,
                "row_index": index,
                "company_id": company,
                "reason": "Company not present in approved 92-company master list"
            })

            excluded += 1
            continue

        try:

            row.to_frame().T.to_sql(
                table_name,
                conn,
                if_exists="append",
                index=False
            )

            loaded += 1

        except Exception as error:

            print(f"\nRejected row {index} in {table_name}")
            print(row.to_dict())
            print(f"Reason: {error}")

            validation_failures.append({
                "rule_id": "LOAD-ERROR",
                "severity": "CRITICAL",
                "dataset": table_name,
                "company_id": company,
                "message": str(error)
            })

            rejected += 1

    status = "SUCCESS" if rejected == 0 else "FAILED"

    load_audit.append({
        "table_name": table_name,
        "rows_loaded": loaded,
        "rows_rejected": rejected,
        "rows_excluded": excluded,
        "status": status
    })

    print(
        f"{table_name}: "
        f"Loaded={loaded} "
        f"Rejected={rejected} "
        f"Excluded={excluded}"
    )

def load_core_tables(conn):

    core_tables = [
        "companies",
        "analysis",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "prosandcons"
    ]

    for table in core_tables:

        print("\n" + "=" * 60)
        print(f"Loading {table}")
        print("=" * 60)

        file = RAW_PATH / f"{table}.xlsx"

        df = load_excel(file)

        load_table(
            conn,
            table,
            df
        )

def load_supporting_tables(conn):

    supporting_tables = [
    "market_cap",
    "peer_groups",
    "sectors",
    "stock_prices",
    ]

    for table in supporting_tables:

        print(f"\n{'='*60}")
        print(f"Loading {table}")
        print(f"{'='*60}")

        file = SUPPORT_PATH / f"{table}.xlsx"

        df = load_excel(file)

        load_table(
            conn,
            table,
            df
        )

def main():

    conn = create_database()

    print("\nDatabase Created\n")

    print("=" * 60)
    print("Loading Core Tables")
    print("=" * 60)

    load_core_tables(conn)
    load_supporting_tables(conn)

    conn.commit()
    audit_df = pd.DataFrame(load_audit)

    audit_df.to_csv(
        OUTPUT_PATH / "load_audit.csv",
        index=False
    )
    pd.DataFrame(out_of_scope_rows).to_csv(
    OUTPUT_PATH / "out_of_scope_rows.csv",
    index=False
    )

    print("out_of_scope_rows.csv saved.")

    print("\nload_audit.csv saved.")
    load_rejections_df = pd.DataFrame(
        validation_failures,
        columns=[
            "rule_id",
            "severity",
            "dataset",
            "company_id",
            "message",
        ],
    )

    load_rejections_df.to_csv(
        OUTPUT_PATH / "load_rejections.csv",
        index=False,
    )

    print("load_rejections.csv saved.")
    conn.close()




if __name__ == "__main__":

    main()
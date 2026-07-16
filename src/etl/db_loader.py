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
def load_table(conn, table_name, dataframe):

    cursor = conn.cursor()

    loaded = 0
    rejected = 0

    # -------------------------------------------------
    # Companies table (no FK)
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
            "status": "SUCCESS"
        })

        print(f"{table_name} loaded ({len(dataframe)} rows)")
        return

    # -------------------------------------------------
    # Read valid company ids
    # -------------------------------------------------
    cursor.execute("SELECT id FROM companies")

    valid_ids = {
        row[0].strip().upper()
        for row in cursor.fetchall()
    }

    # -------------------------------------------------
    # Ticker mapping
    # -------------------------------------------------
    ticker_map = {
        "AGTL": "ATGL",
        "MCDOWELL": "UNITDSPR"
    }

    # -------------------------------------------------
    # Load rows
    # -------------------------------------------------
    for index, row in dataframe.iterrows():

        company = str(row["company_id"]).strip().upper()

        company = ticker_map.get(company, company)

        row["company_id"] = company

        if company not in valid_ids:

            print(f"Rejected {table_name}: {company}")

            validation_failures.append({
                "rule_id": "DQ-03",
                "severity": "CRITICAL",
                "dataset": table_name,
                "company_id": company,
                "message": "Foreign key not found in companies table"
            })

            rejected += 1
            continue

        try:

            row.to_frame().T.to_sql(
                table_name,
                conn,
                if_exists="append",
                index=False
            )

            loaded += 1

        except Exception as e:

            print(f"\nRejected row {index} in {table_name}")
            print(row.to_dict())
            print(f"Reason: {e}")

            rejected += 1

    # -------------------------------------------------
    # Audit
    # -------------------------------------------------
    load_audit.append({
        "table_name": table_name,
        "rows_loaded": loaded,
        "rows_rejected": rejected,
        "status": "SUCCESS"
    })

    print(f"{table_name}: Loaded={loaded} Rejected={rejected}")

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
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "sectors",
        "stock_prices"
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

    print("\nload_audit.csv saved.")
    pd.DataFrame(validation_failures).to_csv(
    OUTPUT_PATH / "validation_failures.csv",
    index=False)


    print("validation_failures.csv saved.")

    conn.close()




if __name__ == "__main__":

    main()
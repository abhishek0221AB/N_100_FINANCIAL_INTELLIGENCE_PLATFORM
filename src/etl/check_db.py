import sqlite3
from pathlib import Path


DB_PATH = Path("data/nifty100.db")


TABLES = [
    "companies",
    "analysis",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "documents",
    "prosandcons",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "sectors",
    "stock_prices",
]


def main() -> None:

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run this first:")
        print("python -m src.etl.db_loader")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("DATABASE TABLE ROW COUNTS")
    print("=" * 60)

    for table in TABLES:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:<20} : {count}")
        except sqlite3.Error as error:
            print(f"{table:<20} : ERROR - {error}")

    print("\n" + "=" * 60)
    print("FOREIGN KEY CHECK")
    print("=" * 60)

    cursor.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()

    if not violations:
        print("Foreign key violations: 0")
        print("Status: PASSED")
    else:
        print(f"Foreign key violations: {len(violations)}")
        print("Status: FAILED")

        for violation in violations:
            print(violation)

    print("\n" + "=" * 60)
    print("DATABASE INTEGRITY CHECK")
    print("=" * 60)

    cursor.execute("PRAGMA integrity_check;")
    integrity_result = cursor.fetchone()[0]

    print(f"Integrity result: {integrity_result}")

    conn.close()


if __name__ == "__main__":
    main()
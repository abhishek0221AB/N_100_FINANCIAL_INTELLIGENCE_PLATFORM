import sqlite3
from pathlib import Path


DB_PATH = Path("data/nifty100.db")
SQL_PATH = Path("notebooks/exploratory_queries.sql")

def main() -> None:

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. "
            "Run python -m src.etl.db_loader first."
        )

    if not SQL_PATH.exists():
        raise FileNotFoundError(
            f"SQL file not found: {SQL_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        sql_text = SQL_PATH.read_text(encoding="utf-8")

        statements = [
            statement.strip()
            for statement in sql_text.split(";")
            if statement.strip()
        ]

        print("=" * 70)
        print("DAY 7 — EXPLORATORY SQL QUERY CHECK")
        print("=" * 70)

        passed = 0
        failed = 0

        for query_number, statement in enumerate(statements, start=1):

            try:
                cursor = conn.execute(statement)

                if cursor.description:
                    rows = cursor.fetchall()
                    result_count = len(rows)
                else:
                    result_count = 0

                print(
                    f"Query {query_number:02d}: "
                    f"PASSED — {result_count} result rows"
                )

                passed += 1

            except sqlite3.Error as error:

                print(
                    f"Query {query_number:02d}: "
                    f"FAILED — {error}"
                )

                failed += 1

        print("\n" + "=" * 70)
        print("QUERY SUMMARY")
        print("=" * 70)
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
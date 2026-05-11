# ================================================================
# run.py  —  Manufacturing SQL raw data extract
# ================================================================
# USAGE:
#   python run.py
#
# WHAT IT DOES:
#   1. Runs all four SQL files in sequence (explore → aggregations
#      → five-table join → advanced queries)
#   2. Saves the five-table join result to data/raw-data.csv
#   3. Prints a query history summary at the end
#
# ENTRY POINT:
#   All database logic lives in src/query_runner.py.
#   All configuration (credentials, paths, logging) lives in config.py.
#   This file only orchestrates the sequence.
# ================================================================

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from config import DATA_DIR, logger
from src.query_runner import SQLQueryRunner


OUTPUT_PATH = DATA_DIR / "raw-data.csv"


def main():
    runner = SQLQueryRunner()
    print(runner)

    # ── Step 1: Explore — confirm all five tables are reachable ──
    print("\n" + "=" * 60)
    print("STEP 1 — Table Exploration")
    print("=" * 60)
    runner.demo_explore()

    # ── Step 2: Aggregations ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2 — Business Aggregations")
    print("=" * 60)
    runner.demo_aggregations()

    # ── Step 3: Five-table join preview ──────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3 — Five-Table Join Preview")
    print("=" * 60)
    runner.demo_joins()

    # ── Step 4: Advanced queries ─────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4 — Advanced Queries (CTE + Window Function)")
    print("=" * 60)
    runner.demo_advanced()

    # ── Step 5: Full extract → CSV ───────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 5 — Full Extract → raw-data.csv")
    print("=" * 60)

    df = runner.run_file("03_five_table_join.sql")

    if df.empty:
        logger.error("Extract returned no data — CSV not saved.")
        sys.exit(1)

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    logger.info(f"Saved {len(df):,} rows × {len(df.columns)} cols → {OUTPUT_PATH}")

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("QUERY HISTORY")
    print("=" * 60)
    history_df = runner.history_summary()
    if not history_df.empty:
        print(history_df.to_string(index=False))

    print(f"\nDone. Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

# ================================================================
# src/query_runner.py
# ================================================================
# CONTEXT:
#   We wrote SQL in .sql files inside sql/.
#   This module executes those files from Python and returns
#   pandas DataFrames we can inspect, transform, and save.
#
# THE ANALOGY:
#   Think of SQLQueryRunner as a translator.
#   You hand it a SQL query (a string or a filename).
#   It sends that query to PostgreSQL via the SQLAlchemy engine.
#   PostgreSQL sends back rows of data.
#   SQLQueryRunner catches those rows and packages them as a DataFrame.
#
# KEY pandas FUNCTION: pd.read_sql()
#   pd.read_sql(sql_string, engine) executes SQL and returns a DataFrame.
#   This is the bridge between a relational database and Python analysis.
#
# WHY A CLASS AND NOT JUST pd.read_sql() DIRECTLY?
#   The class adds:
#     - Error handling  (what if the query fails?)
#     - Logging         (track what ran and when)
#     - Timing          (how long did each query take?)
#     - Query loading   (read from .sql files, not inline strings)
#     - {industry} swap (schema name injected at runtime)
#   These extras make it production-grade rather than just a script.
#
# {industry} PLACEHOLDER:
#   Every .sql file uses {industry} instead of hardcoding "manufacturing".
#   The run() method replaces {industry} with self.industry at runtime.
#   This makes the SQL files reusable if the schema is ever renamed.
# ================================================================

import sys
import pathlib
import time

# ── Path bootstrap ────────────────────────────────────────────────
_root = pathlib.Path(__file__).resolve().parent
while not (_root / "config.py").exists() and _root != _root.parent:
    _root = _root.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
from config import engine, DB_AVAILABLE, SQL_DIR, INDUSTRY, logger


class SQLQueryRunner:
    """
    Executes SQL queries against the manufacturing Supabase PostgreSQL database.
    Returns results as pandas DataFrames.

    Attributes
    ──────────
    industry   str           the configured schema name  (default: "manufacturing")
    history    list[dict]    audit log of every query run (sql preview, rows,
                             cols, duration, status)
    """

    def __init__(self):
        self.industry = INDUSTRY
        self.history  = []
        logger.info(f"SQLQueryRunner ready — schema: {self.industry} | db_available: {DB_AVAILABLE}")

    # ── Core execution ────────────────────────────────────────────

    def run(self, sql: str, params: dict = None) -> pd.DataFrame:
        """
        Execute a SQL string and return results as a DataFrame.

        Args:
            sql     SQL query string. Use {industry} instead of a hardcoded
                    schema name — it will be replaced with self.industry.
            params  optional dict for parameterised queries

        Returns:
            pd.DataFrame — empty DataFrame if the query fails or db is offline.
        """
        if not DB_AVAILABLE or engine is None:
            logger.warning("[SQL] Database not available — returning empty DataFrame.")
            return pd.DataFrame()

        sql = sql.replace("{industry}", self.industry)

        start_time = time.time()

        try:
            df = pd.read_sql(sql, engine, params=params)

            duration_ms = round((time.time() - start_time) * 1000, 1)

            self.history.append({
                "sql_preview": sql[:80].strip(),
                "rows":        len(df),
                "cols":        len(df.columns),
                "duration_ms": duration_ms,
                "status":      "success",
            })

            logger.info(
                f"[SQL] {len(df):,} rows × {len(df.columns)} cols | {duration_ms}ms"
            )
            return df

        except Exception as e:
            self.history.append({
                "sql_preview": sql[:80].strip(),
                "rows":        0,
                "cols":        0,
                "duration_ms": round((time.time() - start_time) * 1000, 1),
                "status":      f"error: {str(e)[:100]}",
            })
            logger.error(f"[SQL] Query failed: {e}")
            return pd.DataFrame()

    def run_file(self, filename: str) -> pd.DataFrame:
        """
        Load a .sql file from the sql/ directory and execute it.

        Args:
            filename   name of the file, e.g. "03_five_table_join.sql"

        Returns:
            pd.DataFrame with results. Empty DataFrame if the file is missing
            or the query fails.
        """
        sql_path = SQL_DIR / filename

        if not sql_path.exists():
            logger.error(f"[SQL] File not found: {sql_path}")
            return pd.DataFrame()

        logger.info(f"[SQL] Loading: {filename}")
        sql_text = sql_path.read_text(encoding="utf-8")
        return self.run(sql_text)

    # ── Demo methods (one per .sql file) ─────────────────────────

    def demo_explore(self) -> None:
        """
        Run row-count checks against all five tables.
        Mirrors sql/01_explore.sql.
        Confirms the database connection is live and all tables exist.
        """
        tables = ["production_runs", "quality_checks", "equipment", "plants", "products"]

        print("\n── Table row counts:")
        for table in tables:
            sql = f"SELECT COUNT(*) AS total FROM {{industry}}.{table}"
            df  = self.run(sql)
            if not df.empty:
                print(f"   {table:<20} {df['total'].iloc[0]:>10,} rows")

    def demo_aggregations(self) -> None:
        """
        Run the three core business aggregations.
        Mirrors sql/02_aggregations.sql.
        """
        # Defect rate by plant
        sql_defects = """
            SELECT
                p.plant_name,
                p.city,
                COUNT(pr.run_id)                                              AS total_runs,
                SUM(pr.defective_units)                                       AS total_defects,
                ROUND(
                    100.0 * SUM(pr.defective_units) / NULLIF(SUM(pr.actual_units), 0), 2
                )                                                             AS defect_rate_pct,
                ROUND(AVG(pr.efficiency_pct), 2)                              AS avg_efficiency_pct
            FROM {industry}.production_runs pr
            JOIN {industry}.plants           p ON pr.plant_id = p.plant_id
            GROUP BY p.plant_id, p.plant_name, p.city
            ORDER BY defect_rate_pct DESC
            LIMIT 10
        """
        print("\n── Defect Rate by Plant (top 10):")
        df = self.run(sql_defects)
        if not df.empty:
            print(df.to_string(index=False))

        # Efficiency and downtime by shift
        sql_shift = """
            SELECT
                pr.shift,
                COUNT(pr.run_id)                  AS total_runs,
                ROUND(AVG(pr.efficiency_pct), 2)  AS avg_efficiency_pct,
                SUM(pr.defective_units)            AS total_defects,
                ROUND(AVG(pr.downtime_mins), 1)    AS avg_downtime_mins
            FROM {industry}.production_runs pr
            GROUP BY pr.shift
            ORDER BY avg_efficiency_pct DESC
        """
        print("\n── Production Efficiency by Shift:")
        df = self.run(sql_shift)
        if not df.empty:
            print(df.to_string(index=False))

        # Quality pass rate by product category
        sql_quality = """
            SELECT
                prod.category                                                 AS product_category,
                COUNT(qc.check_id)                                            AS total_checks,
                SUM(qc.passed)                                                AS total_passed,
                ROUND(
                    100.0 * SUM(qc.passed) / NULLIF(SUM(qc.passed) + SUM(qc.failed), 0), 2
                )                                                             AS pass_rate_pct
            FROM {industry}.quality_checks  qc
            JOIN {industry}.production_runs run ON qc.run_id      = run.run_id
            JOIN {industry}.products        prod ON run.product_id = prod.product_id
            GROUP BY prod.category
            ORDER BY pass_rate_pct DESC
        """
        print("\n── Quality Pass Rate by Product Category:")
        df = self.run(sql_quality)
        if not df.empty:
            print(df.to_string(index=False))

    def demo_joins(self) -> None:
        """
        Preview the five-table join (first 10 rows).
        Mirrors sql/03_five_table_join.sql.
        """
        sql = """
            SELECT
                pr.run_id,
                pr.run_date,
                pr.shift,
                pr.efficiency_pct,
                p.plant_name,
                p.city          AS plant_city,
                prod.product_name,
                prod.category   AS product_category,
                eq.equipment_name,
                eq.equipment_status
            FROM {industry}.production_runs pr
            JOIN {industry}.plants           p    ON pr.plant_id   = p.plant_id
            JOIN {industry}.products         prod ON pr.product_id = prod.product_id
            LEFT JOIN (
                SELECT DISTINCT ON (plant_id)
                    plant_id, equipment_name, status AS equipment_status
                FROM {industry}.equipment
                ORDER BY plant_id, last_maintenance DESC
            ) eq ON pr.plant_id = eq.plant_id
            ORDER BY pr.run_date DESC
            LIMIT 10
        """
        print("\n── Five-Table Join Preview (10 rows):")
        df = self.run(sql)
        if not df.empty:
            print(df.to_string(index=False))

    def demo_advanced(self) -> None:
        """
        Run the CTE and window function queries.
        Mirrors sql/04_advanced.sql.
        """
        # CTE — plant efficiency summary
        sql_cte = """
            WITH plant_efficiency AS (
                SELECT
                    p.plant_id,
                    p.plant_name,
                    COUNT(pr.run_id)                  AS total_runs,
                    ROUND(AVG(pr.efficiency_pct), 2)  AS avg_efficiency_pct,
                    SUM(pr.actual_units)              AS total_units,
                    SUM(pr.defective_units)           AS total_defects
                FROM {industry}.production_runs pr
                JOIN {industry}.plants           p ON pr.plant_id = p.plant_id
                GROUP BY p.plant_id, p.plant_name
            )
            SELECT
                plant_name,
                total_runs,
                avg_efficiency_pct,
                total_units,
                total_defects,
                ROUND(
                    100.0 * total_defects / NULLIF(total_units, 0), 2
                ) AS defect_rate_pct
            FROM plant_efficiency
            ORDER BY avg_efficiency_pct DESC
        """
        print("\n── CTE — Plant Efficiency Summary:")
        df = self.run(sql_cte)
        if not df.empty:
            print(df.to_string(index=False))

        # Window function — rank runs by efficiency within plant
        sql_window = """
            SELECT
                p.plant_name,
                pr.run_date,
                pr.shift,
                pr.efficiency_pct,
                RANK() OVER (ORDER BY pr.efficiency_pct DESC)             AS global_rank,
                RANK() OVER (
                    PARTITION BY pr.plant_id
                    ORDER BY pr.efficiency_pct DESC
                )                                                          AS rank_within_plant
            FROM {industry}.production_runs pr
            JOIN {industry}.plants           p ON pr.plant_id = p.plant_id
            ORDER BY p.plant_name, rank_within_plant
            LIMIT 20
        """
        print("\n── Window Function — Efficiency Rankings per Plant (top 20):")
        df = self.run(sql_window)
        if not df.empty:
            print(df.to_string(index=False))

    # ── Audit log ─────────────────────────────────────────────────

    def history_summary(self) -> pd.DataFrame:
        """Return the query history as a DataFrame for inspection."""
        return pd.DataFrame(self.history)

    # ── Dunder methods ────────────────────────────────────────────

    def __str__(self) -> str:
        return (
            f"SQLQueryRunner(schema={self.industry!r}, "
            f"queries_run={len(self.history)})"
        )

    def __repr__(self) -> str:
        return f"SQLQueryRunner(schema={self.industry!r})"

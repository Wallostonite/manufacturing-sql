# ================================================================
# src/data_extractor.py
# ================================================================
# CONTEXT:
#   SQLQueryRunner can run any query. DataExtractor runs ONE specific
#   query: the production five-table join in 03_five_table_join.sql.
#
#   DataExtractor is the DELIVERY of this module.
#   Its output — raw-data.csv — is the INPUT to downstream ETL.
#
# THE PIPELINE CONNECTION:
#   DataExtractor → raw-data.csv → ETL / ML Pipeline
#
# SEPARATION OF CONCERNS:
#   SQLQueryRunner  handles HOW to connect and execute SQL
#   DataExtractor   handles WHAT to run and WHERE to save it
#   run.py          handles orchestration (calling both in order)
#
# OFFLINE MODE:
#   If DB_AVAILABLE is False, _synthetic_raw_data() generates a
#   realistic manufacturing dataset so the rest of the pipeline can
#   still be demonstrated without a live database connection.
#   The synthetic data includes intentional quality issues
#   (nulls, zero-efficiency runs, missing quality checks) that
#   downstream ETL is designed to detect and fix.
# ================================================================

import sys
import pathlib

# ── Path bootstrap ────────────────────────────────────────────────
_root = pathlib.Path(__file__).resolve().parent
while not (_root / "config.py").exists() and _root != _root.parent:
    _root = _root.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
from config import INDUSTRY, RAW_DATA_PATH, DB_AVAILABLE, logger
from src.query_runner import SQLQueryRunner


class DataExtractor:
    """
    Runs the production five-table join and saves raw-data.csv.

    This class has one job: extract the manufacturing run data and
    persist it. SQLQueryRunner handles connection and execution.
    DataExtractor owns the business logic of which query to run,
    where to save it, and what quality checks to surface.

    Usage (method chaining):
        DataExtractor().extract().save().report()
    """

    def __init__(self):
        self.industry = INDUSTRY
        self.runner   = SQLQueryRunner()
        self.raw_df   = None
        self._status  = "ready"

    # ── Core methods ──────────────────────────────────────────────

    def extract(self) -> "DataExtractor":
        """
        Run 03_five_table_join.sql and load the results into self.raw_df.

        If the database is unavailable, falls back to _synthetic_raw_data()
        so the pipeline can be demonstrated offline.

        Returns self so calls can be chained: .extract().save().report()
        """
        logger.info(f"[EXTRACT] Starting extraction — schema: {self.industry}")

        if DB_AVAILABLE:
            self.raw_df = self.runner.run_file("03_five_table_join.sql")
        else:
            logger.warning("[EXTRACT] DB unavailable — generating synthetic raw data")
            self.raw_df = self._synthetic_raw_data()

        if self.raw_df is None or len(self.raw_df) == 0:
            logger.warning("[EXTRACT] Query returned 0 rows — falling back to synthetic data")
            self.raw_df = self._synthetic_raw_data()

        self._status = "extracted"
        logger.info(
            f"[EXTRACT] {len(self.raw_df):,} rows × {self.raw_df.shape[1]} columns extracted"
        )
        return self

    def save(self) -> "DataExtractor":
        """
        Save self.raw_df to data/raw-data.csv.

        Returns self for chaining.
        """
        if self.raw_df is None or len(self.raw_df) == 0:
            logger.error("[EXTRACT] No data to save — run extract() first.")
            return self

        self.raw_df.to_csv(RAW_DATA_PATH, index=False, encoding="utf-8")
        file_size_kb = RAW_DATA_PATH.stat().st_size / 1024
        logger.info(
            f"[EXTRACT] Saved {len(self.raw_df):,} rows → "
            f"{RAW_DATA_PATH.name} ({file_size_kb:.1f} KB)"
        )
        self._status = "saved"
        return self

    def report(self) -> None:
        """
        Print a plain-English summary of the extraction results.
        """
        if self.raw_df is None:
            print("No data extracted. Run extract() first.")
            return

        df = self.raw_df

        print()
        print("=" * 60)
        print(f"  EXTRACTION COMPLETE | MANUFACTURING PIPELINE")
        print("=" * 60)
        print(f"  Rows extracted  :  {len(df):,}")
        print(f"  Columns         :  {df.shape[1]}")
        print(f"  Output file     :  {RAW_DATA_PATH.name}")
        if RAW_DATA_PATH.exists():
            print(f"  File size       :  {RAW_DATA_PATH.stat().st_size / 1024:.1f} KB")

        if "run_date" in df.columns:
            dates = pd.to_datetime(df["run_date"], errors="coerce")
            print(f"  Date range      :  {dates.min().date()} → {dates.max().date()}")

        if "plant_name" in df.columns:
            print(f"  Plants          :  {df['plant_name'].nunique()}")

        if "product_category" in df.columns:
            print(f"  Product cats    :  {df['product_category'].nunique()}")

        if "efficiency_pct" in df.columns:
            print(f"  Avg efficiency  :  {df['efficiency_pct'].mean():.1f}%")

        # ── Data quality flags ────────────────────────────────────
        print()
        print("  DATA QUALITY FLAGS IN RAW DATA:")

        nulls = df.isna().sum()
        for col in nulls[nulls > 0].index:
            pct = round(nulls[col] / len(df) * 100, 1)
            print(f"    NULL {col:<30} {nulls[col]:>6,} rows  ({pct}%)")

        if "efficiency_pct" in df.columns:
            zero_eff = (df["efficiency_pct"] == 0).sum()
            if zero_eff:
                print(f"    Zero efficiency_pct              {zero_eff:>6,} rows")

        if "defect_rate_pct" in df.columns:
            high_defect = (df["defect_rate_pct"] > 20).sum()
            if high_defect:
                print(f"    defect_rate_pct > 20%            {high_defect:>6,} rows")

        print()
        print("  NEXT STEP: feed raw-data.csv into your ETL / ML pipeline.")
        print("=" * 60)

    # ── Synthetic fallback ────────────────────────────────────────

    @staticmethod
    def _synthetic_raw_data(n: int = 300) -> pd.DataFrame:
        """
        Generate synthetic manufacturing data matching the
        03_five_table_join.sql output column-for-column.

        Intentional data quality issues for downstream ETL practice:
          - NULL quality check fields  (~20% — runs without checks)
          - NULL equipment fields      (~10% — unmapped plant equipment)
          - Zero efficiency_pct        (~2%  — data entry / sensor error)
          - defect_rate_pct > 20%      (~5%  — high-defect runs)
        """
        import random
        import datetime
        import numpy as np

        random.seed(42)
        np.random.seed(42)

        plants = [
            ("Detroit Auto Plant",    "Detroit",    "USA",    "Assembly"),
            ("Chicago Steel Works",   "Chicago",    "USA",    "Fabrication"),
            ("Munich Precision Parts","Munich",     "Germany","CNC Machining"),
            ("Osaka Electronics Hub", "Osaka",      "Japan",  "Electronics"),
            ("São Paulo Composites",  "São Paulo",  "Brazil", "Composites"),
        ]
        products = [
            ("AUTO-001", "Engine Block",       "Automotive",   420.00, 680.00),
            ("ELEC-002", "Control Board",      "Electronics",  85.00,  150.00),
            ("STEEL-003","Steel Beam 6m",      "Structural",   210.00, 340.00),
            ("COMP-004", "Carbon Fibre Panel", "Composites",   310.00, 520.00),
            ("PREC-005", "Gear Assembly",      "Precision",    175.00, 290.00),
        ]
        equipment = [
            ("CNC Machine",    "Operational"),
            ("Conveyor Belt",  "Maintenance"),
            ("Welding Robot",  "Operational"),
            ("Press Machine",  "Operational"),
            ("Laser Cutter",   "Standby"),
        ]
        shifts       = ["Morning", "Afternoon", "Night"]
        defect_types = ["Surface Scratch", "Dimensional Error", "Material Flaw",
                        "Assembly Fault", "Contamination", None]
        severities   = ["Low", "Medium", "High", None]

        today = datetime.date.today()
        rows  = []

        for i in range(1, n + 1):
            plant      = random.choice(plants)
            product    = random.choice(products)
            equip      = random.choice(equipment)
            shift      = random.choice(shifts)

            planned    = random.randint(200, 800)
            actual     = int(planned * random.uniform(0.70, 1.0))
            defective  = int(actual  * random.uniform(0.00, 0.15))
            efficiency = round(random.uniform(60, 98), 2)
            if random.random() < 0.02:   # ~2% zero-efficiency
                efficiency = 0.0
            yield_pct  = round(actual / planned * 100, 2) if planned else 0
            downtime   = random.randint(0, 180)
            run_date   = today - datetime.timedelta(days=random.randint(0, 365))

            # Quality check (LEFT JOIN — ~20% have no check)
            has_check  = random.random() > 0.20
            if has_check:
                sampled      = random.randint(20, 100)
                failed_q     = int(sampled * random.uniform(0, 0.25))
                passed_q     = sampled - failed_q
                defect_rate  = round(failed_q / sampled * 100, 2) if sampled else None
                defect_type  = random.choice(defect_types)
                severity     = random.choice(severities)
                total_checks = random.randint(1, 5)
            else:
                sampled = passed_q = failed_q = defect_rate = None
                defect_type = severity = None
                total_checks = None

            # Equipment (LEFT JOIN — ~10% unmapped)
            has_equip = random.random() > 0.10
            eq_name, eq_status = equip if has_equip else (None, None)
            eq_eff    = round(random.uniform(55, 95), 2) if has_equip else None
            days_maint = random.randint(1, 120) if has_equip else None

            rows.append({
                # Production run
                "run_id":                   i,
                "run_date":                 run_date.isoformat(),
                "shift":                    shift,
                "operator":                 f"Operator-{random.randint(1, 80)}",
                "planned_units":            planned,
                "actual_units":             actual,
                "defective_units":          defective,
                "efficiency_pct":           efficiency,
                "downtime_mins":            downtime,
                "yield_pct":                yield_pct,
                # Plant
                "plant_name":               plant[0],
                "plant_city":               plant[1],
                "plant_country":            plant[2],
                "plant_type":               plant[3],
                "plant_capacity":           random.randint(5000, 20000),
                "employees_count":          random.randint(50, 500),
                # Product
                "product_code":             product[0],
                "product_name":             product[1],
                "product_category":         product[2],
                "unit_cost":                product[3],
                "target_price":             product[4],
                "lead_time_days":           random.randint(3, 30),
                # Quality checks (nullable — LEFT JOIN)
                "total_checks":             total_checks,
                "total_sampled":            sampled,
                "total_passed":             passed_q,
                "total_failed":             failed_q,
                "defect_rate_pct":          defect_rate,
                "primary_defect_type":      defect_type,
                "primary_severity":         severity,
                # Equipment (nullable — LEFT JOIN)
                "equipment_name":           eq_name,
                "equipment_type":           eq_name,
                "equipment_status":         eq_status,
                "equipment_efficiency_pct": eq_eff,
                "days_since_maintenance":   days_maint,
            })

        return pd.DataFrame(rows)

    # ── Dunder methods ────────────────────────────────────────────

    def __str__(self) -> str:
        return f"DataExtractor(schema={self.industry!r}, status={self._status!r})"

    def __repr__(self) -> str:
        return f"DataExtractor(schema={self.industry!r})"

# ================================================================
# test/test_sql.py — Unit Tests for the Manufacturing SQL pipeline
# ================================================================

import sys, pathlib
try:
    _root = pathlib.Path(__file__).resolve().parent.parent
except NameError:
    _root = pathlib.Path.cwd().parent

if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import config
from src.query_runner   import SQLQueryRunner
from src.data_extractor import DataExtractor


# ── SQL File Tests ────────────────────────────────────────────────

def test_sql_files_exist():
    """All four SQL query files must exist in the sql/ directory."""
    expected = [
        "01_explore.sql",
        "02_aggregations.sql",
        "03_five_table_join.sql",
        "04_advanced.sql",
    ]
    for fname in expected:
        assert (config.SQL_DIR / fname).exists(), f"SQL file missing: {fname}"


def test_sql_files_contain_select_keyword():
    """Each SQL file must contain at least one SELECT statement."""
    for fname in [
        "01_explore.sql",
        "02_aggregations.sql",
        "03_five_table_join.sql",
        "04_advanced.sql",
    ]:
        content = (config.SQL_DIR / fname).read_text()
        assert "SELECT" in content.upper(), f"No SELECT found in {fname}"


def test_all_sql_files_contain_industry_placeholder():
    """
    Every SQL file must use {industry} instead of a hardcoded schema name.
    This ensures SQLQueryRunner can inject the correct schema at runtime.
    """
    for fname in [
        "01_explore.sql",
        "02_aggregations.sql",
        "03_five_table_join.sql",
        "04_advanced.sql",
    ]:
        content = (config.SQL_DIR / fname).read_text()
        assert "{industry}" in content, (
            f"{fname} must use {{industry}} placeholder — "
            f"do not hardcode 'manufacturing' directly in SQL files"
        )


def test_join_sql_contains_left_join():
    """
    03_five_table_join.sql must use a LEFT JOIN for quality checks and equipment.
    An INNER JOIN would silently drop runs without quality checks.
    """
    content = (config.SQL_DIR / "03_five_table_join.sql").read_text().upper()
    assert "LEFT JOIN" in content, (
        "03_five_table_join.sql must LEFT JOIN quality_checks and equipment — "
        "production runs without checks must be preserved in the extract"
    )


def test_aggregation_sql_contains_group_by():
    """02_aggregations.sql must use GROUP BY for aggregation logic."""
    content = (config.SQL_DIR / "02_aggregations.sql").read_text().upper()
    assert "GROUP BY" in content, "02_aggregations.sql must contain GROUP BY"


def test_advanced_sql_contains_cte_and_window_function():
    """04_advanced.sql must contain both a CTE (WITH) and a window function (OVER)."""
    content = (config.SQL_DIR / "04_advanced.sql").read_text().upper()
    assert "WITH " in content, "04_advanced.sql must contain a CTE (WITH clause)"
    assert " OVER " in content, "04_advanced.sql must contain a window function (OVER clause)"


def test_advanced_sql_contains_partition_by():
    """04_advanced.sql must rank runs within each plant using PARTITION BY."""
    content = (config.SQL_DIR / "04_advanced.sql").read_text().upper()
    assert "PARTITION BY" in content, (
        "04_advanced.sql must use PARTITION BY to rank runs within each plant"
    )


# ── SQLQueryRunner Tests ──────────────────────────────────────────

def test_query_runner_returns_dataframe():
    """SQLQueryRunner.run() must always return a DataFrame (never crashes)."""
    runner = SQLQueryRunner()
    df = runner.run("SELECT 1 AS test_col")
    assert isinstance(df, pd.DataFrame), "run() must always return a DataFrame"


def test_query_runner_handles_bad_sql_gracefully():
    """A broken query should return an empty DataFrame, not raise an exception."""
    runner = SQLQueryRunner()
    df = runner.run("THIS IS NOT VALID SQL AT ALL")
    assert isinstance(df, pd.DataFrame), (
        "run() should return an empty DataFrame on SQL error, not raise an exception"
    )


def test_query_runner_history_records_each_run():
    """Every query run must be appended to the history log."""
    runner = SQLQueryRunner()
    initial_count = len(runner.history)
    runner.run("SELECT 1")
    runner.run("SELECT 2")
    assert len(runner.history) == initial_count + 2, (
        "history should record one entry per query run"
    )


def test_query_runner_history_entry_has_required_keys():
    """Each history entry must contain the expected audit fields."""
    runner = SQLQueryRunner()
    runner.run("SELECT 1 AS x")
    entry = runner.history[-1]
    for key in ("sql_preview", "rows", "cols", "duration_ms", "status"):
        assert key in entry, f"History entry missing key: {key}"


def test_query_runner_missing_file_returns_empty_dataframe():
    """run_file() with a non-existent filename must return an empty DataFrame."""
    runner = SQLQueryRunner()
    df = runner.run_file("does_not_exist.sql")
    assert isinstance(df, pd.DataFrame), "run_file() should return empty DataFrame for missing file"
    assert df.empty, "run_file() should return empty DataFrame for missing file"


# ── DataExtractor Synthetic Data Tests ───────────────────────────

def test_extractor_synthetic_data_has_required_columns():
    """Synthetic fallback data must contain all expected manufacturing columns."""
    raw = DataExtractor._synthetic_raw_data(50)

    assert isinstance(raw, pd.DataFrame), "Expected DataFrame output"
    assert len(raw) == 50, f"Expected 50 rows, got {len(raw)}"

    required = [
        # Production run
        "run_id", "run_date", "shift", "operator",
        "planned_units", "actual_units", "defective_units",
        "efficiency_pct", "downtime_mins", "yield_pct",
        # Plant
        "plant_name", "plant_city", "plant_country", "plant_type",
        "plant_capacity", "employees_count",
        # Product
        "product_code", "product_name", "product_category",
        "unit_cost", "target_price", "lead_time_days",
        # Quality checks (nullable)
        "total_checks", "total_sampled", "total_passed", "total_failed",
        "defect_rate_pct", "primary_defect_type", "primary_severity",
        # Equipment (nullable)
        "equipment_name", "equipment_type", "equipment_status",
        "equipment_efficiency_pct", "days_since_maintenance",
    ]

    for col in required:
        assert col in raw.columns, f"Synthetic data missing column: {col}"


def test_extractor_synthetic_data_correct_row_count():
    """_synthetic_raw_data(n) must return exactly n rows."""
    for n in [10, 100, 500]:
        raw = DataExtractor._synthetic_raw_data(n)
        assert len(raw) == n, f"Expected {n} rows, got {len(raw)}"


def test_extractor_synthetic_data_has_quality_issues():
    """
    Synthetic data must contain the intentional data quality issues
    that downstream ETL is designed to detect and fix.
    """
    raw = DataExtractor._synthetic_raw_data(300)

    # ~20% of runs have no quality check (LEFT JOIN behaviour)
    null_checks = raw["total_checks"].isna().sum()
    assert null_checks > 0, (
        "Synthetic data should have NULL total_checks rows — "
        "mirrors the LEFT JOIN on quality_checks"
    )

    # ~10% have no equipment mapping
    null_equip = raw["equipment_name"].isna().sum()
    assert null_equip > 0, "Synthetic data should have some NULL equipment_name rows"

    # ~2% zero efficiency
    zero_eff = (raw["efficiency_pct"] == 0).sum()
    assert zero_eff > 0, "Synthetic data should have some zero efficiency_pct rows"


def test_extractor_synthetic_data_is_deterministic():
    """Two calls to _synthetic_raw_data(n) must produce identical DataFrames."""
    df1 = DataExtractor._synthetic_raw_data(100)
    df2 = DataExtractor._synthetic_raw_data(100)
    pd.testing.assert_frame_equal(df1, df2, check_like=False)


def test_extractor_synthetic_data_shifts_are_valid():
    """shift column must only contain Morning, Afternoon, or Night."""
    raw = DataExtractor._synthetic_raw_data(200)
    valid_shifts = {"Morning", "Afternoon", "Night"}
    actual = set(raw["shift"].unique())
    assert actual.issubset(valid_shifts), (
        f"Unexpected shift values: {actual - valid_shifts}"
    )


def test_extractor_synthetic_data_units_are_positive():
    """planned_units and actual_units must be positive integers."""
    raw = DataExtractor._synthetic_raw_data(200)
    assert (raw["planned_units"] > 0).all(), "planned_units must all be positive"
    assert (raw["actual_units"]  > 0).all(), "actual_units must all be positive"


# ── DataExtractor Save / Load Tests ──────────────────────────────

def test_extractor_save_creates_csv(tmp_path, monkeypatch):
    """DataExtractor.save() must create raw-data.csv at the configured path."""
    target_path = tmp_path / "raw-data.csv"

    monkeypatch.setattr("src.data_extractor.RAW_DATA_PATH", target_path)

    extractor = DataExtractor()
    extractor.raw_df = DataExtractor._synthetic_raw_data(50)
    extractor._status = "extracted"
    extractor.save()

    assert target_path.exists(), f"save() should create raw-data.csv at {target_path}"

    reloaded = pd.read_csv(target_path)
    assert len(reloaded) == 50, "Saved CSV should have the correct row count"

    for col in ["run_id", "plant_name", "efficiency_pct", "product_name", "defect_rate_pct"]:
        assert col in reloaded.columns, f"Saved CSV missing column: {col}"


def test_extractor_save_without_extract_does_not_crash():
    """Calling save() before extract() should log an error but not raise an exception."""
    extractor = DataExtractor()
    try:
        extractor.save()
    except Exception as e:
        assert False, f"save() before extract() should not raise: {e}"


def test_extractor_chaining_returns_self():
    """extract() and save() must return self to support method chaining."""
    extractor = DataExtractor()
    result = extractor.extract()
    assert result is extractor, "extract() must return self"


if __name__ == "__main__":
    import pytest
    pytest.main(["-v", "--tb=short", __file__])

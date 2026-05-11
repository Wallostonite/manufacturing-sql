-- ============================================================
-- 01_explore.sql  —  Individual table exploration
-- Schema: {industry}   (replaced at runtime by SQLQueryRunner)
-- ============================================================

-- Production Runs
SELECT * FROM {industry}.production_runs LIMIT 10;
SELECT COUNT(*) AS total_production_runs FROM {industry}.production_runs;

-- Quality Checks
SELECT * FROM {industry}.quality_checks LIMIT 10;
SELECT COUNT(*) AS total_quality_checks FROM {industry}.quality_checks;

-- Equipment
SELECT * FROM {industry}.equipment LIMIT 10;
SELECT COUNT(*) AS total_equipment FROM {industry}.equipment;

-- Plants
SELECT * FROM {industry}.plants LIMIT 10;
SELECT COUNT(*) AS total_plants FROM {industry}.plants;

-- Products
SELECT * FROM {industry}.products LIMIT 10;
SELECT COUNT(*) AS total_products FROM {industry}.products;

-- ============================================================
-- 02_aggregations.sql  —  Business-level aggregations
-- Schema: {industry}   (replaced at runtime by SQLQueryRunner)
-- ============================================================

-- Defect rate and output volume by plant
SELECT
    p.plant_name,
    p.city,
    COUNT(pr.run_id)                                              AS total_runs,
    SUM(pr.actual_units)                                          AS total_units_produced,
    SUM(pr.defective_units)                                       AS total_defects,
    ROUND(
        100.0 * SUM(pr.defective_units) / NULLIF(SUM(pr.actual_units), 0), 2
    )                                                             AS defect_rate_pct,
    ROUND(AVG(pr.efficiency_pct), 2)                              AS avg_efficiency_pct,
    SUM(pr.downtime_mins)                                         AS total_downtime_mins
FROM {industry}.production_runs pr
JOIN {industry}.plants           p ON pr.plant_id = p.plant_id
GROUP BY p.plant_id, p.plant_name, p.city
ORDER BY defect_rate_pct DESC;


-- Production efficiency and defect counts by shift
SELECT
    pr.shift,
    COUNT(pr.run_id)                                              AS total_runs,
    ROUND(AVG(pr.efficiency_pct), 2)                              AS avg_efficiency_pct,
    SUM(pr.defective_units)                                       AS total_defects,
    ROUND(AVG(pr.downtime_mins), 1)                               AS avg_downtime_mins
FROM {industry}.production_runs pr
GROUP BY pr.shift
ORDER BY avg_efficiency_pct DESC;


-- Quality check pass rate by product category
SELECT
    pr.category                                                   AS product_category,
    COUNT(qc.check_id)                                            AS total_checks,
    SUM(qc.passed)                                                AS total_passed,
    SUM(qc.failed)                                                AS total_failed,
    ROUND(
        100.0 * SUM(qc.passed) / NULLIF(SUM(qc.passed) + SUM(qc.failed), 0), 2
    )                                                             AS pass_rate_pct
FROM {industry}.quality_checks  qc
JOIN {industry}.production_runs run ON qc.run_id     = run.run_id
JOIN {industry}.products        pr  ON run.product_id = pr.product_id
GROUP BY pr.category
ORDER BY pass_rate_pct DESC;

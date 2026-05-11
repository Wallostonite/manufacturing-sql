-- ============================================================
-- 04_advanced.sql  —  CTE + Window function
-- Schema: {industry}   (replaced at runtime by SQLQueryRunner)
-- ============================================================

-- ── CTE: plant efficiency summary ────────────────────────────────
WITH plant_efficiency AS (
    SELECT
        p.plant_id,
        p.plant_name,
        p.city,
        COUNT(pr.run_id)                                          AS total_runs,
        ROUND(AVG(pr.efficiency_pct), 2)                          AS avg_efficiency_pct,
        SUM(pr.actual_units)                                      AS total_units,
        SUM(pr.defective_units)                                   AS total_defects,
        ROUND(
            100.0 * SUM(pr.defective_units) / NULLIF(SUM(pr.actual_units), 0), 2
        )                                                         AS defect_rate_pct
    FROM {industry}.production_runs pr
    JOIN {industry}.plants           p ON pr.plant_id = p.plant_id
    GROUP BY p.plant_id, p.plant_name, p.city
)
SELECT
    plant_name,
    city,
    total_runs,
    avg_efficiency_pct,
    total_units,
    total_defects,
    defect_rate_pct,
    ROUND(total_units::NUMERIC / NULLIF(total_runs, 0), 0) AS avg_units_per_run
FROM plant_efficiency
ORDER BY avg_efficiency_pct DESC;


-- ── Window function: rank each run by efficiency within its plant ─
SELECT
    pr.run_id,
    p.plant_name,
    pr.run_date,
    pr.shift,
    pr.efficiency_pct,
    pr.actual_units,
    pr.defective_units,
    RANK() OVER (
        ORDER BY pr.efficiency_pct DESC
    )                                                             AS global_efficiency_rank,
    RANK() OVER (
        PARTITION BY pr.plant_id
        ORDER BY pr.efficiency_pct DESC
    )                                                             AS efficiency_rank_within_plant
FROM {industry}.production_runs pr
JOIN {industry}.plants           p ON pr.plant_id = p.plant_id
ORDER BY p.plant_name, efficiency_rank_within_plant
LIMIT 50;

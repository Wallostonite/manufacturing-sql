-- ============================================================
-- 03_five_table_join.sql  —  One row per production run, all five tables
-- Schema: {industry}   (replaced at runtime by SQLQueryRunner)
-- ============================================================

SELECT
    -- Production run
    pr.run_id,
    pr.run_date,
    pr.shift,
    pr.operator,
    pr.planned_units,
    pr.actual_units,
    pr.defective_units,
    pr.efficiency_pct,
    pr.downtime_mins,
    ROUND(
        pr.actual_units::NUMERIC / NULLIF(pr.planned_units, 0) * 100, 2
    )                           AS yield_pct,

    -- Plant
    p.plant_name,
    p.city                      AS plant_city,
    p.country                   AS plant_country,
    p.plant_type,
    p.capacity_units            AS plant_capacity,
    p.employees_count,

    -- Product
    prod.product_code,
    prod.product_name,
    prod.category               AS product_category,
    prod.unit_cost,
    prod.target_price,
    prod.lead_time_days,

    -- Quality checks (aggregated)
    qc.total_checks,
    qc.total_sampled,
    qc.total_passed,
    qc.total_failed,
    qc.defect_rate_pct,
    qc.primary_defect_type,
    qc.primary_severity,

    -- Equipment (most recently maintained per plant)
    eq.equipment_name,
    eq.equipment_type,
    eq.equipment_status,
    eq.equipment_efficiency_pct,
    eq.days_since_maintenance

FROM {industry}.production_runs pr
JOIN {industry}.plants           p    ON pr.plant_id   = p.plant_id
JOIN {industry}.products         prod ON pr.product_id = prod.product_id
LEFT JOIN (
    SELECT
        run_id,
        COUNT(check_id)                                                        AS total_checks,
        SUM(sample_size)                                                       AS total_sampled,
        SUM(passed)                                                            AS total_passed,
        SUM(failed)                                                            AS total_failed,
        ROUND(SUM(failed)::NUMERIC / NULLIF(SUM(sample_size), 0) * 100, 2)    AS defect_rate_pct,
        MODE() WITHIN GROUP (ORDER BY defect_type)                             AS primary_defect_type,
        MODE() WITHIN GROUP (ORDER BY severity)                                AS primary_severity
    FROM {industry}.quality_checks
    GROUP BY run_id
) qc ON pr.run_id = qc.run_id
LEFT JOIN (
    SELECT DISTINCT ON (plant_id)
        plant_id,
        equipment_name,
        equipment_type,
        status                  AS equipment_status,
        efficiency_pct          AS equipment_efficiency_pct,
        CURRENT_DATE - last_maintenance AS days_since_maintenance
    FROM {industry}.equipment
    ORDER BY plant_id, last_maintenance DESC
) eq ON pr.plant_id = eq.plant_id

WHERE p.is_active  = TRUE
  AND prod.is_active = TRUE

ORDER BY pr.run_date DESC, pr.plant_id, pr.shift;

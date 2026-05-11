# Business Problem Documentation: PrecisionOps Manufacturing Defect Prediction & Operational Intelligence Data Foundation

> **Document Owner:** Data Analytics Team
> **Sponsor:** Chief Operations Officer, PrecisionOps Manufacturing
> **Status:** Draft → Ready for Execution
> **Target Audience:** Data Analyst, Data Engineering, Operations, Quality Assurance, Plant Leadership

---

## 1. Executive Summary

PrecisionOps Manufacturing operates ten production facilities across three continents, but strategic quality and efficiency decisions are constrained by fragmented, siloed operational data. The Chief Operations Officer has identified an urgent need for a unified, run-level dataset to power defect prediction modelling and operational efficiency tracking. This document defines the business problem, outlines the data foundation initiative, and establishes success criteria for delivering a production-ready extract (`raw-data.csv`) that will serve as the single source of truth for downstream ETL, machine learning models, and plant performance dashboards.

---

## 2. Business Context & Background

- **Operations Model:** PrecisionOps runs discrete production shifts across ten plants, each producing hundreds of SKUs ranging from automotive components to pharmaceutical goods. Every production run generates quality inspection records, equipment telemetry, and output metrics.
- **Current State:** Production run records, quality check results, equipment status, plant metadata, and product specifications reside in five separate tables within the `manufacturing` schema on Supabase. Reporting relies on manual exports or stale aggregates prepared by plant coordinators.
- **Pain Points:**
  - Defect root cause analysis requires manual joins across multiple exports, introducing errors and delaying response by 24–72 hours.
  - Equipment maintenance scheduling is disconnected from quality outcome data, making it impossible to correlate downtime events with defect spikes.
  - Plant-to-plant performance benchmarking is inconsistent — different teams export at different times using different join logic, producing conflicting efficiency figures.
  - Product-level quality standards and tolerance targets cannot be evaluated against actual defect rates without a joined view.
- **Trigger:** COO mandate to establish a reproducible, automated data pipeline that delivers a fully joined, validation-ready flat file for downstream ETL and ML feature engineering.

---

## 3. Problem Statement

PrecisionOps Manufacturing lacks a centralised, run-granular dataset that unifies production output records, quality inspection results, equipment maintenance status, plant operational context, and product specifications. This fragmentation creates analytical latency, increases QA overhead, and limits the organisation's ability to:

1. Predict and prevent defects before they reach downstream production stages
2. Benchmark plant and shift efficiency with consistent, reproducible metrics
3. Correlate equipment health with quality outcomes to optimise maintenance scheduling
4. Build ML-ready feature sets for defect classification and yield forecasting models

Without a reliable data foundation, operational decisions, quality interventions, and capacity planning operate on incomplete signals, leading to excess scrap, unplanned downtime, and missed SLA targets.

---

## 4. Business Objectives

| Objective                                        | Business Impact                                                                          |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Deliver a unified, run-level dataset             | Enable defect prediction modelling and reduce analytical preparation time by ≥70%        |
| Standardise join logic & data quality rules      | Eliminate conflicting plant-level reports and reduce QA investigation overhead by ≥30%  |
| Provide baseline efficiency & quality metrics    | Empower Operations and QA with consistent cross-plant KPIs and benchmarking capability  |
| Automate extraction via `run.py`                 | Ensure reproducibility, auditability, and seamless handoff to Data Engineering          |

---

## 5. Key Business Questions to Answer

- Which plants and shifts have the highest defect rates, and what equipment or product factors correlate with those defects?
- How does equipment maintenance status (days since last service, next scheduled maintenance) correlate with production efficiency and defect rates?
- Which product categories consistently underperform against their quality tolerance targets?
- How does downtime distribute across shifts and plants, and what is its measurable impact on yield?
- Which production runs rank highest for efficiency within each plant, and what operational conditions characterise top-performing runs?

---

## 6. Scope & Boundaries

| ✅ In Scope                                                                                                                         | ❌ Out of Scope                                                        |
| ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Extraction & joining of `production_runs`, `quality_checks`, `equipment`, `plants`, `products` from `manufacturing` schema         | ML model training, feature engineering, or dashboard creation          |
| Output: `data/raw-data.csv` (1 row/production run, UTF-8, snake_case headers)                                                      | Real-time streaming, CDC, sensor telemetry ingestion                   |
| Automated execution via `python run.py`                                                                                             | PII masking or GDPR compliance workflows (handled downstream in ETL)   |
| Baseline aggregations & validation queries (defect rates, shift efficiency, quality pass rates)                                     | Cross-system reconciliation with ERP or MES systems                    |

---

## 7. Stakeholders & Responsibilities

| Role                            | Responsibility                                                                |
| ------------------------------- | ----------------------------------------------------------------------------- |
| **Chief Operations Officer**    | Strategic sponsor, prioritisation, business alignment                         |
| **Data Analyst**                | SQL development, query validation, pipeline automation, QA                    |
| **Data Engineering**            | Consumes `raw-data.csv` for ETL, schema validation, scheduling                |
| **Quality Assurance**           | Defines defect classification requirements, validates quality metrics          |
| **Plant Operations Managers**   | Reviews plant-level efficiency benchmarks, provides operational context        |
| **Maintenance Engineering**     | Validates equipment correlation logic, reviews downtime and maintenance KPIs  |

---

## 8. Success Metrics & KPIs

| Metric                        | Target                                                                       | Measurement Method                              |
| ----------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------- |
| **Data Completeness**         | 100% of active production runs represented                                   | Row count match vs. `production_runs` table     |
| **Join Accuracy**             | 0% fan-out duplication across quality check aggregation                      | `COUNT(*)` after join == source run count       |
| **Critical Null Rate**        | ≤2% on `run_id`, `plant_id`, `product_id`, `efficiency_pct`                  | Automated validation script                     |
| **Pipeline Runtime**          | <5 minutes for current volume                                                | `time python run.py`                            |
| **ETL Readiness**             | Passes schema & dtype validation                                             | Downstream ingestion test                       |
| **Defect Model Readiness**    | Defect rate feature available at run granularity for ≥80% of runs            | ML team feature validation post-ETL             |

---

## 9. Data Requirements & Deliverables

- **Format:** `CSV`, UTF-8 encoded, comma-delimited, header row included
- **Granularity:** One row per `run_id`
- **Key Joins:**
  - `production_runs` → `plants` (many:1)
  - `production_runs` → `products` (many:1)
  - `production_runs` → `quality_checks` (1:many → aggregated via subquery to preserve 1 row/run)
  - `production_runs` → `equipment` (many:1 via plant → most recent maintenance record)
- **Advanced Logic Included:**
  - Subquery aggregation for quality checks (total passed/failed, defect rate, mode defect type)
  - `DISTINCT ON (plant_id)` for equipment (most recently maintained machine per plant)
  - Window function: `RANK() OVER (PARTITION BY plant_id ORDER BY efficiency_pct DESC)` for within-plant efficiency ranking
- **Deliverables:**
  - `data/raw-data.csv`
  - `sql/03_five_table_join.sql`
  - `run.py` (automated extraction script)
  - Validation queries (defect rates by plant, shift efficiency, quality pass rates by category)

---

## 10. Assumptions & Constraints

- Supabase read access is stable, performant, and scoped to the `manufacturing` schema.
- Schema structure remains static during extraction; any changes require version control & re-validation.
- Historical data quality is sufficient for baseline analysis; runs without quality checks are treated as `NULL` (not imputed) and preserved via `LEFT JOIN`.
- Equipment is mapped to plants (not individual runs); the most recently maintained machine per plant is used as a proxy for equipment context.
- Dataset volume fits within standard pandas memory constraints for local execution.

---

## 11. Next Steps & Timeline

| Phase                   | Action                                                              | Owner              | ETA     |
| ----------------------- | ------------------------------------------------------------------- | ------------------ | ------- |
| 1. Query Development    | Write & validate 5-table join + aggregations                        | Data Analyst       | Day 1-2 |
| 2. Automation & QA      | Build `run.py`, run validation checks, fix duplicates/nulls         | Data Analyst       | Day 3   |
| 3. Code Review & GitHub | Push to repo, open PR, attach QA report                             | Data Analyst       | Day 4   |
| 4. ETL Handoff          | Deliver `raw-data.csv`, align with Data Eng on ETL specs            | Data Analyst + Eng | Day 5   |
| 5. Business Validation  | QA and Operations confirm metric alignment                          | COO + Stakeholders | Day 6-7 |

---

## 12. Approval & Sign-Off

| Role                      | Name | Signature | Date |
| ------------------------- | ---- | --------- | ---- |
| Chief Operations Officer  |      |           |      |
| Data Analytics Lead       |      |           |      |
| Data Engineering Lead     |      |           |      |
| Data Analyst (Author)     |      |           |      |

---

📎 **Attachments / References:**

- `run.py` execution guide
- `sql/03_five_table_join.sql`
- Validation checklist & QA script
- Downstream ETL Specification (future)

> 💡 **Note for Team Members:** This document should live in your project wiki or repository root. Update the `[Status]`, `ETA`, and `Sign-Off` fields as the project progresses. All downstream work (defect prediction, efficiency benchmarking, maintenance optimisation) depends on the integrity of this extract. Treat `raw-data.csv` as a contract between Analytics and Engineering.

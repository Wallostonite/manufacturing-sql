# 🏭 Manufacturing SQL Data Pipeline

> A production-style SQL extraction & automation pipeline that consolidates fragmented manufacturing data into a unified, analysis-ready dataset. Built to support defect prediction modeling, operational efficiency tracking, and cross-plant performance analysis.

## 📖 Overview
This project simulates a real-world data analyst workflow: connecting to a live PostgreSQL database, writing optimized SQL to join and aggregate data across five core operational tables, and automating the export process via Python. The final output (`raw-data.csv`) serves as the foundational dataset for downstream machine learning models, BI dashboards, and ETL workflows.

## 🛠 Tech Stack
- **Database:** PostgreSQL (hosted on Supabase)
- **Query Language:** Advanced SQL (CTEs, Window Functions, Multi-table Joins, Time-based Aggregations)
- **Automation:** Python (`psycopg2`, `pandas`, `csv`)
- **Environment:** `.env` for secure credential management
- **Version Control:** Git & GitHub

## 📊 Database Schema
All queries target the `manufacturing` schema:
| Table             | Purpose                                  |
|-------------------|------------------------------------------|
| `production_runs` | Shift records, output volume, downtime   |
| `quality_checks`  | Inspection results, defect counts, status|
| `equipment`       | Machine IDs, maintenance schedules, age  |
| `plants`          | Facility locations, capacity, operating hours |
| `products`        | SKUs, specifications, target tolerances  |

## ✨ Key Features & SQL Techniques
- **Five-Table Consolidation:** One row per production run, enriched with quality metrics, equipment status, plant context, and product specifications
- **Operational Metrics Aggregation:**
  - Defect rates by plant and shift
  - Production efficiency & yield calculations
  - Equipment downtime correlation with quality outcomes
- **Advanced Query Patterns:**
  - ✅ Common Table Expressions (CTEs) for modular, readable logic
  - ✅ Window functions (`RANK() OVER(PARTITION BY plant)`) to rank production runs by efficiency within each facility
- **Automated Export:** Python script executes queries, manages connections, and writes a clean `raw-data.csv` ready for ML/ETL ingestion

## 🚀 How to Run Locally
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/manufacturing-sql-pipeline.git
   cd manufacturing-sql-pipeline
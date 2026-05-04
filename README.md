# P02 ⭐⭐ — Manufacturing SQL
## The Darko Method 2026 | Student Project

---

## Your Brief

**Company:** PrecisionCraft Industries
**Your role:** Data Analyst

PrecisionCraft runs 4 manufacturing plants. The Operations Director needs a raw data
extract combining production run records, quality check results, and equipment
maintenance logs so the data science team can begin building a defect prediction model.

Your job is to connect to the Supabase database, write SQL queries against the
`manufacturing` schema, and produce `raw-data.csv`.

**Schema:** `manufacturing`
**Key tables:** `production_runs`, `quality_checks`, `equipment`, `plants`, `products`

**Deliverable:** `data/raw-data.csv` — joined production and quality data,
ready for Module 05 ETL.

---

## Success Criteria

- [ ] All five tables queried individually in DBeaver
- [ ] Aggregation queries show defect rates and efficiency by plant and shift
- [ ] Join query combines production runs with quality check results
- [ ] At least one CTE or window function ranks production runs by efficiency within each plant
- [ ] `python run.py` saves `raw-data.csv`
- [ ] Project pushed to GitHub

---

> Build your project from scratch using the teaching project as your reference.

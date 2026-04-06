# Technical Ingestion Plan: Census 2011 Primary Census Abstract (PCA)

> **Pipeline Registry ID**: `census_2011_pca`
> **Status**: Implementation Ready
> **Target Table**: `census_2011_pca`
> **Last Updated**: April 2026

---

## Overview

This document describes the end-to-end technical strategy for ingesting the
Census 2011 Primary Census Abstract (PCA) into the BharatData pipeline.
It covers file acquisition, extraction logic, field normalization, validation
rules, and storage configuration — aligned with the patterns established by
the NCRB ingestion pipeline.

---

## 1. Source Data Characteristics

### File Format
- **Type**: Microsoft Excel (`.xls` / `.xlsx`)
- **Distribution**: One file per state/UT (35 files total)
- **File Naming Pattern**: `DDW_PCA_[STATE_CODE]_[YEAR].xlsx`
  - Example: `DDW_PCA_27_2011.xlsx` (Maharashtra)
- **Download Source**: https://censusindia.gov.in/census.website/data/census-tables

### Typical File Structure

Each file contains:
- A metadata header (rows 1–4, not tabular data)
- A column header row (typically row 5 or 6 — varies by file)
- Data rows (one per village/town/sub-district/district)
- **Summary rows** (must be filtered out): e.g., "State - Total", "District - Total"

### Header Detection Challenge

Census files do not have a guaranteed fixed header row. The pipeline must
**dynamically detect** the header row by scanning for the presence of
`TOT_P` (or `State`) in the row cells.

---

## 2. YAML Registry Reference

The registry file `pipeline/engine/registry/census_2011_pca.yaml` fully
describes the ingestion configuration. Below is a human-readable breakdown
of its key sections.

### Identity

```yaml
identity:
  id: census_2011_pca
  name: "Census 2011 Primary Census Abstract"
  publishing_body: "Office of the Registrar General & Census Commissioner"
  update_frequency: "decadal"
```

### Acquisition

```yaml
acquisition:
  method: manual_upload
  search_pattern: "data/raw/census-2011/*.xlsx"
```

**Rationale for `manual_upload`**: Census data does not have a stable, programmatic
download URL. Files are downloaded manually from censusindia.gov.in and placed in
the `data/raw/census-2011/` directory.

### Extraction

```yaml
extraction:
  format: xlsx
  header_detection:
    method: pattern_match
    pattern: "^(State|District|Sub-district|Village|TOT_P)$"
  column_mapping:
    "State":        {field: "state_name",        type: "str"}
    "District":     {field: "district_name",     type: "str"}
    "Sub-district": {field: "sub_district_name", type: "str"}
    "Village":      {field: "village_name",      type: "str"}
    "TOT_P":        {field: "total_population",  type: "int"}
    "TOT_M":        {field: "male_population",   type: "int"}
    "TOT_F":        {field: "female_population", type: "int"}
    "P_06":         {field: "population_0_6",    type: "int"}
    "P_SC":         {field: "sc_population",     type: "int"}
    "P_ST":         {field: "st_population",     type: "int"}
    "P_LIT":        {field: "literate_population", type: "int"}
    "MAIN_W_P":     {field: "main_workers",      type: "int"}
    "MARG_W_P":     {field: "marginal_workers",  type: "int"}
    "NON_WORK_P":   {field: "non_workers",       type: "int"}
```

---

## 3. Pipeline Stages

### Stage 1: Acquisition

| Step | Action | Detail |
|------|--------|--------|
| 1.1 | Download state files | From censusindia.gov.in → `data/raw/census-2011/` |
| 1.2 | Verify file count | Expect 35 `.xlsx` files (one per state/UT) |
| 1.3 | Log file checksums | Record SHA-256 hash per file for reproducibility |

**Directory Structure After Acquisition:**
```
data/
└── raw/
    └── census-2011/
        ├── DDW_PCA_01_2011.xlsx    # Jammu & Kashmir
        ├── DDW_PCA_02_2011.xlsx    # Himachal Pradesh
        ├── DDW_PCA_03_2011.xlsx    # Punjab
        ├── ...
        └── DDW_PCA_35_2011.xlsx    # Goa
```

---

### Stage 2: Extraction

The pipeline reads each `.xlsx` file using `openpyxl` (or equivalent).

#### 2.1 Header Row Detection

```python
def find_header_row(sheet) -> int:
    """
    Scans up to row 15 to find the row containing 'TOT_P' or 'State'.
    Returns the 0-indexed row number.
    """
    import re
    pattern = re.compile(r"^(State|District|Sub-district|Village|TOT_P)$", re.IGNORECASE)
    for i, row in enumerate(sheet.iter_rows(max_row=15, values_only=True)):
        if any(pattern.match(str(cell)) for cell in row if cell is not None):
            return i
    raise ValueError("Header row not found in first 15 rows")
```

#### 2.2 Column Mapping

After header detection, each column is mapped to its canonical field name
using the registry's `column_mapping`. Columns not in the mapping are **ignored**.

#### 2.3 Row Filtering (Summary Row Removal)

```yaml
row_filters:
  summary_patterns: ["State - ", "District - ", "TOTAL"]
```

Rows where `state_name` or `district_name` matches any of these patterns
are excluded from the output. This removes aggregated summary rows that
would cause double-counting.

**Example filtered rows:**
```
"State - Maharashtra - Total"   → FILTERED
"District - Pune - Total"       → FILTERED
"TOTAL"                         → FILTERED
"Pune"                          → RETAINED
```

---

### Stage 3: Normalization

#### 3.1 Type Casting

All fields defined with `type: int` in the registry are cast using:

```python
def safe_int(value) -> int:
    """Returns 0 for null/empty/non-numeric values."""
    if value is None or str(value).strip() == "":
        return 0
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return 0
```

**Rationale**: Census files often contain commas in large numbers (`1,23,456`),
blank cells where data was not collected, and occasional text like `"N.A."`.

#### 3.2 Null Handling

```yaml
normalization:
  null_handling:
    total_population: "zero"
    male_population: "zero"
    female_population: "zero"
```

Population counts default to `0` when null. This is acceptable because
a null population count typically means the administrative unit is
uninhabited (e.g., a forest reserve listed as a village).

#### 3.3 Derived Field Computation

After normalization, the pipeline computes derived fields:

```python
def compute_derived_fields(row: dict) -> dict:
    totpop = row["total_population"]
    pop_0_6 = row["population_0_6"]

    # Literacy Rate
    effective_pop = totpop - pop_0_6
    if effective_pop > 0:
        row["literacy_rate"] = round(row["literate_population"] / effective_pop * 100, 2)
    else:
        row["literacy_rate"] = None

    # Sex Ratio
    if row["male_population"] > 0:
        row["sex_ratio"] = round(row["female_population"] / row["male_population"] * 1000, 1)
    else:
        row["sex_ratio"] = None

    # Workforce Participation Rate
    total_workers = row["main_workers"] + row["marginal_workers"]
    if totpop > 0:
        row["workforce_participation_rate"] = round(total_workers / totpop * 100, 2)
    else:
        row["workforce_participation_rate"] = None

    return row
```

---

### Stage 4: Validation

Before loading to the database, each processed file's output is validated:

| Validation Rule | Check | Action on Failure |
|----------------|-------|-------------------|
| Row count | `row_count >= 100` per state file | Log warning, do NOT block |
| Population balance | `total_population == male_population + female_population` (±1) | Flag row |
| Literacy balance | `literate_population + illiterate_population ≈ total_population - population_0_6` | Flag row |
| Worker balance | `main_workers + marginal_workers + non_workers ≈ total_population` | Flag row |
| Sex ratio sanity | `sex_ratio` between 500 and 1200 | Flag row for review |
| Non-negative values | All integer fields must be `>= 0` | Reject row |

**Flagged rows** are written to a `_flagged/census_2011_pca_flags.csv` file for
manual inspection. They are **not loaded** into the main table.

---

### Stage 5: Loading

#### 5.1 Target Table

```yaml
storage:
  table_name: "census_2011_pca"
  unique_key: ["state_name", "district_name", "sub_district_name", "village_name"]
```

#### 5.2 Upsert Strategy

The pipeline uses an **upsert** (INSERT OR UPDATE) strategy based on the
`unique_key`. This means re-running the ingestion on the same files is safe —
it will update existing records rather than creating duplicates.

#### 5.3 Batch Loading

Records are loaded in batches of `1000` rows to avoid memory pressure and
provide progress visibility.

```python
BATCH_SIZE = 1000

def load_to_db(records: list[dict], table: str):
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        db.upsert(table, batch, conflict_fields=UNIQUE_KEY)
        logger.info(f"Loaded batch {i // BATCH_SIZE + 1}: {len(batch)} rows")
```

#### 5.4 Source Tracking

Each loaded record includes metadata for lineage tracking:

| Field | Value |
|-------|-------|
| `_source_id` | Registry ID: `census_2011_pca` |
| `_source_file` | Original filename (e.g., `DDW_PCA_27_2011.xlsx`) |
| `_ingested_at` | UTC timestamp of ingestion run |

---

## 4. Error Handling Strategy

| Error Type | Handling |
|-----------|---------|
| File not found | Skip file, log error, continue with next |
| Header not detected | Skip file, log critical error, alert |
| Type cast failure (single cell) | Set to `0`, log warning |
| Validation failure (single row) | Write to flags file, skip row |
| DB connection error | Retry 3×, then fail loudly |
| Duplicate key violation | Use upsert — should not occur |

---

## 5. Running the Ingestion

### Prerequisites

1. Place all state `.xlsx` files in `data/raw/census-2011/`
2. Ensure the `census_2011_pca` table exists in the database
3. Confirm the registry file is at `pipeline/engine/registry/census_2011_pca.yaml`

### Execution

```bash
# Ingest all Census 2011 PCA files
python -m pipeline.engine.ingest --source census_2011_pca

# Ingest a single state file (for testing)
python -m pipeline.engine.ingest --source census_2011_pca --file DDW_PCA_27_2011.xlsx

# Dry run (validate without loading)
python -m pipeline.engine.ingest --source census_2011_pca --dry-run
```

### Expected Output

```
INFO  [census_2011_pca] Found 35 files in data/raw/census-2011/
INFO  [census_2011_pca] Processing: DDW_PCA_01_2011.xlsx ...
INFO  [census_2011_pca] Header found at row 5
INFO  [census_2011_pca] Extracted 14,821 rows, filtered 48 summary rows
INFO  [census_2011_pca] Normalized 14,773 records
INFO  [census_2011_pca] Validation: 14,773 OK, 12 flagged
INFO  [census_2011_pca] Loaded 14,773 rows to census_2011_pca table
...
INFO  [census_2011_pca] COMPLETE: 35 files, 640,932 total rows loaded
```

---

## 6. Database Schema

```sql
CREATE TABLE census_2011_pca (
    id                          SERIAL PRIMARY KEY,
    state_name                  TEXT NOT NULL,
    district_name               TEXT,
    sub_district_name           TEXT,
    village_name                TEXT,

    -- Core population
    total_population            INTEGER DEFAULT 0,
    male_population             INTEGER DEFAULT 0,
    female_population           INTEGER DEFAULT 0,
    population_0_6              INTEGER DEFAULT 0,

    -- SC/ST
    sc_population               INTEGER DEFAULT 0,
    st_population               INTEGER DEFAULT 0,

    -- Literacy
    literate_population         INTEGER DEFAULT 0,
    illiterate_population       INTEGER DEFAULT 0,

    -- Workers
    main_workers                INTEGER DEFAULT 0,
    marginal_workers            INTEGER DEFAULT 0,
    non_workers                 INTEGER DEFAULT 0,

    -- Derived (computed during normalization)
    literacy_rate               NUMERIC(5,2),
    sex_ratio                   NUMERIC(6,1),
    workforce_participation_rate NUMERIC(5,2),

    -- Lineage
    _source_id                  TEXT DEFAULT 'census_2011_pca',
    _source_file                TEXT,
    _ingested_at                TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (state_name, district_name, sub_district_name, village_name)
);

-- Indexes for common query patterns
CREATE INDEX idx_census_pca_state   ON census_2011_pca (state_name);
CREATE INDEX idx_census_pca_district ON census_2011_pca (district_name);
```

---

## 7. Consistency with NCRB Pipeline

This plan is intentionally aligned with the NCRB ingestion pattern
(`ncrb_state_unified.yaml`). Key similarities:

| Aspect | NCRB Pattern | Census PCA Pattern |
|--------|-------------|-------------------|
| Registry file structure | `identity`, `acquisition`, `extraction`, `storage`, `normalization` | Same |
| Header detection | `pattern_match` on anchor columns | Same |
| Row filtering | `summary_patterns` list | Same |
| Null handling | `zero` for numeric fields | Same |
| Unique key | Multi-column natural key | Same |
| Upsert strategy | INSERT OR UPDATE | Same |

**Divergences:**
- Census uses `manual_upload` (vs. NCRB which supports automated scraping)
- Census adds `derived field computation` stage (not in NCRB)
- Census has stricter cross-validation rules due to inter-field relationships

---

## 8. Verification Checklist

After running ingestion, verify:

- [ ] Total row count is approximately 640,000 (all villages/towns)
- [ ] All 35 state files processed without critical errors
- [ ] `_flagged/census_2011_pca_flags.csv` has fewer than 500 flagged rows
- [ ] Query `SELECT COUNT(*) FROM census_2011_pca WHERE state_name = 'Maharashtra'` returns ~45,000+
- [ ] Run YAML syntax check: `python -c "import yaml; yaml.safe_load(open('pipeline/engine/registry/census_2011_pca.yaml'))"`
- [ ] Cross-check sample row: Pune district total population ≈ 9.4 million

---

*Maintained by BharatData Pipeline Team | April 2026*

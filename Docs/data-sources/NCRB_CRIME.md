# NCRB Crime in India — Data Source Reference

> **Formal Data Source Document** | Last updated: 2026-03-20 | Step 10 of Stage 1

---

## Source Overview

| Field | Value |
|---|---|
| **Source** | National Crime Records Bureau (NCRB), MHA, Government of India |
| **Dataset** | Crime in India — Annual Statistical Report |
| **Coverage** | All 28 States + 8 Union Territories |
| **Geographic Levels** | National, State/UT, District (~780 districts), Metropolitan Cities (34) |
| **Years in v1** | 2021, 2022, 2023 |
| **Formats** | Excel (.xlsx) via Additional Tables + PDF (main report) |
| **License** | Public government data (open access, attribution required) |

---

## Access Methods

### Method 1 — Additional Tables (Primary for v1)

**URL Pattern:** `https://www.ncrb.gov.in/crime-in-india-additional-table?year={year}&category=`

Available years: 2019, 2020, 2021, 2022, 2023 (verify 2019/2020 availability before parsing)

Files are downloadable Excel (.xlsx) files organized into sections on the page:
- States/UTs section
- District Wise Reports section
- Metropolitan Cities section

**Note:** This page is not prominently linked from the NCRB homepage. It is a discovery finding from Stage 1 exploration.

### Method 2 — Main PDF Report (Future v2 expansion)

**URL:** `https://ncrb.gov.in/crime-in-india.html`

Annual multivolume PDF. 400-600 pages. Contains additional tables not in the structured files (victim profiles, motive analysis, monthly distribution). See `examination-notes/pdf-gap-analysis.md` for full gap inventory.

---

## v1 File Inventory — States/UTs (Priority 1)

All 12 files are identical in structure across each year. Columns: 4-5 for simple category files, 38-114 for disposal/detailed files.

| File # | File Description | Cols | Years |
|---|---|---|---|
| 001 | State/UT-wise Cases Registered IPC | 5 | 2021, 2022, 2023 |
| 002 | State/UT-wise Cases Registered SLL | 5 | 2021, 2022, 2023 |
| 003 | State/UT-wise Cases against Women | 5 | 2021, 2022, 2023 |  
| 004 | State/UT-wise Cases against Children | 5 | 2021, 2022, 2023 |
| 005 | State/UT-wise Cases against SCs | 5 | 2021, 2022, 2023 |
| 006 | State/UT-wise Cases against STs | 5 | 2021, 2022, 2023 |
| 007 | State/UT-wise Cases against Senior Citizens | 5 | 2021, 2022, 2023 |
| 008 | Crimehead-wise IPC and SLL (national) | 5 | 2021, 2022, 2023 |
| 028 | State/UT Persons Disposal IPC | 114 | 2021, 2022, 2023 |
| 041 | State/UT Persons Disposal Cyber | 114 | 2021, 2022, 2023 |
| 046 | State/UT Property Stolen & Recovered | 38 | 2021, 2022, 2023 |
| 049 | State/UT Seizures NDPS Act | 77 | 2021, 2022, 2023 |

**Row count per year:** ~42 rows (36 states/UTs + header rows + total rows)

---

## v1 File Inventory — Districts (Priority 2)

All 10 files per year. ~1050-1080 rows per file (one row per district).

| File # | Description | Cols | Row Count (2023) |
|---|---|---|---|
| 1 | Districtwise IPC Crimes | 144 | ~1081 |
| 2 | Districtwise SLL Crimes | 93 | ~1079 |
| 3 | Districtwise Crime against Women | 54 | ~1079 |
| 4 | Districtwise Crime against Children | 71 | ~1079 |
| 5 | Districtwise Crime against SCs | 51 | ~1079 |
| 6 | Districtwise Crime against STs | 51 | ~1079 |
| 7 | Districtwise IPC Crime by Juveniles | 144 | ~1081 |
| 8 | Districtwise SLL Crime by Juveniles | 92 | ~1079 |
| 9 | Districtwise Cyber Crimes | 51 | ~1080 |
| 10 | Districtwise Missing Persons | 26 | ~1079 |

---

## v1 File Inventory — Metro Cities (Priority 3)

3 files processed per year across 2021-2023. All extracted to unified JSON format.

| Category | Source Format | Parsed JSON File | Records |
|---|---|---|---|
| IPC Crimes City-wise | PDF (22/23), XLSX (21) | `{year}_ipc.json` | 34 |
| SLL Crimes City-wise | PDF (22/23), XLSX (21) | `{year}_sll.json` | 34 |
| Total IPC & SLL Crimes | PDF (22/23), XLSX (21) | `{year}_total.json` | 34 |

Location: `data/structured/metro-cities/`


---

## File Format Findings

**File extension:** All structured files are .xlsx (Excel 2010+ format). Compatible with pandas + openpyxl.

**Header structure:** Single header row at row 0 (no hidden title rows above). `skiprows=0` works for all files tested.

**Data types:** Numbers are stored as actual numeric types (not text) in 2022 and 2023 files. Some 2021 files may contain text-stored numbers — verify during parsing.

**Skip rows needed:** 0 (no skiprows parameter required).

**Null representations:** 
- Empty cells → `None`
- `-` (dash) found in some files → treat as `None`
- `0` in some contexts may mean missing rather than zero — verify per crime category

**Summary rows:** Files contain an `All India` total row at the bottom of data rows. District files contain state subtotal rows interspersed. Parser must identify and exclude these from data rows.

**Footnotes:** Found in NDPS Act file (2021). Footnote text appears in a cell below the data table. Parser should strip rows below the state data block.

---

## Known Data Quality Issues

### Q1 — Nagaland `#` Marker (2022)
State name appears as `Nagaland #` in 2022 files. The `#` indicates revised data. Canonical mapping strips the `#`. Original anomaly should be logged.

### Q2 — Timestamp Prefixes in 2021 Filenames
All 2021 files have 10-digit Unix timestamp prefixes (e.g., `1673006901_001StateUT...`). This is a download artifact from the older NCRB website. File contents are identical in structure. Parser must handle both naming conventions.

### Q3 — D&N Haveli and Daman & Diu Merger
This UT was formed in 2020 by merging two separate UTs. Files from 2020 onwards show the merged UT. Files from 2019 and earlier show separate entries. Cross-year queries must account for this.

### Q4 — Timestamp Prefix District Files (2021 and 2022)
District files for 2021 and 2022 also have timestamp prefixes in filenames. 2023 district files use simple numeric prefixes (1, 2, 3...). File contents are structurally equivalent.

### Q5 — Category Name Inconsistency Risk
Crime category names in Crimehead-wise files may use slightly different spellings across years. Example: `Cyber Crime` vs `Cyber Crimes`. Parser must normalize category names through the canonical-mappings system.

---

## Parsed File Counts (Automated Test Results)
From `examination-notes/parse-test-results.md`:

- **2021 files:** 12 states-uts + 10 districts = 22 files | All parsed OK
- **2022 files:** 12 states-uts + 10 districts = 22 files | All parsed OK
- **2023 files:** 12 states-uts + 10 districts = 22 files | All parsed OK
- **Total:** 66 files | 66 OK | 0 Failed

---

## URL Patterns

```
Additional Tables (by year):
https://www.ncrb.gov.in/crime-in-india-additional-table?year=2023&category=
https://www.ncrb.gov.in/crime-in-india-additional-table?year=2022&category=
https://www.ncrb.gov.in/crime-in-india-additional-table?year=2021&category=

Main PDF Report:
https://ncrb.gov.in/crime-in-india.html

NCRB Homepage:
https://www.ncrb.gov.in/
```

---

## State/UT Name Normalization

All state/UT names are normalized through `data/canonical-mappings/states.json`. 
Full variation list is in `examination-notes/state-name-variations.md`.

Key variations to handle:
- `State: Andhra Pradesh` (district files prefix) → `Andhra Pradesh`
- `Nagaland #` (2022 revised marker) → `Nagaland`
- `D&N Haveli and Daman & Diu` → canonical: `D&N Haveli and Daman & Diu`
- `J&K` / `Jammu and Kashmir` → `Jammu & Kashmir`
- `NCT of Delhi` / `Delhi UT` → `Delhi`

---

## Confidence Score Policy

| Source | Confidence Score | Reason |
|---|---|---|
| Additional Tables .xlsx | 0.95 | Direct structured export from NCRB |
| PDF extracted (future) | 0.70 | Parsing uncertainty |
| Cross-validated (xlsx vs PDF match) | 0.99 | Dual-source confirmation |

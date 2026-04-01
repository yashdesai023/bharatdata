# PDF Gap Analysis — NCRB Crime in India vs Additional Tables

> Step 9 of Stage 1 | 2026-03-20

## Overview

NCRB publishes data in two distinct forms:

1. **Additional Tables** — Downloadable structured Excel files at `https://www.ncrb.gov.in/crime-in-india-additional-table?year={year}&category=`
2. **Main Report PDF** — The "Crime in India" annual report, a 400+ page PDF at `https://ncrb.gov.in/crime-in-india.html`

BharatData v1 is built on the Additional Tables. This document defines what the PDF contains that the structured files do not, establishing the scope for future PDF parser work.

---

## What the Structured Files Cover (v1 Baseline)

| Category | Available in Structured Files |
|---|---|
| State/UT-wise total IPC crimes | YES |
| State/UT-wise SLL crimes | YES |
| State/UT-wise Crimes against Women | YES |
| State/UT-wise Crimes against Children | YES |
| State/UT-wise Crimes against SCs | YES |
| State/UT-wise Crimes against STs | YES |
| State/UT-wise Crimes against Senior Citizens | YES |
| Crimehead-wise IPC & SLL breakdown (national) | YES |
| State/UT Persons Disposal (IPC) | YES |
| State/UT Persons Disposal (Cyber) | YES |
| State/UT Property Stolen & Recovered | YES |
| State/UT Seizures under NDPS Act | YES |
| District-wise IPC, SLL, Women, Children, SCs, STs | YES |
| District-wise Cyber crimes, Missing Persons | YES |
| District-wise Juveniles (IPC + SLL) | YES |

---

## What Is ONLY in the PDF (v2 Parser Scope)

These are the data types available in the Crime in India PDF report but NOT exported as structured Additional Tables files.

### A — Victim Profile Data
- Age-wise breakdown of victims for each crime category
- Gender distribution of victims
- Relationship of offender to victim (e.g., known person, family member, stranger)
- Victim occupation and social status

**Why it matters:** Essential for social science research and policy analysis. Cannot be reconstructed from aggregate data.

### B — Temporal / Monthly Distribution
- Month-wise distribution of crime incidents
- Seasonal crime patterns
- Year-on-year change analysis within the PDF narrative

**Why it matters:** Researchers and journalists need monthly crime trends. Only available in PDF tables.

### C — Detailed Disposal Breakdowns by Crime Sub-Category
- State-wise disposal pipeline broken down by individual crime type (not just aggregate IPC/SLL)
- Conviction rates for specific crimes (murder, rape, robbery separately)
- Cases pending investigation by crime type at state level

**Why it matters:** Legal researchers and policy analysts need crime-specific conviction data.

### D — Motive and Cause Analysis
- Motive analysis for specific crimes (e.g., murder — motives: property dispute, personal enmity, etc.)
- Cause analysis for accidents and negligence-related crimes

**Why it matters:** Criminology research requires causal breakdowns, not just counts.

### E — Comparative Analysis Tables
- Multi-year comparison tables (5+ years) for select crime categories at national level
- Crime rate per lakh population calculations built into PDF tables
- State ranking tables for crime incidence

**Why it matters:** The PDF's pre-computed rates are used by journalists directly. We need to compute these ourselves from the structured data, which we can do — but the PDF tables reveal the denominator populations NCRB uses.

### F — Specific Sub-Category Crime Tables Not in Additional Tables
- Robbery breakdown by method (armed/unarmed)
- Cheating breakdown by mode (online/offline)
- Counterfeiting/forgery by document type
- Kidnapping & Abduction breakdown by motive and age of victim

**Why it matters:** These granular sub-category breakdowns appear in PDF chapter tables but are not exported as Additional Table files.

### G — Narrative Context and Footnotes
- Chapter-level analysis and commentary by NCRB
- Definitional notes for crime categories under IPC
- Footnotes explaining state-specific reporting anomalies

**Why it matters:** The footnotes are critical for data quality understanding. For example, the `#` marker on Nagaland in 2022 (which we found in the data) is explained only in the PDF footnote.

---

## Priority for PDF Parsing (Future Phase)

| Priority | Data | Reason |
|---|---|---|
| P1 | Victim age & gender profiles | Highest user demand from researchers |
| P2 | Crime-specific disposal rates | Policy research requirement |
| P1 | Monthly distribution tables | Journalist use case |
| P2 | Motive analysis tables | Criminology research |
| P3 | Narrative footnotes | Data quality context |

---

## Implication for v1

BharatData v1 built on structured files is fully functional for:
- Total crime counts by state, district, city
- Crime category comparisons
- 3-year trend analysis
- Cross-category analysis (IPC vs SLL vs Women vs Children)
- Property and drug crime analysis

The PDF parser addresses gaps B, D, and F above (victim profiles, temporal distribution, motive analysis) and can be built as a v2 feature once v1 is shipping and users have validated the data quality.

---

## Technical Notes for PDF Parser (Future)

- The main Crime in India PDF is a multi-chapter document with 400-600 pages
- Each chapter corresponds to a crime category
- Tables within chapters are numbered sequentially (Table 1.1, Table 1.2, etc.)
- Most tables are 2-5 column-wide with merged header cells
- Tool recommendation: `pdfplumber` for structured table extraction; fallback to `tabula-py`
- Key challenge: page headers and footers intrude into extracted text
- Confidence score for PDF-extracted data should start at 0.70 (vs 0.95 for structured files)

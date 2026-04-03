<div align="center">
  <img src="../../Docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>BharatData for Researchers</h1>
  <em>Pandas, Jupyter, and programmatic access to Indian government statistics.</em>
</div>

---

## Overview

This guide is for researchers, data scientists, economists, and academics who want to integrate Indian government statistics into quantitative workflows using Python.

BharatData provides:
- A **Python SDK** (`bharatdata`) that returns `pandas.DataFrame` objects natively
- A **REST API** for language-agnostic access
- A **TypeScript SDK** for Node.js and browser environments

---

## Installation

```bash
pip install bharatdata
```

For Conda environments:
```bash
conda install -c conda-forge bharatdata
```

Minimum Python version: **3.9**

---

## Quick Start: Jupyter Notebook

```python
import bharatdata as bd
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- 1. Discover Available Datasets ---
datasets = bd.list_datasets()
print(datasets[['id', 'name', 'temporalCoverage', 'geographicCoverage']])
```

```
              id                        name temporalCoverage geographicCoverage
0      ncrb-crime  NCRB Crime Statistics        2001-2023           district
```

---

## Core Methods

### `bd.list_datasets()`
Returns a `DataFrame` of all registered datasets.

```python
datasets = bd.list_datasets()
# Returns: pd.DataFrame with columns [id, name, publishingBody, description, ...]
```

---

### `bd.query(dataset_id, level, filters, limit, sort, order)`

The primary data retrieval method. Returns a `pandas.DataFrame`.

```python
# State-level crime data for all of Maharashtra
df = bd.query(
    "ncrb-crime",
    level="district",
    filters={
        "entity": "Maharashtra",
        "year": "2023"
    },
    limit=500
)
print(df.shape)      # (287, 8)
print(df.dtypes)
print(df.head())
```

**Parameters:**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `dataset_id` | `str` | Dataset ID from `bd.list_datasets()` |
| `level` | `str` | Geographic level: `"district"`, `"state"`, `"national"` |
| `filters` | `dict` | Key-value filter pairs (entity, year, category, etc.) |
| `limit` | `int` | Max rows to return (default: 100, max: 500) |
| `sort` | `str` | Column to sort by |
| `order` | `str` | `"asc"` or `"desc"` (default: `"desc"`) |

---

### `bd.query_ai(prompt)`

Runs an AI-powered analysis and returns the narrative and underlying data.

```python
result = bd.query_ai("Compare cybercrime rates across all Indian states in 2023")

print(result['narrative'])  # AI-generated analysis text
print(result['data'])       # pd.DataFrame of underlying records
print(result['queryPlan'])  # Dict describing what the AI searched for
```

---

## Research Workflows

### Workflow 1: Year-over-Year Trend Analysis

```python
import bharatdata as bd
import matplotlib.pyplot as plt

# Fetch 5-year trend for Maharashtra
df = bd.query(
    "ncrb-crime",
    level="state",
    filters={
        "entity": "Maharashtra",
        "year": "2019,2020,2021,2022,2023"
    },
    sort="year",
    order="asc"
)

# Aggregate IPC totals by year
annual = df.groupby('year')['total_cases'].sum().reset_index()

# Plot
plt.figure(figsize=(10, 6))
plt.plot(annual['year'], annual['total_cases'], marker='o', linewidth=2, color='#1A237E')
plt.title("Total IPC Cases in Maharashtra (2019–2023)", fontsize=14)
plt.xlabel("Year")
plt.ylabel("Total Cases")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("maharashtra_crime_trend.png", dpi=300)
plt.show()
```

---

### Workflow 2: State-Level Comparison (Cross-Sectional)

```python
import bharatdata as bd
import seaborn as sns

# All-India state comparison for 2023
df = bd.query(
    "ncrb-crime",
    level="state",
    filters={"year": "2023"},
    limit=500
)

# Pivot: Group by state, sum total cases
state_totals = (
    df.groupby('state')['total_cases']
    .sum()
    .sort_values(ascending=False)
    .reset_index()
    .head(15)
)

# Horizontal bar chart
plt.figure(figsize=(12, 8))
sns.barplot(data=state_totals, x='total_cases', y='state', palette='Blues_r')
plt.title("Top 15 States by Total IPC Cases (2023)", fontsize=14)
plt.xlabel("Total Cases")
plt.ylabel("")
plt.tight_layout()
plt.show()
```

---

### Workflow 3: District-Level Analysis

```python
# District analysis within a state
district_df = bd.query(
    "ncrb-crime",
    level="district",
    filters={
        "entity": "Uttar Pradesh",
        "year": "2023"
    },
    sort="total_cases",
    order="desc",
    limit=500
)

# Top 10 districts by crime
top_10 = district_df.nlargest(10, 'total_cases')[['district', 'total_cases', 'category_label']]
print(top_10.to_markdown(index=False))
```

---

### Workflow 4: Panel Data for Regression Analysis

```python
import bharatdata as bd
import pandas as pd

# Build a panel dataset: all available years, all states
years = [str(y) for y in range(2015, 2024)]
dfs = []

for year in years:
    df = bd.query(
        "ncrb-crime",
        level="state",
        filters={"year": year},
        limit=500
    )
    dfs.append(df)

panel = pd.concat(dfs, ignore_index=True)
panel['year'] = panel['year'].astype(int)

# Now use for fixed-effects regression (e.g., with linearmodels or statsmodels)
print(panel.shape)
print(panel.groupby('year')['total_cases'].sum())
```

---

### Workflow 5: Merging with External Data

```python
import bharatdata as bd
import pandas as pd

# BharatData: state-level crime
crime_df = bd.query(
    "ncrb-crime",
    level="state",
    filters={"year": "2023"},
    limit=500
)

# External: your own state-level population data
pop_df = pd.read_csv("state_population_2023.csv")  # columns: state, population

# Merge on normalized state name
crime_totals = crime_df.groupby('state')['total_cases'].sum().reset_index()
merged = crime_totals.merge(pop_df, on='state', how='inner')
merged['crime_rate_per_lakh'] = (merged['total_cases'] / merged['population']) * 100_000

print(merged.sort_values('crime_rate_per_lakh', ascending=False).head(10))
```

> **Note on State Name Normalization:** BharatData uses a canonical state name list. Your external data must match this list. See the [states reference](../../packages/typescript-sdk/src/) or call `bd.list_states()`.

---

## Academic Citation

When publishing research that uses BharatData, cite both the original source and the access platform:

**APA 7:**
```
National Crime Records Bureau. (2023). Crime in India: 2023 [Data set].
Ministry of Home Affairs, Government of India. Data normalized and
accessed via BharatData (https://bharatdata.dev).
```

For formal methodology sections, see [ATTRIBUTION.md](../legal/ATTRIBUTION.md).

---

## Data Quality Notes for Researchers

| Issue | BharatData Approach |
| :--- | :--- |
| **Administrative boundary changes** | We maintain year-specific district lists. Some districts changed boundaries between 2001 and 2023 — time-series analyses should account for this |
| **Missing data** | Some districts in some years have no filed report. These appear as null values, not as zero |
| **Reporting bias** | NCRB data reflects only crimes registered with police. Under-reporting is a known methodological concern in criminology literature |
| **Category changes** | IPC crime categories have been amended over the years. Some categories are not comparable across all years |
| **Confidence scores** | Records below 0.7 confidence involve complex PDF extraction — validate against source before using in published work |

---

## Python SDK Reference

```python
import bharatdata as bd

# Dataset discovery
bd.list_datasets()              # -> pd.DataFrame
bd.get_dataset_metadata(id)     # -> dict

# Data access
bd.query(id, level, filters, limit, sort, order)    # -> pd.DataFrame
bd.query_ai(prompt)                                  # -> dict {narrative, data, queryPlan}

# Metadata helpers
bd.list_states()                # -> list[str]
bd.list_years(dataset_id)       # -> list[int]
bd.list_fields(dataset_id)      # -> list[str]
```

---

## PDF Export for Academic Submission

To convert this guide or your research notes into a professional PDF:

### Using Pandoc (Recommended)

```bash
# Install Pandoc: https://pandoc.org/installing.html
pandoc RESEARCHER_GUIDE.md \
  -o RESEARCHER_GUIDE.pdf \
  --pdf-engine=xelatex \
  --toc \
  --toc-depth=3 \
  --variable margin-top=30mm \
  --variable margin-bottom=25mm \
  --variable margin-left=25mm \
  --variable margin-right=25mm \
  --variable fontsize=12pt
```

### Using VS Code

1. Install the **"Markdown PDF"** extension by yzane
2. Right-click any `.md` file → **"Markdown PDF: Export (pdf)"**
3. For custom styling, create a `markdown-pdf.css` file in the project root:
```css
body { font-family: 'Inter', sans-serif; color: #1a1a1a; }
h1 { color: #1A237E; border-bottom: 2px solid #1A237E; }
table { border-collapse: collapse; width: 100%; }
th { background: #f0f4ff; color: #1A237E; }
code { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
```

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body &nbsp;|&nbsp; For research support: research@bharatdata.dev</sub>
</div>

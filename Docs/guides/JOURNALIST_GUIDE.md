<div align="center">
  <img src="../../Docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>BharatData for Researchers</h1>
  <em>Pandas, Jupyter, and programmatic access to Indian government statistics.</em>
</div>

---

## Who This Guide Is For

This guide is for reporters, editors, and fact-checkers who want to use BharatData to support their journalism. You do not need to know how to code. You do not need to understand APIs.

What you need: a web browser and a question.

---

## What BharatData Can Do For You

| Task | How BharatData Helps |
| :--- | :--- |
| Understand crime trends in your city or state | Ask a plain-English question and get an analysis with data |
| Compare statistics across states | The AI engine handles multi-state comparisons automatically |
| Find the official government source for a statistic | Every result links back to the official NCRB publication |
| Download raw data for your own analysis | One-click CSV export for any query result |
| Generate a shareable summary of findings | "Generate Scholarly Report" exports a full text analysis |

---

## Quick Start: Your First Query

### Step 1: Open the Playground

Go to: **https://bharatdata.dev**

You will see a search bar in the center of the page.

### Step 2: Ask Your Question

Type a question naturally, just as you would ask a colleague:

```
Examples:
- "What was the murder rate in Delhi in 2023?"
- "Which state had the most cybercrime cases in 2022?"
- "How did crimes against women change in Maharashtra from 2019 to 2023?"
- "Show me district-wise theft data for Rajasthan in 2023"
```

Press **Enter** or click **Ask Bharat Data**.

### Step 3: Read the Analysis

BharatData will:
1. **Identify the relevant dataset** automatically (e.g., NCRB Crime Statistics)
2. **Fetch the data** from its database
3. **Write an analysis** in plain English that interprets the numbers for you
4. **Display a chart or map** so you can see patterns visually

### Step 4: Verify the Source

At the bottom of every analysis, click **"Verify Source"**. This opens the official government portal (e.g., NCRB's website) where the same figures are published. This is your verification step.

### Step 5: Download the Data

Click **"Download raw records (CSV)"** to download the complete dataset for your query as a spreadsheet. Open it in Excel or Google Sheets for further analysis.

---

## Asking Better Questions

The more specific your question, the more precise the answer.

| Less Effective | More Effective |
| :--- | :--- |
| "Crime data" | "Total cognizable crimes in Gujarat in 2023" |
| "Cybercrime" | "Cybercrime cases across Indian states from 2019 to 2023" |
| "Women safety" | "Crimes against women in Uttar Pradesh districts in 2022" |

### Supported Dimensions

You can filter by **any combination** of:
- **State or District**: "Maharashtra", "Pune district", "North East Delhi"
- **Year or Year Range**: "2023", "2019 to 2023", "the last 5 years"
- **Crime Category**: "murder", "rape", "cybercrime", "theft", "dowry deaths", "kidnapping"

---

## Understanding the Results

### The Narrative Analysis

The text analysis you see is AI-generated based on the actual data. It is a starting point for your story, not a finished quote. Always:

- Verify the specific numbers against the original source
- Cross-reference with local knowledge and expert sources
- Use the BharatData citation when publishing (see citation formats below)
- Do not publish AI-generated text as a news article without human editorial review

### The Confidence Score

Each data record has a `confidence` field. This reflects how cleanly the data was extracted from the original PDF report:

| Confidence | What It Means |
| :--- | :--- |
| `0.9 - 1.0` | Directly extracted, high quality |
| `0.7 - 0.9` | Minor normalization applied (e.g., district name standardized) |
| `< 0.7` | Complex extraction — **always verify against original source** |

### The Map View

When BharatData detects a state-level query, it automatically shows a **choropleth map of India** where darker colors indicate higher values. Click the **"Geo Intelligence"** tab at the top of the data section. Hover over any state to see the exact figure.

---

## How to Cite BharatData in Your Story

**In-text citation (news article):**
> According to data from the National Crime Records Bureau, accessed via BharatData (bharatdata.dev)...

**Data note at the end of a story:**
> **Data Sources:** Crime statistics from the National Crime Records Bureau. (2023). Crime in India: 2023 [Data set].
Ministry of Home Affairs, Government of India. Data normalized and
accessed via BharatData (https://bharatdata.dev). The platform does not modify any numerical values from original government publications.

**For research pieces with a methodology section:**
See [ATTRIBUTION.md](../legal/ATTRIBUTION.md) for formal citation formats (APA, Chicago, etc.)

---

## Checking Data Yourself (For Fact-Checkers)

If you want to verify a number that BharatData showed you:

1. Note the **dataset ID** shown in the analysis footer (e.g., `ncrb-crime`)
2. Click **"Verify Source"** — this opens the official government portal
3. On the NCRB website: go to "Crime in India" → Select the relevant year → Download the PDF or XLSX
4. Find the state/district table and confirm the figure

BharatData's normalization only standardizes administrative names and formats. It **does not change any numerical figure** from the original government report.

---

## Common Story Types and Suggested Queries

### Crime Trend Stories

```
"How has murder changed in [State] over the last 5 years?"
"Which districts in [State] have the highest crime rates in 2023?"
"Has cybercrime increased year over year across India?"
```

### Comparative Stories

```
"Compare crimes against women across all Indian states in 2022"
"Which 5 states have the highest and lowest overall crime rates in 2023?"
"How does [State] compare to the national average for theft?"
```

### Investigative Deep-Dives

```
"Show me all crime categories in [District] from 2018 to 2023"
"What are the most common crimes in [City]?"
"Compare district-level data within [State] for dowry deaths"
```

---

## Limitations to Know

| Limitation | What This Means for Your Story |
| :--- | :--- |
| **Data is from NCRB only (currently)** | Covers all major IPC crimes; economic statistics (RBI) coming soon |
| **Data is reported crime** | NCRB captures only crimes that were filed with police — actual crime rates may differ |
| **Data reflects publication schedule** | 2023 data became available in late 2024/2025. Very recent data may not be available yet |
| **District boundaries change** | New districts carved from old ones may affect year-over-year comparisons |
| **AI narratives can have errors** | Always verify numbers against the original source before publishing |

---

## Getting Help

If you cannot find the data you are looking for, or you encounter an error:

1. Try rephrasing your question (more specific is usually better)
2. Check the **Data Coverage** section at the top of the playground
3. Open a [GitHub Issue](https://github.com/bharatdata/bharatdata/issues) describing what you were looking for

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body &nbsp;|&nbsp; For research support: research@bharatdata.dev</sub>
</div>

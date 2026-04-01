<div align="center">
  <img src="../../docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>Data Attribution</h1>
  <em>Official source citations for all datasets served by BharatData.</em>
</div>

---

## Important Notice

**BharatData does not collect, generate, or own any of the underlying statistical data we serve.** We are a normalization and access layer. All data originates from official Government of India publications and is redistributed in a machine-readable format under the terms of the respective government open data policies.

When using BharatData in research, journalism, or any published work, you are **required** to cite both the original government source and the BharatData platform (see attribution formats below).

---

## Currently Served Datasets

### 1. NCRB Crime Statistics

| Field | Details |
| :--- | :--- |
| **Full Name** | Crime in India — State/UT-wise and District-wise Statistics |
| **Publishing Body** | National Crime Records Bureau (NCRB) |
| **Parent Ministry** | Ministry of Home Affairs, Government of India |
| **Source URL** | [https://ncrb.gov.in/en/crime-in-india](https://ncrb.gov.in/en/crime-in-india) |
| **Dataset ID on BharatData** | `ncrb-crime` |
| **Years Available** | 2001 – 2023 |
| **Granularity** | National → State → District |
| **Update Frequency** | Annual (published approximately 12–18 months after the reference year) |
| **License** | Government of India Open Data License 1.0 |
| **Original Format** | PDF / XLSX tables within annual "Crime in India" volumes |

**What we normalize:**
- Inconsistent district names across years (e.g., "Bangalore" vs "Bengaluru" vs "Bengaluru Urban")
- Administrative reorganization (new districts carved from old ones)
- Column header changes across annual report editions
- Encoding inconsistencies in XLSX files

**What we do NOT modify:**
- Any numerical figure (total cases, sub-category breakdowns, rates)
- The year of publication or the reference year
- The state-district administrative hierarchy as published by NCRB

---

## Upcoming Datasets (In Pipeline)

### 2. RBI Economic & Banking Statistics *(Planned)*

| Field | Details |
| :--- | :--- |
| **Publishing Body** | Reserve Bank of India (RBI) |
| **Source URL** | [https://dbie.rbi.org.in/](https://dbie.rbi.org.in/) |
| **Planned Dataset IDs** | `rbi-banking-state`, `rbi-gdp-state` |
| **Years Expected** | 2000 – 2024 |
| **Granularity** | State |
| **Status** | 🔄 In design |

---

### 3. Census of India — Demographic Statistics *(Planned)*

| Field | Details |
| :--- | :--- |
| **Publishing Body** | Office of the Registrar General & Census Commissioner |
| **Source URL** | [https://censusindia.gov.in/](https://censusindia.gov.in/) |
| **Planned Dataset IDs** | `census-2011-district`, `census-2011-state` |
| **Years Expected** | 2011 (primary), 2001 (historical) |
| **Granularity** | District & Sub-district |
| **Status** | 🔄 In design |

---

### 4. National Sample Survey (NSS) — Employment Data *(Planned)*

| Field | Details |
| :--- | :--- |
| **Publishing Body** | National Statistical Office (NSO), Ministry of Statistics |
| **Source URL** | [https://mospi.gov.in/](https://mospi.gov.in/) |
| **Planned Dataset IDs** | `nso-employment-state` |
| **Status** | 📋 Backlog |

---

## Mandatory Citation Formats

Use **one of the following formats** depending on your publication type:

### For Journalism and News Articles

```
Data: National Crime Records Bureau, Ministry of Home Affairs, Government of India.
Accessed via BharatData (bharatdata.org). Retrieved [Month Year].
```

### For Academic Publications

APA 7th Edition:
```
National Crime Records Bureau. (2023). Crime in India: 2023 [Data set].
Ministry of Home Affairs, Government of India. Accessed via BharatData.
https://bharatdata.org
```

Chicago Author-Date:
```
National Crime Records Bureau. 2023. "Crime in India." Ministry of Home Affairs,
Government of India. Accessed via BharatData (bharatdata.org).
```

### For Technical Reports and Policy Briefs

```
Source: National Crime Records Bureau (NCRB), Ministry of Home Affairs,
Government of India. Data normalized and accessed via BharatData API
(api.bharatdata.org, Dataset ID: ncrb-crime). Data reflects published figures
as of [Report Year]. No modification to numerical values.
```

### For Code Documentation & API Integrations

```typescript
// Data source: NCRB Crime in India
// Published by: Ministry of Home Affairs, Government of India
// Accessed via: BharatData API (api.bharatdata.org)
// Attribution: See https://bharatdata.org/docs/legal/attribution
```

---

## Verifying Data Against Original Sources

Each BharatData API response includes a `sourceUrl` field in the dataset metadata that points directly to the official government portal. You can also use the **"Verify Source"** button in the BharatData Playground, which opens the corresponding government portal in a new tab.

To manually verify a specific figure:
1. Call `GET /v1/registry/ncrb-crime` to retrieve the `sourceUrl`
2. Visit the NCRB portal at [https://ncrb.gov.in/en/crime-in-india](https://ncrb.gov.in/en/crime-in-india)
3. Download the relevant annual volume (e.g., "Crime in India 2023")
4. Locate the figure in the corresponding table

If you discover a discrepancy between BharatData's figures and the original government publication, please open a GitHub issue immediately.

---

## Government Open Data License

The Government of India operates under the [National Data Sharing and Accessibility Policy (NDSAP)](https://data.gov.in/sites/default/files/NDSAP.pdf). Most datasets published by GOI bodies are made available under the **Government Open Data License — India (GODL-India)**, which permits:

- ✅ Free use, reuse, and redistribution
- ✅ Translation and adaptation
- ✅ Commercial use

Subject to the condition that the source is attributed clearly in any derived work.

BharatData operates in full compliance with GODL-India terms.

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body &nbsp;|&nbsp; Last updated: April 1, 2026</sub>
</div>

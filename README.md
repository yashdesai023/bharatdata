<div align="center">
  <img src="docs/assets/logo_full.png" alt="BharatData" height="90" />
  <br/><br/>
  <strong>India's Open Public Data Infrastructure</strong>
  <br/>
  <em>Clean, queryable, and trusted government statistics for everyone.</em>
  <br/><br/>

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![API Status](https://img.shields.io/badge/API-Operational-brightgreen)](https://api.bharatdata.org/health)
  [![Data Source](https://img.shields.io/badge/Source-NCRB%20%7C%20GOI-orange)](https://ncrb.gov.in)
  [![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red)](CONTRIBUTING.md)

</div>

---

## What is BharatData?

BharatData is an independent open-source initiative that eliminates the **data access tax** paid by every developer, researcher, journalist, and student who needs to work with Indian government statistics.

Every fintech building credit models, every journalist investigating crime trends, every academic studying demographic shifts—they all spend weeks downloading PDFs, normalizing administrative names, and building fragile scrapers before writing a single line of their actual product.

**BharatData solves this at the infrastructure level.** We collect, normalize, and serve verified Indian public data through a single, consistent API.

---

## Core Features

| Feature | Description |
| :--- | :--- |
| 🔍 **AI Query Engine** | Ask questions in plain English about Indian government data |
| 📊 **Universal API** | One consistent endpoint for all datasets (`/v1/data/:dataset`) |
| 🗺️ **Geo Intelligence** | Built-in choropleth maps for state and district-level visualization |
| 📡 **TypeScript SDK** | Type-safe client for Node.js, browsers, and edge environments |
| 🐍 **Python SDK** | Pandas-native client built for data science workflows |
| 📥 **CSV Export** | One-click export of any query result for offline analysis |
| 🏛️ **Source Attribution** | Every data point traces back to its official government source |

---

## Packages

This monorepo contains the following production components:

```
bharatdata/
├── packages/
│   ├── api/               # Core Cloudflare Workers API (Hono)
│   ├── typescript-sdk/    # Official TypeScript/JavaScript client
│   ├── python-sdk/        # Official Python client (Pandas integration)
│   ├── playground/        # Next.js interactive data playground
│   └── shared/            # Shared types and constants
├── pipeline/              # Data ingestion and normalization scripts
├── Docs/                  # Full documentation suite
└── sources/               # Raw government data archives
```

---

## Quick Start

### Using the Playground (No Code Required)
Visit the live playground and ask any question about Indian government data:

```
https://bharatdata.org
```

### TypeScript SDK

```bash
npm install @bharatdata/typescript-sdk
```

```typescript
import { BharatData } from '@bharatdata/typescript-sdk';

const bd = new BharatData();

// AI-powered query — ask in plain English
for await (const event of bd.queryAI('Crime trends in Maharashtra 2021-2023')) {
  if (event.type === 'initial') {
    console.log(`Found ${event.count} records`);
    console.table(event.data);
  }
  if (event.type === 'delta') {
    process.stdout.write(event.content);
  }
}

// Direct structured query
const data = await bd.query('ncrb-crime', 'state', {
  entity: 'Maharashtra',
  year: '2023',
  limit: '50',
});
```

### Python SDK

```bash
pip install bharatdata
```

```python
import bharatdata as bd

# Discover all available datasets
datasets = bd.list_datasets()

# Query directly into a Pandas DataFrame
df = bd.query("ncrb-crime", level="district", filters={
    "entity": "Maharashtra",
    "year": "2023"
})
print(df.describe())

# AI-powered narrative analysis
report = bd.query_ai("Compare cyber crime across top 5 Indian states in 2023")
print(report['narrative'])
```

---

## API Reference

Base URL: `https://api.bharatdata.org`

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | System health, Supabase status, latency |
| `/v1/registry` | `GET` | List all registered datasets |
| `/v1/registry/:id` | `GET` | Full metadata for one dataset |
| `/v1/data/:dataset` | `GET` | Universal data query endpoint |
| `/v1/ai/query` | `POST` | Streaming AI narrative endpoint |
| `/v1/meta/states` | `GET` | List of all Indian states |
| `/v1/meta/years` | `GET` | Available data years |
| `/v1/fallback` | `GET` | Static fallback dataset (always available) |

**Rate Limits (per IP):**
- `10 requests / minute`
- `200 requests / day`

---

## Current Data Coverage

| Dataset | Source | Years Available | Granularity |
| :--- | :--- | :--- | :--- |
| NCRB Crime Statistics | Ministry of Home Affairs | 2021–2023 | State & District |
| *(RBI Economic Data)* | Reserve Bank of India | *Coming soon* | State |
| *(Census Demographics)* | Office of the Registrar General | *Coming soon* | District & Sub-district |

---

## Architecture

```
┌──────────────────────────────────┐
│        BharatData Playground     │  ← Next.js App Router
│         (bharatdata.org)         │
└────────────┬─────────────────────┘
             │ HTTPS
┌────────────▼─────────────────────┐
│        BharatData API            │  ← Cloudflare Workers + Hono
│   (api.bharatdata.org)           │
│                                  │
│  ┌─────────────┐ ┌─────────────┐ │
│  │ Registry    │ │ AI Service  │ │
│  │ (Dataset    │ │ (Gemini     │ │
│  │  Discovery) │ │  Flash)     │ │
│  └──────┬──────┘ └──────┬──────┘ │
│         └───────┬───────┘        │
│  ┌──────────────▼──────────────┐ │
│  │      Query Builder          │ │
│  │  (Universal filter engine)  │ │
│  └──────────────┬──────────────┘ │
└─────────────────┼────────────────┘
                  │ Supabase Client
┌─────────────────▼────────────────┐
│           Supabase               │  ← PostgreSQL (Hosted)
│      (Primary Data Store)        │
└──────────────────────────────────┘
```

---

## Contributing

We welcome contributions of all kinds — new data sources, bug fixes, documentation, and translations. Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

---

## Data Attribution & Legal

All data served by BharatData originates from official Government of India publications. We do not modify, interpolate, or editorialize source data.

- **Data Sources**: See [docs/legal/ATTRIBUTION.md](docs/legal/ATTRIBUTION.md)
- **Terms of Use**: See [docs/legal/TERMS.md](docs/legal/TERMS.md)
- **Privacy Policy**: See [docs/legal/PRIVACY.md](docs/legal/PRIVACY.md)
- **Security Reporting**: See [SECURITY.md](SECURITY.md)

BharatData is an independent project. **We are not affiliated with any government body.**

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for full terms.

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; <a href="docs/legal/ATTRIBUTION.md">Data Attribution</a> &nbsp;|&nbsp; <a href="CONTRIBUTING.md">Contribute</a></sub>
</div>

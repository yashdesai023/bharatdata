<div align="center">
  <img src="docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>Contributing to BharatData</h1>
  <em>Help us build India's open public data infrastructure.</em>
</div>

---

## Welcome

BharatData depends on contributors from every discipline — data engineers who can ingest new government sources, backend developers who can harden the API, frontend contributors who can improve the playground, and documentation writers who make the platform accessible to non-technical users.

Every contribution, no matter how small, directly improves access to public information for millions of Indians.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Types of Contributions](#types-of-contributions)
- [Adding a New Data Source](#adding-a-new-data-source-)
- [Development Workflow](#development-workflow)
- [Testing Standards](#testing-standards)
- [Pull Request Process](#pull-request-process)
- [Commit Message Format](#commit-message-format)

---

## Code of Conduct

We are committed to creating a welcoming, inclusive, and respectful community. All contributors are expected to:

- **Be respectful** of differing viewpoints and experiences
- **Be constructive** — focus on the issue, not the person
- **Be transparent** — disclose conflicts of interest (e.g., government affiliation)
- **Avoid bias** — never manipulate, suppress, or cherry-pick government source data

Violations may result in removal from the project. Report misconduct to: `conduct@bharatdata.org`

---

## Getting Started

### Prerequisites

| Tool | Minimum Version |
| :--- | :--- |
| Node.js | 18.x or later |
| Python | 3.9 or later |
| pnpm | 8.x or later |
| Git | 2.x or later |

### Fork and Clone

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/bharatdata.git
cd bharatdata

# 3. Install all dependencies (monorepo)
pnpm install

# 4. Copy example environment file
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, SARVAM_API_KEY

# 5. Start local development
pnpm dev
```

### Repository Structure

```
bharatdata/
├── packages/
│   ├── api/               # Cloudflare Workers API (Hono)
│   │   ├── src/
│   │   │   ├── index.ts          # Main router, rate limit, CORS
│   │   │   ├── routes/           # data.ts, registry.ts
│   │   │   ├── services/         # ai-service.ts, query-builder.ts
│   │   │   └── registry/         # Dataset registry (source-of-truth)
│   ├── typescript-sdk/    # @bharatdata/typescript-sdk
│   ├── python-sdk/        # bharatdata Python package
│   ├── playground/        # Next.js app (Interactive Playground)
│   └── shared/            # Shared types, constants, state lists
├── pipeline/              # Data ingestion scripts (Python)
├── Docs/                  # Documentation
├── sources/               # Raw government data archives
└── canonical-mappings/    # Administrative name normalization maps
```

---

## Types of Contributions

### 🗄️ Adding New Data Sources
The highest-impact contribution. See the dedicated section below.

### 🐛 Bug Fixes
- Search [existing issues](https://github.com/bharatdata/bharatdata/issues) before filing a new one
- Include steps to reproduce, expected vs. actual behavior, and your environment

### ✨ Feature Requests
- Open a GitHub Discussion before starting work on a large feature
- Features must align with BharatData's core mission: improving access to verifiable Indian public data

### 📚 Documentation
- Improvements to any `.md` file are always welcome
- For guides targeting journalists or researchers, include a practical example from a real-world use case

### 🧪 Tests
- We especially welcome tests for the API routes, SDK methods, and geographic name normalization engine

---

## Adding a New Data Source 🆕

This is the most important contribution you can make. Follow this process precisely:

### Step 1: Verify the Source

Before writing any code, answer these questions:
- Is this data from an **official Government of India body**? (Required)
- Is the data **publicly accessible** without any login or fee? (Required)
- Does the data have a **consistent update schedule**? (Required)
- Are column definitions **documented** in the original report? (Required)

### Step 2: Create a Source Document

Create a new file in `sources/` describing the raw data:

```yaml
# sources/rbi-state-gdp.yaml
name: RBI State-wise GDP Data
publishing_body: Reserve Bank of India
source_url: https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics
update_frequency: Annual
available_years: [2001, 2023]
granularity: [state]
format: XLSX
license: Government Open Data
verified_on: 2026-04-01
```

### Step 3: Write the Ingestion Script

Add a Python script in `pipeline/ingest/`:

```python
# pipeline/ingest/rbi_gdp.py

import pandas as pd
from supabase import create_client

def ingest(supabase_url: str, supabase_key: str):
    # 1. Download source file
    # 2. Normalize column names (snake_case)
    # 3. Normalize state names against canonical-mappings/states.json
    # 4. Validate: no nulls in required fields, years in valid range
    # 5. Upsert into Supabase table
    pass
```

### Step 4: Register the Dataset

Add an entry to the API Registry at `packages/api/src/registry/`:

```typescript
// packages/api/src/registry/rbi-gdp.ts
export const RBI_GDP_DATASET: DatasetDefinition = {
  id: 'rbi-gdp',
  name: 'RBI State-wise GDP Statistics',
  publishingBody: 'Reserve Bank of India',
  description: 'Annual state-wise Gross Domestic Product data from RBI',
  geographicCoverage: 'state',
  temporalCoverage: '2001-2023',
  updateFrequency: 'annual',
  tableName: 'rbi_gdp_state',
  availableFields: ['state', 'year', 'gdp_current_prices', 'gdp_constant_prices', 'growth_rate'],
  conceptMapping: { entity: 'state', year: 'year', value: 'gdp_current_prices' },
  sourceUrl: 'https://dbie.rbi.org.in/'
};
```

### Step 5: Open a Pull Request

Your PR description must include:
- Link to the original government source URL
- Screenshot of the raw data format
- Output of your ingestion test (`pnpm test:pipeline`)
- A sample `curl` query demonstrating the new dataset endpoint

---

## Development Workflow

### Branch Naming

```
feature/add-rbi-gdp-dataset
fix/district-name-normalization
docs/update-researcher-guide
chore/upgrade-hono-4
```

### Running Locally

```bash
# Start all services (API + Playground)
pnpm dev

# API only (runs on http://localhost:8787)
pnpm --filter @bharatdata/api dev

# Playground only (runs on http://localhost:3000)
pnpm --filter playground dev
```

---

## Testing Standards

All code contributions must include tests. We use a layered testing approach:

| Layer | Tool | Location |
| :--- | :--- | :--- |
| Unit Tests | Vitest | `*.test.ts` alongside source files |
| Integration Tests | Vitest + msw | `tests/integration/` |
| E2E Tests | Playwright | `tests/e2e/` |

### Running Tests

```bash
# Unit + Integration
pnpm test

# End-to-End (requires running dev server)
pnpm test:e2e

# Specific package
pnpm --filter @bharatdata/api test
```

---

## Pull Request Process

1. **One PR per concern** — do not combine unrelated changes
2. **Fill in the PR template** — describe what changed and why
3. **All tests must pass** — no exceptions for any green-light merge
4. **Documentation is required** — update relevant `.md` files for any user-visible change
5. **At least one review** — all PRs require review from a project maintainer

PRs that modify data ingestion logic require review from **two maintainers** due to the public trust implications.

---

## Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) standard:

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

| Type | When to Use |
| :--- | :--- |
| `feat` | A new feature or dataset |
| `fix` | A bug fix |
| `docs` | Documentation-only changes |
| `data` | Changes to ingestion pipelines or source data |
| `refactor` | Code restructuring with no behavior change |
| `test` | Adding or fixing tests |
| `chore` | Build scripts, dependency updates |

**Examples:**
```
feat(api): add rbi-gdp dataset to registry
fix(playground): restore query event loop after error state refactor
data(pipeline): update NCRB 2023 crime normalization script
docs(security): add safe harbor provisions to SECURITY.md
```

---

## Questions?

If you are unsure about anything, open a [GitHub Discussion](https://github.com/bharatdata/bharatdata/discussions). We are happy to guide you.

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body</sub>
</div>

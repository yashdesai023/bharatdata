<div align="center">
  <img src="../../docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>BharatData TypeScript SDK</h1>
  <em>Official TypeScript and JavaScript client for the BharatData API.</em>
  <br/><br/>

  [![npm version](https://img.shields.io/npm/v/@bharatdata/typescript-sdk)](https://www.npmjs.com/package/@bharatdata/typescript-sdk)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)

</div>

---

## Installation

```bash
# npm
npm install @bharatdata/typescript-sdk

# pnpm
pnpm add @bharatdata/typescript-sdk

# yarn
yarn add @bharatdata/typescript-sdk
```

**Requirements:** Node.js 18+ | Modern browsers with Fetch API | Cloudflare Workers

---

## Quick Start

```typescript
import { BharatData } from '@bharatdata/typescript-sdk';

const bd = new BharatData();

// AI-powered natural language query
for await (const event of bd.queryAI('Crime trends in Maharashtra 2021-2023')) {
  if (event.type === 'initial') {
    console.log(`Found ${event.count} records`);
    console.table(event.data.slice(0, 5));
  }
  if (event.type === 'delta') {
    process.stdout.write(event.content);
  }
}
```

---

## Configuration

```typescript
const bd = new BharatData({
  baseUrl: 'https://api.bharatdata.org', // default — production API
  // baseUrl: 'http://localhost:8787',   // local development
});
```

---

## API Methods

### `bd.listDatasets()`

Returns all datasets registered in the BharatData Registry.

```typescript
const datasets = await bd.listDatasets();
// Returns: DatasetMetadata[]
```

---

### `bd.getDatasetMetadata(datasetId)`

Returns full metadata for a specific dataset including available fields, years, and source URL.

```typescript
const metadata = await bd.getDatasetMetadata('ncrb-crime');
console.log(metadata.availableFields);
// ['state', 'district', 'year', 'total_cases', 'category_label', 'confidence']
```

---

### `bd.query<T>(datasetId, level, params)`

Universal data query. Returns typed results from any registered dataset.

```typescript
const data = await bd.query('ncrb-crime', 'district', {
  entity: 'Maharashtra',
  year: '2023',
  sort: 'total_cases',
  order: 'desc',
  limit: '50',
});
```

**Supported `QueryParams` keys:**

| Key | Type | Description |
| :--- | :--- | :--- |
| `entity` | `string` | Geographic filter (partial match on state/district name) |
| `year` | `string` | Year filter, single or comma-separated (`"2021,2022,2023"`) |
| `sort` | `string` | Column to sort by |
| `order` | `"asc" \| "desc"` | Sort direction |
| `limit` | `string` | Max records returned (default 100, max 500) |
| `offset` | `string` | Pagination offset |

---

### `bd.queryAI(prompt)`

Returns an `AsyncGenerator<AIQueryEvent>` that streams the AI analysis.

```typescript
for await (const event of bd.queryAI('Which states have the highest cybercrime rates in 2023?')) {
  switch (event.type) {
    case 'initial':
      // event.queryPlan: parsed intent
      // event.data: raw records from database
      // event.count: total matching records
      break;
    case 'delta':
      process.stdout.write(event.content); // Streaming narrative
      break;
    case 'done':
      break;
  }
}
```

---

### Helper Methods

```typescript
const states     = await bd.getStates();     // All Indian states and UTs
const categories = await bd.getCategories(); // All crime categories
const years      = await bd.getYears();      // Available data years
```

---

## TypeScript Interfaces

```typescript
interface AIQueryPlan {
  dataset: string | null;
  level: 'state' | 'district' | 'city' | 'national';
  filters: { state?: string; district?: string; year?: number; category?: string; };
  sort?: { field: string; order: 'asc' | 'desc' };
  limit?: number;
  queryComplexity?: 'simple' | 'comparison' | 'trend' | 'ranking' | 'exploration';
  chart_type: 'bar' | 'line' | 'map' | 'none';
  explanation: string;
}

type AIQueryEvent = AIQueryInitial | AIQueryDelta | { type: 'done' };
```

---

## Error Handling

```typescript
try {
  for await (const event of bd.queryAI(prompt)) {
    // handle events
  }
} catch (error) {
  if (error.message.includes('Rate Limit')) {
    // Respect the retryAfter value in the error — see API Reference
    console.error('Rate limited. Wait and retry.');
  } else {
    console.error('Query failed:', error.message);
  }
}
```

---

## Usage Examples by Environment

### React Component

```tsx
import { useState, useEffect } from 'react';
import { BharatData } from '@bharatdata/typescript-sdk';

const bd = new BharatData();

export function CrimeStats() {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    bd.query('ncrb-crime', 'state', { year: '2023' })
      .then(setData)
      .catch(console.error);
  }, []);
  
  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}
```

### Cloudflare Worker

```typescript
import { BharatData } from '@bharatdata/typescript-sdk';

export default {
  async fetch(request: Request) {
    const bd = new BharatData({ baseUrl: 'https://api.bharatdata.org' });
    const data = await bd.query('ncrb-crime', 'state', { year: '2023' });
    return Response.json({ data });
  }
};
```

---

## Data Attribution

When publishing projects that use this SDK, include attribution per [ATTRIBUTION.md](../../docs/legal/ATTRIBUTION.md):

```typescript
// Data source: NCRB Crime in India
// Published by: Ministry of Home Affairs, Government of India
// Accessed via: BharatData API (https://bharatdata.org)
```

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body</sub>
</div>

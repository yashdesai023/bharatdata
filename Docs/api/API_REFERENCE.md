<div align="center">
  <img src="../../Docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>API Reference</h1>
  <em>Complete reference for the BharatData REST API v0.0.1</em>
</div>

---

## Base URL

```
Production:  https://api.bharatdata.dev
Development: http://localhost:8787
```

All responses are `application/json` unless otherwise specified.  
All requests must include the `Accept: application/json` header.

---

## Rate Limits

The BharatData API enforces per-IP rate limits to ensure fair access for all users.

| Window | Maximum Requests |
| :--- | :--- |
| Per Minute | **10 requests** |
| Per Day | **200 requests** |

### Rate Limit Headers

Every API response includes the following headers:

| Header | Description |
| :--- | :--- |
| `X-RateLimit-Limit` | Maximum requests allowed in the current minute window |
| `X-RateLimit-Remaining` | Requests remaining in the current minute window |

### Exceeded Limit Response

When a rate limit is exceeded, the API returns `HTTP 429` with a structured JSON body:

```json
{
  "error": "Rate Limit Exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "You are moving too fast. Please wait a moment.",
  "retryAfter": 47,
  "unit": "seconds"
}
```

- `retryAfter` is the number of seconds until your window resets
- For daily limits, the message will read: `"You have reached your daily limit of 200 requests."`

---

## Authentication

The API is currently publicly accessible without authentication. No API key is required.

---

## Endpoints

### `GET /`

Returns a welcome message and list of available endpoints.

**Cache**: 24 hours (Cloudflare Edge)

**Response:**
```json
{
  "message": "Welcome to BharatData API",
  "status": "operational",
  "version": "0.0.1",
  "documentation": "https://github.com/bharatdata/bharatdata",
  "endpoints": {
    "health": "/health",
    "ai": "/v1/ai/query",
    "registry": "/v1/registry"
  }
}
```

---

### `GET /health`

Returns real-time system health including Supabase database connectivity and latency.

**Response — Healthy:**
```json
{
  "status": "ok",
  "timestamp": "2026-04-01T12:00:00.000Z",
  "version": "0.0.1",
  "dependencies": {
    "supabase": { "status": "connected", "latency": "42ms" },
    "registry": { "status": "loaded" },
    "cache": { "status": "active", "strategy": "edge-caching" }
  }
}
```

**Response — Degraded (Supabase unreachable):**
```json
{
  "status": "degraded",
  "timestamp": "2026-04-01T12:00:00.000Z",
  "version": "0.0.1",
  "dependencies": {
    "supabase": { "status": "unreachable", "latency": "-1ms" },
    "registry": { "status": "loaded" },
    "cache": { "status": "active", "strategy": "edge-caching" }
  }
}
```

---

### `GET /v1/registry`

Lists all datasets registered in the BharatData Registry.

**Cache**: 24 hours (Cloudflare Edge)

```bash
curl https://api.bharatdata.dev/v1/registry
```

**Response:**
```json
{
  "data": [
    {
      "id": "ncrb-crime",
      "name": "NCRB Crime Statistics",
      "description": "District and state-level crime data from the National Crime Records Bureau",
      "publishingBody": "Ministry of Home Affairs",
      "geographicCoverage": "district",
      "temporalCoverage": "2001-2023",
      "updateFrequency": "annual"
    }
  ],
  "count": 1,
  "meta": { "message": "Use /v1/registry/:id for full details" }
}
```

---

### `GET /v1/registry/:id`

Returns full metadata for a specific registered dataset.

**Cache**: 24 hours (Cloudflare Edge)

```bash
curl https://api.bharatdata.dev/v1/registry/ncrb-crime
```

**Response:**
```json
{
  "data": {
    "id": "ncrb-crime",
    "name": "NCRB Crime Statistics",
    "publishingBody": "National Crime Records Bureau",
    "description": "District and state-level crime statistics from the National Crime Records Bureau",
    "geographicCoverage": "district",
    "temporalCoverage": "2001-2023",
    "updateFrequency": "annual",
    "tableName": "crime_records_district",
    "availableFields": [
      "state", "district", "year", "total_cases", "category_label",
      "confidence", "report_name", "ipc_crime_code"
    ],
    "sourceUrl": "https://ncrb.gov.in/en/crime-in-india"
  }
}
```

**Error (Dataset not found):**
```json
{
  "error": "Dataset 'rbi-economic' is not registered.",
  "hint": "Call GET /v1/registry to see all available datasets.",
  "available": ["ncrb-crime"]
}
```
`HTTP 404`

---

### `GET /v1/registry/:id/fields`

Returns only the list of available query fields for a dataset.

**Cache**: 24 hours (Cloudflare Edge)

```bash
curl https://api.bharatdata.dev/v1/registry/ncrb-crime/fields
```

**Response:**
```json
{
  "data": ["state", "district", "year", "total_cases", "category_label", "confidence"],
  "count": 6
}
```

---

### `GET /v1/registry/:id/years`

Returns the list of available years for a dataset (live database query).

**Cache**: 24 hours (Cloudflare Edge)

```bash
curl https://api.bharatdata.dev/v1/registry/ncrb-crime/years
```

**Response:**
```json
{
  "data": [2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015],
  "count": 9
}
```

---

### `GET /v1/data/:dataset`

The **Universal Query Endpoint**. Retrieves data from any registered dataset with full filter support.

```bash
curl "https://api.bharatdata.dev/v1/data/ncrb-crime?entity=Maharashtra&year=2023&limit=10"
```

**Query Parameters:**

| Parameter | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `entity` | `string` | Geographic filter (partial match on state or district name) | `Maharashtra` |
| `year` | `string` | Year filter (single value or comma-separated) | `2023` or `2021,2022,2023` |
| `limit` | `number` | Max records to return. Default 100, max 500. | `50` |
| `offset` | `number` | Pagination offset. Default 0. | `100` |
| `sort` | `string` | Column to sort by (must be in `availableFields`) | `total_cases` |
| `order` | `asc\|desc` | Sort direction. Default `desc`. | `desc` |

**Response:**
```json
{
  "data": [
    {
      "state": "Maharashtra",
      "district": "Pune",
      "year": 2023,
      "total_cases": 12450,
      "category_label": "Total Cognizable Crimes",
      "confidence": 0.97,
      "report_name": "Crime in India 2023"
    }
  ],
  "count": 287,
  "metadata": {
    "dataset": "ncrb-crime",
    "level": "district",
    "source": "National Crime Records Bureau",
    "timestamp": "2026-04-01T12:00:00.000Z",
    "attribution": "National Crime Records Bureau, Ministry of Home Affairs, Government of India"
  },
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 287,
    "hasMore": true
  }
}
```

**Error (Invalid sort field):**
```json
{
  "error": "Invalid sort column 'population'.",
  "availableFields": ["state", "district", "year", "total_cases", "category_label"]
}
```
`HTTP 400`

**Error (Invalid year format):**
```json
{
  "error": "Invalid year value(s): abc"
}
```
`HTTP 400`

---

### `POST /v1/ai/query`

Submits a natural language query to the BharatData AI Engine. Returns a **streaming Server-Sent Events (SSE)** response.

```bash
curl -X POST https://api.bharatdata.dev/v1/ai/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Compare murder rates across Indian states in 2023"}'
```

**Request Body:**
```json
{ "prompt": "Compare murder rates across Indian states in 2023" }
```

**Response:** `text/event-stream`

The response is a stream of `data:` events. There are three event types:

**Type 1: `status`** — Processing update for UI (display but don't store)
```
data: {"type": "status", "content": "Strategizing query for BharatData archive..."}
```

**Type 2: `initial`** — Query plan and raw data
```
data: {
  "type": "initial",
  "queryPlan": {
    "dataset": "ncrb-crime",
    "level": "state",
    "filters": { "category": "Murder" },
    "chart_type": "bar",
    "queryComplexity": "comparison",
    "explanation": "Fetching state-level murder data for 2023"
  },
  "data": [{"state": "Uttar Pradesh", "total_cases": 2987, ...}],
  "count": 36
}
```

**Type 3: `delta`** — Streaming narrative text chunk
```
data: {"type": "delta", "content": "Uttar Pradesh recorded the highest number of "}
data: {"type": "delta", "content": "murder cases in 2023 with 2,987 incidents..."}
```

**Type 4: `done`**
```
data: [DONE]
```

---

### `GET /v1/meta/states`

Returns the complete list of Indian states and union territories recognized by BharatData.

**Cache**: 24 hours (Cloudflare Edge)

```bash
curl https://api.bharatdata.dev/v1/meta/states
```

**Response:**
```json
{
  "data": [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Delhi", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir",
    "...all 36 states/UTs"
  ],
  "count": 36
}
```

---

### `GET /v1/fallback`

Returns the Level-3 static fallback dataset. This endpoint is always available, even during Supabase downtime. Use it to verify API reachability.

```bash
curl https://api.bharatdata.dev/v1/fallback
```

**Response:**
```json
{
  "dataset": "ncrb_crime_summary_2023",
  "generated_at": "2026-04-01T12:00:00Z",
  "summary": [
    { "state": "Maharashtra", "total_ipc": 345000, "major_crime": "Theft" },
    { "state": "Uttar Pradesh", "total_ipc": 412000, "major_crime": "Assault" }
  ],
  "note": "This is a static fallback dataset used when the primary database is unreachable."
}
```

---

## Error Reference

| HTTP Code | Code | Meaning |
| :--- | :--- | :--- |
| `400` | `BAD_REQUEST` | Invalid query parameters (bad year, invalid sort field) |
| `404` | `NOT_FOUND` | Dataset ID does not exist in the Registry |
| `429` | `RATE_LIMIT_EXCEEDED` | Per-minute or per-day limit exceeded |
| `500` | `INTERNAL_ERROR` | Unexpected server error (check `/health` for status) |

---

## SDK Quick Reference

### TypeScript

```typescript
import { BharatData } from '@bharatdata/typescript-sdk';
const bd = new BharatData({ baseUrl: 'https://api.bharatdata.dev' });

const data = await bd.query('ncrb-crime', 'district', { entity: 'Delhi', year: '2023' });
```

### Python

```python
import bharatdata as bd
df = bd.query("ncrb-crime", level="district", filters={"entity": "Delhi", "year": "2023"})
```

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body &nbsp;|&nbsp; API v0.0.1</sub>
</div>

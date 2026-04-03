<div align="center">
  <img src="../../Docs/assets/logo_full.png" alt="BharatData" height="72" />
  <h1>System Architecture</h1>
  <em>Technical architecture of the BharatData platform for contributors and integrators.</em>
</div>

---

## Overview

BharatData is a **monorepo** built with **Turborepo** that spans five packages and a data pipeline. The platform is designed for three core principles:

1. **Infrastructure-grade reliability** — The API must be available even when Supabase is degraded
2. **Lineage-first transparency** — Every data point traces back to its official government source
3. **Universal accessibility** — The same data must be queryable by a journalist with no code skills and a data scientist with a Jupyter notebook

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                      │
│                                                             │
│  ┌───────────────────┐  ┌───────────────┐  ┌────────────┐  │
│  │  BharatData       │  │  TypeScript   │  │  Python    │  │
│  │  Playground       │  │  SDK          │  │  SDK       │  │
│  │  (Next.js)        │  │  (Node/Browser│  │  (Pandas)  │  │
│  └─────────┬─────────┘  └───────┬───────┘  └─────┬──────┘  │
└────────────┼────────────────────┼────────────────┼─────────┘
             │HTTPS               │HTTPS           │HTTPS
┌────────────▼────────────────────▼────────────────▼─────────┐
│                    CLOUDFLARE EDGE LAYER                     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  BharatData API                        │ │
│  │              (Cloudflare Workers + Hono)               │ │
│  │                 (api.bharatdata.dev)                   │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌────────────┐  ┌───────────────┐  │ │
│  │  │  CORS +      │  │  Registry  │  │  AI Service   │  │ │
│  │  │  Rate Limit  │  │  (Dataset  │  │  (Gemini      │  │ │
│  │  │  Middleware  │  │  Discovery)│  │  Flash)       │  │ │
│  │  └──────┬───────┘  └─────┬──────┘  └──────┬────────┘  │ │
│  │         └────────────────┼────────────────┘           │ │
│  │                 ┌────────▼───────┐                    │ │
│  │                 │ Query Builder  │                    │ │
│  │                 │ (Universal     │                    │ │
│  │                 │  filter engine)│                    │ │
│  │                 └────────┬───────┘                    │ │
│  └──────────────────────────┼────────────────────────────┘ │
│                    CACHE LAYER (Edge)                       │
│    Metadata: 24h | Data: 1h | Static: ∞                    │
└────────────┬───────────────────────────────────────────────┘
│        BharatData Playground     │  ← Next.js App Router
│         (bharatdata.dev)         │
└────────────┬─────────────────────┘
             │Supabase Client
┌────────────▼────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│                                                             │
│  ┌───────────────────────┐   ┌────────────────────────────┐ │
│  │      Supabase         │   │  Level-3 Static Fallback   │ │
│  │  (PostgreSQL)         │◄──┤  (fallback_data.json)      │ │
│  │                       │   │  Always available,         │ │
│  │  crime_records_       │   │  bundled in worker         │ │
│  │  district (main)      │   └────────────────────────────┘ │
│  └───────────────────────┘                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Package Breakdown

### `packages/api` — Core API

**Runtime**: Cloudflare Workers  
**Framework**: [Hono](https://hono.dev/) (Ultra-lightweight, edge-native)  
**Language**: TypeScript

| File | Responsibility |
| :--- | :--- |
| `src/index.ts` | Main router, CORS, rate limiting middleware |
| `src/routes/data.ts` | Universal data query endpoint (`/v1/data/:dataset`) |
| `src/routes/registry.ts` | Dataset discovery (`/v1/registry`) |
| `src/services/ai-service.ts` | Gemini AI integration (query planning + narrative streaming) |
| `src/services/query-builder.ts` | Universal Supabase filter engine |
| `src/services/response-builder.ts` | Standardized API response formatter |
| `src/registry/registry-service.ts` | In-memory dataset registry |
| `src/db.ts` | Supabase client initialization |
| `src/fallback_data.json` | Level-3 static fallback dataset |

**Key Design Decisions:**

- **In-memory rate limiting**: Rate limit counters are held in Worker memory (not KV) for zero-latency enforcement. Trade-off: counters reset on Worker cold start.
- **Registry is code-defined, not database-driven**: Dataset metadata is defined in TypeScript objects and deployed with the worker. This means no registry queries to Supabase, enabling zero-downtime registry updates.
- **Level-3 Fallback**: The `fallback_data.json` file is bundled directly in the Worker. No external dependency is needed for the `/v1/fallback` endpoint.

---

### `packages/typescript-sdk` — JavaScript/TypeScript Client

**Runtime**: Browser + Node.js + Edge  
**Language**: TypeScript

| File | Responsibility |
| :--- | :--- |
| `src/client.ts` | `BharatData` class with all API methods |
| `src/types.ts` | TypeScript interfaces for all API types |
| `src/index.ts` | Package exports |

**Key exports:**
```typescript
export class BharatData { ... }
export interface AIQueryPlan { ... }
export interface CrimeRecord { ... }
export type AIQueryEvent = AIQueryInitial | AIQueryDelta | { type: 'done' };
```

The SDK's `queryAI` method returns an `AsyncGenerator<AIQueryEvent>`, enabling incremental streaming consumption:

```typescript
for await (const event of bd.queryAI(prompt)) {
  if (event.type === 'initial') { /* handle data */ }
  if (event.type === 'delta') { /* append narrative text */ }
}
```

---

### `packages/playground` — Web Application

**Runtime**: Netlify (Next.js 15 App Router)  
**Framework**: Next.js  
**Styling**: Tailwind CSS + Material Symbols

Key components:

| Component | Path | Purpose |
| :--- | :--- | :--- |
| `PlaygroundPage` | `src/app/page.tsx` | Main application state and query orchestration |
| `DataTable` | `components/ui/DataTable.tsx` | Paginated data display |
| `DataChart` | `components/ui/DataChart.tsx` | Bar/line chart visualization (Recharts) |
| `IndiaMap` | `components/ui/IndiaMap.tsx` | Choropleth map (Leaflet + GeoJSON) |
| `ErrorState` | `components/ui/ErrorStates.tsx` | Professional error display with countdown timer |
| `StructuredQueryBuilder` | `components/ui/StructuredQueryBuilder.tsx` | Form-based query interface (no-code) |

---

### `packages/python-sdk` — Python Client

**Runtime**: Python 3.9+  
**Key dependency**: `pandas`, `requests`

---

### `packages/shared` — Shared Constants

**Runtime**: Universal  
Exports the canonical list of Indian states and crime categories used by both the API and SDKs. This ensures consistent filtering across all clients.

---

## Data Pipeline

```
Raw Government PDF/XLSX
         │
         ▼
┌─────────────────────┐
│  pipeline/ingest/   │  ← Python scripts per source (NCRB, RBI, Census)
│  ncrb_ingest.py     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Normalization      │  ← Administrative name canonicalization
│  Engine             │     against canonical-mappings/states.json
└─────────┬───────────┘     and canonical-mappings/districts.json
          │
          ▼
┌─────────────────────┐
│  Quality Check      │  ← Verify no null values in required fields,
│  scripts/           │     year in valid range, confidence scoring
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Supabase Upsert   │  ← crime_records_district, or other tables
└─────────────────────┘
```

**Normalization Strategy:**

The most critical step in the pipeline is **administrative name normalization**. Indian government datasets exhibit significant inconsistency:

- District name variations: "Bangalore", "Bengaluru", "Bengaluru Urban", "Bangalore Urban"
- New districts: Post-2019 district bifurcations in Telangana, Himachal Pradesh, etc.
- Encoding issues: Windows-1252 encoded XLSX files from pre-2015 NCRB reports

We maintain a `canonical-mappings/` directory with hand-verified mapping files that resolve 400+ known variant names to their canonical form.

---

## API Resilience Architecture (3-Level Fallback)

| Level | Mechanism | When It Activates |
| :--- | :--- | :--- |
| **Level 1** | Cloudflare Edge Cache (`Cache-Control: public, max-age=86400`) | For all metadata endpoints (States, Years, Registry). Serves stale-while-revalidate. |
| **Level 2** | Supabase Connection Retry | Automatic on transient network error (handled internally by Supabase client) |
| **Level 3** | Static Fallback (`fallback_data.json`) | When `buildAndExecuteQuery` throws, the data route redirects to `/v1/fallback`. Always returns HTTP 200. |

---

## Rate Limiting Design

Rate limits are enforced in an in-memory `Map<IP, { minCount, dayCount, minReset, dayReset }>` in the Cloudflare Worker:

- **Minute window**: Resets every 60 seconds
- **Day window**: Resets every 86,400 seconds
- **No persistence**: Resets on Worker cold start (acceptable for prototype)
- **Response headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining` on every response
- **429 Body**: Structured JSON with `retryAfter` in seconds

**Post-launch improvement**: Migrate to Cloudflare KV for persistent rate limit counters across Worker instances.

---

## AI Service Architecture

The AI query pipeline has two sequential calls:

```
User Prompt → generateQueryPlan() → Structured Plan JSON
                                          │
                                          ▼
                                   buildAndExecuteQuery()
                                          │
                                          ▼
                               generateNarrativeStream()  → SSE stream to client
```

**Call 1: `generateQueryPlan`**  
Prompt: System prompt instructing the model to parse the user's question into a structured JSON object (`AIQueryPlan`) containing: dataset, filters, sort, limit, chart_type, and explanation.

**Call 2: `generateNarrativeStream`**  
Prompt: System prompt with the query plan + actual retrieved data, instructing the model to write a scholarly, citation-ready analysis.

Both calls go to **Gemini Flash** via the Sarvam AI gateway. Narrative streaming is handled via ReadableStream in the Worker and passed to the client as Server-Sent Events.

---

## Deployment

| Service | Platform | Config File |
| :--- | :--- | :--- |
| API | Cloudflare Workers | `packages/api/wrangler.toml` |
| Playground | Netlify | `netlify.toml` |
| Database | Supabase | `supabase/migrations/` |

```bash
# Deploy API to Cloudflare
npm run deploy-api

# Deploy Playground to Netlify
# Automatic via GitHub integration
```

Environment variables required:

| Variable | Where Set | Purpose |
| :--- | :--- | :--- |
| `SUPABASE_URL` | Cloudflare Worker Secrets | Database connection |
| `SUPABASE_ANON_KEY` | Cloudflare Worker Secrets | Database authentication |
| `SARVAM_API_KEY` | Cloudflare Worker Secrets | Gemini AI access |
| `NEXT_PUBLIC_API_URL` | Netlify Site Settings | API base URL for playground |

---

<div align="center">
  <sub>Generated by the BharatData Team &nbsp;|&nbsp; Not affiliated with any government body</sub>
</div>

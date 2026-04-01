// Universal Data Routes
// GET /v1/data/:dataset   -> query any registered dataset
//
// Supported query params:
//   ?entity=Agra               filter by geographic entity (partial match)
//   ?year=2023                 filter by year (comma-separated)
//   ?limit=100                 pagination limit (max 500)
//   ?offset=0                  pagination offset
//   ?sort=total_ipc            sort column (must be in availableFields)
//   ?order=desc|asc            sort direction

import { Hono } from 'hono';
import { Env, getSupabase } from '../db';
import { registry } from '../registry/registry-service';
import { buildAndExecuteQuery, QueryParams } from '../services/query-builder';
import { buildResponse } from '../services/response-builder';

const dataRoutes = new Hono<{ Bindings: Env }>();

dataRoutes.get('/:dataset', async (c) => {
  const datasetId = c.req.param('dataset');

  // --- 1. Lookup dataset ---
  const definition = registry.get(datasetId);
  if (!definition) {
    return c.json(
      {
        error: `Dataset '${datasetId}' is not registered.`,
        hint: 'Call GET /v1/registry to see all available datasets.',
        available: registry.getAll().map((d) => d.id),
      },
      404
    );
  }

  // --- 2. Extract and validate params ---
  const raw = c.req.query();
  const params: QueryParams = {
    entity: raw['entity'],
    year: raw['year'],
    limit: raw['limit'],
    offset: raw['offset'],
    sort: raw['sort'],
    order: raw['order'] as 'asc' | 'desc' | undefined,
  };

  // Validate sort column
  if (params.sort && typeof params.sort === 'string' && !definition.availableFields.includes(params.sort)) {
    return c.json(
      {
        error: `Invalid sort column '${params.sort}'.`,
        availableFields: definition.availableFields,
      },
      400
    );
  }

  // Validate year format
  if (params.year) {
    const years = String(params.year).split(',');
    const invalid = years.filter((y: string) => isNaN(parseInt(y.trim())));
    if (invalid.length > 0) {
      return c.json({ error: `Invalid year value(s): ${invalid.join(', ')}` }, 400);
    }
  }

  // --- 3. Execute query ---
  try {
    const supabase = getSupabase(c.env);
    const result = await buildAndExecuteQuery(supabase, definition, params);

    if (result.error) {
      throw new Error(result.error);
    }

    // --- 4. Build response ---
    const limit = Math.min(parseInt(String(params.limit || '100')), 500);
    const offset = parseInt(String(params.offset || '0'));

    const response = buildResponse(
      (result.data as Record<string, unknown>[]) ?? [],
      result.count,
      definition,
      raw,
      limit,
      offset
    );

    return c.json(response);
  } catch (e) {
    // Level-3 Fallback Trigger: Seamless recovery for V1 prototype
    console.error(`[API ERROR] ${datasetId} failed, falling back:`, e);
    return c.redirect('/v1/fallback');
  }
});

export { dataRoutes };

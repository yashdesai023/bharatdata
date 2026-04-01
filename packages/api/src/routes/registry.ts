// Registry Discovery Routes
// GET /v1/registry                      -> list all datasets
// GET /v1/registry/:dataset             -> full metadata for one dataset
// GET /v1/registry/:dataset/fields      -> available columns
// GET /v1/registry/:dataset/years       -> available years (queries DB)

import { Hono } from 'hono';
import { Env } from '../db';
import { registry } from '../registry/registry-service';
import { getSupabase } from '../db';

const registryRoutes = new Hono<{ Bindings: Env }>();

// List all datasets
registryRoutes.get('/', (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  const datasets = registry.getSummaries();
  return c.json({
    data: datasets,
    count: datasets.length,
    meta: { message: 'Use /v1/registry/:id for full details' },
  });
});

// Full definition for a dataset
registryRoutes.get('/:id', (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  const id = c.req.param('id');
  const def = registry.get(id);

  if (!def) {
    return c.json(
      {
        error: `Dataset '${id}' is not registered.`,
        available: registry.getAll().map((d) => d.id),
      },
      404
    );
  }

  return c.json({
    data: {
      id: def.id,
      name: def.name,
      publishingBody: def.publishingBody,
      description: def.description,
      geographicCoverage: def.geographicCoverage,
      temporalCoverage: def.temporalCoverage,
      updateFrequency: def.updateFrequency,
      tableName: def.tableName,
      availableFields: def.availableFields,
      sourceUrl: def.sourceUrl ?? null,
    },
  });
});

// Available fields for a dataset
registryRoutes.get('/:id/fields', (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  const id = c.req.param('id');
  const def = registry.get(id);

  if (!def) {
    return c.json({ error: `Dataset '${id}' not found.` }, 404);
  }

  return c.json({ data: def.availableFields, count: def.availableFields.length });
});

// Available years — live query
registryRoutes.get('/:id/years', async (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  const id = c.req.param('id');
  const def = registry.get(id);

  if (!def) {
    return c.json({ error: `Dataset '${id}' not found.` }, 404);
  }

  const yearCol = def.conceptMapping.year;
  if (!yearCol) {
    return c.json({ error: `Dataset '${id}' has no year dimension.` }, 400);
  }

  const supabase = getSupabase(c.env);
  const { data, error } = await supabase
    .from(def.tableName)
    .select(yearCol)
    .order(yearCol, { ascending: false });

  if (error) {
    return c.json({ error: 'Failed to query years.' }, 500);
  }

  const years = Array.from(new Set((data as unknown as Record<string, unknown>[])?.map((r) => r[yearCol])));
  return c.json({ data: years, count: years.length });
});

// Available entities — live query (top 200)
registryRoutes.get('/:id/entities', async (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  const id = c.req.param('id');
  const def = registry.get(id);

  if (!def) {
    return c.json({ error: `Dataset '${id}' not found.` }, 404);
  }

  const entityCol = def.conceptMapping.entity;
  const supabase = getSupabase(c.env);
  const { data, error } = await supabase
    .from(def.tableName)
    .select(entityCol)
    .order(entityCol, { ascending: true })
    .limit(200);

  if (error) {
    return c.json({ error: 'Failed to query entities.' }, 500);
  }

  const entities = Array.from(new Set((data as unknown as Record<string, unknown>[])?.map((r) => r[entityCol])));
  return c.json({ data: entities, count: entities.length });
});


export { registryRoutes };

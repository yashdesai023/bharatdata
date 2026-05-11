import { Hono } from 'hono';
import { stream } from 'hono/streaming';
import { cors } from 'hono/cors';
import { getSupabase, Env } from './db';
import { STATES, CATEGORIES } from '@bharatdata/shared';

// --- Universal Layer (Stage 4) ---
import { dataRoutes } from './routes/data';
import { registryRoutes } from './routes/registry';
import { generateQueryPlan, generateNarrativeStream } from './services/ai-service';
import { registry } from './registry/registry-service';
import { buildAndExecuteQuery } from './services/query-builder';

const app = new Hono<{ Bindings: Env }>();

// Hardened CORS: Dynamically permit origin and expose required metrics/streaming headers
app.use('*', cors({
  origin: (origin) => origin || '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization', 'Cache-Control', 'Connection'],
  exposeHeaders: ['Content-Length', 'X-Kuma-Revision', 'X-RateLimit-Limit', 'X-RateLimit-Remaining'],
  maxAge: 600,
  credentials: true,
}));
// Reloading worker to pick up environment changes.
import fallbackData from './fallback_data.json';

// --- Rate Limiting Strategy (Hardened) ---
// Per IP Tracking: 10/min (performance) | 200/day (database safety)
const rateLimitMap = new Map<string, { 
  minCount: number, 
  dayCount: number, 
  minReset: number, 
  dayReset: number 
}>();

app.use('*', async (c, next) => {
  const ip = c.req.header('x-forwarded-for') || 'anonymous';
  const now = Date.now();
  
  let record = rateLimitMap.get(ip);
  if (!record) {
    record = { 
      minCount: 0, 
      dayCount: 0, 
      minReset: now + (60 * 1000), 
      dayReset: now + (24 * 60 * 60 * 1000) 
    };
  }

  // Reset windows if expired
  if (now > record.minReset) {
    record.minCount = 0;
    record.minReset = now + (60 * 1000);
  }
  if (now > record.dayReset) {
    record.dayCount = 0;
    record.dayReset = now + (24 * 60 * 60 * 1000);
  }

  record.minCount++;
  record.dayCount++;
  rateLimitMap.set(ip, record);

  const MINUTES_LIMIT = 10;
  const DAYS_LIMIT = 200;

  if (record.minCount > MINUTES_LIMIT || record.dayCount > DAYS_LIMIT) {
    const isDayBan = record.dayCount > DAYS_LIMIT;
    const retryAfter = Math.ceil(((isDayBan ? record.dayReset : record.minReset) - now) / 1000);
    
    return c.json({
      error: 'Rate Limit Exceeded',
      code: 'RATE_LIMIT_EXCEEDED',
      message: isDayBan 
        ? 'You have reached your daily limit of 200 requests.' 
        : 'You are moving too fast. Please wait a moment.',
      retryAfter,
      unit: 'seconds'
    }, 429);
  }

  c.header('X-RateLimit-Limit', MINUTES_LIMIT.toString());
  c.header('X-RateLimit-Remaining', Math.max(0, MINUTES_LIMIT - record.minCount).toString());
  
  await next();
});

// ── System Routes ─────────────────────────────────────────────────────────────
app.get('/', (c) => {
  // Level-1 Cache: This root message is immutable for 24h
  c.header('Cache-Control', 'public, max-age=86400');
  return c.json({ 
    message: 'Welcome to BharatData API',
    status: 'operational',
    version: '2.0.0',
    documentation: 'https://github.com/bharatdata/bharatdata',
    endpoints: {
      health: '/health',
      ai: '/v1/ai/query',
      registry: '/v1/registry'
    }
  });
});

// ── Health Check (Enhanced) ───────────────────────────────────────────────────
app.get('/health', async (c) => {
  const supabase = getSupabase(c.env);
  let dbStatus = 'unreachable';
  let latency = -1;

  try {
    const start = Date.now();
    // Check first dataset in registry to prove universal health
    const firstDataset = registry.getAll()[0];
    const { error } = firstDataset 
      ? await supabase.from(firstDataset.tableName).select('count', { count: 'exact', head: true }) 
      : { error: null };
      
    latency = Date.now() - start;
    if (!error) dbStatus = 'connected';
  } catch (e) {
    dbStatus = 'error';
  }

  return c.json({ 
    status: dbStatus === 'connected' ? 'ok' : 'degraded',
    timestamp: new Date().toISOString(),
    version: '2.1.0-universal',
    dependencies: {
      supabase: { status: dbStatus, latency: `${latency}ms` },
      registry: { datasets: registry.getAll().length, status: registry ? 'loaded' : 'missing' },
      cache: { status: 'active', strategy: 'edge-caching' }
    }
  });
});


// ── Legacy Meta Routes (v1) ───────────────────────────────────────────────────
app.get('/v1/meta/states', (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  return c.json({ data: STATES, count: STATES.length });
});
app.get('/v1/meta/categories', (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  return c.json({ data: CATEGORIES, count: CATEGORIES.length });
});

// ── Universal Meta Routes (v2) ─────────────────────────────────────────────────
app.get('/v1/meta/datasets', (c) => {
  c.header('Cache-Control', 'public, max-age=86400');
  const summaries = registry.getSummaries();
  return c.json({ data: summaries, count: summaries.length });
});

app.get('/v1/meta/:dataset/years', async (c) => {
  const datasetId = c.req.param('dataset');
  const dataset = registry.get(datasetId);
  if (!dataset) return c.json({ error: 'Dataset not found' }, 404);

  c.header('Cache-Control', 'public, max-age=86400');
  const supabase = getSupabase(c.env);
  const { data, error } = await supabase
    .from(dataset.tableName)
    .select('year')
    .order('year', { ascending: false });

  if (error) return c.json({ error: `Failed to fetch years for ${datasetId}` }, 500);
  const years = Array.from(new Set(data.map((r: any) => r.year)));
  return c.json({ data: years, count: years.length });
});

// Legacy path support (Maps to first dataset or ncrb by default)
app.get('/v1/meta/years', async (c) => {
  const ncrb = registry.get('ncrb-crime') || registry.getAll()[0];
  if (!ncrb) return c.json({ error: 'No datasets available' }, 500);
  return c.redirect(`/v1/meta/${ncrb.id}/years`, 301);
});

// ── Legacy Crime Route (backward compat) ──────────────────────────────────────
// Maps old /v1/crime/summary to the new universal endpoint behaviour
app.get('/v1/crime/summary', async (c) => {
  const state = c.req.query('state');
  const year = c.req.query('year');
  const category = c.req.query('category');

  if (!state || !year || !category) {
    return c.json({ error: 'Missing required query parameters: state, year, category' }, 400);
  }

  const supabase = getSupabase(c.env);
  
  let query = supabase
    .from('crime_records_district')
    .select('district, total_cases, year, confidence, report_name')
    .eq('year', parseInt(year))
    .order('total_cases', { ascending: false });

  if (state && state !== 'All States') {
    query = query.ilike('state', `%${state}%`);
  }

  const { data, error } = await query;

  if (error) return c.json({ error: 'Internal Server Error' }, 500);

  return c.json({ data: data || [], count: data?.length || 0 });
});

// ── Universal API Routes (Stage 4) ────────────────────────────────────────────
//   /v1/registry       → dataset discovery
//   /v1/data/:dataset  → universal data access
app.route('/v1/registry', registryRoutes);
app.route('/v1/registry', registryRoutes);
app.route('/v1/data', dataRoutes);

// ── AI Playground Routes (Stage 4) ──────────────────────────────────────────
app.post('/v1/ai/query', async (c) => {
  const body = await c.req.json();
  const prompt = body.prompt;
  const apiKey = c.env.SARVAM_API_KEY;

  if (!prompt) return c.json({ error: 'Missing prompt' }, 400);
  if (!apiKey) return c.json({ error: 'AI not configured' }, 500);

  try {
    return stream(c, async (s) => {
      try {
        // 1. Initial Setup
        c.header('Content-Type', 'text/event-stream');
        c.header('Cache-Control', 'no-cache');
        c.header('Connection', 'keep-alive');

        // 2. Send initial "Thinking" status
        await s.write(`data: ${JSON.stringify({ type: 'status', content: "Strategizing query for BharatData archive..." })}\n\n`);

        // 3. Understanding & Plan (Call 1)
        const queryPlan = await generateQueryPlan(prompt, apiKey);
        console.log('[AI Query Plan]:', JSON.stringify(queryPlan, null, 2));

        await s.write(`data: ${JSON.stringify({ type: 'status', content: `Searching ${queryPlan.dataset || 'appropriate records'}...` })}\n\n`);
        
        // 4. Execute Data Fetch (if dataset found)
        let dataResult: { data: any[] | null, count: number } = { data: [], count: 0 };
        if (queryPlan.dataset && typeof queryPlan.dataset === 'string') {
          const definition = registry.get(queryPlan.dataset);
          if (definition) {
            // UNIVERSAL FILTER FIX: Pass expanded filters, sort, and limit from the AI Plan
            dataResult = await buildAndExecuteQuery(getSupabase(c.env), definition, {
              ...queryPlan.filters,
              sort: queryPlan.sort,
              limit: queryPlan.limit,
            });
            console.log(`[Data Result]: Fetched ${dataResult.count} records`);
          }
        }

        // 5. Send dataset/initial plan to UI
        await s.write(`data: ${JSON.stringify({ 
          type: 'initial', 
          queryPlan, 
          data: dataResult.data,
          count: dataResult.count
        })}\n\n`);

        if (dataResult.data && dataResult.data.length > 0) {
          await s.write(`data: ${JSON.stringify({ type: 'status', content: "Translating data into narrative insight..." })}\n\n`);
          
          const narrativeStream = await generateNarrativeStream(prompt, queryPlan, dataResult.data, apiKey);
          const reader = narrativeStream.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let isThinking = false;
          let filterBuffer = ''; // Sliding window for robust chunk matching
          let lastHeartbeat = Date.now();

          while (true) {
            try {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';

              for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || !trimmed.startsWith('data: ')) continue;
                const dataStr = trimmed.slice(6);
                if (dataStr === '[DONE]') continue;

                const json = JSON.parse(dataStr);
                const content = json.choices?.[0]?.delta?.content;

                if (content !== undefined && content !== null) {
                  filterBuffer += content;

                  while (filterBuffer.length > 0) {
                    if (isThinking) {
                      const endIndex = filterBuffer.indexOf('</think>');
                      if (endIndex !== -1) {
                        isThinking = false;
                        filterBuffer = filterBuffer.substring(endIndex + 8);
                      } else {
                        // Swallowing: keep only the last 7 chars to ensure we don't drop a split '</think>'
                        if (filterBuffer.length > 7) {
                          filterBuffer = filterBuffer.slice(-7);
                        }
                        break;
                      }
                    } else {
                      const startIndex = filterBuffer.indexOf('<think>');
                      if (startIndex !== -1) {
                        isThinking = true;
                        const toEmit = filterBuffer.substring(0, startIndex);
                        if (toEmit) {
                          await s.write(`data: ${JSON.stringify({ type: 'delta', content: toEmit })}\n\n`);
                        }
                        filterBuffer = filterBuffer.substring(startIndex + 7);
                      } else {
                        // Safe to emit all but the last 6 chars (in case it's part of '<think>')
                        if (filterBuffer.length > 6) {
                          const toEmit = filterBuffer.slice(0, -6);
                          filterBuffer = filterBuffer.slice(-6);
                          await s.write(`data: ${JSON.stringify({ type: 'delta', content: toEmit })}\n\n`);
                        } else {
                          break;
                        }
                      }
                    }
                  }

                  if (isThinking) {
                     const now = Date.now();
                     if (now - lastHeartbeat > 5000) {
                        await s.write(`data: ${JSON.stringify({ type: 'status', content: 'AI is synthesizing deep insights...' })}\n\n`);
                        lastHeartbeat = now;
                     }
                  } else {
                     lastHeartbeat = Date.now();
                  }
                }
              }
            } catch (e) {
              console.error('Narrative Stream Parse Error:', e);
            }
          }
          
          if (!isThinking && filterBuffer.length > 0) {
             await s.write(`data: ${JSON.stringify({ type: 'delta', content: filterBuffer })}\n\n`);
          }
        } else {
          await s.write(`data: ${JSON.stringify({ type: 'delta', content: "No specific government records found for this combination. Try broadening your query." })}\n\n`);
        }
      } catch (err: any) {
        console.error('Inner Stream Error:', err);
        await s.write(`data: ${JSON.stringify({ type: 'error', content: err.message || "An unexpected error occurred." })}\n\n`);
      } finally {
        await s.write(`data: [DONE]\n\n`);
      }
    });
  } catch (err: any) {
    console.error('AI Route Error:', err);
    return c.json({ error: err.message }, 500);
  }
});

export default app;

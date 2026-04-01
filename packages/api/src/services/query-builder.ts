// Universal Query Builder
// Translates generic request parameters into Supabase queries
// using the dataset's conceptMapping from the registry.

import { SupabaseClient } from '@supabase/supabase-js';
import { DatasetDefinition } from '../registry/types';

export interface QueryParams {
  state?: string | string[];
  district?: string | string[];
  city?: string | string[];
  year?: string | number;
  years?: string | number | (string | number)[];
  category?: string | string[];
  limit?: string | number;
  offset?: string | number;
  sort?: string | { field: string; order: 'asc' | 'desc' };
  order?: 'asc' | 'desc';
  [key: string]: any;
}

export interface QueryResult {
  data: Record<string, unknown>[] | null;
  count: number;
  error?: string;
}

export async function buildAndExecuteQuery(
  supabase: SupabaseClient,
  definition: DatasetDefinition,
  params: QueryParams
): Promise<QueryResult> {
  const limit = Math.min(parseInt(String(params.limit || '100')), 500);
  const offset = parseInt(String(params.offset || '0'));

  const publicFields = definition.availableFields.join(', ');

  let query = supabase
    .from(definition.tableName)
    .select(publicFields, { count: 'exact' });

  // 1. Process Geographic & Category Filters (Dynamic)
  // Mapping logic: check if the key matches a concept or points directly to a column
  const filterKeys = ['state', 'district', 'city', 'category'];
  
  for (const key of filterKeys) {
    const val = params[key];
    if (val) {
      const dbCol = definition.conceptMapping[key] || key;
      if (definition.availableFields.includes(dbCol)) {
        if (Array.isArray(val)) {
          // Robust OR logic for multiple districts/entities using fuzzy ilike
          const cleanVals = val.filter(v => typeof v === 'string' && v.trim().length > 0);
          if (cleanVals.length > 1) {
            const orString = cleanVals.map(v => `${dbCol}.ilike.%${v.trim()}%`).join(',');
            query = query.or(orString);
          } else if (cleanVals.length === 1) {
            query = query.ilike(dbCol, `%${cleanVals[0].trim()}%`);
          }
        } else {
          // Use ilike for partial case-insensitive matches to prevent "0 records" from minor typos
          query = query.ilike(dbCol, `%${val}%`);
        }
      }
    }
  }

  // 2. Process Temporal Filters (Singular or Array)
  const yearCol = definition.conceptMapping.year || 'year';
  if (definition.availableFields.includes(yearCol)) {
    const yearsInput = params.years || params.year;
    if (yearsInput) {
      const parseYear = (y: any) => parseInt(String(y).trim());
      if (Array.isArray(yearsInput)) {
        const years = yearsInput.map(parseYear).filter(y => !isNaN(y));
        if (years.length > 0) query = query.in(yearCol, years);
      } else if (typeof yearsInput === 'string' && yearsInput.includes(',')) {
        const years = yearsInput.split(',').map(parseYear).filter(y => !isNaN(y));
        if (years.length > 0) query = query.in(yearCol, years);
      } else {
        const y = parseYear(yearsInput);
        if (!isNaN(y)) query = query.eq(yearCol, y);
      }
    }
  }

  // 3. Apply Confidence Guard
  if (definition.availableFields.includes('_confidence')) {
    query = query.gte('_confidence', 0.5);
  }

  // 4. Sorting logic
  let sortField = definition.conceptMapping.year || definition.conceptMapping.entity || 'id';
  let ascending = true;

  if (params.sort) {
    if (typeof params.sort === 'object') {
      sortField = params.sort.field;
      ascending = params.sort.order !== 'desc';
    } else if (definition.availableFields.includes(params.sort)) {
      sortField = params.sort;
      ascending = params.order !== 'desc';
    }
  }
  
  // PRIMARY SORT
  query = query.order(sortField, { ascending });
  
  // SECONDARY SORT (Fallback for ties/nulls): Always sort by total_cases desc if available to ensure meaningful ranking
  if (sortField !== 'total_cases' && definition.availableFields.includes('total_cases')) {
    query = query.order('total_cases', { ascending: false });
  }

  // 5. Pagination
  query = query.range(offset, offset + limit - 1);

  const { data, error, count } = await query;

  if (error) {
    console.error(`[QueryBuilder] Error on table ${definition.tableName}:`, error.message);
    return { data: null, count: 0, error: error.message };
  }

  return { data: (data || []) as unknown as Record<string, unknown>[], count: count || 0 };
}

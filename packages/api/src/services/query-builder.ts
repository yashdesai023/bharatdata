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

// Helper to convert display field names to actual DB column names
function getActualColumns(definition: DatasetDefinition): string[] {
  const { availableFields, fieldMapping } = definition;

  // If fieldMapping exists, extract actual DB column names
  if (fieldMapping && Object.keys(fieldMapping).length > 0) {
    // fieldMapping values are the actual DB column names
    return Object.values(fieldMapping);
  }

  // Otherwise, try to convert display names to snake_case
  const columns: string[] = [];
  for (const field of availableFields) {
    // Skip meta fields and patterns
    if (field.startsWith('_') || field.includes('.*') || /^\d{4}$/.test(field)) {
      continue;
    }
    // Convert "State Name" -> "state_name", "Total P" -> "total_p"
    const col = field.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    if (col) columns.push(col);
  }
  return columns;
}

export async function buildAndExecuteQuery(
  supabase: SupabaseClient,
  definition: DatasetDefinition,
  params: QueryParams
): Promise<QueryResult> {
  const limit = Math.min(parseInt(String(params.limit || '100')), 500);
  const offset = parseInt(String(params.offset || '0'));

  // Get actual DB column names instead of display names
  const actualColumns = getActualColumns(definition);
  const publicFields = actualColumns.join(', ');

  let query = supabase
    .from(definition.tableName)
    .select(publicFields, { count: 'exact' });

  // 1. Process Geographic & Category Filters (Dynamic)
  // Mapping logic: check if the key matches a concept or points directly to a column
  const filterKeys = ['state', 'district', 'city', 'category'];
  const actualColSet = new Set(actualColumns);

  for (const key of filterKeys) {
    const val = params[key];
    if (val) {
      const dbCol = definition.conceptMapping[key] || key;
      // Check against actual column names, not display names
      if (actualColSet.has(dbCol)) {
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
  // Check against actual column names
  if (actualColSet.has(yearCol)) {
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
  if (actualColSet.has('_confidence')) {
    query = query.gte('_confidence', 0.5);
  }

  // 4. Sorting logic
  let sortField = definition.conceptMapping.year || definition.conceptMapping.entity || 'id';
  let ascending = true;

  if (params.sort) {
    if (typeof params.sort === 'object' && 'field' in params.sort) {
      sortField = params.sort.field;
      ascending = params.sort.order !== 'desc';
    } else if (typeof params.sort === 'string' && actualColSet.has(params.sort)) {
      // Convert display name to actual column name if needed
      const sortString = params.sort;
      sortField = sortString;
      // Try to find actual column name from fieldMapping
      if (definition.fieldMapping) {
        const mapped = Object.entries(definition.fieldMapping).find(
          ([, dbCol]) => dbCol.toLowerCase() === sortString.toLowerCase()
        );
        if (mapped) sortField = mapped[1];
      }
      ascending = params.order !== 'desc';
    }
  }

  // Ensure sortField is in actual columns
  if (!actualColSet.has(sortField)) {
    sortField = actualColumns[0] || 'id';
  }

  // PRIMARY SORT
  query = query.order(sortField, { ascending });

  // SECONDARY SORT (Fallback for ties/nulls): Always sort by total_cases desc if available
  if (sortField !== 'total_cases' && actualColSet.has('total_cases')) {
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

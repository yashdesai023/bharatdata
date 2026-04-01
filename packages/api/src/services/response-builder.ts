// Universal Response Builder
// Wraps raw Supabase rows in the standard BharatData response envelope.
// This shape is identical regardless of the dataset being queried.

import { DatasetDefinition } from '../registry/types';

export interface BharatDataResponse {
  data: Record<string, unknown>[];
  meta: {
    count: number;
    total: number;
    offset: number;
    limit: number;
    source: {
      id: string;
      name: string;
      publishingBody: string;
      url?: string;
      temporalCoverage: string;
    };
    confidence: {
      avg: number;
      min: number;
      records_above_threshold: number;
    } | null;
  };
  query: Record<string, unknown>;
}

export function buildResponse(
  data: Record<string, unknown>[],
  totalCount: number,
  definition: DatasetDefinition,
  appliedParams: Record<string, string | undefined>,
  limit: number,
  offset: number
): BharatDataResponse {
  // Calculate confidence stats if field is present
  let confidence = null;
  if (definition.availableFields.includes('_confidence') && data.length > 0) {
    const scores = data
      .map((r) => r['_confidence'] as number)
      .filter((s) => typeof s === 'number');

    if (scores.length > 0) {
      confidence = {
        avg: Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 1000) / 1000,
        min: Math.min(...scores),
        records_above_threshold: scores.filter((s) => s >= 0.8).length,
      };
    }
  }

  // Clean params for query echo (remove undefined values)
  const cleanQuery: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(appliedParams)) {
    if (v !== undefined) cleanQuery[k] = v;
  }

  return {
    data,
    meta: {
      count: data.length,
      total: totalCount,
      offset,
      limit,
      source: {
        id: definition.id,
        name: definition.name,
        publishingBody: definition.publishingBody,
        url: definition.sourceUrl,
        temporalCoverage: definition.temporalCoverage,
      },
      confidence,
    },
    query: cleanQuery,
  };
}

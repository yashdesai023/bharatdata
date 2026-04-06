import { State, Category } from '@bharatdata/shared';

export interface ApiResponse<T> {
  data: T;
  count?: number;
  error?: string;
  metadata?: {
    dataset: string;
    level: string;
    source?: string;
    timestamp?: string;
    attribution?: string;
  };
}

export interface DatasetMetadata {
  id: string;
  name: string;
  description: string;
  publishingBody: string;
  updateFrequency: string;
  tableName: string;
  availableFields: string[];
  fieldMapping?: Record<string, string>;
  conceptMapping?: {
    entity: string;
    year: string;
    [key: string]: string;
  };
}

export interface CrimeRecord {
  id: string;
  state: State;
  year: number;
  category: Category | string;
  total_cases: number;
  confidence: number;
  collection_date: string;
  source_file: string;
}

export interface SummaryParams {
  state: State;
  year: number;
  category: Category;
}

export interface QueryParams {
  [key: string]: string | number | boolean | string[] | number[];
}

export interface AIQueryPlan {
  dataset: string | null;
  level: 'state' | 'district' | 'city' | 'national';
  filters: {
    state?: string;
    district?: string;
    city?: string;
    year?: number;
    years?: number[] | string;
    category?: string;
    [key: string]: string | number | boolean | string[] | number[] | undefined;
  };
  sort?: { 
    field: string; 
    order: 'asc' | 'desc'
  };
  limit?: number;
  queryComplexity?: 'simple' | 'comparison' | 'trend' | 'ranking' | 'exploration';
  comparison: boolean;
  trend: boolean;
  entities: string[];
  years: string[]; // Keep for backward compatibility with UI if needed
  chart_type: 'bar' | 'line' | 'map' | 'none';
  explanation: string;
}

export interface AIQueryInitial {
  type: 'initial';
  queryPlan: AIQueryPlan;
  data: Record<string, unknown>[];
  count: number;
}

export interface AIQueryDelta {
  type: 'delta';
  content: string;
}

export type AIQueryEvent = AIQueryInitial | AIQueryDelta | { type: 'done' };


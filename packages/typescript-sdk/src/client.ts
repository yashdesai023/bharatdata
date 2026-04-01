import { ApiResponse, CrimeRecord, SummaryParams, DatasetMetadata, QueryParams } from './types';
import { State, Category } from '@bharatdata/shared';

export interface BharatDataConfig {
  baseUrl?: string;
  apiKey?: string; // Future proofing
}

export class BharatData {
  private baseUrl: string;

  constructor(config: BharatDataConfig = {}) {
    this.baseUrl = config.baseUrl || 'https://api.bharatdata.org'; // Default to production or local as configured
  }

  private async request<T>(path: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((v) => url.searchParams.append(key, String(v)));
        } else if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json() as ApiResponse<null>;
      throw new Error(errorData.error || `Request failed with status ${response.status}`);
    }

    const result = await response.json() as ApiResponse<T>;
    return result.data;
  }

  /**
   * List all available datasets in the BharatData Registry.
   */
  async listDatasets(): Promise<DatasetMetadata[]> {
    return this.request<DatasetMetadata[]>('/v1/registry');
  }

  /**
   * Get full metadata for a specific dataset.
   */
  async getDatasetMetadata(datasetId: string): Promise<DatasetMetadata> {
    return this.request<DatasetMetadata>(`/v1/registry/${datasetId}`);
  }

  /**
   * Universal Query: Fetch data from any registered dataset.
   * @param datasetId The ID of the dataset (e.g., 'ncrb-crime')
   * @param level The granularity level (e.g., 'summary', 'state', 'district')
   * @param params Query parameters (e.g., entity, year)
   */
  async query<T>(datasetId: string, level: string, params?: QueryParams): Promise<T> {
    return this.request<T>(`/v1/data/${datasetId}/${level}`, params);
  }

  /**
   * Backward Compatibility: Fetch crime summary.
   */
  async getCrimeSummary(params: SummaryParams): Promise<CrimeRecord[]> {
    return this.query<CrimeRecord[]>('ncrb-crime', 'summary', {
      entity: params.state,
      year: params.year,
      category: params.category,
    });
  }

  // Helper methods for discovery
  async getStates(): Promise<State[]> { return this.request<State[]>('/v1/meta/states'); }
  async getCategories(): Promise<Category[]> { return this.request<Category[]>('/v1/meta/categories'); }
  async getYears(): Promise<number[]> { return this.request<number[]>('/v1/meta/years'); }

  /**
   * AI Query: Ask a natural language question and stream the results.
   * Returns an AsyncGenerator that yields AIQueryEvent (Initial plan + data, then text deltas).
   */
  async *queryAI(prompt: string): AsyncGenerator<import('./types').AIQueryEvent> {
    const response = await fetch(`${this.baseUrl}/v1/ai/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'AI Query failed' }));
      throw new Error(errorData.error || `AI Query failed with status ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep the last incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;
        
        const data = trimmed.slice(6);
        if (data === '[DONE]') {
          yield { type: 'done' };
        } else {
          try {
            yield JSON.parse(data);
          } catch (e) {
            console.error('[SDK] Failed to parse AI event:', data);
          }
        }
      }
    }
  }
}


// Registry Service: Loads BharatData source definitions into memory.
// The API reads from this service instead of hardcoded logic.

import { DatasetDefinition, DatasetRegistry } from './types';

// Static registry — seeded from the YAML definitions that the pipeline uses.
// In a deployed Cloudflare Worker, the YAML cannot be read at runtime from disk.
// The registry is compiled at build time. Adding a new YAML + redeploying
// makes it live automatically.
// 
// Convention: tableName matches the Supabase table created by the ingestion engine.
// conceptMapping maps generic API concepts (entity, year) → actual DB column names.

const STATIC_DEFINITIONS: DatasetDefinition[] = [
  {
    id: 'ncrb-crime',
    name: 'NCRB Crime in India (2021–2023)',
    publishingBody: 'National Crime Records Bureau, Ministry of Home Affairs',
    description:
      'Annual district-level and state-level crime statistics across IPC, SLL, Women, Children, SC/ST, and Cyber crime categories.',
    updateFrequency: 'annual',
    geographicCoverage: 'state and district',
    temporalCoverage: '2021–2023',
    geographicLevel: 'district',
    tableName: 'crime_records_district',
    conceptMapping: {
      entity: 'district',
      year: 'year',
      category: 'category_label',
    },
    availableFields: [
      'state',
      'district',
      'year',
      'category',
      'category_label',
      'total_cases',
      'rate_per_lakh',
      'confidence',
      'report_name',
    ],
    sourceUrl: 'https://ncrb.gov.in/crime-in-india.html',
  },
  {
    id: 'ncrb-crime-state',
    name: 'NCRB Crime in India — State Level (2021–2023)',
    publishingBody: 'National Crime Records Bureau, Ministry of Home Affairs',
    description:
      'Annual state-and-UT-level aggregate crime counts across IPC and SLL categories for all 36 States/UTs.',
    updateFrequency: 'annual',
    geographicCoverage: 'state',
    temporalCoverage: '2021–2023',
    geographicLevel: 'state',
    tableName: 'crime_records_state',
    conceptMapping: {
      entity: 'state',
      year: 'year',
      category: 'category_label',
    },
    availableFields: [
      'state',
      'year',
      'category',
      'category_label',
      'total_cases',
      'rate_per_lakh',
      'confidence',
      'report_name',
    ],
    sourceUrl: 'https://ncrb.gov.in/crime-in-india.html',
  },
];

class RegistryService {
  private registry: DatasetRegistry = new Map();

  constructor() {
    this.load();
  }

  private load(): void {
    for (const def of STATIC_DEFINITIONS) {
      this.registry.set(def.id, def);
    }
  }

  getAll(): DatasetDefinition[] {
    return Array.from(this.registry.values());
  }

  get(id: string): DatasetDefinition | undefined {
    return this.registry.get(id);
  }

  exists(id: string): boolean {
    return this.registry.has(id);
  }

  getSummaries() {
    return this.getAll().map((d) => ({
      id: d.id,
      name: d.name,
      publishingBody: d.publishingBody,
      description: d.description,
      geographicCoverage: d.geographicCoverage,
      temporalCoverage: d.temporalCoverage,
      availableFields: d.availableFields,
    }));
  }
}

// Singleton — shared across all requests in a Worker isolate
export const registry = new RegistryService();

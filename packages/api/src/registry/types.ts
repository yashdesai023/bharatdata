// Core types for the Universal Registry System

export interface ColumnMapping {
  field: string;
  type: 'string' | 'integer' | 'float';
  role?: 'geographic_entity' | 'metric' | 'dimension';
}

export interface DatasetDefinition {
  id: string;
  name: string;
  publishingBody: string;
  description: string;
  updateFrequency: string;
  geographicCoverage: string;
  temporalCoverage: string;
  tableName: string;
  geographicLevel: string;
  // Maps the canonical concept (state, year) to actual DB column name
  conceptMapping: {
    entity: string;   // e.g., "entity_name" in district_crime_stats
    year?: string;    // e.g., "year"
    [key: string]: string | undefined;
  };
  availableFields: string[];
  sourceUrl?: string;
}

export type DatasetRegistry = Map<string, DatasetDefinition>;

// Registry Service: Loads BharatData source definitions.
// Now powered by generated-registry.json (synced from pipeline YAMLs).

import { DatasetDefinition, DatasetRegistry } from './types';
import generatedRegistry from './generated-registry.json';

class RegistryService {
  private registry: DatasetRegistry = new Map();

  constructor() {
    this.load();
  }

  private load(): void {
    // Load from the JSON generated at build-time
    const definitions = generatedRegistry as any[];
    
    for (const def of definitions) {
      this.registry.set(def.id, {
        ...def,
        // Ensure some fields have defaults if missing in YAML
        geographicCoverage: def.geographicCoverage || 'India',
        temporalCoverage: def.temporalCoverage || 'Recent',
      });
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
      updateFrequency: d.updateFrequency,
      availableFields: d.availableFields,
    }));
  }
}

// Singleton — shared across all requests in a Worker isolate
export const registry = new RegistryService();

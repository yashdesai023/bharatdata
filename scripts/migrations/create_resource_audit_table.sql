-- Migration: Create Resource Audit Table
-- --------------------------------------
-- This table tracks the cryptographic fidelity of individual government resources (States/Districts).

CREATE TABLE IF NOT EXISTS resource_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'success', 'failed', 'halted'
    record_count INT DEFAULT 0,
    payload_hash TEXT, -- SHA-256 of the raw API response
    error_message TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure we have one audit record per dataset-entity pair for quick status checks
    CONSTRAINT unique_resource_audit UNIQUE (dataset_id, entity_name)
);

-- Index for quick lookup of fidelity by dataset
CREATE INDEX IF NOT EXISTS idx_audit_dataset_entity ON resource_audit(dataset_id, entity_name);

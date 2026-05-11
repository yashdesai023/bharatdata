-- ============================================================
-- Migration: Add unique constraint for census_2011_pca upsert
-- Run this in Supabase SQL Editor BEFORE running the ingestion
-- ============================================================

-- Step 1: Ensure the table exists with the correct structure
-- (Run only if the table doesn't already exist)
CREATE TABLE IF NOT EXISTS public.census_2011_pca (
    id                  BIGSERIAL PRIMARY KEY,
    state_code          TEXT,
    district_code       TEXT,
    sub_district_code   TEXT,
    entity_name         TEXT,
    admin_level         TEXT,
    total_population    BIGINT,
    male_population     BIGINT,
    female_population   BIGINT,
    population_0_6      BIGINT,
    sc_population       BIGINT,
    st_population       BIGINT,
    literate_population BIGINT,
    main_workers        BIGINT,
    marginal_workers    BIGINT,
    non_workers         BIGINT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Step 2: Add the unique constraint required for upsert (ON CONFLICT)
-- This is the EXACT fix for error: 42P10
-- NOTE: If the table already has data, this will fail if there are duplicate rows.
-- In that case, run the DROP + RECREATE below instead.
ALTER TABLE public.census_2011_pca
    ADD CONSTRAINT census_2011_pca_unique_entity
    UNIQUE (state_code, district_code, sub_district_code, entity_name);

-- ============================================================
-- ALTERNATIVE: If the table already exists and you get an error
-- above, use this block to truncate and re-add cleanly.
-- Uncomment the lines below ONLY if the ALTER TABLE above fails:
-- ============================================================
-- TRUNCATE TABLE public.census_2011_pca;
-- ALTER TABLE public.census_2011_pca
--     ADD CONSTRAINT census_2011_pca_unique_entity
--     UNIQUE (state_code, district_code, sub_district_code, entity_name);

-- Step 3: Verify the constraint was created
SELECT
    conname AS constraint_name,
    contype AS type
FROM pg_constraint
WHERE conrelid = 'public.census_2011_pca'::regclass;

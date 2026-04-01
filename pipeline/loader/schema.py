import os
import sys

# Get the absolute path of the pipeline root to resolve imports cleanly
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.insert(0, pipeline_root)

from utils.db_connection import get_connection, get_cursor
from utils.logger_config import pipeline_logger as logger

SCHEMA_QUERIES = [
    # Enable UUID generation
    'CREATE EXTENSION IF NOT EXISTS "pgcrypto";',

    # Metadata Tables
    """
    CREATE TABLE IF NOT EXISTS data_sources (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT NOT NULL,
        source_url TEXT,
        publishing_body TEXT,
        data_format TEXT,
        update_frequency TEXT,
        last_ingested_at TIMESTAMPTZ,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_runs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        source_id UUID REFERENCES data_sources(id),
        started_at TIMESTAMPTZ DEFAULT NOW(),
        completed_at TIMESTAMPTZ,
        status TEXT DEFAULT 'running',
        files_processed INT DEFAULT 0,
        records_extracted INT DEFAULT 0,
        records_stored INT DEFAULT 0,
        records_skipped INT DEFAULT 0,
        parse_failures INT DEFAULT 0,
        error_message TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,

    # Data Tables (State)
    """
    CREATE TABLE IF NOT EXISTS crime_records_state (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ingestion_run_id UUID REFERENCES ingestion_runs(id),
        state TEXT NOT NULL,
        state_code TEXT NOT NULL,
        year INT NOT NULL,
        category TEXT NOT NULL,
        category_label TEXT NOT NULL,
        total_cases INT,
        rate_per_lakh FLOAT,
        chargesheeted INT,
        convicted INT,
        acquitted INT,
        pending_investigation INT,
        pending_trial INT,
        confidence FLOAT NOT NULL,
        source_url TEXT NOT NULL,
        source_file TEXT NOT NULL,
        report_name TEXT NOT NULL,
        publishing_body TEXT NOT NULL,
        collection_date TIMESTAMPTZ NOT NULL,
        normalizer_version TEXT NOT NULL,
        boundary_note TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT state_confidence_range 
            CHECK (confidence >= 0.0 AND confidence <= 1.0),
        CONSTRAINT state_year_range 
            CHECK (year >= 2000 AND year <= 2030),
        CONSTRAINT state_unique_record 
            UNIQUE (state, year, category, source_file)
    );
    """,

    # Data Tables (District)
    """
    CREATE TABLE IF NOT EXISTS crime_records_district (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ingestion_run_id UUID REFERENCES ingestion_runs(id),
        state TEXT NOT NULL,
        state_code TEXT NOT NULL,
        district TEXT NOT NULL,
        year INT NOT NULL,
        category TEXT NOT NULL,
        category_label TEXT NOT NULL,
        total_cases INT,
        rate_per_lakh FLOAT,
        chargesheeted INT,
        convicted INT,
        acquitted INT,
        pending_investigation INT,
        pending_trial INT,
        confidence FLOAT NOT NULL,
        source_url TEXT NOT NULL,
        source_file TEXT NOT NULL,
        report_name TEXT NOT NULL,
        publishing_body TEXT NOT NULL,
        collection_date TIMESTAMPTZ NOT NULL,
        normalizer_version TEXT NOT NULL,
        boundary_note TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT district_confidence_range 
            CHECK (confidence >= 0.0 AND confidence <= 1.0),
        CONSTRAINT district_unique_record 
            UNIQUE (state, district, year, category, source_file)
    );
    """,

    # Data Tables (City)
    """
    CREATE TABLE IF NOT EXISTS crime_records_city (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ingestion_run_id UUID REFERENCES ingestion_runs(id),
        city TEXT NOT NULL,
        parent_state TEXT NOT NULL,
        year INT NOT NULL,
        category TEXT NOT NULL,
        category_label TEXT NOT NULL,
        total_cases INT,
        rate_per_lakh FLOAT,
        chargesheeted INT,
        convicted INT,
        acquitted INT,
        pending_investigation INT,
        pending_trial INT,
        confidence FLOAT NOT NULL,
        source_url TEXT NOT NULL,
        source_file TEXT NOT NULL,
        report_name TEXT NOT NULL,
        publishing_body TEXT NOT NULL,
        collection_date TIMESTAMPTZ NOT NULL,
        normalizer_version TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT city_confidence_range 
            CHECK (confidence >= 0.0 AND confidence <= 1.0),
        CONSTRAINT city_unique_record 
            UNIQUE (city, year, category, source_file)
    );
    """,

    # Quality Tables
    """
    CREATE TABLE IF NOT EXISTS parse_failures (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ingestion_run_id UUID REFERENCES ingestion_runs(id),
        source_file TEXT NOT NULL,
        source_sheet TEXT,
        row_number INT,
        column_name TEXT,
        raw_value TEXT,
        expected_type TEXT,
        error_message TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS normalization_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        record_id UUID,
        field TEXT NOT NULL,
        input_value TEXT NOT NULL,
        output_value TEXT NOT NULL,
        mapping_source TEXT NOT NULL,
        confidence_impact FLOAT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS health_checks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ingestion_run_id UUID REFERENCES ingestion_runs(id),
        check_name TEXT NOT NULL,
        status TEXT NOT NULL,
        metrics JSONB,
        error_description TEXT,
        run_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,

    # File Tracking Table
    """
    CREATE TABLE IF NOT EXISTS ingested_files (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        file_path TEXT NOT NULL,
        file_hash_sha256 TEXT NOT NULL,
        file_size_bytes INT,
        year INT NOT NULL,
        table_type TEXT NOT NULL,
        geographic_level TEXT NOT NULL,
        records_extracted INT DEFAULT 0,
        ingested_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT unique_file_hash 
            UNIQUE (file_hash_sha256)
    );
    """,

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_crime_state_year ON crime_records_state(state, year);",
    "CREATE INDEX IF NOT EXISTS idx_crime_year ON crime_records_state(year);",
    "CREATE INDEX IF NOT EXISTS idx_crime_category ON crime_records_state(category);",
    "CREATE INDEX IF NOT EXISTS idx_crime_state_cat_year ON crime_records_state(state, category, year);",
    "CREATE INDEX IF NOT EXISTS idx_state_confidence_filter ON crime_records_state(confidence) WHERE confidence >= 0.5;",
    "CREATE INDEX IF NOT EXISTS idx_district_state ON crime_records_district(state);",
    "CREATE INDEX IF NOT EXISTS idx_district_state_year ON crime_records_district(state, year);",
    "CREATE INDEX IF NOT EXISTS idx_district_district ON crime_records_district(district);",
    "CREATE INDEX IF NOT EXISTS idx_district_category ON crime_records_district(category);",
    "CREATE INDEX IF NOT EXISTS idx_district_confidence_filter ON crime_records_district(confidence) WHERE confidence >= 0.5;",
    "CREATE INDEX IF NOT EXISTS idx_city_name ON crime_records_city(city);",
    "CREATE INDEX IF NOT EXISTS idx_city_year ON crime_records_city(city, year);",
    "CREATE INDEX IF NOT EXISTS idx_ingested_files_hash ON ingested_files(file_hash_sha256);",
    "CREATE INDEX IF NOT EXISTS idx_ingested_files_path ON ingested_files(file_path);"
]

def create_all_tables():
    """Execute all schema creation queries."""
    try:
        logger.info("Initializing Database Migration (Supabase Modern Schema)...")
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                for query in SCHEMA_QUERIES:
                    try:
                        cur.execute(query)
                        logger.debug(f"Executed Migration Step: {query[:40].strip()}...")
                    except Exception as e:
                        logger.error(f"Migration Failed for step: {e}")
                        conn.rollback()
                        continue
        
        logger.success("Schema Migration Created Successfully on Supabase.")
    except Exception as e:
        logger.error(f"Migration Fatal Error: {e}")

def verify_tables():
    """Verify that all expected tables are in the public schema."""
    try:
        with get_cursor() as cur:
            cur.execute('''
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' ORDER BY table_name;
            ''')
            tables = cur.fetchall()
            tables = [row[0] for row in tables]
            
            EXPECTED_TABLES = [
                "data_sources", "ingestion_runs", "crime_records_state", 
                "crime_records_district", "crime_records_city", "parse_failures", 
                "normalization_log", "health_checks", "ingested_files"
            ]
            
            missing = [t for t in EXPECTED_TABLES if t not in tables]
            extra = [t for t in tables if t not in EXPECTED_TABLES]
            
            logger.info(f"Verification Results: found {len(tables)} tables in DB.")
            for table_name in tables:
                logger.info(f"  - {table_name}")
                
            if missing:
                logger.warning(f"Missing tables: {missing}")
            if extra:
                logger.info(f"Extra tables: {extra}")

            if not missing:
                logger.success(f"DB Schema matches requirements! ({len(EXPECTED_TABLES)} core tables present).")
            else:
                logger.warning("DB Schema verification indicates mismatch with requirements.")
    except Exception as e:
        logger.error(f"Verification Failed: {e}")

if __name__ == "__main__":
    create_all_tables()
    verify_tables()

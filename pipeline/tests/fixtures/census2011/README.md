Census 2011 fixture directory

Purpose:
- Store minimal reproducible raw artifacts and golden outputs for the Census 2011 ingestion.
- Tests use this directory to validate parser behavior for Census 2011 sources.

Format:
- raw/<filename>  # raw source (PDF/HTML). Prefer not to commit large binaries; store a small representative sample.
- golden/<filename>.json  # expected normalized output for the raw sample

Notes:
- The ingestion pipeline is YAML-driven. Do not hardcode dataset-specific logic in tests; the test harness will load the source YAML and find the relevant parser/registry entry.
- Add additional samples for edge-cases (merged headers, multiple header rows) to improve parser coverage.
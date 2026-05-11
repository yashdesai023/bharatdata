"""
Supabase Batch Loader
----------------------
Pushes transformed records into Supabase via REST API.
Handles batching, upsert conflict resolution, and error aggregation.
"""

import os
import time
import requests
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class LoadResult:
    """Summary of a load operation."""
    total_submitted: int = 0
    total_inserted: int = 0  # Note: PostgREST return representation doesn't distinguish insert vs update easily
    total_failed: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_submitted == 0:
            return 0.0
        return (self.total_inserted) / self.total_submitted * 100

    def __str__(self) -> str:
        return (
            f"Submitted: {self.total_submitted} | "
            f"Processed: {self.total_inserted} | "
            f"Failed: {self.total_failed} | "
            f"Success Rate: {self.success_rate:.1f}%"
        )


class SupabaseLoadError(Exception):
    """Raised on non-recoverable Supabase load errors."""
    pass


class SupabaseLoader:
    """
    Batch loader for Supabase using the PostgREST REST API.

    Usage:
        loader = SupabaseLoader(table="census_2011_pca", unique_key=["state_code", "entity_name"])
        result = loader.load_batch(clean_records)
    """

    DEFAULT_BATCH_SIZE = 500
    MAX_RETRIES = 3
    RETRY_DELAY = 3

    def __init__(
        self,
        table: str,
        unique_key: List[str],
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        """
        Args:
            table: Target Supabase table name.
            unique_key: List of column names forming the unique constraint (for upsert).
            supabase_url: Supabase project URL (from env SUPABASE_URL).
            supabase_key: Supabase anon or service-role key (from env SUPABASE_ANON_KEY).
            batch_size: Number of records per HTTP request (500 recommended).
        """
        self.table = table
        self.unique_key = unique_key
        # Ensure URL is clean and doesn't have double slashes
        raw_url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.supabase_url = raw_url.rstrip("/")
        
        # Priority: explicit param -> SUPABASE_SERVICE_ROLE_KEY -> SUPABASE_ANON_KEY
        self.supabase_key = (
            supabase_key or 
            os.getenv("SUPABASE_SERVICE_ROLE_KEY") or 
            os.getenv("SUPABASE_ANON_KEY", "")
        )
        self.batch_size = batch_size

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase URL and Key are required. "
                "Set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file."
            )

        self.endpoint = f"{self.supabase_url}/rest/v1/{table}"
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _chunk(self, records: List[Dict]) -> List[List[Dict]]:
        """Split records into fixed-size batches."""
        return [
            records[i : i + self.batch_size]
            for i in range(0, len(records), self.batch_size)
        ]

    def _post_batch(self, batch: List[Dict[str, Any]]) -> int:
        """
        POST a single batch to Supabase with upsert semantics.
        """
        delay = self.RETRY_DELAY
        on_conflict = ",".join(self.unique_key)
        url = f"{self.endpoint}?on_conflict={on_conflict}"

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.session.post(url, json=batch, timeout=30)

                if response.status_code in (200, 201):
                    inserted = response.json()
                    # If return=representation is active, we get the list of processed rows
                    return len(inserted) if isinstance(inserted, list) else len(batch)

                elif response.status_code == 409:
                    # Conflict — usually means missing unique constraint in DB
                    logger.error(f"  DB Conflict (409): Verify unique constraint on {self.unique_key}")
                    raise SupabaseLoadError(f"Unique constraint conflict: {response.text}")

                elif response.status_code == 429:
                    logger.warning(f"  Rate limited by Supabase. Waiting 60s (Attempt {attempt})...")
                    time.sleep(60)
                    continue

                elif response.status_code >= 500:
                    logger.warning(
                        f"  Supabase server error ({response.status_code}). "
                        f"Attempt {attempt}/{self.MAX_RETRIES}"
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

                else:
                    raise SupabaseLoadError(
                        f"Supabase returned {response.status_code}: {response.text[:300]}"
                    )

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"  Network error (Attempt {attempt}): {e}")
                time.sleep(delay)
                delay *= 2

        raise SupabaseLoadError(
            f"Failed to load batch after {self.MAX_RETRIES} attempts."
        )

    def load_batch(self, records: List[Dict[str, Any]]) -> LoadResult:
        """
        Load a list of clean records into Supabase.
        Splits into sub-batches automatically.
        """
        result = LoadResult(total_submitted=len(records))

        if not records:
            return result

        # Remove None values to allow DB defaults/not-null checks to handle their part
        sanitized = [
            {k: v for k, v in rec.items() if v is not None}
            for rec in records
        ]

        chunks = self._chunk(sanitized)
        logger.info(
            f"Loading {len(records)} records into '{self.table}' "
            f"({len(chunks)} batches)..."
        )

        for i, chunk in enumerate(chunks, 1):
            try:
                count = self._post_batch(chunk)
                result.total_inserted += count
                logger.debug(f"  Batch {i}/{len(chunks)}: {count} rows processed.")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"  Batch {i}/{len(chunks)} FAILED: {error_msg}")
                result.total_failed += len(chunk)
                result.errors.append(error_msg)

        logger.info(f"Load result for '{self.table}': {result}")
        return result

    def count_rows(self) -> int:
        """
        Query the current row count of the target table.
        """
        headers = {**self.headers, "Prefer": "count=exact"}
        try:
            resp = self.session.get(
                self.endpoint,
                headers=headers,
                params={"select": "count", "limit": 1},
                timeout=15
            )
            if resp.status_code == 200:
                content_range = resp.headers.get("Content-Range", "*/0")
                total = content_range.split("/")[-1]
                return int(total)
        except Exception as e:
            logger.warning(f"Could not fetch row count: {e}")
        
        return -1

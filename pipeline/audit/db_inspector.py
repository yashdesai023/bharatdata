"""
Audit and DB Inspection Utilities
----------------------------------
Handles database-level logging of ingestion events and provides 
utilities for inspecting the state of ingested data.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from loguru import logger
from pipeline.core.loader import SupabaseLoader


class AuditWriter:
    """
    Writes ingestion audit logs to Supabase to maintain a permanent
    history of which resources were processed, when, and with what result.
    """

    AUDIT_TABLE = "resource_audit"

    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        # We use a separate loader for the audit table
        try:
            self.loader = SupabaseLoader(
                table=self.AUDIT_TABLE,
                unique_key=["dataset_id", "entity_name"] # Helps track current state per entity
            )
        except Exception as e:
            logger.warning(f"AuditWriter: Supabase not configured for audit logging: {e}")
            self.loader = None

    def log_event(
        self, 
        entity_name: str, 
        status: str, 
        resource_id: str,
        record_count: int = 0,
        error_message: Optional[str] = None,
        payload_hash: Optional[str] = None
    ):
        """
        Log an ingestion event to the audit table.
        """
        if not self.loader:
            return

        payload = {
            "dataset_id": self.dataset_id,
            "entity_name": entity_name,
            "resource_id": resource_id,
            "status": status,
            "record_count": record_count,
            "error_message": error_message,
            "payload_hash": payload_hash,
            "processed_at": datetime.now().isoformat()
        }

        try:
            # We don't want audit failures to crash the main pipeline
            self.loader.load_batch([payload])
            logger.debug(f"Audit log written for {entity_name}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def write_validation(
        self,
        dataset_id: str,
        status: str,
        checks_passed: list,
        checks_failed: list,
    ) -> None:
        if not self.loader:
            return

        payload = {
            "dataset_id": dataset_id,
            "entity_name": "__validation_gate__",
            "status": status,
            "error_log": str(checks_failed) if checks_failed else None,
            "run_metadata": {
                "checks_passed": [c[0] for c in checks_passed],
                "checks_failed": [c[0] for c in checks_failed],
                "pass_details": [c[1] for c in checks_passed],
                "fail_details": [c[1] for c in checks_failed],
            },
        }

        try:
            result = self.loader.load_batch([payload])
            if result.total_failed == 0 and result.total_inserted > 0:
                logger.debug("Validation gate record written")
            else:
                logger.warning(
                    f"Validation gate write completed with issues: {result.errors}"
                )
        except Exception as e:
            logger.warning(f"Failed to write validation gate record: {e}")

    def get_latest_validation(self) -> dict | None:
        if not self.loader:
            return None

        try:
            response = self.loader.session.get(
                self.loader.endpoint,
                headers=self.loader.headers,
                params={
                    "select": "*",
                    "dataset_id": f"eq.{self.dataset_id}",
                    "entity_name": "eq.__validation_gate__",
                    "order": "ingested_at.desc",
                    "limit": 1,
                },
                timeout=15,
            )

            if response.status_code != 200:
                logger.warning(
                    f"Could not fetch latest validation record: HTTP {response.status_code}"
                )
                return None

            data = response.json()
            if isinstance(data, list):
                return data[0] if data else None
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"Could not fetch latest validation record: {e}")

        return None

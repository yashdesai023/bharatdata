"""
OGD API Downloader
------------------
Integrates with OGDApiAdapter to download Census and other government datasets
from data.gov.in via the manifest file approach.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional

from pipeline.engine.downloaders.base import BaseDownloader
from pipeline.adapters.ogd_api import OGDApiAdapter, OGDRecord


class OGDDownloader(BaseDownloader):
    """
    Downloads data from data.gov.in OGD API using a manifest file that contains
    resource IDs organized by district/state.
    """

    def __init__(self, config):
        super().__init__(config)
        self.api_key = os.getenv(config.get('api_key_env', 'DATA_GOV_IN_API_KEY'))
        self.batch_size = config.get('batch_size', 1000)
        self.max_retries = config.get('max_retries', 5)
        self.retry_delay = config.get('retry_delay_seconds', 20)
        self.source_name = config.get('source_name', 'unknown')
        self.output_dir = Path("data/raw") / self.source_name
        self.manifest_path = config.get('manifest_file')
        self.resource_id = config.get('resource_id')  # Direct resource ID
        self.logger = logging.getLogger("OGDDownloader")

        if not self.api_key:
            raise ValueError(
                "OGD API key not found. Set DATA_GOV_IN_API_KEY in your .env file "
                "or provide api_key_env in the acquisition config."
            )

    def download(self, url=None, dest_folder=None) -> List[str]:  # pylint: disable=unused-argument
        """
        Downloads data from OGD API.
        Supports both manifest file and direct resource_id from config.
        Returns list of downloaded JSON file paths.
        """
        if dest_folder:
            self.output_dir = Path(dest_folder)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files = []

        # Check for direct resource_id first
        if self.resource_id:
            self.logger.info(f"Using direct resource_id: {self.resource_id}")
            try:
                file_path = self._fetch_resource(None, self.resource_id, self.resource_id)
                if file_path:
                    downloaded_files.append(str(file_path))
            except Exception as e:
                self.logger.error(f"Failed to fetch resource {self.resource_id}: {e}")

        # Fallback to manifest file
        elif self.manifest_path:
            resource_ids = self._load_manifest(self.manifest_path)
            if not resource_ids:
                self.logger.warning(f"No resource IDs found in manifest: {self.manifest_path}")
                return downloaded_files

            # Initialize adapter
            adapter = OGDApiAdapter(
                api_key=self.api_key,
                batch_size=self.batch_size,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay
            )

            # Fetch each resource
            for resource_info in resource_ids:
                resource_id = resource_info.get('resource_id')
                name = resource_info.get('name', resource_id)

                self.logger.info(f"Fetching resource: {name} ({resource_id})")

                try:
                    file_path = self._fetch_resource(adapter, resource_id, name)
                    if file_path:
                        downloaded_files.append(str(file_path))
                except Exception as e:
                    self.logger.error(f"Failed to fetch resource {resource_id}: {e}")
                    continue
        else:
            self.logger.warning("No resource_id or manifest_file configured")

        return downloaded_files

    def _load_manifest(self, manifest_path: str) -> List[dict]:
        """
        Loads resource IDs from manifest Excel file.
        Manifest expected columns: resource_id, name, state, district
        """
        try:
            import openpyxl
            wb = openpyxl.load_workbook(manifest_path, data_only=True)
            sheet = wb.active

            resources = []
            for row in sheet.iter_rows(min_row=2, values_only=True):  # Skip header
                if row and row[0]:  # First column is resource_id
                    resource_id = str(row[0]).strip()
                    if resource_id and resource_id not in ('None', ''):
                        name = str(row[1]) if len(row) > 1 and row[1] else resource_id
                        state = str(row[2]) if len(row) > 2 else None
                        district = str(row[3]) if len(row) > 3 else None
                        resources.append({
                            'resource_id': resource_id,
                            'name': name,
                            'state': state,
                            'district': district
                        })

            return resources

        except Exception as e:
            self.logger.error(f"Failed to load manifest {manifest_path}: {e}")
            return []

    def _fetch_resource(self, adapter: OGDApiAdapter, resource_id: str, name: str) -> Optional[Path]:
        """
        Fetches all records for a resource and saves to JSON file.
        If adapter is None, creates a new one.
        """
        output_file = self.output_dir / f"{name.replace(' ', '_')}.json"

        # Check if already downloaded (skip if exists)
        if output_file.exists() and output_file.stat().st_size > 100:
            self.logger.info(f"File already exists, skipping: {output_file}")
            return output_file

        # Create adapter if not provided
        if adapter is None:
            adapter = OGDApiAdapter(
                api_key=self.api_key,
                batch_size=self.batch_size,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay
            )

        all_records = []
        total = None

        try:
            # Probe first to get total count
            total = adapter.fetch_total_count(resource_id)
            self.logger.info(f"Resource {resource_id}: {total} total records")

            # Fetch all batches
            for ogd_record in adapter.fetch_all(resource_id):
                all_records.extend(ogd_record.data)
                self.logger.debug(f"Fetched {len(ogd_record.data)} records, total: {len(all_records)}/{total}")

            # Save to file
            output_data = {
                'resource_id': resource_id,
                'total': len(all_records),
                'records': all_records
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Saved {len(all_records)} records to {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"Failed to fetch resource {resource_id}: {e}")
            # Clean up partial file
            if output_file.exists():
                output_file.unlink()
            return None
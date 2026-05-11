import pandas as pd

from pipeline.adapters.ogd_api import OGDApiError
from pipeline.core.loader import LoadResult
from pipeline.core.orchestrator import BDIFOrchestrator


class TestEntityIsolation:
    def test_maharashtra_and_karnataka_complete_when_bihar_fails(self, monkeypatch):
        manifest_df = pd.DataFrame(
            [
                {"entity_name": "Maharashtra", "is_verified": "TRUE", "status": "pending"},
                {"entity_name": "Bihar", "is_verified": "TRUE", "status": "pending"},
                {"entity_name": "Karnataka", "is_verified": "TRUE", "status": "pending"},
            ]
        )

        orchestrator = BDIFOrchestrator(dataset_id="census_2011_pca", dry_run=True)
        call_log: list[str] = []

        def fake_process_resource(row):
            entity_name = row.get("entity_name") or row.get("state_name") or "Unknown"
            call_log.append(entity_name)
            if entity_name == "Bihar":
                raise OGDApiError("Simulated OGD truncation")
            return LoadResult(total_submitted=100, total_inserted=100, total_failed=0)

        monkeypatch.setattr(orchestrator, "_load_manifest_df", lambda: manifest_df.copy())
        monkeypatch.setattr(orchestrator, "_process_resource", fake_process_resource)
        monkeypatch.setattr(orchestrator, "_update_manifest_status", lambda *args, **kwargs: None)
        monkeypatch.setattr("pipeline.core.orchestrator.time.sleep", lambda _: None)

        summary = orchestrator.run()

        assert "Maharashtra" in call_log
        assert "Bihar" in call_log
        assert "Karnataka" in call_log
        assert summary.successful_entities == 2
        assert "Bihar" in summary.failed_entities
        assert "Karnataka" not in summary.failed_entities

from pathlib import Path
import json

from airesearch.candidates import CandidatePaper
from airesearch.launch_refresh import run_launch_refresh


class FakeProvider:
    name = "fake"

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        return [
            CandidatePaper(
                source="arxiv",
                source_id="1706.03762",
                title="Cosmos World Foundation Model for Physical AI",
                url="1706.03762",
                organizations=["NVIDIA"],
                venue="ICLR 2026",
                published_date="2026-01-15",
                year=2026,
                abstract="world foundation model physical AI",
            )
        ]


def test_run_launch_refresh_completes_duplicate_ingest_mvp_and_publish(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fact_fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    approved_manifest = tmp_path / "approved.txt"
    out_dir = tmp_path / "mvp"
    site_dir = tmp_path / "site"
    run_manifest = tmp_path / "launch-refresh.json"
    history_dir = tmp_path / "history"
    log_dir = tmp_path / "logs"

    result = run_launch_refresh(
        db_path=db_path,
        paper_db_path=paper_db,
        providers=[FakeProvider()],
        profile_names=["world_models_physical_ai"],
        limit_per_profile=5,
        select_limit=1,
        min_score=0.1,
        approved_manifest_path=approved_manifest,
        papi_executable="papi-not-needed-for-duplicate",
        out_dir=out_dir,
        site_dir=site_dir,
        run_manifest_path=run_manifest,
        history_dir=history_dir,
        log_dir=log_dir,
        fact_provider="fixture",
        fixture_path=fact_fixture,
    )

    assert result.discovery[0].stored_count == 1
    assert result.canonical.canonical_count == 1
    assert result.selected_count == 1
    assert result.approved_count == 1
    assert result.batch is not None
    assert result.batch.duplicate == 1
    assert result.mvp.papers_seen == 1
    assert result.mvp.fact_failures == 0
    assert result.publish.entrypoint == site_dir / "index.html"
    assert result.publish.diff_path == site_dir / "publish-diff.json"
    assert result.candidate_review.selected_count == 1
    assert result.candidate_review.json_path == out_dir / "candidate-review.json"
    assert result.candidate_review.markdown_path == out_dir / "candidate-review.md"
    assert result.candidate_review.json_path.exists()
    assert result.candidate_review.markdown_path is not None
    assert result.candidate_review.markdown_path.exists()
    assert result.run_history_path is not None
    assert result.run_history_path.exists()
    assert result.concise_log_path is not None
    assert result.concise_log_path.exists()
    assert approved_manifest.read_text(encoding="utf-8").strip() == "1706.03762"
    assert (site_dir / "index.html").exists()
    assert (site_dir / "publish-diff.json").exists()

    payload = json.loads(run_manifest.read_text(encoding="utf-8"))
    assert payload["profile_names"] == ["world_models_physical_ai"]
    assert payload["provider_names"] == ["fake"]
    assert payload["steps"][-1] == "publish-static-site"
    history_payload = json.loads(result.run_history_path.read_text(encoding="utf-8"))
    assert history_payload["run_manifest_path"] == str(run_manifest)
    assert history_payload["candidate_review"]["selected_count"] == 1
    assert history_payload["mvp"]["fact_failures"] == 0
    log_text = result.concise_log_path.read_text(encoding="utf-8")
    assert "discovered=1" in log_text
    assert f"candidate_review={out_dir / 'candidate-review.json'}" in log_text
    assert "fact_failures=0" in log_text
    assert f"publish_diff={site_dir / 'publish-diff.json'}" in log_text

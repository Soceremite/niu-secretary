from pathlib import Path

from airesearch.mvp_pipeline import run_mvp_pipeline


def test_run_mvp_pipeline_exports_bundle_and_site(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_dir = tmp_path / "mvp"

    result = run_mvp_pipeline(
        db_path=db_path,
        paper_db_path=paper_db,
        out_dir=out_dir,
        fact_provider="fixture",
        fixture_path=fixture,
    )

    assert result.papers_seen == 1
    assert result.cards_written == 1
    assert result.facts_written == 2
    assert result.fact_failures == 0
    assert result.hard_failures == 0
    assert (out_dir / "bundle" / "manifest.json").exists()
    assert result.site_path == out_dir / "bundle" / "index.html"
    assert "extract-artifact-ledger" in result.steps
    assert "generate-report-site" in result.steps

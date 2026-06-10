from pathlib import Path

from airesearch.candidates import CandidatePaper
from airesearch.db import connect, init_db
from airesearch.discovery import run_discovery
from airesearch.profiles import seed_profiles


class FakeProvider:
    name = "fake"

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        return [
            CandidatePaper(
                source="arxiv",
                source_id="2601.00001",
                title="Cosmos World Foundation Model for Physical AI",
                organizations=["NVIDIA"],
                venue="ICLR 2026",
                published_date="2026-01-15",
                year=2026,
                abstract="world foundation model physical AI",
            ),
            CandidatePaper(
                source="arxiv",
                source_id="2402.00001",
                title="Plain Old Simulation Paper",
                published_date="2024-02-01",
                year=2024,
                abstract="simulation",
            ),
            CandidatePaper(
                source="arxiv",
                source_id="2508.00001",
                title="Video World Model for Embodied Agents",
                published_date="2025-08-01",
                year=2025,
                abstract="video world model for embodied agents",
            ),
        ]


def test_run_discovery_stores_allowed_candidates_and_records_run(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    seed_profiles(db_path)

    result = run_discovery(
        db_path=db_path,
        profile_name="world_models_physical_ai",
        providers=[FakeProvider()],
        limit=10,
    )

    assert result.total_seen == 3
    assert result.stored_count == 2
    assert result.skipped_count == 1
    with connect(db_path) as conn:
        candidates = conn.execute("select title from research_candidates order by score desc").fetchall()
        run = conn.execute("select * from discovery_runs").fetchone()
    assert [row["title"] for row in candidates] == [
        "Cosmos World Foundation Model for Physical AI",
        "Video World Model for Embodied Agents",
    ]
    assert run["status"] == "success"
    assert run["stored_count"] == 2

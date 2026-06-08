import json
from pathlib import Path

from airesearch.candidates import CandidatePaper, score_candidate, upsert_candidate
from airesearch.canonical_candidates import (
    canonical_key_for_candidate,
    export_canonical_candidates,
    list_canonical_candidates,
    materialize_candidate_papers,
)
from airesearch.db import connect, init_db
from airesearch.profiles import load_profile, seed_profiles


def test_canonical_key_prefers_arxiv_id_from_url():
    row = {
        "source": "google_scholar",
        "source_id": "cluster-1",
        "title": "A Paper",
        "url": "https://arxiv.org/abs/2601.01234v2",
        "year": 2026,
    }

    assert canonical_key_for_candidate(row) == "arxiv:2601.01234"


def test_canonical_key_extracts_doi_before_provider_ids():
    row = {
        "source": "openalex",
        "source_id": "https://doi.org/10.1234/ABC.Def",
        "title": "A Paper",
        "url": "",
        "year": 2026,
    }

    assert canonical_key_for_candidate(row) == "doi:10.1234/abc.def"


def test_canonical_key_falls_back_to_title_year():
    row = {
        "source": "custom",
        "source_id": "",
        "title": "Robots Need More than VLA and World Models!",
        "url": "",
        "year": 2026,
    }

    assert canonical_key_for_candidate(row) == "title_year:robots need more than vla and world models:2026"


def test_materialize_candidate_papers_merges_provider_and_profile_duplicates(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    seed_profiles(db_path)
    world = load_profile(db_path, "world_models_physical_ai")
    embodied = load_profile(db_path, "embodied_ai_vla_robotics")

    arxiv_candidate = CandidatePaper(
        source="arxiv",
        source_id="2601.01234",
        title="Robots Need More than VLA and World Models",
        url="https://arxiv.org/abs/2601.01234",
        organizations=["NVIDIA"],
        published_date="2026-01-10",
        year=2026,
        abstract="world model physical AI robot vla",
    )
    scholar_candidate = CandidatePaper(
        source="google_scholar",
        source_id="cluster-123",
        title="Robots Need More than VLA and World Models",
        url="https://arxiv.org/abs/2601.01234v1",
        organizations=["NVIDIA"],
        published_date="2026-01-10",
        year=2026,
        abstract="world model physical AI robot vla",
    )

    for profile, candidate in [(world, arxiv_candidate), (embodied, scholar_candidate)]:
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)

    result = materialize_candidate_papers(db_path)

    assert result.candidates_seen == 2
    assert result.canonical_count == 1
    assert result.links_count == 2
    rows = list_canonical_candidates(db_path, 10)
    assert len(rows) == 1
    assert rows[0]["canonical_key"] == "arxiv:2601.01234"
    assert json.loads(rows[0]["profiles_json"]) == [
        "embodied_ai_vla_robotics",
        "world_models_physical_ai",
    ]
    assert json.loads(rows[0]["sources_json"]) == ["arxiv", "google_scholar"]


def test_export_canonical_candidates_writes_each_paper_once_in_score_order(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "canonical_manifest.txt"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")

    high = CandidatePaper(
        source="arxiv",
        source_id="2601.01234",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.01234",
        organizations=["NVIDIA"],
        published_date="2026-01-10",
        year=2026,
        abstract="world foundation model physical AI",
    )
    duplicate = CandidatePaper(
        source="google_scholar",
        source_id="cluster-123",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.01234",
        organizations=["NVIDIA"],
        published_date="2026-01-10",
        year=2026,
        abstract="world foundation model physical AI",
    )
    lower = CandidatePaper(
        source="arxiv",
        source_id="2507.00001",
        title="World Model for Agents",
        url="https://arxiv.org/abs/2507.00001",
        published_date="2025-07-01",
        year=2025,
        abstract="world model",
    )

    for candidate in [lower, duplicate, high]:
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)

    materialize_candidate_papers(db_path)
    written = export_canonical_candidates(db_path, 10, out_path)

    assert written == 2
    assert out_path.read_text(encoding="utf-8").splitlines() == [
        "https://arxiv.org/abs/2601.01234",
        "https://arxiv.org/abs/2507.00001",
    ]


def test_materialize_preserves_existing_canonical_status(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    candidate = CandidatePaper(
        source="arxiv",
        source_id="2601.01234",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.01234",
        published_date="2026-01-10",
        year=2026,
        abstract="world foundation model physical AI",
    )
    score, reasons = score_candidate(profile, candidate)
    upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)
    materialize_candidate_papers(db_path)
    with connect(db_path) as conn:
        conn.execute(
            "update candidate_papers set status = 'selected' where canonical_key = 'arxiv:2601.01234'"
        )
        conn.commit()

    materialize_candidate_papers(db_path)

    rows = list_canonical_candidates(db_path, 10)
    assert rows[0]["status"] == "selected"

import json
from pathlib import Path

from airesearch.candidates import CandidatePaper, score_candidate, upsert_candidate
from airesearch.canonical_candidates import (
    canonical_key_for_candidate,
    canonical_keys_for_existing_papers,
    export_approved_candidates,
    export_candidate_review,
    export_canonical_candidates,
    list_approved_candidates,
    list_canonical_candidates,
    materialize_candidate_papers,
    select_top_canonical_candidates,
    set_canonical_status,
    validate_status,
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


def test_review_workflow_selects_top_candidates_and_exports_only_selected(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "approved_manifest.txt"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    papers = [
        CandidatePaper(
            source="arxiv",
            source_id="2601.00001",
            title="Cosmos World Foundation Model for Physical AI",
            url="https://arxiv.org/abs/2601.00001",
            organizations=["NVIDIA"],
            published_date="2026-01-10",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.00002",
            title="Rejected World Model for Agents",
            url="https://arxiv.org/abs/2601.00002",
            published_date="2026-01-09",
            year=2026,
            abstract="world model agents",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2507.00001",
            title="World Model for Agents",
            url="https://arxiv.org/abs/2507.00001",
            published_date="2025-07-01",
            year=2025,
            abstract="world model",
        ),
    ]
    for candidate in papers:
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)
    materialize_candidate_papers(db_path)

    assert set_canonical_status(db_path, "arxiv:2601.00002", "rejected")
    selected = select_top_canonical_candidates(db_path, limit=2)
    written = export_approved_candidates(db_path, out_path)

    assert selected == 2
    assert written == 2
    assert [row["canonical_key"] for row in list_approved_candidates(db_path)] == [
        "arxiv:2601.00001",
        "arxiv:2507.00001",
    ]
    assert out_path.read_text(encoding="utf-8").splitlines() == [
        "https://arxiv.org/abs/2601.00001",
        "https://arxiv.org/abs/2507.00001",
    ]


def test_set_canonical_status_reports_unknown_key_and_validates_status(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    assert set_canonical_status(db_path, "arxiv:missing", "selected") is False

    try:
        validate_status("maybe")
    except ValueError as exc:
        assert "invalid canonical candidate status" in str(exc)
    else:
        raise AssertionError("validate_status should reject unknown values")


def test_select_top_canonical_candidates_respects_min_score(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    high = CandidatePaper(
        source="arxiv",
        source_id="2601.00001",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.00001",
        organizations=["NVIDIA"],
        published_date="2026-01-10",
        year=2026,
        abstract="world foundation model physical AI",
    )
    low = CandidatePaper(
        source="arxiv",
        source_id="2507.00001",
        title="World Model for Agents",
        url="https://arxiv.org/abs/2507.00001",
        published_date="2025-07-01",
        year=2025,
        abstract="world model",
    )
    for candidate in [high, low]:
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)
    materialize_candidate_papers(db_path)

    selected = select_top_canonical_candidates(db_path, limit=10, min_score=0.6)

    assert selected == 1
    assert [row["canonical_key"] for row in list_approved_candidates(db_path)] == ["arxiv:2601.00001"]


def test_select_top_canonical_candidates_skips_existing_papers(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    papers = [
        CandidatePaper(
            source="arxiv",
            source_id="2601.00001",
            title="Already Ingested World Model",
            url="https://arxiv.org/abs/2601.00001",
            organizations=["NVIDIA"],
            published_date="2026-01-10",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.00002",
            title="New World Model One",
            url="https://arxiv.org/abs/2601.00002",
            organizations=["NVIDIA"],
            published_date="2026-01-09",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.00003",
            title="New World Model Two",
            url="https://arxiv.org/abs/2601.00003",
            organizations=["NVIDIA"],
            published_date="2026-01-08",
            year=2026,
            abstract="world foundation model physical AI",
        ),
    ]
    for candidate in papers:
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)
    now = "2026-06-10T00:00:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2601_00001",
                "Already Ingested World Model",
                "[]",
                2026,
                "",
                json.dumps({"arxiv_id": "2601.00001"}),
                str(tmp_path / "paper"),
                json.dumps({"arxiv_id": "2601.00001"}),
                now,
                now,
            ),
        )
        conn.execute(
            """
            insert into paper_sources (paper_key, source_type, source_value, created_at)
            values (?, ?, ?, ?)
            """,
            ("2601_00001", "arxiv_id", "2601.00001", now),
        )
        conn.commit()
    materialize_candidate_papers(db_path)

    existing_keys = canonical_keys_for_existing_papers(db_path)
    selected = select_top_canonical_candidates(db_path, limit=2)

    assert "arxiv:2601.00001" in existing_keys
    assert selected == 2
    assert [row["canonical_key"] for row in list_approved_candidates(db_path)] == [
        "arxiv:2601.00002",
        "arxiv:2601.00003",
    ]


def test_export_candidate_review_explains_selection_outcomes(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    json_path = tmp_path / "candidate-review.json"
    markdown_path = tmp_path / "candidate-review.md"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    candidates = [
        CandidatePaper(
            source="arxiv",
            source_id="2601.10001",
            title="Already Ingested Candidate",
            url="https://arxiv.org/abs/2601.10001",
            published_date="2026-01-10",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.10002",
            title="Selected New Candidate",
            url="https://arxiv.org/abs/2601.10002",
            published_date="2026-01-09",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.10003",
            title="Top Limit Overflow Candidate",
            url="https://arxiv.org/abs/2601.10003",
            published_date="2026-01-08",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.10004",
            title="Manually Rejected Candidate",
            url="https://arxiv.org/abs/2601.10004",
            published_date="2026-01-07",
            year=2026,
            abstract="world foundation model physical AI",
        ),
        CandidatePaper(
            source="arxiv",
            source_id="2601.10005",
            title="Low Score Candidate",
            url="https://arxiv.org/abs/2601.10005",
            published_date="2026-01-06",
            year=2026,
            abstract="world model",
        ),
    ]
    for candidate in candidates:
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)
    materialize_candidate_papers(db_path)
    now = "2026-06-10T00:00:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2601_10001",
                "Already Ingested Candidate",
                "[]",
                2026,
                "",
                json.dumps({"arxiv_id": "2601.10001"}),
                str(tmp_path / "paper"),
                json.dumps({"arxiv_id": "2601.10001"}),
                now,
                now,
            ),
        )
        conn.execute(
            "update candidate_papers set best_score = 0.99 where canonical_key = 'arxiv:2601.10001'"
        )
        conn.execute(
            "update candidate_papers set best_score = 0.98 where canonical_key = 'arxiv:2601.10002'"
        )
        conn.execute(
            "update candidate_papers set best_score = 0.97 where canonical_key = 'arxiv:2601.10003'"
        )
        conn.execute(
            "update candidate_papers set best_score = 0.96, status = 'rejected' where canonical_key = 'arxiv:2601.10004'"
        )
        conn.execute(
            "update candidate_papers set best_score = 0.20 where canonical_key = 'arxiv:2601.10005'"
        )
        conn.commit()

    selected = select_top_canonical_candidates(db_path, limit=1, min_score=0.6)
    result = export_candidate_review(
        db_path,
        json_path,
        markdown_path=markdown_path,
        min_score=0.6,
        limit=1,
    )

    assert selected == 1
    assert result.total_count == 5
    assert result.selected_count == 1
    assert result.already_in_database_count == 1
    assert result.manually_rejected_count == 1
    assert result.below_min_score_count == 1
    assert result.not_in_top_limit_count == 1
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    reasons = {item["canonical_key"]: item["review_reason"] for item in payload["items"]}
    assert reasons == {
        "arxiv:2601.10001": "already_in_database",
        "arxiv:2601.10002": "selected",
        "arxiv:2601.10003": "not_in_top_limit",
        "arxiv:2601.10004": "manually_rejected",
        "arxiv:2601.10005": "below_min_score",
    }
    assert "already_in_database: 1" in markdown_path.read_text(encoding="utf-8")

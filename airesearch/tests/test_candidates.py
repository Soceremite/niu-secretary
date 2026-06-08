from pathlib import Path

from airesearch.candidates import (
    CandidatePaper,
    export_candidates,
    is_candidate_allowed,
    score_candidate,
    upsert_candidate,
)
from airesearch.db import init_db
from airesearch.profiles import default_profiles, seed_profiles


def world_profile():
    return {profile.name: profile for profile in default_profiles()}["world_models_physical_ai"]


def test_new_strongly_backed_candidate_beats_generic_old_candidate():
    profile = world_profile()
    strong = CandidatePaper(
        source="arxiv",
        source_id="2601.00001",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.00001",
        authors=["NVIDIA Research"],
        organizations=["NVIDIA"],
        venue="ICLR 2026",
        published_date="2026-01-15",
        year=2026,
        abstract="A world model for embodied agents and physical AI.",
        artifact_links=["https://github.com/nvidia/cosmos"],
    )
    generic = CandidatePaper(
        source="arxiv",
        source_id="2402.00001",
        title="A Generic Learning System",
        published_date="2024-02-01",
        year=2024,
        abstract="A broad machine learning paper.",
    )

    strong_score, strong_reasons = score_candidate(profile, strong)
    generic_score, generic_reasons = score_candidate(profile, generic)

    assert strong_score > generic_score
    assert "recency:2026_or_newer" in strong_reasons
    assert generic_score == 0.0
    assert "filtered:outside_recency_policy" in generic_reasons


def test_2024_candidate_allowed_only_with_exception_signal():
    profile = world_profile()
    famous = CandidatePaper(
        source="arxiv",
        source_id="2403.00001",
        title="Genie Interactive World Model",
        organizations=["Google DeepMind"],
        published_date="2024-03-01",
        year=2024,
        abstract="A generative world model for interactive environments.",
    )
    plain = CandidatePaper(
        source="arxiv",
        source_id="2403.00002",
        title="Small Simulation Study",
        published_date="2024-03-01",
        year=2024,
        abstract="A simulation paper.",
    )

    assert is_candidate_allowed(profile, famous)
    assert not is_candidate_allowed(profile, plain)


def test_export_candidates_writes_urls_in_score_order(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "manifest.txt"
    init_db(db_path)
    seed_profiles(db_path)
    profile = world_profile()
    a = CandidatePaper(
        source="arxiv",
        source_id="2601.00001",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.00001",
        organizations=["NVIDIA"],
        published_date="2026-01-15",
        year=2026,
        abstract="world foundation model physical AI",
    )
    b = CandidatePaper(
        source="arxiv",
        source_id="2507.00001",
        title="World Model for Agents",
        url="https://arxiv.org/abs/2507.00001",
        published_date="2025-07-01",
        year=2025,
        abstract="world model",
    )
    for candidate in (b, a):
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)

    written = export_candidates(db_path, profile.name, 2, out_path)

    assert written == 2
    assert out_path.read_text(encoding="utf-8").splitlines() == [
        "https://arxiv.org/abs/2601.00001",
        "https://arxiv.org/abs/2507.00001",
    ]

def test_candidate_filter_rejects_future_and_topicless_primary_results():
    profile = world_profile()

    future = CandidatePaper(
        source="openalex",
        source_id="future",
        title="Video World Model for Physical AI",
        published_date="2099-01-01",
        year=2099,
        abstract="world foundation model physical AI",
    )
    topicless = CandidatePaper(
        source="openalex",
        source_id="topicless",
        title="General Education Methods",
        published_date="2025-09-01",
        year=2025,
        abstract="classroom force concept practices",
    )

    future_score, future_reasons = score_candidate(profile, future)
    topicless_score, topicless_reasons = score_candidate(profile, topicless)

    assert future_score == 0.0
    assert "filtered:outside_recency_policy" in future_reasons
    assert topicless_score == 0.0
    assert "filtered:outside_recency_policy" in topicless_reasons



def test_google_scholar_gets_conservative_trusted_source_score():
    profile = next(profile for profile in default_profiles() if profile.name == "diffusion_models")
    candidate = CandidatePaper(
        source="google_scholar",
        source_id="abc",
        title="Diffusion Policy for Generalist Robot Foundation Models",
        url="https://arxiv.org/abs/2601.00001",
        venue="",
        published_date="2026-01-01",
        year=2026,
        abstract="diffusion policy for robot foundation models",
    )

    score, reasons = score_candidate(profile, candidate)

    assert score > 0
    assert "venue:trusted_source=google_scholar" in reasons

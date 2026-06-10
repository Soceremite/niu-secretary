from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.profiles import default_profiles, seed_profiles


def test_default_profiles_include_required_research_directions():
    names = {profile.name for profile in default_profiles()}

    assert {
        "multimodal_foundation_models",
        "unified_multimodal_understanding_generation",
        "world_models_physical_ai",
        "diffusion_models",
        "embodied_ai_vla_robotics",
    } == names


def test_seed_profiles_writes_default_profiles(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    count = seed_profiles(db_path)

    with connect(db_path) as conn:
        rows = conn.execute("select name, primary_since, exception_since from research_profiles").fetchall()

    assert count == 5
    assert len(rows) == 5
    assert {row["primary_since"] for row in rows} == {"2025-06-08"}
    assert {row["exception_since"] for row in rows} == {"2024-01-01"}

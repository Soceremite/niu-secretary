from pathlib import Path

from airesearch.cli import main


def test_cli_init_db(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "init-db"])

    assert code == 0
    assert db_path.exists()


def test_cli_status_empty_db(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"
    main(["--db", str(db_path), "init-db"])

    code = main(["--db", str(db_path), "status"])

    assert code == 0
    assert "papers: 0" in capsys.readouterr().out


def test_cli_sync_paperpipe(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"

    code = main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])

    assert code == 0
    assert "papers_seen=1" in capsys.readouterr().out



def test_cli_seed_profiles(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "seed-profiles"])

    assert code == 0
    assert "profiles_seeded=5" in capsys.readouterr().out


def test_cli_list_and_export_candidates(tmp_path: Path, capsys):
    from airesearch.candidates import CandidatePaper, score_candidate, upsert_candidate
    from airesearch.db import init_db
    from airesearch.profiles import load_profile, seed_profiles

    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "manifest.txt"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    candidate = CandidatePaper(
        source="arxiv",
        source_id="2601.00001",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.00001",
        organizations=["NVIDIA"],
        published_date="2026-01-15",
        year=2026,
        abstract="world foundation model physical AI",
    )
    score, reasons = score_candidate(profile, candidate)
    upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)

    list_code = main([
        "--db",
        str(db_path),
        "list-candidates",
        "--profile",
        profile.name,
        "--limit",
        "1",
    ])
    list_out = capsys.readouterr().out
    export_code = main([
        "--db",
        str(db_path),
        "export-candidates",
        "--profile",
        profile.name,
        "--limit",
        "1",
        "--out",
        str(out_path),
    ])

    assert list_code == 0
    assert "Cosmos World Foundation Model" in list_out
    assert export_code == 0
    assert out_path.read_text(encoding="utf-8") == "https://arxiv.org/abs/2601.00001\n"


from airesearch.cli import build_discovery_providers


def test_google_scholar_is_not_default_provider():
    providers = build_discovery_providers(None)

    assert [provider.name for provider in providers] == ["openalex", "arxiv", "semantic_scholar"]


def test_google_scholar_provider_can_be_selected(tmp_path, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-key")
    providers = build_discovery_providers(["google_scholar"], db_path=tmp_path / "db.sqlite3")

    assert [provider.name for provider in providers] == ["google_scholar"]


def test_google_scholar_refresh_cache_flag_is_passed(tmp_path, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-key")
    providers = build_discovery_providers(
        ["google_scholar"],
        db_path=tmp_path / "db.sqlite3",
        refresh_provider_cache=True,
    )

    assert providers[0].refresh_cache is True


def test_cli_dedupe_list_and_export_canonical_candidates(tmp_path: Path, capsys):
    from airesearch.candidates import CandidatePaper, score_candidate, upsert_candidate
    from airesearch.db import init_db
    from airesearch.profiles import load_profile, seed_profiles

    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "canonical_manifest.txt"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    candidate = CandidatePaper(
        source="arxiv",
        source_id="2601.01234",
        title="Cosmos World Foundation Model for Physical AI",
        url="https://arxiv.org/abs/2601.01234",
        organizations=["NVIDIA"],
        published_date="2026-01-15",
        year=2026,
        abstract="world foundation model physical AI",
    )
    score, reasons = score_candidate(profile, candidate)
    upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)

    dedupe_code = main(["--db", str(db_path), "dedupe-candidates"])
    dedupe_out = capsys.readouterr().out
    list_code = main(["--db", str(db_path), "list-canonical-candidates", "--limit", "1"])
    list_out = capsys.readouterr().out
    export_code = main([
        "--db",
        str(db_path),
        "export-canonical-candidates",
        "--limit",
        "1",
        "--out",
        str(out_path),
    ])
    export_out = capsys.readouterr().out

    assert dedupe_code == 0
    assert "canonical=1" in dedupe_out
    assert list_code == 0
    assert "Cosmos World Foundation Model" in list_out
    assert export_code == 0
    assert "canonical_candidates_exported=1" in export_out
    assert out_path.read_text(encoding="utf-8") == "https://arxiv.org/abs/2601.01234\n"

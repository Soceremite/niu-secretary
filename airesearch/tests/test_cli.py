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


def test_cli_review_status_select_and_export_approved_candidates(tmp_path: Path, capsys):
    from airesearch.candidates import CandidatePaper, score_candidate, upsert_candidate
    from airesearch.canonical_candidates import materialize_candidate_papers
    from airesearch.db import init_db
    from airesearch.profiles import load_profile, seed_profiles

    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "approved_manifest.txt"
    init_db(db_path)
    seed_profiles(db_path)
    profile = load_profile(db_path, "world_models_physical_ai")
    for source_id, title in [
        ("2601.00001", "Cosmos World Foundation Model for Physical AI"),
        ("2507.00001", "World Model for Agents"),
    ]:
        candidate = CandidatePaper(
            source="arxiv",
            source_id=source_id,
            title=title,
            url=f"https://arxiv.org/abs/{source_id}",
            organizations=["NVIDIA"] if source_id.startswith("2601") else [],
            published_date="2026-01-15" if source_id.startswith("2601") else "2025-07-01",
            year=2026 if source_id.startswith("2601") else 2025,
            abstract="world foundation model physical AI",
        )
        score, reasons = score_candidate(profile, candidate)
        upsert_candidate(db_path, profile_name=profile.name, candidate=candidate, score=score, reasons=reasons)
    materialize_candidate_papers(db_path)

    reject_code = main([
        "--db",
        str(db_path),
        "set-canonical-status",
        "arxiv:2507.00001",
        "--status",
        "rejected",
    ])
    reject_out = capsys.readouterr().out
    select_code = main(["--db", str(db_path), "select-canonical-candidates", "--limit", "5"])
    select_out = capsys.readouterr().out
    export_code = main(["--db", str(db_path), "export-approved-candidates", "--out", str(out_path)])
    export_out = capsys.readouterr().out

    assert reject_code == 0
    assert "status=rejected" in reject_out
    assert select_code == 0
    assert "canonical_candidates_selected=1" in select_out
    assert export_code == 0
    assert "approved_candidates_exported=1" in export_out
    assert out_path.read_text(encoding="utf-8") == "https://arxiv.org/abs/2601.00001\n"


def test_cli_set_canonical_status_unknown_key_returns_error(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main([
        "--db",
        str(db_path),
        "set-canonical-status",
        "arxiv:missing",
        "--status",
        "selected",
    ])

    assert code == 2
    assert "canonical_candidate_not_found=arxiv:missing" in capsys.readouterr().out


def test_cli_extract_list_and_export_paper_cards(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    out_path = tmp_path / "paper_cards.jsonl"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    extract_code = main(["--db", str(db_path), "extract-paper-cards"])
    extract_out = capsys.readouterr().out
    list_code = main(["--db", str(db_path), "list-paper-cards", "--limit", "1"])
    list_out = capsys.readouterr().out
    export_code = main(["--db", str(db_path), "export-paper-cards", "--out", str(out_path)])
    export_out = capsys.readouterr().out
    status_code = main(["--db", str(db_path), "status"])
    status_out = capsys.readouterr().out

    assert extract_code == 0
    assert "cards=1" in extract_out
    assert list_code == 0
    assert "Attention Is All You Need" in list_out
    assert export_code == 0
    assert "paper_cards_exported=1" in export_out
    assert status_code == 0
    assert "paper_cards: 1" in status_out
    payload = json.loads(out_path.read_text(encoding="utf-8").strip())
    assert payload["paper_key"] == "1706_03762"


def test_cli_extract_list_and_export_research_facts(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_path = tmp_path / "research_facts.jsonl"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    extract_code = main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    extract_out = capsys.readouterr().out
    list_code = main(["--db", str(db_path), "list-research-facts", "--type", "method", "--limit", "5"])
    list_out = capsys.readouterr().out
    export_code = main(["--db", str(db_path), "export-research-facts", "--out", str(out_path)])
    export_out = capsys.readouterr().out
    status_code = main(["--db", str(db_path), "status"])
    status_out = capsys.readouterr().out

    assert extract_code == 0
    assert "facts=2" in extract_out
    assert list_code == 0
    assert "Transformer replaces recurrence" in list_out
    assert export_code == 0
    assert "research_facts_exported=2" in export_out
    assert status_code == 0
    assert "research_facts: 2" in status_out
    payload = json.loads(out_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["evidence_quote"]


def test_cli_extract_list_and_export_code_links(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    out_path = tmp_path / "code_links.jsonl"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    extract_code = main(["--db", str(db_path), "extract-code-links"])
    extract_out = capsys.readouterr().out
    list_code = main(["--db", str(db_path), "list-code-links", "--limit", "5"])
    list_out = capsys.readouterr().out
    export_code = main(["--db", str(db_path), "export-code-links", "--out", str(out_path)])
    export_out = capsys.readouterr().out
    status_code = main(["--db", str(db_path), "status"])
    status_out = capsys.readouterr().out

    assert extract_code == 0
    assert "code_links=1" in extract_out
    assert list_code == 0
    assert "https://github.com/attention/transformer" in list_out
    assert export_code == 0
    assert "code_links_exported=1" in export_out
    assert status_code == 0
    assert "code_links: 1" in status_out
    payload = json.loads(out_path.read_text(encoding="utf-8").strip())
    assert payload["repo"] == "transformer"

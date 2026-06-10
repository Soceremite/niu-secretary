import json
from pathlib import Path

from airesearch.cli import main
from airesearch.db import connect
from test_evidence_repair import make_repair_db


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
    review_path = tmp_path / "candidate-review.json"
    review_markdown_path = tmp_path / "candidate-review.md"
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
    review_code = main([
        "--db",
        str(db_path),
        "export-candidate-review",
        "--out",
        str(review_path),
        "--markdown-out",
        str(review_markdown_path),
        "--limit",
        "5",
        "--min-score",
        "0.1",
    ])
    review_out = capsys.readouterr().out

    assert reject_code == 0
    assert "status=rejected" in reject_out
    assert select_code == 0
    assert "canonical_candidates_selected=1" in select_out
    assert export_code == 0
    assert "approved_candidates_exported=1" in export_out
    assert out_path.read_text(encoding="utf-8") == "https://arxiv.org/abs/2601.00001\n"
    assert review_code == 0
    assert "candidate_review_exported total=2 selected=1" in review_out
    assert "candidate_review_markdown=" in review_out
    review_payload = json.loads(review_path.read_text(encoding="utf-8"))
    reasons = {item["canonical_key"]: item["review_reason"] for item in review_payload["items"]}
    assert reasons["arxiv:2601.00001"] == "selected"
    assert reasons["arxiv:2507.00001"] == "manually_rejected"
    assert "manually_rejected: 1" in review_markdown_path.read_text(encoding="utf-8")


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
    assert "failed=0" in extract_out
    assert list_code == 0
    assert "Transformer replaces recurrence" in list_out
    assert export_code == 0
    assert "research_facts_exported=2" in export_out
    assert status_code == 0
    assert "research_facts: 2" in status_out
    payload = json.loads(out_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["evidence_quote"]


def test_cli_claim_trace_prints_markdown_and_exports_json(tmp_path: Path, capsys):
    import json

    from airesearch.db import connect

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_path = tmp_path / "claim-trace.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    main(["--db", str(db_path), "extract-code-links"])
    main(["--db", str(db_path), "extract-paper-cards"])
    capsys.readouterr()
    with connect(db_path) as conn:
        fact_id = conn.execute(
            "select id from research_facts where fact_type = 'claim' order by id limit 1"
        ).fetchone()["id"]

    markdown_code = main(["--db", str(db_path), "claim-trace", "--fact-id", str(fact_id)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "claim-trace",
        "--paper-key",
        "1706_03762",
        "--type",
        "method",
        "--query",
        "recurrence",
        "--format",
        "json",
        "--out",
        str(out_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "# Claim Trace" in markdown_out
    assert "Attention Is All You Need" in markdown_out
    assert "https://github.com/attention/transformer" in markdown_out
    assert json_code == 0
    assert "claim_trace_exported format=json" in json_out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["fact"]["fact_type"] == "method"
    assert payload["artifacts"][0]["artifact_type"] == "summary"


def test_cli_claim_trace_missing_fact_returns_2(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "claim-trace", "--fact-id", "999999"])
    out = capsys.readouterr().out

    assert code == 2
    assert "claim_trace_not_found fact_id=999999" in out


def test_cli_extract_and_export_artifact_ledger(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    markdown_path = tmp_path / "artifact-ledger.md"
    json_path = tmp_path / "artifact-ledger.json"
    jsonl_path = tmp_path / "artifact-ledger.jsonl"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    extract_code = main([
        "--db",
        str(db_path),
        "extract-artifact-ledger",
        "--paper-key",
        "1706_03762",
    ])
    extract_out = capsys.readouterr().out
    markdown_code = main(["--db", str(db_path), "export-artifact-ledger", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "export-artifact-ledger",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out
    jsonl_code = main([
        "--db",
        str(db_path),
        "export-artifact-ledger",
        "--format",
        "jsonl",
        "--out",
        str(jsonl_path),
    ])
    jsonl_out = capsys.readouterr().out

    assert extract_code == 0
    assert "artifact_ledger_extracted papers_seen=1" in extract_out
    assert "equations_written=1" in extract_out
    assert markdown_code == 0
    assert "artifact_ledger_exported papers=1" in markdown_out
    assert "# AIResearch Artifact Ledger" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "format=json" in json_out
    assert json.loads(json_path.read_text(encoding="utf-8"))["equation_count"] == 1
    assert jsonl_code == 0
    assert "format=jsonl" in jsonl_out
    assert json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])["kind"] == "chunk"


def test_cli_audit_research_facts_passes_for_fixture_facts(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main(["--db", str(db_path), "audit-research-facts"])
    out = capsys.readouterr().out

    assert code == 0
    assert "total_facts=2" in out
    assert "hard_failures=0" in out


def test_cli_audit_research_facts_fails_for_empty_statement(tmp_path: Path, capsys):
    from airesearch.db import connect, init_db

    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    now = "2026-06-09T00:00:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("bad_paper", "Bad Paper", "[]", 2026, "TestConf", "{}", "/tmp/bad", "{}", now, now),
        )
        cursor = conn.execute(
            """
            insert into research_facts (
                paper_key, fact_type, name, statement, confidence, metadata_json,
                provider_name, extractor_version, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("bad_paper", "method", "", "", 0.9, "{}", "test", "audit-test", now, now),
        )
        conn.execute(
            """
            insert into research_fact_provenance (
                fact_id, evidence_quote, evidence_artifact_type, evidence_source_path, created_at
            ) values (?, ?, ?, ?, ?)
            """,
            (cursor.lastrowid, "quote", "summary", "/tmp/summary.md", now),
        )

    code = main(["--db", str(db_path), "audit-research-facts"])
    out = capsys.readouterr().out

    assert code == 1
    assert "empty_statement=1" in out
    assert "hard_failures=1" in out


def test_cli_repair_evidence_source_paths_dry_run(tmp_path: Path, capsys):
    import json

    db_path, _summary_path = make_repair_db(tmp_path)
    out_path = tmp_path / "repair.jsonl"

    code = main(["--db", str(db_path), "repair-evidence-source-paths", "--out", str(out_path)])
    out = capsys.readouterr().out

    assert code == 0
    assert "evidence_source_path_repair candidates=1 repairable=1 applied=0" in out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["repairable"] is True
    with connect(db_path) as conn:
        row = conn.execute("select evidence_source_path from research_fact_provenance").fetchone()
    assert row["evidence_source_path"] == ""


def test_cli_repair_evidence_source_paths_apply(tmp_path: Path, capsys):
    db_path, summary_path = make_repair_db(tmp_path)
    out_path = tmp_path / "repair.jsonl"

    code = main([
        "--db",
        str(db_path),
        "repair-evidence-source-paths",
        "--apply",
        "--out",
        str(out_path),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "evidence_source_path_repair candidates=1 repairable=1 applied=1" in out
    with connect(db_path) as conn:
        row = conn.execute("select evidence_source_path from research_fact_provenance").fetchone()
    assert row["evidence_source_path"] == str(summary_path)


def test_cli_generate_research_digest_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "digest.md"
    json_path = tmp_path / "digest.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-research-digest", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-research-digest",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "research_digest_exported=1 facts=2 format=markdown" in markdown_out
    assert "# AIResearch Digest" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "research_digest_exported=1 facts=2 format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["papers"][0]["paper_key"] == "1706_03762"


def test_cli_generate_research_digest_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-research-digest", "--out", str(tmp_path / "digest.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_research_map_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "research-map.md"
    json_path = tmp_path / "research-map.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-research-map", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-research-map",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "research_map_exported=1 facts=2 items=2 format=markdown" in markdown_out
    assert "# AIResearch Research Map" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "research_map_exported=1 facts=2 items=2 format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["item_count"] == 2
    assert payload["sections"][0]["items"][0]["papers"][0]["paper_key"] == "1706_03762"


def test_cli_generate_research_map_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-research-map", "--out", str(tmp_path / "research-map.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_research_relations_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "relations.md"
    json_path = tmp_path / "relations.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-research-relations", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-research-relations",
        "--out",
        str(json_path),
        "--format",
        "json",
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "research_relations_exported=1 facts=2 relations=0" in markdown_out
    assert json_code == 0
    assert "research_relations_exported=1 facts=2 relations=0" in json_out
    assert "# AIResearch Cross-Paper Relations" in markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["citation_status"]["status"] == "citation_ledger_missing"


def test_cli_generate_research_relations_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-research-relations", "--out", str(tmp_path / "relations.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_gap_analysis_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "gap-analysis.md"
    json_path = tmp_path / "gap-analysis.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-gap-analysis", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-gap-analysis",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "gap_analysis_exported=1 facts=2 missing_papers=1 format=markdown" in markdown_out
    assert "# AIResearch Gap Analysis" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "gap_analysis_exported=1 facts=2 missing_papers=1 format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["papers"][0]["paper_key"] == "1706_03762"
    assert payload["papers"][0]["missing_fact_types"] == ["dataset", "benchmark", "limitation"]


def test_cli_generate_gap_analysis_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-gap-analysis", "--out", str(tmp_path / "gap-analysis.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_research_synthesis_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "research-synthesis.md"
    json_path = tmp_path / "research-synthesis.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-research-synthesis", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-research-synthesis",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "research_synthesis_exported=1 facts=2 targets=1 format=markdown" in markdown_out
    assert "# AIResearch Research Synthesis" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "research_synthesis_exported=1 facts=2 targets=1 format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["extraction_targets"][0]["paper_key"] == "1706_03762"
    assert payload["weak_coverage"]["fact_types"][0]["fact_type"] == "dataset"


def test_cli_generate_research_synthesis_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-research-synthesis", "--out", str(tmp_path / "synthesis.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_narrative_report_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "research-narrative.md"
    json_path = tmp_path / "research-narrative.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-narrative-report", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-narrative-report",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "narrative_report_exported=1 facts=2 findings=2 actions=1 format=markdown" in markdown_out
    assert "# AIResearch Narrative Report" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "narrative_report_exported=1 facts=2 findings=2 actions=1 format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["representative_findings"][0]["paper_key"] == "1706_03762"
    assert payload["priority_actions"][0]["paper_key"] == "1706_03762"


def test_cli_generate_narrative_report_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-narrative-report", "--out", str(tmp_path / "narrative.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_research_clusters_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "research-clusters.md"
    json_path = tmp_path / "research-clusters.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-research-clusters", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-research-clusters",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "research_clusters_exported=1 facts=2 clusters=0 singletons=2 mode=token format=markdown" in markdown_out
    assert "# AIResearch Research Clusters" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "research_clusters_exported=1 facts=2 clusters=0 singletons=2 mode=token format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "token"
    assert payload["cluster_count"] == 0
    assert payload["singleton_count"] == 2


def test_cli_generate_research_clusters_semantic_requires_embedding_env(tmp_path: Path, capsys, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    for key in [
        "AIRESEARCH_EMBEDDING_MODEL",
        "PAPERPIPE_EMBEDDING_MODEL",
        "OPENAI_EMBEDDING_MODEL",
        "AIRESEARCH_EMBEDDING_API_KEY",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "generate-research-clusters",
        "--mode",
        "semantic",
        "--semantic-threshold",
        "0.9",
        "--out",
        str(tmp_path / "clusters.md"),
    ])
    out = capsys.readouterr().out

    assert code == 2
    assert "semantic clustering requires AIRESEARCH_EMBEDDING_MODEL" in out


def test_cli_generate_research_clusters_semantic_with_embedding_provider(tmp_path: Path, capsys, monkeypatch):
    import json

    class FakeProvider:
        @classmethod
        def from_env(cls):
            return cls()

        def embed_texts(self, texts):
            return [[1.0, 0.0] for _text in texts]

    monkeypatch.setattr("airesearch.cli.OpenAICompatibleEmbeddingProvider", FakeProvider)
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_path = tmp_path / "semantic-clusters.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "generate-research-clusters",
        "--mode",
        "semantic",
        "--format",
        "json",
        "--out",
        str(out_path),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "mode=semantic format=json" in out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "semantic"
    assert payload["semantic_threshold"] == 0.82


def test_cli_calibrate_research_clusters_with_embedding_provider(tmp_path: Path, capsys, monkeypatch):
    import json

    class FakeProvider:
        model = "fixture-embedding"

        @classmethod
        def from_env(cls):
            return cls()

        def embed_texts(self, texts):
            vectors = []
            for text in texts:
                if "translation" in text.lower():
                    vectors.append([1.0, 0.0])
                else:
                    vectors.append([0.0, 1.0])
            return vectors

    monkeypatch.setattr("airesearch.cli.OpenAICompatibleEmbeddingProvider", FakeProvider)
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_path = tmp_path / "cluster-calibration.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "calibrate-research-clusters",
        "--format",
        "json",
        "--threshold",
        "0.7",
        "--threshold",
        "0.9",
        "--out",
        str(out_path),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "cluster_calibration_exported=1 facts=2 thresholds=2 recommended_threshold=" in out
    assert "model=fixture-embedding format=json" in out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["embedding_model"] == "fixture-embedding"
    assert "recommendation" in payload
    assert [point["threshold"] for point in payload["points"]] == [0.7, 0.9]


def test_cli_generate_cluster_review_markdown_and_json(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    markdown_path = tmp_path / "cluster-review.md"
    json_path = tmp_path / "cluster-review.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    markdown_code = main(["--db", str(db_path), "generate-cluster-review", "--out", str(markdown_path)])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "--db",
        str(db_path),
        "generate-cluster-review",
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "cluster_review_exported=1 facts=2 items=0 accept_candidates=0 needs_review=0 mode=token" in markdown_out
    assert "# AIResearch Cluster Review Packet" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "token"
    assert payload["review_item_count"] == 0


def test_cli_generate_cluster_review_semantic_with_embedding_provider(tmp_path: Path, capsys, monkeypatch):
    import json

    class FakeProvider:
        @classmethod
        def from_env(cls):
            return cls()

        def embed_texts(self, texts):
            return [[1.0, 0.0] for _text in texts]

    monkeypatch.setattr("airesearch.cli.OpenAICompatibleEmbeddingProvider", FakeProvider)
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_path = tmp_path / "semantic-cluster-review.json"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "generate-cluster-review",
        "--mode",
        "semantic",
        "--format",
        "json",
        "--out",
        str(out_path),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "mode=semantic format=json" in out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "semantic"
    assert payload["semantic_threshold"] == 0.82


def test_cli_generate_cluster_review_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-cluster-review", "--out", str(tmp_path / "review.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_summarize_cluster_review_markdown_and_json(tmp_path: Path, capsys):
    import json

    review_path = tmp_path / "cluster-review.json"
    markdown_path = tmp_path / "review-summary.md"
    json_path = tmp_path / "review-summary.json"
    review_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 2,
                "fact_count": 2,
                "mode": "semantic",
                "semantic_threshold": 0.82,
                "items": [
                    {
                        "cluster_id": "method:attention-world",
                        "fact_type": "method",
                        "label": "Attention World",
                        "token_signature": ["attention", "world"],
                        "paper_count": 2,
                        "fact_count": 2,
                        "average_confidence": 0.91,
                        "recommended_status": "accept_candidate",
                        "review_status": "accepted",
                        "review_notes": "Confirmed by reviewer.",
                        "rationale": "Cross-paper support.",
                        "facts": [
                            {
                                "paper_key": "paper_a",
                                "paper_title": "Paper A",
                                "year": 2026,
                                "fact_name": "Attention model",
                                "statement": "Uses attention.",
                                "confidence": 0.9,
                                "evidence_source_path": "/tmp/a.md",
                            },
                            {
                                "paper_key": "paper_b",
                                "paper_title": "Paper B",
                                "year": 2026,
                                "fact_name": "Attention model",
                                "statement": "Uses attention.",
                                "confidence": 0.92,
                                "evidence_source_path": "/tmp/b.md",
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    markdown_code = main([
        "summarize-cluster-review",
        "--review-packet",
        str(review_path),
        "--out",
        str(markdown_path),
    ])
    markdown_out = capsys.readouterr().out
    json_code = main([
        "summarize-cluster-review",
        "--review-packet",
        str(review_path),
        "--format",
        "json",
        "--out",
        str(json_path),
    ])
    json_out = capsys.readouterr().out

    assert markdown_code == 0
    assert "cluster_review_summary_exported=1 accepted=1 accepted_facts=2 accepted_papers=2" in markdown_out
    assert "# AIResearch Reviewed Cluster Summary" in markdown_path.read_text(encoding="utf-8")
    assert json_code == 0
    assert "format=json" in json_out
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["accepted_count"] == 1
    assert payload["accepted_items"][0]["review_notes"] == "Confirmed by reviewer."


def test_cli_summarize_cluster_review_rejects_invalid_status(tmp_path: Path, capsys):
    import json

    review_path = tmp_path / "cluster-review.json"
    item = {
        "cluster_id": "method:attention-world",
        "fact_type": "method",
        "label": "Attention World",
        "token_signature": ["attention", "world"],
        "paper_count": 1,
        "fact_count": 1,
        "average_confidence": 0.91,
        "recommended_status": "needs_review",
        "review_status": "approved",
        "review_notes": "",
        "rationale": "Test item.",
        "facts": [
            {
                "paper_key": "paper_a",
                "paper_title": "Paper A",
                "year": 2026,
                "fact_name": "Attention model",
                "statement": "Uses attention.",
                "confidence": 0.9,
                "evidence_source_path": "/tmp/a.md",
            }
        ],
    }
    review_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 0,
                "fact_count": 0,
                "mode": "token",
                "semantic_threshold": None,
                "items": [item],
            }
        ),
        encoding="utf-8",
    )

    code = main([
        "summarize-cluster-review",
        "--review-packet",
        str(review_path),
        "--out",
        str(tmp_path / "summary.md"),
    ])
    out = capsys.readouterr().out

    assert code == 2
    assert "unsupported review_status" in out


def test_cli_set_cluster_review_status_updates_json(tmp_path: Path, capsys):
    import json

    review_path = tmp_path / "cluster-review.json"
    out_path = tmp_path / "cluster-review-edited.json"
    review_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 1,
                "mode": "token",
                "semantic_threshold": None,
                "items": [
                    {
                        "cluster_id": "method:attention-world",
                        "fact_type": "method",
                        "label": "Attention World",
                        "token_signature": ["attention", "world"],
                        "paper_count": 1,
                        "fact_count": 1,
                        "average_confidence": 0.91,
                        "recommended_status": "needs_review",
                        "review_status": "pending",
                        "review_notes": "",
                        "rationale": "Test item.",
                        "facts": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    code = main([
        "set-cluster-review-status",
        "--review-packet",
        str(review_path),
        "--cluster-id",
        "method:attention-world",
        "--status",
        "accepted",
        "--notes",
        "Confirmed.",
        "--out",
        str(out_path),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "cluster_review_status_updated=method:attention-world previous=pending status=accepted" in out
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["items"][0]["review_status"] == "accepted"
    assert payload["items"][0]["review_notes"] == "Confirmed."


def test_cli_generate_research_clusters_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-research-clusters", "--out", str(tmp_path / "clusters.md")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_report_bundle(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_dir = tmp_path / "report-bundle"
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-artifact-ledger"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main(["--db", str(db_path), "generate-report-bundle", "--out-dir", str(out_dir)])
    out = capsys.readouterr().out

    assert code == 0
    assert "report_bundle_exported=18 papers=1 facts=2" in out
    payload = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["artifact_count"] == 18
    assert payload["artifacts"][0]["markdown_path"] == "digest.md"
    assert payload["artifacts"][1]["markdown_path"] == "artifact-ledger.md"
    assert payload["artifacts"][3]["markdown_path"] == "relations.md"
    assert payload["artifacts"][7]["markdown_path"] == "clusters.md"
    assert "# AIResearch Report Bundle" in (out_dir / "index.md").read_text(encoding="utf-8")


def test_cli_generate_report_bundle_with_review_packet(tmp_path: Path, capsys):
    import json

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_dir = tmp_path / "report-bundle"
    review_path = tmp_path / "cluster-review.json"
    review_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 2,
                "mode": "token",
                "semantic_threshold": None,
                "items": [
                    {
                        "cluster_id": "method:attention-world",
                        "fact_type": "method",
                        "label": "Attention World",
                        "token_signature": ["attention", "world"],
                        "paper_count": 1,
                        "fact_count": 2,
                        "average_confidence": 0.91,
                        "recommended_status": "accept_candidate",
                        "review_status": "accepted",
                        "review_notes": "Confirmed.",
                        "rationale": "Cross-paper support.",
                        "facts": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    main(["--db", str(db_path), "extract-artifact-ledger"])
    main(["--db", str(db_path), "extract-paper-cards"])
    main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "generate-report-bundle",
        "--out-dir",
        str(out_dir),
        "--review-packet",
        str(review_path),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "report_bundle_exported=20 papers=1 facts=2" in out
    payload = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["report_count"] == 9
    assert payload["artifact_count"] == 20
    assert payload["artifacts"][-1]["markdown_path"] == "reviewed-clusters.md"
    assert (out_dir / "reviewed-clusters.json").exists()


def test_cli_generate_report_bundle_requires_paper_cards(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"

    code = main(["--db", str(db_path), "generate-report-bundle", "--out-dir", str(tmp_path / "bundle")])
    out = capsys.readouterr().out

    assert code == 2
    assert "paper_cards is empty" in out


def test_cli_generate_report_site(tmp_path: Path, capsys):
    import json

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "digest.md").write_text("# Digest\n", encoding="utf-8")
    (bundle_dir / "digest.json").write_text("{}\n", encoding="utf-8")
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 2,
                "report_count": 1,
                "artifact_count": 4,
                "artifacts": [
                    {
                        "name": "digest",
                        "title": "Research Digest",
                        "markdown_path": "digest.md",
                        "json_path": "digest.json",
                        "paper_count": 1,
                        "fact_count": 2,
                        "extra_counts": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    code = main(["generate-report-site", "--bundle-dir", str(bundle_dir)])
    out = capsys.readouterr().out

    assert code == 0
    assert "report_site_exported=1" in out
    assert (bundle_dir / "index.html").exists()


def test_cli_publish_static_site(tmp_path: Path, capsys):
    import json

    source_dir = tmp_path / "bundle"
    source_dir.mkdir()
    (source_dir / "index.html").write_text("<!doctype html><title>AIResearch</title>\n", encoding="utf-8")
    (source_dir / "manifest.json").write_text('{"artifact_count": 1}\n', encoding="utf-8")
    out_dir = tmp_path / "site-current"

    code = main([
        "publish-static-site",
        "--source-dir",
        str(source_dir),
        "--out-dir",
        str(out_dir),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "static_site_published files=4" in out
    assert (out_dir / "index.html").exists()
    assert (out_dir / "publish-diff.json").exists()
    publish_manifest = json.loads((out_dir / "publish.json").read_text(encoding="utf-8"))
    assert publish_manifest["entrypoint"] == str(out_dir / "index.html")


def test_cli_write_static_host_config(tmp_path: Path, capsys):
    site_dir = tmp_path / "site-current"
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<!doctype html><title>AIResearch</title>\n", encoding="utf-8")
    (site_dir / "manifest.json").write_text('{"artifact_count": 1}\n', encoding="utf-8")
    out_dir = tmp_path / "deploy"

    code = main([
        "write-static-host-config",
        "--site-dir",
        str(site_dir),
        "--out-dir",
        str(out_dir),
        "--base-path",
        "/niu-secretary/airesearch/",
        "--deploy-root",
        str(tmp_path / "www" / "niu-secretary" / "airesearch"),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "static_host_config_written" in out
    assert "base_path=/niu-secretary/airesearch/" in out
    assert (out_dir / "airesearch.nginx.conf").exists()
    manifest = json.loads((out_dir / "static-host.json").read_text(encoding="utf-8"))
    assert manifest["base_path"] == "/niu-secretary/airesearch/"


def test_cli_write_static_deploy_scripts(tmp_path: Path, capsys):
    import json

    site_dir = tmp_path / "site-current"
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<!doctype html><title>AIResearch</title>\n", encoding="utf-8")
    (site_dir / "manifest.json").write_text('{"artifact_count": 1}\n', encoding="utf-8")
    out_dir = tmp_path / "deploy"
    deploy_root = tmp_path / "www" / "niu-secretary" / "airesearch"
    snapshot_root = tmp_path / "snapshots"

    code = main([
        "write-static-deploy-scripts",
        "--site-dir",
        str(site_dir),
        "--out-dir",
        str(out_dir),
        "--deploy-root",
        str(deploy_root),
        "--snapshot-root",
        str(snapshot_root),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "static_deploy_scripts_written" in out
    assert "deploy-airesearch.sh" in out
    assert "rollback-airesearch.sh" in out
    assert (out_dir / "deploy-airesearch.sh").exists()
    assert (out_dir / "rollback-airesearch.sh").exists()
    manifest = json.loads((out_dir / "static-deploy-scripts.json").read_text(encoding="utf-8"))
    assert manifest["deploy_root"] == str(deploy_root.resolve(strict=False))
    assert manifest["snapshot_root"] == str(snapshot_root.resolve(strict=False))


def test_cli_run_mvp_pipeline_fixture(tmp_path: Path, capsys):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_dir = tmp_path / "mvp"

    code = main([
        "--db",
        str(db_path),
        "--paper-db",
        str(paper_db),
        "run-mvp-pipeline",
        "--out-dir",
        str(out_dir),
        "--fact-provider",
        "fixture",
        "--fixture",
        str(fixture),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "mvp_pipeline_completed papers=1 cards=1 facts=2 fact_failures=0" in out
    assert "extract-artifact-ledger" in out
    assert "generate-report-site" in out
    assert (out_dir / "bundle" / "index.html").exists()


def test_cli_run_launch_refresh_fixture(tmp_path: Path, capsys, monkeypatch):
    from airesearch.candidates import CandidatePaper
    import airesearch.cli as cli

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

    monkeypatch.setattr(cli, "build_discovery_providers", lambda *args, **kwargs: [FakeProvider()])
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    fixture = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
    out_dir = tmp_path / "mvp"
    site_dir = tmp_path / "site"
    run_manifest = tmp_path / "launch-refresh.json"
    history_dir = tmp_path / "history"
    log_dir = tmp_path / "logs"

    code = main([
        "--db",
        str(db_path),
        "--paper-db",
        str(paper_db),
        "run-launch-refresh",
        "--profile",
        "world_models_physical_ai",
        "--limit-per-profile",
        "5",
        "--select-limit",
        "1",
        "--min-score",
        "0.1",
        "--approved-manifest",
        str(tmp_path / "approved.txt"),
        "--out-dir",
        str(out_dir),
        "--site-dir",
        str(site_dir),
        "--run-manifest",
        str(run_manifest),
        "--history-dir",
        str(history_dir),
        "--log-dir",
        str(log_dir),
        "--fact-provider",
        "fixture",
        "--fixture",
        str(fixture),
        "--progress",
    ])
    captured = capsys.readouterr()
    out = captured.out
    err = captured.err

    assert code == 0
    assert "launch_refresh_completed profiles=1 providers=fake discovered=1 canonical=1 selected=1 approved=1" in out
    assert "fact_failures=0" in out
    assert "publish-static-site" in out
    assert f"run_history={history_dir}" in out
    assert f"run_log={log_dir}" in out
    assert f"publish_diff={site_dir / 'publish-diff.json'}" in out
    assert f"candidate_review={out_dir / 'candidate-review.json'}" in out
    assert f"candidate_review_markdown={out_dir / 'candidate-review.md'}" in out
    assert "airesearch progress" in err
    assert "23/23" in err
    assert "publish-static-site" in err
    assert (site_dir / "index.html").exists()
    assert (site_dir / "publish-diff.json").exists()
    assert (out_dir / "candidate-review.json").exists()
    assert (out_dir / "candidate-review.md").exists()
    assert run_manifest.exists()
    assert list(history_dir.glob("launch-refresh-*.json"))
    assert list(log_dir.glob("launch-refresh-*.log"))


def test_cli_health_check_and_backup_db(tmp_path: Path, capsys, monkeypatch):
    from airesearch.db import init_db

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    site_dir = tmp_path / "site-current"
    backup_dir = tmp_path / "backups"
    init_db(db_path)
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<!doctype html><title>AIResearch</title>\n", encoding="utf-8")
    (site_dir / "manifest.json").write_text('{"artifact_count": 1}\n', encoding="utf-8")
    (site_dir / "publish.json").write_text('{"file_count": 3}\n', encoding="utf-8")
    monkeypatch.setenv("AIRESEARCH_DB_PATH", "secret-db-path")
    monkeypatch.setenv("PAPER_DB_PATH", "secret-paper-path")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-api-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "secret-base-url")
    monkeypatch.setenv("AIRESEARCH_FACT_MODEL", "secret-model")

    health_code = main([
        "--db",
        str(db_path),
        "--paper-db",
        str(paper_db),
        "health-check",
        "--site-dir",
        str(site_dir),
        "--require-fact-provider",
    ])
    health_out = capsys.readouterr().out
    backup_code = main([
        "--db",
        str(db_path),
        "backup-db",
        "--out-dir",
        str(backup_dir),
        "--label",
        "launch",
    ])
    backup_out = capsys.readouterr().out

    assert health_code == 0
    assert "health_check status=ok" in health_out
    assert "ok env.OPENAI_API_KEY present" in health_out
    assert "secret-api-key" not in health_out
    assert "secret-db-path" not in health_out
    assert backup_code == 0
    assert "db_backup_created" in backup_out
    assert (backup_dir / "airesearch-launch.sqlite3").exists()
    assert (backup_dir / "airesearch-launch.json").exists()


def test_cli_write_refresh_wrapper(tmp_path: Path, capsys):
    wrapper = tmp_path / "scripts" / "refresh.sh"

    code = main([
        "write-refresh-wrapper",
        "--out",
        str(wrapper),
        "--project-dir",
        str(tmp_path),
        "--schedule",
        "weekly",
        "--refresh-command",
        "python -m airesearch.cli run-launch-refresh --limit-per-profile 5 --progress",
    ])
    captured = capsys.readouterr()

    assert code == 0
    assert "refresh_wrapper_written" in captured.out
    script = wrapper.read_text(encoding="utf-8")
    assert "# schedule=weekly" in script
    assert "run-launch-refresh --limit-per-profile 5 --progress --run-manifest" in script


def test_cli_health_check_missing_site_returns_failure(tmp_path: Path, capsys, monkeypatch):
    from airesearch.db import init_db

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    monkeypatch.setenv("AIRESEARCH_DB_PATH", str(db_path))
    monkeypatch.setenv("PAPER_DB_PATH", str(paper_db))

    code = main([
        "--db",
        str(db_path),
        "--paper-db",
        str(paper_db),
        "health-check",
        "--site-dir",
        str(tmp_path / "missing-site"),
    ])
    out = capsys.readouterr().out

    assert code == 1
    assert "health_check status=fail" in out
    assert "fail site_index" in out


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

def test_cli_openai_compatible_dry_run(tmp_path: Path, capsys, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "openai-compatible",
        "--paper-key",
        "1706_03762",
        "--model",
        "qwen3.7-max",
        "--dry-run",
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "papers_seen=1" in out
    assert "dry_runs=1" in out
    assert "llm_calls=0" in out


def test_cli_openai_compatible_missing_key_returns_2(tmp_path: Path, capsys, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "openai-compatible",
        "--paper-key",
        "1706_03762",
        "--model",
        "gpt5.5",
    ])
    out = capsys.readouterr().out

    assert code == 2
    assert "OPENAI_API_KEY" in out

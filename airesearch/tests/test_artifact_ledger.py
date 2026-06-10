import json
import shutil
from pathlib import Path

from airesearch.artifact_ledger import (
    build_artifact_ledger_report,
    export_artifact_ledger,
    extract_artifact_ledger,
    extract_citations_from_text,
    extract_chunks_from_text,
    extract_equations_from_text,
    find_ledger_matches,
)
from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import sync_paperpipe


FIXTURE_DB = Path(__file__).parent / "fixtures" / "paperpipe_db"


def paperpipe_copy_with_citation(tmp_path: Path) -> Path:
    copied = tmp_path / "paperpipe_db"
    shutil.copytree(FIXTURE_DB, copied)
    source = copied / "papers" / "1706_03762" / "source.tex"
    source.write_text(
        source.read_text(encoding="utf-8")
        + "\nPrior work includes \\cite{vaswani2017attention,devlin2019bert}.\n",
        encoding="utf-8",
    )
    return copied


def synced_db(tmp_path: Path, *, with_citation: bool = False) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    sync_paperpipe(
        db_path=db_path,
        paper_db_path=paperpipe_copy_with_citation(tmp_path) if with_citation else FIXTURE_DB,
    )
    return db_path


def test_schema_has_artifact_ledger_tables(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        names = {
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table' and name like 'paper_%'"
            ).fetchall()
        }

    assert {"paper_chunks", "paper_equations", "paper_citations"}.issubset(names)


def test_extractors_parse_chunks_equations_and_citations():
    chunks = extract_chunks_from_text(
        "# Summary\n\nAttention uses scaled dot-product attention.\n\n## Limits\n\nNeeds large data.",
        artifact_type="summary",
        source_path="/tmp/summary.md",
    )
    equations = extract_equations_from_text(
        "# Equations\n\nattn: Attention(Q,K,V)=softmax(QK^T)V\n",
        source_path="/tmp/equations.md",
    )
    citations = extract_citations_from_text(
        "Prior work \\citep{vaswani2017attention, devlin2019bert} is relevant.",
        source_path="/tmp/source.tex",
    )

    assert [chunk.heading for chunk in chunks] == ["Summary", "Limits"]
    assert chunks[0].text == "Attention uses scaled dot-product attention."
    assert equations[0].label == "attn"
    assert equations[0].latex == "Attention(Q,K,V)=softmax(QK^T)V"
    assert [citation.citation_key for citation in citations] == [
        "vaswani2017attention",
        "devlin2019bert",
    ]


def test_extract_artifact_ledger_is_idempotent_and_writes_rows(tmp_path: Path):
    db_path = synced_db(tmp_path, with_citation=True)

    first = extract_artifact_ledger(db_path)
    second = extract_artifact_ledger(db_path)

    assert first.papers_seen == 1
    assert first.chunks_written >= 3
    assert first.equations_written == 1
    assert first.citations_written == 2
    assert second == first
    with connect(db_path) as conn:
        counts = {
            "chunks": conn.execute("select count(*) as count from paper_chunks").fetchone()["count"],
            "equations": conn.execute("select count(*) as count from paper_equations").fetchone()["count"],
            "citations": conn.execute("select count(*) as count from paper_citations").fetchone()["count"],
        }
    assert counts == {
        "chunks": first.chunks_written,
        "equations": first.equations_written,
        "citations": first.citations_written,
    }


def test_export_artifact_ledger_markdown_json_and_jsonl(tmp_path: Path):
    db_path = synced_db(tmp_path, with_citation=True)
    extract_artifact_ledger(db_path)
    markdown_path = tmp_path / "ledger.md"
    json_path = tmp_path / "ledger.json"
    jsonl_path = tmp_path / "ledger.jsonl"

    markdown_report = export_artifact_ledger(db_path, markdown_path)
    json_report = export_artifact_ledger(db_path, json_path, output_format="json")
    jsonl_report = export_artifact_ledger(db_path, jsonl_path, output_format="jsonl")

    assert markdown_report.chunk_count >= 3
    assert json_report.citation_count == 2
    assert jsonl_report.equation_count == 1
    assert "# AIResearch Artifact Ledger" in markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["citation_count"] == 2
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert {row["kind"] for row in rows} == {"chunk", "equation", "citation"}


def test_find_ledger_matches_returns_bounded_deterministic_matches(tmp_path: Path):
    db_path = synced_db(tmp_path)
    extract_artifact_ledger(db_path)

    with connect(db_path) as conn:
        matches = find_ledger_matches(
            conn,
            "1706_03762",
            "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V",
        )

    assert matches[0]["kind"] == "equation"
    assert matches[0]["latex"] == "Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V"


def test_build_artifact_ledger_report_on_empty_db(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    report = build_artifact_ledger_report(db_path)

    assert report.paper_count == 0
    assert report.chunk_count == 0
    assert report.equation_count == 0
    assert report.citation_count == 0

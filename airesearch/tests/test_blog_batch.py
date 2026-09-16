from __future__ import annotations

import hashlib
import json
import importlib.util
import re
import threading
from pathlib import Path

import pytest

from airesearch import blog_batch, paper_blog
from airesearch.blog_batch import (
    BlogBatchError,
    BlogModelArm,
    audit_blog_version,
    backup_blog_state,
    model_arm_from_env,
    preflight_papers,
    provider_for_arm,
    restore_blog_state,
    run_ab,
    run_batch,
    select_ab_winner,
)
from airesearch.db import connect, init_db
from airesearch.paper_blog import (
    BLOG_PROMPT_VERSION,
    DEFAULT_SECTIONS,
    FixtureBlogProvider,
    publish_blog_version,
)


NOW = "2026-08-11T00:00:00+00:00"
FACT_TYPES = ("benchmark", "claim", "dataset", "limitation", "method")


def load_cli_module():
    script_path = Path(__file__).parents[1] / "scripts" / "generate_deep_readings.py"
    spec = importlib.util.spec_from_file_location("test_generate_deep_readings", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_ready_db(tmp_path: Path, paper_keys: tuple[str, ...] = ("paper-a",)) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    paper_blog.ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        for paper_key in paper_keys:
            paper_dir = tmp_path / "papers" / paper_key
            paper_dir.mkdir(parents=True)
            summary_path = paper_dir / "summary.md"
            summary_path.write_text(
                "该论文提出证据驱动方法，在数据集上达到 91.5 分，并报告 12.3% 的提升。" * 80,
                encoding="utf-8",
            )
            original_image = paper_dir / "figure-1.png"
            original_image.write_bytes(b"fixture-image")
            conn.execute(
                """
                insert into papers (
                    paper_key, title, authors_json, year, venue, ids_json,
                    paper_dir, meta_json, created_at, updated_at
                ) values (?, ?, '[]', 2026, 'FixtureConf', '{}', ?, '{}', ?, ?)
                """,
                (paper_key, f"Fixture {paper_key}", str(paper_dir), NOW, NOW),
            )
            conn.execute(
                """
                insert into paper_cards (
                    paper_key, title, authors_json, year, venue, ids_json,
                    artifact_types_json, source_dir, status, extractor_version,
                    created_at, updated_at
                ) values (?, ?, '[]', 2026, 'FixtureConf', '{}', '["summary"]', ?,
                          'complete', 'fixture', ?, ?)
                """,
                (paper_key, f"Fixture {paper_key}", str(paper_dir), NOW, NOW),
            )
            conn.execute(
                """
                insert into paper_artifacts (
                    paper_key, artifact_type, path, sha256, size_bytes, updated_at
                ) values (?, 'summary', ?, 'fixture-sha', ?, ?)
                """,
                (paper_key, str(summary_path), summary_path.stat().st_size, NOW),
            )
            for index, fact_type in enumerate(FACT_TYPES, start=1):
                cursor = conn.execute(
                    """
                    insert into research_facts (
                        paper_key, fact_type, name, statement, confidence,
                        metadata_json, provider_name, extractor_version, created_at, updated_at
                    ) values (?, ?, ?, ?, 0.95, '{}', 'fixture', 'v1', ?, ?)
                    """,
                    (
                        paper_key,
                        fact_type,
                        f"{fact_type} fact",
                        f"{fact_type} 证据表明方法在指标 {index} 上达到 {90 + index}.5 分。",
                        NOW,
                        NOW,
                    ),
                )
                conn.execute(
                    """
                    insert into research_fact_provenance (
                        fact_id, evidence_quote, evidence_artifact_type,
                        evidence_source_path, created_at
                    ) values (?, ?, 'summary', ?, ?)
                    """,
                    (cursor.lastrowid, f"原文证据 {index}: {90 + index}.5", str(summary_path), NOW),
                )
            run_id = conn.execute(
                """
                insert into paper_layout_runs (
                    paper_key, provider, provider_version, backend, method, status,
                    input_pdf_path, output_dir, artifact_json, stats_json,
                    started_at, finished_at
                ) values (?, 'airesearch_layout', 'fixture', 'fixture', 'native',
                          'completed', '', ?, '{}', '{}', ?, ?)
                """,
                (paper_key, str(paper_dir / "layout"), NOW, NOW),
            ).lastrowid
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (?, ?, 0, 1, 'image', '[0,0,100,100]', '', ?, ?, ?)
                """,
                (
                    paper_key,
                    run_id,
                    str(original_image),
                    json.dumps(
                        {
                            "caption": "Figure 1. Complete method overview.",
                            "quality_score": 0.95,
                            "quality_reasons": ["fixture", "complete"],
                        }
                    ),
                    NOW,
                ),
            )
            for block_index, latex in (
                (2, r"L_{total}=\sum_{i=1}^{N}(y_i-\hat{y}_i)^2"),
                (3, r"p(z|x)=\frac{\exp(f(x,z))}{\sum_j\exp(f(x,j))}"),
            ):
                conn.execute(
                    """
                    insert into paper_layout_blocks (
                        paper_key, run_id, page_index, block_index, block_type,
                        bbox_json, text, asset_path, metadata_json, created_at
                    ) values (?, ?, 1, ?, 'interline_equation', '[0,0,100,30]', ?, '', ?, ?)
                    """,
                    (
                        paper_key,
                        run_id,
                        block_index,
                        latex,
                        json.dumps({"quality_score": 0.96, "quality_reasons": ["fixture"]}),
                        NOW,
                    ),
                )
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (?, ?, 2, 4, 'table', '[0,0,100,100]', '实验结果', ?, ?, ?)
                """,
                (
                    paper_key,
                    run_id,
                    str(original_image),
                    json.dumps(
                        {
                            "caption": "Table 1. Benchmark results.",
                            "quality_score": 0.94,
                            "quality_reasons": ["fixture"],
                            "table_markdown": "| 方法 | 分数 |\n| --- | --- |\n| 本文 | 91.5 |",
                        },
                        ensure_ascii=False,
                    ),
                    NOW,
                ),
            )
        conn.commit()
    return db_path


def valid_outline(db_path: Path, paper_key: str) -> dict[str, object]:
    with connect(db_path) as conn:
        fact_ids = [
            int(row["id"])
            for row in conn.execute(
                "select id from research_facts where paper_key = ? order by id", (paper_key,)
            ).fetchall()
        ]
    return {
        "sections": [
            {
                "section_key": key,
                "title": title,
                "fact_ids": fact_ids,
                "image_ids": ["img-1"] if key == "method" else [],
            }
            for key, title in DEFAULT_SECTIONS
        ]
    }


def valid_markdown(asset_path: str = "blog-assets/layout/page-1-block-1.png") -> str:
    sections = []
    body = (
        "本节依据论文证据解释方法、数据流、训练目标、实验边界与工程约束。"
        "实验在数据集上达到九十一点五分，说明该设计需要结合指标和局限性理解。"
    ) * 50
    for _key, title in DEFAULT_SECTIONS:
        sections.append(f"## {title}\n\n{body}")
    sections.append(f"![完整方法图]({asset_path})")
    sections.append("| 方法 | 分数 |\n| --- | --- |\n| 本文 | 91.5 |")
    sections.append("$$\nL_{total}=\\sum_i(y_i-\\hat y_i)^2\n$$")
    sections.append("$$\np(z|x)=\\frac{\\exp f(x,z)}{\\sum_j \\exp f(x,j)}\n$$")
    return "# 深度解读\n\n" + "\n\n".join(sections)


def publish_valid_version(
    db_path: Path,
    paper_key: str,
    *,
    model: str = "fixture-model",
    markdown: str | None = None,
    outline: dict[str, object] | None = None,
    image_refs: list[dict[str, object]] | None = None,
    llm_calls: int = 9,
):
    pack = paper_blog.build_blog_evidence_pack(db_path, paper_key)
    refs = (
        paper_blog.select_blog_images(db_path, paper_key, max_images=1)
        if image_refs is None
        else image_refs
    )
    if image_refs is None:
        assert refs
    return publish_blog_version(
        db_path,
        paper_key=paper_key,
        title=f"{paper_key} 深度解读",
        slug=paper_key,
        markdown=markdown or valid_markdown(str(refs[0]["asset_path"])),
        html="<h1>深度解读</h1>",
        outline=outline or valid_outline(db_path, paper_key),
        image_refs=refs,
        generation_meta={"llm_calls": llm_calls, "target_chars": 5000},
        model=model,
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash=pack.source_hash,
    )


def arm(name: str, model: str | None = None) -> BlogModelArm:
    return BlogModelArm(
        name=name,
        model=model or f"{name}-model",
        api_style="responses" if name == "luna" else "chat_completions",
        base_url="https://provider.example/v1/responses" if name == "luna" else "https://provider.example/v1",
        api_key_env=f"{name.upper()}_KEY",
        proxy_url="http://127.0.0.1:7890" if name == "luna" else "",
    )


def prepare_backup(db_path: Path, paper_keys: list[str], out_dir: Path) -> dict[str, object]:
    return backup_blog_state(db_path, paper_keys, out_dir, env={})


def prepare_winner(
    db_path: Path,
    paper_keys: list[str],
    out_dir: Path,
    model_arm: BlogModelArm,
    *,
    sample_papers: list[str] | None = None,
    prompt_version: str = BLOG_PROMPT_VERSION,
) -> dict[str, object]:
    manifest = prepare_backup(db_path, paper_keys, out_dir)
    samples = sample_papers or paper_keys[: min(2, len(paper_keys))]
    source_hashes = {
        paper_key: paper_blog.build_blog_evidence_pack(db_path, paper_key).source_hash
        for paper_key in samples
    }
    public_arm = blog_batch._arm_public_dict(model_arm)
    report = {
        "status": "completed",
        "database_path": str(db_path.resolve()),
        "backup_id": manifest["backup_id"],
        "paper_keys": paper_keys,
        "prompt_version": prompt_version,
        "scoring_version": blog_batch.SCORING_VERSION,
        "sample_papers": samples,
        "sample_source_hashes": source_hashes,
        "winner": model_arm.name,
        "arms": [public_arm],
    }
    winner = {
        "database_path": str(db_path.resolve()),
        "backup_id": manifest["backup_id"],
        "paper_keys": paper_keys,
        "prompt_version": prompt_version,
        "scoring_version": blog_batch.SCORING_VERSION,
        "sample_papers": samples,
        "sample_source_hashes": source_hashes,
        "model_arm": model_arm.name,
        "model": model_arm.model,
        "api_style": model_arm.api_style,
    }
    (out_dir / "ab-report.json").write_text(json.dumps(report), encoding="utf-8")
    (out_dir / "winner.json").write_text(json.dumps(winner), encoding="utf-8")
    return winner


def _current_model(db_path: Path, paper_key: str) -> str | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "select model from paper_blog_posts where paper_key = ?",
            (paper_key,),
        ).fetchone()
    return str(row["model"]) if row is not None else None


def test_model_arm_resolution_does_not_store_secret():
    secret = "deepseek-secret-value"
    deepseek = model_arm_from_env(
        "deepseek",
        {
            "NIU_ASSISTANT_MODEL": "qwen3.6-plus",
            "NIU_ASSISTANT_API_BASE": "https://opencode.example/v1",
            "NIU_ASSISTANT_API_KEY": secret,
        },
    )
    luna = model_arm_from_env(
        "luna",
        {
            "AIRESEARCH_FORMULA_OCR_MODEL": "gpt-5.6-luna",
            "AIRESEARCH_FORMULA_OCR_API_BASE": "https://opencode.example/v1/responses",
            "AIRESEARCH_FORMULA_OCR_API_KEY": "luna-secret-value",
            "AIRESEARCH_FORMULA_OCR_PROXY": "http://127.0.0.1:7890",
        },
    )

    assert deepseek.model == "deepseek-v4-pro"
    assert deepseek.api_key_env == "NIU_ASSISTANT_API_KEY"
    assert deepseek.api_style == "chat_completions"
    assert secret not in repr(deepseek)
    assert luna.api_style == "responses"
    assert luna.proxy_url == "http://127.0.0.1:7890"
    assert luna.api_key_env == "AIRESEARCH_FORMULA_OCR_API_KEY"


def test_named_model_arms_prefer_one_unified_opencode_credential():
    common = {
        "OPENCODE_GO_BASE_URL": "https://opencode.example/v1/responses",
        "OPENCODE_GO_API_KEY": "one-secret",
        "OPENCODE_GO_PROXY": "http://127.0.0.1:7890",
        "AIRESEARCH_FORMULA_OCR_MODEL": "gpt-5.6-luna",
        "AIRESEARCH_BLOG_BASE_URL": "https://unrelated-blog.example/v1",
        "AIRESEARCH_BLOG_API_KEY": "unrelated-secret",
    }

    deepseek = model_arm_from_env("deepseek", common)
    luna = model_arm_from_env("luna", common)

    assert deepseek.base_url == "https://opencode.example/v1"
    assert deepseek.api_key_env == "OPENCODE_GO_API_KEY"
    assert luna.base_url == "https://opencode.example/v1/responses"
    assert luna.api_key_env == "OPENCODE_GO_API_KEY"
    assert luna.proxy_url == "http://127.0.0.1:7890"


@pytest.mark.parametrize(
    ("name", "env", "missing"),
    [
        ("deepseek", {"NIU_ASSISTANT_MODEL": "x", "NIU_ASSISTANT_API_KEY": "secret"}, "NIU_ASSISTANT_API_BASE"),
        (
            "luna",
            {"AIRESEARCH_FORMULA_OCR_MODEL": "x", "AIRESEARCH_FORMULA_OCR_API_BASE": "x"},
            "AIRESEARCH_FORMULA_OCR_API_KEY",
        ),
    ],
)
def test_model_arm_missing_configuration_is_sanitized(name: str, env: dict[str, str], missing: str):
    with pytest.raises(BlogBatchError, match=missing) as raised:
        model_arm_from_env(name, env)
    assert "secret" not in str(raised.value)


def test_deepseek_model_uses_blog_override_precedence_and_ignores_assistant_model():
    common = {
        "NIU_ASSISTANT_MODEL": "qwen3.6-plus",
        "NIU_ASSISTANT_API_BASE": "https://opencode.example/v1",
        "NIU_ASSISTANT_API_KEY": "assistant-secret",
    }

    assert model_arm_from_env("deepseek", common).model == "deepseek-v4-pro"
    assert model_arm_from_env(
        "deepseek",
        {**common, "AIRESEARCH_BLOG_MODEL": "deepseek-v4-pro-blog"},
    ).model == "deepseek-v4-pro-blog"
    assert model_arm_from_env(
        "deepseek",
        {
            **common,
            "AIRESEARCH_BLOG_MODEL": "deepseek-v4-pro-blog",
            "AIRESEARCH_DEEPSEEK_BLOG_MODEL": "deepseek-v4-pro-explicit",
        },
    ).model == "deepseek-v4-pro-explicit"


def test_provider_for_luna_injects_responses_transport_without_network(monkeypatch: pytest.MonkeyPatch):
    requests: list[dict[str, object]] = []

    class FakeResponsesTransport:
        def __init__(self, *, proxy_url: str = "", http_transport=None):
            requests.append({"proxy_url": proxy_url, "http_transport": http_transport})

        def complete_json(self, **_kwargs):
            return {}

    monkeypatch.setattr(paper_blog, "OpenAIResponsesBlogTransport", FakeResponsesTransport, raising=False)
    model_arm = arm("luna", "gpt-5.6-luna")
    provider = provider_for_arm(model_arm, {"LUNA_KEY": "secret-luna-value"})

    assert provider.model == "gpt-5.6-luna"
    assert requests == [{"proxy_url": "http://127.0.0.1:7890", "http_transport": None}]


def test_preflight_reports_all_evidence_gates(tmp_path: Path):
    db_path = build_ready_db(tmp_path)

    row = preflight_papers(db_path, ["paper-a"])[0]

    assert row["paper_key"] == "paper-a"
    assert row["source_hash"]
    assert row["fact_types"] == sorted(FACT_TYPES)
    assert row["fact_count"] == 5
    assert row["equation_count"] == 2
    assert row["image_count"] >= 1
    assert row["structured_table_chars"] > 0
    assert row["ready"] is True
    assert row["errors"] == []


def test_preflight_accumulates_missing_evidence(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("delete from research_facts where paper_key = 'paper-a' and fact_type = 'benchmark'")
        conn.execute("update paper_layout_runs set status = 'failed' where paper_key = 'paper-a'")
        conn.commit()

    row = preflight_papers(db_path, ["paper-a", "missing"])

    assert row[0]["ready"] is False
    assert "fact_types_missing:benchmark" in row[0]["errors"]
    assert "completed_layout_missing" in row[0]["errors"]
    assert row[1]["errors"] == ["paper_missing"]


def test_preflight_rejects_existing_source_path_outside_publishable_paper_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path = build_ready_db(tmp_path)
    external = tmp_path / "outside.png"
    external.write_bytes(b"outside")
    monkeypatch.setattr(
        paper_blog,
        "select_blog_images",
        lambda *_args, **_kwargs: [
            {
                "image_id": "img-1",
                "asset_path": "../../outside.png",
                "source_path": str(external),
            }
        ],
    )

    row = preflight_papers(db_path, ["paper-a"])[0]

    assert row["ready"] is False
    assert row["image_count"] == 0
    assert "selected_local_image_missing" in row["errors"]


def test_preflight_rejects_external_source_when_only_internal_asset_is_registered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path = build_ready_db(tmp_path)
    paper_dir = tmp_path / "papers" / "paper-a"
    publishable = paper_dir / "publishable.png"
    publishable.write_bytes(b"publishable")
    external = tmp_path / "unregistered-source.png"
    external.write_bytes(b"external")
    monkeypatch.setattr(
        paper_blog,
        "select_blog_images",
        lambda *_args, **_kwargs: [
            {
                "image_id": "img-1",
                "asset_path": "publishable.png",
                "source_path": str(external),
            }
        ],
    )

    row = preflight_papers(db_path, ["paper-a"])[0]

    assert row["ready"] is False
    assert row["image_count"] == 0
    assert "selected_local_image_missing" in row["errors"]


def test_preflight_accepts_external_source_registered_for_same_paper_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path = build_ready_db(tmp_path)
    paper_dir = tmp_path / "papers" / "paper-a"
    publishable = paper_dir / "publishable.png"
    publishable.write_bytes(b"publishable")
    external = tmp_path / "registered-source.png"
    external.write_bytes(b"registered")
    with connect(db_path) as conn:
        conn.execute(
            "update paper_layout_blocks set asset_path = ? "
            "where paper_key = 'paper-a' and block_type = 'image'",
            (str(external),),
        )
        conn.commit()
    monkeypatch.setattr(
        paper_blog,
        "select_blog_images",
        lambda *_args, **_kwargs: [
            {
                "image_id": "img-1",
                "asset_path": "publishable.png",
                "source_path": str(external),
            }
        ],
    )

    row = preflight_papers(db_path, ["paper-a"])[0]

    assert row["ready"] is True
    assert row["image_count"] == 1


def test_backup_rejects_missing_database_without_creating_it(tmp_path: Path):
    missing = tmp_path / "typo.sqlite3"

    with pytest.raises(BlogBatchError, match="does not exist"):
        backup_blog_state(missing, ["paper-a"], tmp_path / "backup", env={})

    assert not missing.exists()


def test_backup_reads_selected_state_inside_explicit_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path = build_ready_db(tmp_path)
    observed: list[bool] = []
    real_selected_rows = blog_batch._selected_rows

    def recording_selected_rows(conn, table, keys):
        observed.append(bool(conn.in_transaction))
        return real_selected_rows(conn, table, keys)

    monkeypatch.setattr(blog_batch, "_selected_rows", recording_selected_rows)
    backup_blog_state(db_path, ["paper-a"], tmp_path / "backup", env={})

    assert observed == [True, True, True]


def test_backup_and_restore_selected_rows_and_new_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    first = publish_valid_version(db_path, "paper-a")
    other = publish_valid_version(db_path, "paper-b")
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into paper_blog_generation_cache (
                paper_key, section_key, source_hash, prompt_version, model,
                request_hash, response_json, markdown, token_estimate, created_at, updated_at
            ) values ('paper-a', 'outline', 'hash', ?, 'fixture-model', 'request', '{}', '', 1, ?, ?)
            """,
            (BLOG_PROMPT_VERSION, NOW, NOW),
        )
        conn.commit()
    secret = "backup-secret-value"
    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", secret)
    backup_dir = tmp_path / "backup"

    manifest = backup_blog_state(db_path, ["paper-a"], backup_dir)

    assert {path.name for path in backup_dir.iterdir()} == {
        "manifest.json",
        "paper_blog_posts.json",
        "paper_blog_versions.json",
        "paper_blog_generation_cache.json",
        "assets.json",
    }
    assert manifest["current_version_ids"] == {"paper-a": first.version_id}
    assert manifest["row_counts"] == {
        "paper_blog_posts": 1,
        "paper_blog_versions": 1,
        "paper_blog_generation_cache": 1,
    }
    for filename, metadata in manifest["files"].items():
        assert len(metadata["sha256"]) == 64
        assert (backup_dir / filename).is_file()
    assert secret not in "".join(path.read_text(encoding="utf-8") for path in backup_dir.iterdir())

    second = publish_valid_version(db_path, "paper-a", model="new-model")
    paper_dir = tmp_path / "papers" / "paper-a"
    existing_asset = paper_dir / "blog-assets" / "layout" / "page-1-block-1.png"
    unrelated_asset = paper_dir / "blog-assets" / "figures" / "unrelated.png"
    generated_asset = paper_dir / "blog-assets" / "figures" / "generated.png"
    changed_generated_asset = paper_dir / "blog-assets" / "figures" / "changed.png"
    unrelated_asset.parent.mkdir(parents=True, exist_ok=True)
    unrelated_asset.write_bytes(b"unrelated")
    generated_asset.write_bytes(b"generated")
    changed_generated_asset.write_bytes(b"generated-before-change")
    generated_hash = hashlib.sha256(generated_asset.read_bytes()).hexdigest()
    changed_hash = hashlib.sha256(changed_generated_asset.read_bytes()).hexdigest()
    (backup_dir / "created-assets.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "database_path": str(db_path.resolve()),
                "backup_id": manifest["backup_id"],
                "paper_keys": ["paper-a"],
                "created": [
                    {"paper_key": "paper-a", "path": "figures/generated.png", "sha256": generated_hash},
                    {"paper_key": "paper-a", "path": "figures/changed.png", "sha256": changed_hash},
                ],
            }
        ),
        encoding="utf-8",
    )
    changed_generated_asset.write_bytes(b"changed-after-generation")

    restored = restore_blog_state(db_path, backup_dir)

    assert restored["status"] == "restored"
    assert existing_asset.is_file()
    assert unrelated_asset.is_file()
    assert generated_asset.is_file()
    assert changed_generated_asset.is_file()
    assert restored["deleted_asset_count"] == 0
    assert restored["asset_restore_policy"] == "retain_all_without_explicit_generator_ownership"
    retained = {item["path"] for item in restored["retained_unowned_assets"]}
    assert {"figures/unrelated.png", "figures/generated.png", "figures/changed.png"} <= retained
    with connect(db_path) as conn:
        selected_versions = conn.execute(
            "select id, model from paper_blog_versions where paper_key = 'paper-a'"
        ).fetchall()
        other_row = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-b'"
        ).fetchone()
    assert [(row["id"], row["model"]) for row in selected_versions] == [(first.version_id, "fixture-model")]
    assert second.version_id != first.version_id
    assert other_row["current_version_id"] == other.version_id


def test_restore_rejects_tampered_backup(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    backup_dir = tmp_path / "backup"
    backup_blog_state(db_path, ["paper-a"], backup_dir, env={})
    (backup_dir / "paper_blog_posts.json").write_text('[{"tampered": true}]\n', encoding="utf-8")

    with pytest.raises(BlogBatchError, match="hash mismatch"):
        restore_blog_state(db_path, backup_dir)


def test_restore_rejects_cross_database_before_database_or_asset_mutation(tmp_path: Path):
    source_db = build_ready_db(tmp_path / "source")
    target_db = build_ready_db(tmp_path / "target")
    source_version = publish_valid_version(source_db, "paper-a", model="source")
    target_version = publish_valid_version(target_db, "paper-a", model="target")
    backup_dir = tmp_path / "backup"
    backup_blog_state(source_db, ["paper-a"], backup_dir, env={})
    target_asset = tmp_path / "target" / "papers" / "paper-a" / "blog-assets" / "keep.png"
    target_asset.parent.mkdir(parents=True, exist_ok=True)
    target_asset.write_bytes(b"keep")

    with pytest.raises(BlogBatchError, match="does not match"):
        restore_blog_state(target_db, backup_dir)

    with connect(target_db) as conn:
        current = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-a'"
        ).fetchone()["current_version_id"]
    assert current == target_version.version_id
    assert current != source_version.version_id or source_db != target_db
    assert target_asset.read_bytes() == b"keep"


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("missing_section", "missing_sections"),
        ("short", "text_too_short"),
        ("absolute_image", "invalid_local_image:absolute"),
        ("raw_path", "raw_absolute_path"),
        ("windows_path", "raw_absolute_path"),
        ("replacement", "replacement_character"),
        ("placeholder", "unresolved_placeholder"),
        ("one_equation", "insufficient_display_math"),
    ],
)
def test_audit_hard_gates(tmp_path: Path, mutation: str, expected_error: str):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    outline = valid_outline(db_path, "paper-a")
    markdown = valid_markdown(str(refs[0]["asset_path"]))
    if mutation == "missing_section":
        outline["sections"] = outline["sections"][:-1]
    elif mutation == "short":
        markdown = "## 导读\n\n太短。"
    elif mutation == "absolute_image":
        refs = [{**refs[0], "asset_path": "/tmp/private.png"}]
        markdown = valid_markdown("/tmp/private.png")
    elif mutation == "raw_path":
        markdown += "\n\n内部文件位于 /home/ubuntu/private/source.tex。"
    elif mutation == "windows_path":
        markdown += r"\n\n内部文件位于 C:\\private\\source.tex。"
    elif mutation == "replacement":
        markdown += "\ufffd"
    elif mutation == "placeholder":
        markdown += "\n\nTODO: 待补充"
    elif mutation == "one_equation":
        markdown = markdown.rsplit("$$", 2)[0] + "\n"
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        outline=outline,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 90.0)

    assert audit["eligible"] is False
    assert audit["score"] == 0.0
    assert any(error.startswith(expected_error) for error in audit["hard_gate_errors"])


def test_audit_allows_placeholder_words_inside_complete_prose(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = valid_markdown(str(refs[0]["asset_path"]))
    markdown += "\n\n当前客观自动化评估体系仍有待完善，但论文已经给出完整的用户研究结果。"
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert "unresolved_placeholder" not in audit["hard_gate_errors"]


def test_audit_does_not_treat_latex_range_as_windows_path(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = valid_markdown(str(refs[0]["asset_path"]))
    markdown += (
        "\n\n$$\n"
        "Z^v_{t,f}=E_\\phi(\\{x^v_\\tau\\}_{\\tau=t+\\Delta:t+K\\Delta:\\Delta})."
        "\n$$"
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert "raw_absolute_path" not in audit["hard_gate_errors"]


def test_audit_does_not_treat_latex_macro_braces_as_placeholder(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = valid_markdown(str(refs[0]["asset_path"]))
    markdown += "\n\n$$\n\\def\\evlambda{{\\lambda}}\n\\evlambda\n$$"
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert "unresolved_placeholder" not in audit["hard_gate_errors"]


def test_audit_returns_deterministic_components_and_metrics(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    version = publish_valid_version(db_path, "paper-a", llm_calls=10)

    first = audit_blog_version(db_path, "paper-a", version.version_id, 90.0)
    second = audit_blog_version(db_path, "paper-a", version.version_id, 90.0)

    assert first == second
    assert first["eligible"] is True
    assert first["score"] == round(sum(first["components"].values()), 2)
    assert set(first["components"]) == {
        "grounding",
        "technical_evidence",
        "section_coverage",
        "chinese_quality",
        "reliability",
    }
    assert first["metrics"]["generation_retry_count"] == 1
    assert first["metrics"]["generation_retry_basis"] == (
        "max(0,llm_calls-(required_sections+1))"
    )
    assert "validation_retries" not in first["metrics"]
    assert "provider_retries" not in first["metrics"]
    assert first["metrics"]["display_math_count"] == 2
    assert first["scoring_version"] == "deep-reading-ab-v1"
    assert first["formulas"]["grounding"]


def test_audit_rejects_zero_valid_fact_coverage_and_reports_invalid_refs_separately(
    tmp_path: Path,
):
    db_path = build_ready_db(tmp_path)
    outline = valid_outline(db_path, "paper-a")
    for section in outline["sections"]:
        section["fact_ids"] = [999999]
    version = publish_valid_version(db_path, "paper-a", outline=outline)

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "insufficient_fact_coverage" in audit["hard_gate_errors"]
    assert "invalid_fact_references:999999" in audit["hard_gate_errors"]
    assert audit["metrics"]["fact_coverage_ratio"] == 0.0


@pytest.mark.parametrize(
    ("referenced_count", "expected_ratio"),
    [(4, 0.5), (6, 0.75)],
)
def test_audit_accepts_fact_coverage_at_or_above_threshold(
    tmp_path: Path,
    referenced_count: int,
    expected_ratio: float,
):
    db_path = build_ready_db(tmp_path)
    with connect(db_path) as conn:
        for index in range(3):
            conn.execute(
                """
                insert into research_facts (
                    paper_key, fact_type, name, statement, confidence,
                    metadata_json, provider_name, extractor_version, created_at, updated_at
                ) values ('paper-a', 'claim', ?, ?, 0.9, '{}', 'fixture', 'v1', ?, ?)
                """,
                (
                    f"extra claim {index}",
                    f"补充证据 {index} 支持覆盖率边界测试。",
                    NOW,
                    NOW,
                ),
            )
        fact_ids = [
            int(row["id"])
            for row in conn.execute(
                "select id from research_facts where paper_key = 'paper-a' order by id"
            ).fetchall()
        ]
        conn.commit()
    assert len(fact_ids) == 8
    outline = valid_outline(db_path, "paper-a")
    for section in outline["sections"]:
        section["fact_ids"] = fact_ids[:referenced_count]
    version = publish_valid_version(db_path, "paper-a", outline=outline)

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert "insufficient_fact_coverage" not in audit["hard_gate_errors"]
    assert audit["metrics"]["fact_coverage_ratio"] == expected_ratio


def test_audit_rejects_visible_unescaped_model_control_token(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    markdown = valid_markdown() + "\n\n模型残留定位符 <loc_841> 出现在正文。"
    version = publish_valid_version(db_path, "paper-a", markdown=markdown)

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "unescaped_model_control_token" in audit["hard_gate_errors"]


def test_audit_rejects_visible_unescaped_closing_model_control_token(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    markdown = valid_markdown() + "\n\n模型残留闭合定位符 </loc_841> 出现在正文。"
    version = publish_valid_version(db_path, "paper-a", markdown=markdown)

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "unescaped_model_control_token" in audit["hard_gate_errors"]


@pytest.mark.parametrize(
    "safe_markdown",
    [
        "`<loc_841>`",
        "```text\n<loc_841>\n```",
        "&lt;loc_841&gt;",
        r"\<loc_841>",
        "<strong>普通合法 HTML</strong>",
        "<loc_token> 与 <loc841> 不符合控制 token 结构",
        "<loc_foo2> 不符合下划线后直接接数字的控制 token 结构",
    ],
)
def test_audit_ignores_non_visible_or_non_control_token_markup(
    tmp_path: Path,
    safe_markdown: str,
):
    db_path = build_ready_db(tmp_path)
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=valid_markdown() + f"\n\n{safe_markdown}",
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert "unescaped_model_control_token" not in audit["hard_gate_errors"]


def test_audit_rejects_old_style_version_without_embedded_image(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(str(refs[0]["asset_path"])),
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "embedded_image_missing" in audit["hard_gate_errors"]


def test_audit_rejects_old_style_version_without_visible_h2_headings(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = re.sub(
        r"(?m)^##(?!#)",
        "###",
        valid_markdown(str(refs[0]["asset_path"])),
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "visible_section_headings_missing" in audit["hard_gate_errors"]


def test_audit_accepts_postprocessed_visible_headings_and_local_image(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    version = publish_valid_version(db_path, "paper-a")

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert audit["hard_gate_errors"] == []
    assert audit["metrics"]["visible_section_heading_count"] == len(DEFAULT_SECTIONS)
    assert audit["metrics"]["embedded_image_count"] == 1


def test_audit_requires_rendered_image_when_evidence_has_image_but_refs_are_empty(
    tmp_path: Path,
):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(str(refs[0]["asset_path"])),
    )
    outline = valid_outline(db_path, "paper-a")
    for section in outline["sections"]:
        section["image_ids"] = []
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        outline=outline,
        image_refs=[],
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "embedded_image_missing" in audit["hard_gate_errors"]


def test_audit_ignores_fenced_and_inline_code_image_syntax(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    asset_path = str(refs[0]["asset_path"])
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(asset_path),
    )
    markdown += (
        f"\n\n```markdown\n![fenced]({asset_path})\n```\n\n"
        f"`![inline]({asset_path})`\n"
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "embedded_image_missing" in audit["hard_gate_errors"]
    assert audit["metrics"]["embedded_image_count"] == 0


def test_audit_does_not_close_fence_with_trailing_non_whitespace(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    asset_path = str(refs[0]["asset_path"])
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(asset_path),
    )
    markdown += (
        f"\n\n```markdown\n![first-fake]({asset_path})\n"
        f"```still-code\n![second-fake]({asset_path})\n"
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "embedded_image_missing" in audit["hard_gate_errors"]
    assert audit["metrics"]["embedded_image_count"] == 0


def test_audit_closes_fence_with_longer_matching_delimiter(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    asset_path = str(refs[0]["asset_path"])
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(asset_path),
    )
    markdown += (
        f"\n\n```markdown\n![fenced]({asset_path})\n````   \n"
        f"![rendered]({asset_path})\n"
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert audit["metrics"]["embedded_image_count"] == 1


def test_audit_ignores_escaped_inline_code_opening_backtick(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    asset_path = str(refs[0]["asset_path"])
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(asset_path),
    )
    markdown += f"\n\n\\`![rendered]({asset_path})`\n"
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert audit["metrics"]["embedded_image_count"] == 1


def test_audit_ignores_escaped_inline_code_closing_backtick(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    asset_path = str(refs[0]["asset_path"])
    markdown = re.sub(
        r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$",
        "",
        valid_markdown(asset_path),
    )
    markdown += f"\n\n`prefix ![still-code]({asset_path}) suffix \\`\n"
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is False
    assert "embedded_image_missing" in audit["hard_gate_errors"]
    assert audit["metrics"]["embedded_image_count"] == 0


@pytest.mark.parametrize(
    "destination",
    [
        '<blog-assets/layout/figure (1).png> "Figure title"',
        "<blog-assets/layout/figure%20%281%29.png> 'Figure title'",
    ],
)
def test_audit_accepts_angle_title_and_decoded_image_destination(
    tmp_path: Path,
    destination: str,
):
    db_path = build_ready_db(tmp_path)
    selected = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)[0]
    asset_path = "blog-assets/layout/figure (1).png"
    image_path = tmp_path / "papers" / "paper-a" / asset_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"destination fixture")
    refs = [{**selected, "asset_path": asset_path}]
    markdown = valid_markdown(asset_path).replace(
        f"![完整方法图]({asset_path})",
        f"![完整方法图]({destination})",
    )
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=markdown,
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert audit["hard_gate_errors"] == []
    assert audit["metrics"]["embedded_image_count"] == 1


def test_audit_decodes_double_encoded_image_destination_exactly_once(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    selected = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)[0]
    declared_asset_path = "blog-assets/layout/figure%20encoded.png"
    markdown_destination = "blog-assets/layout/figure%2520encoded.png"
    image_path = tmp_path / "papers" / "paper-a" / declared_asset_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"double encoding fixture")
    refs = [{**selected, "asset_path": declared_asset_path}]
    version = publish_valid_version(
        db_path,
        "paper-a",
        markdown=valid_markdown(markdown_destination),
        image_refs=refs,
    )

    audit = audit_blog_version(db_path, "paper-a", version.version_id, 0.0)

    assert audit["eligible"] is True
    assert audit["hard_gate_errors"] == []
    assert audit["metrics"]["embedded_image_count"] == 1


def ab_result(
    arm_name: str,
    paper_key: str,
    score: float,
    *,
    generation_retries: int = 0,
    duration: float = 50.0,
    eligible: bool = True,
) -> dict[str, object]:
    return {
        "event": "paper",
        "model_arm": arm_name,
        "paper_key": paper_key,
        "status": "completed" if eligible else "failed",
        "duration_seconds": duration,
        "audit": {
            "eligible": eligible,
            "score": score,
            "hard_gate_errors": [] if eligible else ["failed"],
            "metrics": {"generation_retry_count": generation_retries},
        },
    }


def test_select_ab_winner_uses_score_then_tie_breaks():
    papers = ["a", "b"]
    report = {
        "sample_papers": papers,
        "results": [
            ab_result("deepseek", "a", 94),
            ab_result("deepseek", "b", 92),
            ab_result("luna", "a", 88),
            ab_result("luna", "b", 90),
        ],
    }
    assert select_ab_winner(report) == "deepseek"

    report["results"] = [
        ab_result("deepseek", "a", 91, generation_retries=2, duration=40),
        ab_result("deepseek", "b", 91, generation_retries=2, duration=40),
        ab_result("luna", "a", 92, generation_retries=0, duration=80),
        ab_result("luna", "b", 92, generation_retries=0, duration=80),
    ]
    assert select_ab_winner(report) == "luna"

    report["results"] = [
        ab_result("deepseek", "a", 91, duration=50),
        ab_result("deepseek", "b", 91, duration=50),
        ab_result("luna", "a", 92, duration=20),
        ab_result("luna", "b", 92, eligible=False),
    ]
    assert select_ab_winner(report) == "deepseek"


def test_select_ab_winner_uses_honest_generation_retries_then_latency():
    report = {
        "sample_papers": ["a", "b"],
        "results": [
            ab_result("deepseek", "a", 92, generation_retries=2, duration=10),
            ab_result("deepseek", "b", 92, generation_retries=2, duration=10),
            ab_result("luna", "a", 91, generation_retries=0, duration=80),
            ab_result("luna", "b", 91, generation_retries=0, duration=80),
        ],
    }

    assert select_ab_winner(report) == "luna"
    summaries = blog_batch._ab_summaries(report)
    assert summaries["deepseek"]["generation_retry_count"] == 4
    assert summaries["luna"]["generation_retry_count"] == 0


def test_run_ab_runs_both_arms_resumes_and_never_exports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    arms = [arm("deepseek"), arm("luna")]
    providers = {
        "deepseek": FixtureBlogProvider(chars_per_section=520),
        "luna": FixtureBlogProvider(chars_per_section=520),
    }
    calls: list[tuple[str, str]] = []

    def recording_generate(db_path, paper_key, **kwargs):
        assert kwargs["force"] is False
        calls.append((paper_key, kwargs["model"]))
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    def forbidden_export(*_args, **_kwargs):
        raise AssertionError("site export must not be called")

    monkeypatch.setattr(paper_blog, "export_paper_blogs", forbidden_export)
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a", "paper-b"], out_dir)

    first = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=arms,
        providers=providers,
        generate_func=recording_generate,
    )
    assert first["status"] == "completed"
    assert len(calls) == 4
    assert calls == [
        ("paper-a", "deepseek-model"),
        ("paper-a", "luna-model"),
        ("paper-b", "deepseek-model"),
        ("paper-b", "luna-model"),
    ]
    assert {row["model_arm"] for row in first["results"]} == {"deepseek", "luna"}
    assert (out_dir / "ab-report.json").is_file()
    winner = json.loads((out_dir / "winner.json").read_text(encoding="utf-8"))
    assert winner["model_arm"] == first["winner"]
    assert winner["backup_id"] == first["backup_id"]
    assert winner["paper_keys"] == ["paper-a", "paper-b"]
    assert winner["prompt_version"] == BLOG_PROMPT_VERSION
    assert winner["api_style"] in {"chat_completions", "responses"}
    assert winner["sample_source_hashes"] == first["sample_source_hashes"]
    assert "api_key" not in json.dumps(winner)

    calls.clear()
    second = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=arms,
        providers=providers,
        generate_func=recording_generate,
    )
    assert second["status"] == "completed"
    assert calls == []


def test_run_ab_freshly_audits_stale_resume_version_and_regenerates(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    arms = [arm("deepseek"), arm("luna")]
    providers = {
        "deepseek": FixtureBlogProvider(chars_per_section=520),
        "luna": FixtureBlogProvider(chars_per_section=520),
    }
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a", "paper-b"], out_dir)
    first = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=arms,
        providers=providers,
    )
    stale = first["results"][0]
    with connect(db_path) as conn:
        conn.execute(
            "update paper_blog_versions set markdown = '太短', word_count = 2 where id = ?",
            (stale["version_id"],),
        )
        conn.commit()
    calls: list[tuple[str, str]] = []

    def recording_generate(db_path, paper_key, **kwargs):
        calls.append((paper_key, kwargs["model"]))
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    second = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=arms,
        providers=providers,
        generate_func=recording_generate,
    )

    assert second["status"] == "completed"
    assert calls == [(stale["paper_key"], f"{stale['model_arm']}-model")]
    regenerated = next(
        row
        for row in second["results"]
        if row["paper_key"] == stale["paper_key"] and row["model_arm"] == stale["model_arm"]
    )
    assert regenerated["version_id"] != stale["version_id"]
    assert regenerated["audit"]["eligible"] is True


def test_run_ab_restores_original_pointer_on_keyboard_interrupt(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    original = publish_valid_version(db_path, "paper-a", model="original")
    model_arm = arm("deepseek")

    def interrupt_after_publish(db_path, paper_key, **kwargs):
        paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)
        raise KeyboardInterrupt()

    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a"], out_dir)
    with pytest.raises(KeyboardInterrupt):
        run_ab(
            db_path,
            ["paper-a"],
            out_dir,
            arms=[model_arm],
            providers={"deepseek": FixtureBlogProvider(chars_per_section=520)},
            generate_func=interrupt_after_publish,
        )

    with connect(db_path) as conn:
        current = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-a'"
        ).fetchone()["current_version_id"]
    persisted = json.loads((out_dir / "original-current.json").read_text(encoding="utf-8"))
    assert current == original.version_id
    assert persisted["current_version_ids"] == {"paper-a": original.version_id}


def test_run_ab_write_failure_restores_persisted_pre_run_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path = build_ready_db(tmp_path)
    original = publish_valid_version(db_path, "paper-a", model="original")
    model_arm = arm("deepseek")
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a"], out_dir)
    first = run_ab(
        db_path,
        ["paper-a"],
        out_dir,
        arms=[model_arm],
        providers={"deepseek": FixtureBlogProvider(chars_per_section=520)},
    )
    assert first["status"] == "completed"
    assert _current_model(db_path, "paper-a") == model_arm.model
    real_write = blog_batch._atomic_write_json

    def fail_report(path: Path, value):
        if Path(path).name == "ab-report.json":
            raise OSError("simulated report write failure")
        return real_write(path, value)

    monkeypatch.setattr(blog_batch, "_atomic_write_json", fail_report)
    with pytest.raises(OSError, match="report write failure"):
        run_ab(
            db_path,
            ["paper-a"],
            out_dir,
            arms=[model_arm],
            providers={"deepseek": FixtureBlogProvider(chars_per_section=520)},
        )

    with connect(db_path) as conn:
        current = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-a'"
        ).fetchone()["current_version_id"]
    assert current == original.version_id
    assert not (out_dir / "winner.json").exists()
    assert not (out_dir / "ab-report.json").exists()


def test_ab_report_redacts_endpoint_queries_userinfo_fragments_and_proxy_credentials(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    deepseek = BlogModelArm(
        "deepseek",
        "deepseek-v4-pro",
        "chat_completions",
        "https://api-user:api-password@provider.example/v1?api_key=query-token#fragment-secret",
        "DEEPSEEK_KEY",
        "http://proxy-user:proxy-password@127.0.0.1:7890?token=proxy-token",
    )
    luna = BlogModelArm(
        "luna",
        "gpt-5.6-luna",
        "responses",
        "https://luna-user:luna-password@luna.example/v1/responses?token=luna-token",
        "LUNA_KEY",
        "http://proxy-user:proxy-password@127.0.0.1:7890",
    )

    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a"], out_dir)
    report = run_ab(
        db_path,
        ["paper-a"],
        out_dir,
        arms=[deepseek, luna],
        providers={
            "deepseek": FixtureBlogProvider(chars_per_section=520),
            "luna": FixtureBlogProvider(chars_per_section=520),
        },
    )
    serialized = json.dumps(report)

    for secret in (
        "api-user",
        "api-password",
        "query-token",
        "fragment-secret",
        "luna-user",
        "luna-password",
        "luna-token",
        "proxy-user",
        "proxy-password",
        "proxy-token",
    ):
        assert secret not in serialized
    assert report["arms"][0]["endpoint_origin"] == "https://provider.example"
    assert report["arms"][0]["proxy_enabled"] is True
    assert "base_url" not in report["arms"][0]
    assert "proxy_url" not in report["arms"][0]


def test_run_ab_rejects_evidence_changed_during_generation(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    deepseek = arm("deepseek")
    luna = arm("luna")
    calls: list[str] = []
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a"], out_dir)

    def mutating_generate(db_path, paper_key, **kwargs):
        calls.append(kwargs["model"])
        generated = paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)
        summary = tmp_path / "papers" / paper_key / "summary.md"
        summary.write_text(summary.read_text(encoding="utf-8") + "\n证据在运行中变化。", encoding="utf-8")
        return generated

    report = run_ab(
        db_path,
        ["paper-a"],
        out_dir,
        arms=[deepseek, luna],
        providers={
            "deepseek": FixtureBlogProvider(chars_per_section=520),
            "luna": FixtureBlogProvider(chars_per_section=520),
        },
        generate_func=mutating_generate,
    )

    assert report["status"] == "partial"
    assert report["winner"] is None
    assert calls == [deepseek.model]
    assert all(row["status"] == "failed" for row in report["results"])
    assert any("source hash changed" in row["error"] for row in report["results"])
    assert _current_model(db_path, "paper-a") is None


def test_run_ab_sanitizes_failure_and_preserves_successful_arm(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    deepseek = arm("deepseek")
    luna = arm("luna")
    secret = "super-secret-luna-key"
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a", "paper-b"], out_dir)

    def failing_generate(db_path, paper_key, **kwargs):
        if kwargs["model"] == luna.model and paper_key == "paper-b":
            raise RuntimeError(f"provider rejected {secret}")
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    report = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=[deepseek, luna],
        providers={
            "deepseek": FixtureBlogProvider(chars_per_section=520),
            "luna": FixtureBlogProvider(chars_per_section=520),
        },
        env={"LUNA_KEY": secret, "DEEPSEEK_KEY": "deepseek-secret"},
        generate_func=failing_generate,
    )

    assert report["winner"] == "deepseek"
    assert report["status"] == "completed"
    log_text = (out_dir / "ab.jsonl").read_text(encoding="utf-8")
    assert secret not in log_text
    assert "[REDACTED]" in log_text
    with connect(db_path) as conn:
        models = {
            row["paper_key"]: row["model"]
            for row in conn.execute("select paper_key, model from paper_blog_posts").fetchall()
        }
    assert models == {"paper-a": deepseek.model, "paper-b": deepseek.model}


def test_run_ab_without_winner_restores_original_current_pointers(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    original = publish_valid_version(db_path, "paper-a", model="original")
    deepseek = arm("deepseek")
    luna = arm("luna")
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a", "paper-b"], out_dir)

    def split_failure(db_path, paper_key, **kwargs):
        if (kwargs["model"], paper_key) in {
            (deepseek.model, "paper-b"),
            (luna.model, "paper-a"),
        }:
            raise RuntimeError("split failure")
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    report = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=[deepseek, luna],
        providers={
            "deepseek": FixtureBlogProvider(chars_per_section=520),
            "luna": FixtureBlogProvider(chars_per_section=520),
        },
        generate_func=split_failure,
    )

    assert report["status"] == "partial"
    assert report["winner"] is None
    with connect(db_path) as conn:
        post_a = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-a'"
        ).fetchone()
        post_b = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-b'"
        ).fetchone()
        generated_count = conn.execute(
            "select count(*) from paper_blog_versions where model in (?, ?)",
            (deepseek.model, luna.model),
        ).fetchone()[0]
    assert post_a["current_version_id"] == original.version_id
    assert post_b is None
    assert generated_count == 2
    assert not (out_dir / "winner.json").exists()


def test_run_ab_isolates_malformed_fresh_resume_audit(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    arms = [arm("deepseek"), arm("luna")]
    providers = {
        "deepseek": FixtureBlogProvider(chars_per_section=520),
        "luna": FixtureBlogProvider(chars_per_section=520),
    }
    out_dir = tmp_path / "run"
    prepare_backup(db_path, ["paper-a", "paper-b"], out_dir)
    first = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=arms,
        providers=providers,
    )
    assert first["status"] == "completed"

    def malformed_audit(db_path, paper_key, version_id, duration):
        with connect(db_path) as conn:
            model = conn.execute(
                "select model from paper_blog_versions where id = ?", (version_id,)
            ).fetchone()["model"]
        if paper_key == "paper-a" and model == "deepseek-model":
            raise ValueError("malformed audit payload")
        return audit_blog_version(db_path, paper_key, version_id, duration)

    def forbidden_generate(*_args, **_kwargs):
        raise AssertionError("fresh audit failure must be isolated without generation")

    second = run_ab(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arms=arms,
        providers=providers,
        generate_func=forbidden_generate,
        audit_func=malformed_audit,
    )

    failed = next(
        row
        for row in second["results"]
        if row["paper_key"] == "paper-a" and row["model_arm"] == "deepseek"
    )
    assert failed["status"] == "failed"
    assert "resume audit failed" in failed["error"]
    assert second["status"] == "completed"
    assert second["winner"] == "luna"
    assert sum(bool(row.get("resumed")) for row in second["results"]) == 3


def test_run_batch_resumes_regenerates_changed_source_and_isolates_failures(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b", "paper-c"))
    model_arm = arm("deepseek")
    provider = FixtureBlogProvider(chars_per_section=520)
    calls: list[str] = []
    fail_b = True

    def sometimes_failing_generate(db_path, paper_key, **kwargs):
        calls.append(paper_key)
        if paper_key == "paper-b" and fail_b:
            raise RuntimeError("paper-b failed")
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    out_dir = tmp_path / "run"
    prepare_winner(
        db_path,
        ["paper-a", "paper-b", "paper-c"],
        out_dir,
        model_arm,
        sample_papers=["paper-b", "paper-c"],
    )
    first = run_batch(
        db_path,
        ["paper-a", "paper-b", "paper-c"],
        out_dir,
        model_arm,
        provider=provider,
        generate_func=sometimes_failing_generate,
    )

    assert first["status"] == "partial"
    assert first["failed_paper_keys"] == ["paper-b"]
    assert calls == ["paper-a", "paper-b", "paper-c"]
    assert first["papers"][2]["valid_current_version"] is True

    calls.clear()
    fail_b = False
    second = run_batch(
        db_path,
        ["paper-a", "paper-b", "paper-c"],
        out_dir,
        model_arm,
        provider=provider,
        generate_func=sometimes_failing_generate,
    )
    assert second["status"] == "completed"
    assert calls == ["paper-b"]

    summary_path = tmp_path / "papers" / "paper-a" / "summary.md"
    summary_path.write_text(summary_path.read_text(encoding="utf-8") + "\n来源发生变化。", encoding="utf-8")
    calls.clear()
    third = run_batch(
        db_path,
        ["paper-a", "paper-b", "paper-c"],
        out_dir,
        model_arm,
        provider=provider,
        generate_func=sometimes_failing_generate,
    )
    assert third["status"] == "completed"
    assert calls == ["paper-a"]
    assert (out_dir / "batch-summary.json").is_file()


def test_run_batch_runs_four_papers_concurrently_and_preserves_summary_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    paper_keys = tuple(f"paper-{index}" for index in range(6))
    db_path = build_ready_db(tmp_path, paper_keys)
    model_arm = arm("deepseek")
    out_dir = tmp_path / "run"
    prepare_winner(db_path, list(paper_keys), out_dir, model_arm)
    lock = threading.Lock()
    four_started = threading.Event()
    active = 0
    max_active = 0

    monkeypatch.setattr(
        blog_batch,
        "provider_for_arm",
        lambda _arm, _env: FixtureBlogProvider(chars_per_section=520),
    )

    def concurrent_generate(db_path, paper_key, **kwargs):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            if active == 4:
                four_started.set()
        try:
            assert four_started.wait(timeout=10), "four workers did not start together"
            return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)
        finally:
            with lock:
                active -= 1

    result = run_batch(
        db_path,
        paper_keys,
        out_dir,
        model_arm,
        env={"DEEPSEEK_KEY": "test-key"},
        generate_func=concurrent_generate,
        concurrency=4,
    )

    assert result["status"] == "completed"
    assert result["concurrency"] == 4
    assert max_active == 4
    assert [row["paper_key"] for row in result["events"]] == list(paper_keys)
    assert [row["paper_key"] for row in result["papers"]] == list(paper_keys)


def test_run_batch_rejects_shared_provider_with_multiple_workers(tmp_path: Path):
    paper_keys = ("paper-a", "paper-b")
    db_path = build_ready_db(tmp_path, paper_keys)
    model_arm = arm("deepseek")
    out_dir = tmp_path / "run"
    prepare_winner(db_path, list(paper_keys), out_dir, model_arm)

    with pytest.raises(BlogBatchError, match="explicit provider.*concurrency=1"):
        run_batch(
            db_path,
            paper_keys,
            out_dir,
            model_arm,
            provider=FixtureBlogProvider(chars_per_section=520),
            concurrency=2,
        )


def test_run_batch_interrupt_cancels_unstarted_papers_and_logs_inflight_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    paper_keys = tuple(f"paper-{index}" for index in range(8))
    db_path = build_ready_db(tmp_path, paper_keys)
    model_arm = arm("deepseek")
    out_dir = tmp_path / "run"
    prepare_winner(db_path, list(paper_keys), out_dir, model_arm)
    started = threading.Event()
    calls: list[str] = []
    calls_lock = threading.Lock()

    monkeypatch.setattr(
        blog_batch,
        "provider_for_arm",
        lambda _arm, _env: FixtureBlogProvider(chars_per_section=520),
    )

    def recording_generate(db_path, paper_key, **kwargs):
        with calls_lock:
            calls.append(paper_key)
            started.set()
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    def interrupt_wait(*_args, **_kwargs):
        assert started.wait(timeout=10), "no worker started before interrupt"
        raise KeyboardInterrupt

    monkeypatch.setattr(blog_batch, "wait", interrupt_wait, raising=False)

    with pytest.raises(KeyboardInterrupt):
        run_batch(
            db_path,
            paper_keys,
            out_dir,
            model_arm,
            env={"DEEPSEEK_KEY": "test-key"},
            generate_func=recording_generate,
            concurrency=4,
        )

    assert 1 <= len(calls) <= 4
    logged = [
        json.loads(line)
        for line in (out_dir / "batch.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert sorted(row["paper_key"] for row in logged) == sorted(calls)
    assert not (out_dir / "batch-summary.json").exists()


def test_restore_previous_current_rolls_back_failed_status_when_pointer_update_fails(
    tmp_path: Path,
):
    db_path = build_ready_db(tmp_path)
    previous = publish_valid_version(db_path, "paper-a", model="previous")
    generated = publish_valid_version(db_path, "paper-a", model="generated")
    with connect(db_path) as conn:
        conn.execute(
            """
            create trigger reject_blog_pointer_update
            before update on paper_blog_posts
            when new.paper_key = 'paper-a'
            begin
              select raise(abort, 'pointer update rejected');
            end
            """
        )
        conn.commit()

    with pytest.raises(Exception, match="pointer update rejected"):
        blog_batch._restore_previous_current(
            db_path,
            "paper-a",
            previous.version_id,
            generated.version_id,
        )

    with connect(db_path) as conn:
        statuses = {
            int(row["id"]): row["status"]
            for row in conn.execute(
                "select id, status from paper_blog_versions where paper_key = 'paper-a'"
            )
        }
        current_version_id = int(
            conn.execute(
                "select current_version_id from paper_blog_posts where paper_key = 'paper-a'"
            ).fetchone()["current_version_id"]
        )
    assert statuses[generated.version_id] == "published"
    assert statuses[previous.version_id] == "superseded"
    assert current_version_id == generated.version_id


def test_run_batch_freshly_audits_stale_resume_version_and_regenerates(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    model_arm = arm("deepseek")
    provider = FixtureBlogProvider(chars_per_section=520)
    out_dir = tmp_path / "run"
    prepare_winner(db_path, ["paper-a"], out_dir, model_arm)
    first = run_batch(
        db_path,
        ["paper-a"],
        out_dir,
        model_arm,
        provider=provider,
    )
    stale_version_id = first["papers"][0]["version_id"]
    with connect(db_path) as conn:
        conn.execute(
            "update paper_blog_versions set markdown = '太短', word_count = 2 where id = ?",
            (stale_version_id,),
        )
        conn.commit()
    calls: list[str] = []

    def recording_generate(db_path, paper_key, **kwargs):
        calls.append(paper_key)
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    second = run_batch(
        db_path,
        ["paper-a"],
        out_dir,
        model_arm,
        provider=provider,
        generate_func=recording_generate,
    )

    assert second["status"] == "completed"
    assert calls == ["paper-a"]
    assert second["papers"][0]["version_id"] != stale_version_id
    assert second["papers"][0]["valid_current_version"] is True


def test_run_batch_does_not_restore_resume_version_when_evidence_changes_during_audit(
    tmp_path: Path,
):
    db_path = build_ready_db(tmp_path)
    model_arm = arm("deepseek")
    provider = FixtureBlogProvider(chars_per_section=520)
    out_dir = tmp_path / "run"
    prepare_winner(db_path, ["paper-a"], out_dir, model_arm)
    first = run_batch(
        db_path,
        ["paper-a"],
        out_dir,
        model_arm,
        provider=provider,
    )
    resumed_version_id = first["papers"][0]["version_id"]
    alternate = publish_valid_version(db_path, "paper-a", model="alternate-current")
    assert alternate.version_id != resumed_version_id
    audit_calls = 0

    def evidence_mutating_audit(db_path, paper_key, version_id, duration):
        nonlocal audit_calls
        audit_calls += 1
        audit = audit_blog_version(db_path, paper_key, version_id, duration)
        if audit_calls == 1:
            summary = tmp_path / "papers" / paper_key / "summary.md"
            summary.write_text(
                summary.read_text(encoding="utf-8") + "\n证据在恢复前发生变化。",
                encoding="utf-8",
            )
        return audit

    generation_calls: list[str] = []

    def failing_generate(_db_path, paper_key, **_kwargs):
        generation_calls.append(paper_key)
        raise RuntimeError("generation stopped after evidence change")

    second = run_batch(
        db_path,
        ["paper-a"],
        out_dir,
        model_arm,
        provider=provider,
        generate_func=failing_generate,
        audit_func=evidence_mutating_audit,
    )

    assert second["status"] == "partial"
    assert generation_calls == ["paper-a"]
    with connect(db_path) as conn:
        current_version_id = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = 'paper-a'"
        ).fetchone()["current_version_id"]
    assert current_version_id == alternate.version_id
    assert current_version_id != resumed_version_id


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("no_image", "embedded_image_missing"),
        ("missing_headings", "visible_section_headings_missing"),
    ],
)
def test_run_batch_regenerates_old_style_deepseek_current_version(
    tmp_path: Path,
    mutation: str,
    expected_error: str,
):
    db_path = build_ready_db(tmp_path)
    model_arm = arm("deepseek")
    out_dir = tmp_path / "run"
    prepare_winner(db_path, ["paper-a"], out_dir, model_arm)
    refs = paper_blog.select_blog_images(db_path, "paper-a", max_images=1)
    markdown = valid_markdown(str(refs[0]["asset_path"]))
    if mutation == "no_image":
        markdown = re.sub(r"(?m)^!\[[^\]]*\]\([^)]+\)\s*$", "", markdown)
    else:
        markdown = re.sub(r"(?m)^##(?!#)", "###", markdown)
    old_version = publish_valid_version(
        db_path,
        "paper-a",
        model=model_arm.model,
        markdown=markdown,
        image_refs=refs,
    )
    assert expected_error in audit_blog_version(
        db_path, "paper-a", old_version.version_id, 0.0
    )["hard_gate_errors"]
    calls: list[str] = []

    def recording_generate(db_path, paper_key, **kwargs):
        calls.append(paper_key)
        return paper_blog.generate_and_publish_blog(db_path, paper_key, **kwargs)

    result = run_batch(
        db_path,
        ["paper-a"],
        out_dir,
        model_arm,
        provider=FixtureBlogProvider(chars_per_section=520),
        generate_func=recording_generate,
    )

    assert result["status"] == "completed"
    assert calls == ["paper-a"]
    assert result["papers"][0]["version_id"] != old_version.version_id
    assert result["papers"][0]["valid_current_version"] is True


def test_run_batch_rejects_replaced_backup_before_generation(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    model_arm = arm("deepseek")
    out_dir = tmp_path / "run"
    winner = prepare_winner(db_path, ["paper-a", "paper-b"], out_dir, model_arm)
    replacement = backup_blog_state(db_path, ["paper-a", "paper-b"], out_dir, env={})
    assert replacement["backup_id"] != winner["backup_id"]
    generation_calls: list[str] = []

    with pytest.raises(BlogBatchError, match="incomplete or stale"):
        run_batch(
            db_path,
            ["paper-a", "paper-b"],
            out_dir,
            model_arm,
            provider=FixtureBlogProvider(chars_per_section=520),
            generate_func=lambda *_args, **_kwargs: generation_calls.append("called"),
        )

    assert generation_calls == []


def test_run_batch_rejects_runtime_model_override_before_generation(tmp_path: Path):
    db_path = build_ready_db(tmp_path)
    out_dir = tmp_path / "run"
    selected_arm = arm("deepseek", "deepseek-v4-pro")
    prepare_winner(db_path, ["paper-a"], out_dir, selected_arm)
    overridden_arm = arm("deepseek", "qwen3.6-plus")
    generation_calls: list[str] = []

    with pytest.raises(BlogBatchError, match="runtime model configuration"):
        run_batch(
            db_path,
            ["paper-a"],
            out_dir,
            overridden_arm,
            provider=FixtureBlogProvider(chars_per_section=520),
            generate_func=lambda *_args, **_kwargs: generation_calls.append("called"),
        )

    assert generation_calls == []


def test_run_batch_logs_malformed_fresh_audit_and_continues(tmp_path: Path):
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    model_arm = arm("deepseek")
    provider = FixtureBlogProvider(chars_per_section=520)
    out_dir = tmp_path / "run"
    prepare_winner(db_path, ["paper-a", "paper-b"], out_dir, model_arm)
    first = run_batch(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        model_arm,
        provider=provider,
    )
    assert first["status"] == "completed"

    def malformed_audit(db_path, paper_key, version_id, duration):
        if paper_key == "paper-a":
            raise ValueError("malformed audit payload")
        return audit_blog_version(db_path, paper_key, version_id, duration)

    def forbidden_generate(*_args, **_kwargs):
        raise AssertionError("resume audit isolation must continue without generation")

    second = run_batch(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        model_arm,
        provider=provider,
        generate_func=forbidden_generate,
        audit_func=malformed_audit,
    )

    assert second["status"] == "partial"
    assert second["failed_paper_keys"] == ["paper-a"]
    assert second["papers"][1]["valid_current_version"] is True
    assert any(
        row["paper_key"] == "paper-a" and "audit failed" in row["error"]
        for row in second["events"]
    )
    log_text = (out_dir / "batch.jsonl").read_text(encoding="utf-8")
    assert "malformed audit payload" in log_text


def test_batch_module_does_not_import_site_publishers():
    source = Path(blog_batch.__file__).read_text(encoding="utf-8")
    assert "research_site" not in source
    assert "export_report_bundle" not in source
    assert "deploy" not in source


def test_cli_dispatches_all_commands_without_accepting_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cli = load_cli_module()
    paper_list = tmp_path / "papers.txt"
    paper_list.write_text("paper-a\npaper-b\npaper-c\n", encoding="utf-8")
    db_path = tmp_path / "db.sqlite3"
    out_dir = tmp_path / "out"
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cli.blog_batch,
        "preflight_papers",
        lambda _db, keys: [
            {"paper_key": key, "ready": True, "errors": []} for key in keys
        ],
    )
    monkeypatch.setattr(
        cli.blog_batch,
        "backup_blog_state",
        lambda _db, keys, _out: calls.append(("backup", list(keys))) or {"status": "completed"},
    )
    monkeypatch.setattr(
        cli.blog_batch,
        "run_ab",
        lambda _db, keys, _out, **_kwargs: calls.append(("ab", list(keys)))
        or {"status": "completed"},
    )
    monkeypatch.setattr(
        cli.blog_batch,
        "run_batch",
        lambda _db, keys, _out, model_arm, **_kwargs: calls.append(
            ("batch", (list(keys), model_arm.name, _kwargs["concurrency"]))
        )
        or {"status": "partial"},
    )
    monkeypatch.setattr(cli.blog_batch, "model_arm_from_env", lambda name: arm(name))
    monkeypatch.setattr(
        cli.blog_batch,
        "restore_blog_state",
        lambda _db, backup_dir: calls.append(("restore", backup_dir)) or {"status": "restored"},
    )
    monkeypatch.setattr(
        cli.blog_batch,
        "validate_backup_manifest",
        lambda _db, _out, keys: calls.append(("validate-backup", list(keys))) or {},
    )
    monkeypatch.setattr(
        cli.blog_batch,
        "validate_winner_file",
        lambda _db, _out, keys, requested, **_kwargs: calls.append(
            ("validate-winner", (list(keys), requested))
        )
        or {},
    )

    common = ["--db", str(db_path), "--paper-list", str(paper_list), "--out", str(out_dir)]
    assert cli.main(["preflight", *common]) == 0
    assert cli.main(["backup", *common]) == 0
    assert cli.main(["ab", *common]) == 0
    assert cli.main(
        ["batch", *common, "--model-arm", "deepseek", "--concurrency", "4"]
    ) == 2
    assert cli.main(["restore", "--db", str(db_path), "--backup-dir", str(tmp_path / "backup")]) == 0
    assert calls == [
        ("backup", ["paper-a", "paper-b", "paper-c"]),
        ("validate-backup", ["paper-a", "paper-b", "paper-c"]),
        ("ab", ["paper-a", "paper-b"]),
        ("validate-winner", (["paper-a", "paper-b", "paper-c"], "deepseek")),
        ("batch", (["paper-a", "paper-b", "paper-c"], "deepseek", 4)),
        ("restore", tmp_path / "backup"),
    ]
    help_text = cli.build_parser().format_help()
    assert "api-key" not in help_text


def test_cli_requires_matching_backup_and_winner_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    cli = load_cli_module()
    db_path = build_ready_db(tmp_path, ("paper-a", "paper-b"))
    paper_list = tmp_path / "papers.txt"
    paper_list.write_text("paper-a\npaper-b\n", encoding="utf-8")
    out_dir = tmp_path / "run"
    common = ["--db", str(db_path), "--paper-list", str(paper_list), "--out", str(out_dir)]
    generation_calls: list[str] = []
    monkeypatch.setenv("NIU_ASSISTANT_API_BASE", "https://provider.example/v1")
    monkeypatch.setenv("NIU_ASSISTANT_API_KEY", "deepseek-test-key")
    # 2026-09-16 item 2：运行时路由默认来自 config/models.yaml，要让运行时配置与
    # A/B 胜者臂（provider.example/v1 + deepseek-v4-pro）一致，必须用显式路由 env
    # （AIRESEARCH_BLOG_* 仍高于 yaml；NIU_ASSISTANT_* 已降级为兜底）
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "deepseek-test-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("AIRESEARCH_FORMULA_OCR_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv(
        "AIRESEARCH_FORMULA_OCR_API_BASE",
        "https://provider.example/v1/responses",
    )
    monkeypatch.setenv("AIRESEARCH_FORMULA_OCR_API_KEY", "luna-test-key")
    monkeypatch.setattr(
        cli.blog_batch,
        "run_ab",
        lambda *_args, **_kwargs: generation_calls.append("ab") or {"status": "completed"},
    )
    monkeypatch.setattr(
        cli.blog_batch,
        "run_batch",
        lambda *_args, **_kwargs: generation_calls.append("batch") or {"status": "completed"},
    )

    assert cli.main(["ab", *common]) == 2
    assert generation_calls == []

    backup_blog_state(db_path, ["paper-a"], out_dir, env={})
    assert cli.main(["ab", *common]) == 2
    assert generation_calls == []

    backup_blog_state(db_path, ["paper-a", "paper-b"], out_dir, env={})
    assert cli.main(["ab", *common]) == 0
    assert generation_calls == ["ab"]

    generation_calls.clear()
    assert cli.main(["batch", *common, "--model-arm", "deepseek"]) == 2
    assert generation_calls == []

    prepare_winner(
        db_path,
        ["paper-a", "paper-b"],
        out_dir,
        arm("deepseek", "deepseek-v4-pro"),
    )

    assert cli.main(["batch", *common, "--model-arm", "luna"]) == 2
    assert generation_calls == []
    assert cli.main(["batch", *common, "--model-arm", "deepseek"]) == 0
    assert generation_calls == ["batch"]

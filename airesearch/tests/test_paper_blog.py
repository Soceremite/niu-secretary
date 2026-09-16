import hashlib
import io
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from airesearch.db import connect, init_db
from airesearch.admin_server import (
    AdminConfig,
    PaperBlogPublishError,
    blog_detail as admin_blog_detail,
    hide_blog as admin_hide_blog,
    ingest_single_paper,
    list_state,
    rollback_blog as admin_rollback_blog,
    run_blog_generation_job,
    _worker_loop,
    _blog_provider_from_options,
)
from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paper_blog import (
    DEFAULT_SECTIONS,
    BLOG_PROMPT_VERSION,
    display_math_block_count,
    OUTLINE_MAX_OUTPUT_TOKENS,
    OUTLINE_SOURCE_CHAR_LIMIT,
    SECTION_MAX_OUTPUT_TOKENS,
    SECTION_SOURCE_CHAR_LIMIT,
    BlogValidationError,
    FixtureBlogProvider,
    OpenAICompatibleBlogProvider,
    OpenAICompatibleBlogTransport,
    OpenAIResponsesBlogTransport,
    blog_detail,
    build_blog_evidence_pack,
    ensure_blog_schema,
    export_paper_blogs,
    generate_and_publish_blog,
    hide_blog_post,
    publish_blog_version,
    rollback_blog_post,
    select_blog_images,
    validate_blog,
    _assemble_section_response,
    _candidate_equations_from_text,
    _clean_equation_latex,
    _escape_model_control_tokens,
    _final_outline_with_provenance,
    _generate_validated_section_with_retries,
    _ordered_visual_candidates,
    _outline_with_minimum_fact_coverage,
    _paper_figure_context,
)
from airesearch.paper_figures import FigureRecord, ResolvedFigure
from airesearch.paper_tables import ResolvedTable, TableRecord
from airesearch.paperpipe_sync import sync_paperpipe


FIXTURE_DB = Path(__file__).parent / "fixtures" / "paperpipe_db"
FACT_FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
BLOG_PROVIDER_ENV_VARS = (
    "AIRESEARCH_BLOG_API_KEY",
    "AIRESEARCH_BLOG_MODEL",
    "AIRESEARCH_BLOG_BASE_URL",
    "AIRESEARCH_BLOG_API_STYLE",
    "AIRESEARCH_BLOG_PROXY",
    "OPENCODE_GO_API_KEY",
    "OPENCODE_GO_BASE_URL",
    "OPENCODE_GO_PROXY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "TRANSLATE_API_KEY",
    "TRANSLATE_BASE_URL",
    "NIU_ASSISTANT_API_KEY",
    "NIU_ASSISTANT_MODEL",
    "NIU_ASSISTANT_API_BASE",
)


def clear_blog_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in BLOG_PROVIDER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_blog_provider_can_use_unified_opencode_fallback(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "one-secret")
    monkeypatch.setenv("OPENCODE_GO_BASE_URL", "https://opencode.example/v1")
    monkeypatch.setenv("OPENCODE_GO_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("AIRESEARCH_BLOG_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_STYLE", "responses")

    provider = OpenAICompatibleBlogProvider.from_env()

    from niu_core.llm_client import compat

    _base, _key, _model = compat.resolve("blog")
    assert provider.api_key == _key, "yaml(compat) 应压过历史通用 OPENCODE_GO_* key"
    assert provider.base_url.rstrip("/") == _base.rstrip("/"), "yaml(compat) 应压过历史通用 base"
    assert isinstance(provider.transport, OpenAIResponsesBlogTransport)
    assert provider.transport.proxy_url == "http://127.0.0.1:7890"


def insert_minimal_paper(db_path: Path, paper_key: str = "1706_03762") -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (paper_key, title, paper_dir, created_at, updated_at)
            values (?, 'Attention Is All You Need', ?, '2026-06-19T00:00:00+00:00', '2026-06-19T00:00:00+00:00')
            """,
            (paper_key, paper_key),
        )
        conn.commit()


def build_fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    paper_db = tmp_path / "paperpipe"
    shutil.copytree(FIXTURE_DB, paper_db)
    db_path = tmp_path / "airesearch.sqlite3"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FACT_FIXTURE)
    return db_path, paper_db


def write_deploy_script(path: Path, *, marker: Path | None = None, exit_code: int = 0) -> None:
    marker_command = f"printf 'deployed\\n' >> {marker}\n" if marker is not None else ""
    path.write_text(
        f"#!/bin/sh\n{marker_command}echo deploy-result\nexit {exit_code}\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def install_test_deploy_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    from airesearch import admin_server

    real_run = subprocess.run

    def run_without_sudo(command, **kwargs):
        assert command[0] == "sudo"
        if command[1] == "env":
            env = dict(kwargs.pop("env", os.environ.copy()) or {})
            index = 2
            while index < len(command) and "=" in command[index]:
                key, value = command[index].split("=", 1)
                env[key] = value
                index += 1
            assert command[index] == "bash"
            return real_run(command[index:], env=env, **kwargs)
        assert command[:2] == ["sudo", "bash"]
        return real_run(command[1:], **kwargs)

    monkeypatch.setattr(admin_server.subprocess, "run", run_without_sudo)


def make_admin_config(tmp_path: Path, db_path: Path, paper_db: Path) -> AdminConfig:
    deploy_script = tmp_path / "deploy.sh"
    write_deploy_script(deploy_script)
    return AdminConfig(
        db_path=db_path,
        paper_db_path=paper_db,
        project_dir=tmp_path,
        base_path="/admin",
        deploy_script=deploy_script,
        papi_executable="papi",
        username="admin",
        password="secret",
        layout_output_dir=tmp_path / "layout",
    )


def write_paperpipe_entry(paper_db: Path, paper_key: str) -> None:
    paper_dir = paper_db / "papers" / paper_key
    paper_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "paper.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (paper_dir / "meta.json").write_text(
        json.dumps({"title": "Auto Layout Paper", "authors": ["Test Author"], "arxiv_id": "2607.00001"}),
        encoding="utf-8",
    )
    (paper_db / "index.json").write_text(
        json.dumps({paper_key: {"title": "Auto Layout Paper", "arxiv_id": "2607.00001"}}),
        encoding="utf-8",
    )


def test_deploy_script_rejects_spa_fallback(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[2]
    script = project_root / "airesearch" / "deploy" / "deploy-airesearch.sh"
    site_dir = tmp_path / "site"
    deploy_root = tmp_path / "public"
    snapshot_root = tmp_path / "snapshots"
    (site_dir / "papers").mkdir(parents=True)
    (site_dir / "index.html").write_text("<!doctype html><title>AIResearch</title>", encoding="utf-8")
    (site_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
    (site_dir / "papers" / "index.html").write_text("<h1>Papers</h1>", encoding="utf-8")
    env = {
        **os.environ,
        "SITE_DIR": str(site_dir),
        "DEPLOY_ROOT": str(deploy_root),
        "SNAPSHOT_ROOT": str(snapshot_root),
        "AIRESEARCH_VERIFY_URL": (deploy_root / "papers" / "index.html").as_uri(),
    }

    success = subprocess.run(["bash", str(script)], env=env, text=True, capture_output=True, check=False)
    assert success.returncode == 0, success.stderr

    (site_dir / "papers" / "index.html").write_text('<div id="app"></div>', encoding="utf-8")
    rejected = subprocess.run(["bash", str(script)], env=env, text=True, capture_output=True, check=False)
    assert rejected.returncode == 3
    assert "public_papers_verification_failed" in rejected.stderr


class RecordingOpenAITransport:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def complete_json(
        self,
        *,
        model: str,
        base_url: str | None,
        api_key: str,
        messages: list[dict[str, str]],
        max_output_tokens: int,
    ) -> dict:
        self.requests.append(
            {
                "model": model,
                "base_url": base_url,
                "api_key": api_key,
                "messages": messages,
                "max_output_tokens": max_output_tokens,
            }
        )
        user_text = messages[-1]["content"]
        if "outline" in user_text:
            return {
                "title": "测试论文深度解读",
                "sections": [
                    {"section_key": key, "title": title, "fact_ids": [], "image_ids": [], "target_chars": 500}
                    for key, title in DEFAULT_SECTIONS
                ],
            }
        return {
            "markdown": "## 导读\n\n这是一个中文技术章节。" * 80,
            "fact_ids": [
                fact["fact_id"]
                for fact in json.loads(user_text.split("payload:\n", 1)[1]).get("facts", [])
            ],
            "image_ids": [],
            "notes": "ok",
        }


class RecordingResponsesHTTP:
    def __init__(self, response: dict[str, object]):
        self.response = response
        self.requests: list[dict[str, object]] = []

    def __call__(
        self,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout: float,
        proxy_url: str,
    ) -> dict[str, object]:
        self.requests.append(
            {
                "endpoint": endpoint,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
                "proxy_url": proxy_url,
            }
        )
        return self.response


def make_publishable_layout_candidate(
    tmp_path: Path,
    name: str,
    *,
    asset_kind: str,
    artifact_type: str = "layout_block",
    quality_score: float = 0.9,
) -> dict[str, object]:
    source_path = tmp_path / f"{name}.png"
    source_path.write_bytes(name.encode())
    return {
        "asset_path": f"blog-assets/layout/{source_path.name}",
        "source_path": str(source_path),
        "caption_seed": f"{asset_kind} {name}",
        "artifact_type": artifact_type,
        "asset_kind": asset_kind,
        "figure_role": "table" if asset_kind == "table" else "figure",
        "quality_score": quality_score,
        "content_fingerprint": {"sha256": f"sha-{name}", "size_bytes": source_path.stat().st_size},
    }


def test_visual_candidates_prefer_complete_numbered_crop_over_same_figure_fragments(tmp_path: Path):
    complete = make_publishable_layout_candidate(
        tmp_path,
        "figure-1-complete",
        asset_kind="figure",
        artifact_type="layout_pdf_crop",
    )
    complete.update(
        caption_seed="Figure 1. Complete architecture overview.",
        figure_number=1,
        page_index=2,
        source_reference="pdf page=3 figure=1 fragmented_layers=4",
    )
    fragments = []
    for index in range(3):
        fragment = make_publishable_layout_candidate(
            tmp_path,
            f"figure-1-fragment-{index}",
            asset_kind="figure",
        )
        fragment.update(
            caption_seed="Figure 1. Complete architecture overview.",
            figure_number=1,
            page_index=2,
            block_index=20 + index,
        )
        fragments.append(fragment)
    independent = make_publishable_layout_candidate(tmp_path, "figure-2", asset_kind="figure")
    independent.update(
        caption_seed="Figure 2. Independent experiment.",
        figure_number=2,
        page_index=6,
    )

    selected = _ordered_visual_candidates(
        [*fragments, independent, complete],
        max_images=6,
    )

    assert [candidate["source_path"] for candidate in selected] == [
        complete["source_path"],
        independent["source_path"],
    ]


def test_visual_candidates_keep_distinct_subfigure_captions(tmp_path: Path):
    complete = make_publishable_layout_candidate(
        tmp_path,
        "figure-1-complete",
        asset_kind="figure",
        artifact_type="layout_pdf_crop",
    )
    complete.update(caption_seed="Figure 1. Full system.", figure_number=1, page_index=0)
    subfigure = make_publishable_layout_candidate(tmp_path, "figure-1b", asset_kind="figure")
    subfigure.update(caption_seed="Figure 1(b). Independent ablation detail.", figure_number=1, page_index=0)

    selected = _ordered_visual_candidates([complete, subfigure], max_images=6)

    assert len(selected) == 2


@pytest.mark.parametrize(
    ("latex", "expected"),
    [
        (r"x = y \right] \quad 3", ""),
        (r"x_3 \quad 4 \quad 5 \quad 6 \quad 7", r"x_3 \quad 4 \quad 5 \quad 6 \quad 7"),
        (r"x = \left[ y \right]", r"x = \left[ y \right]"),
    ],
)
def test_clean_equation_latex_validates_sized_delimiters(latex: str, expected: str):
    assert _clean_equation_latex(latex) == expected


def test_blog_schema_is_created_by_init_db(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute("select name from sqlite_master where type = 'table'").fetchall()
        }
    assert "paper_blog_posts" in tables
    assert "paper_blog_versions" in tables
    assert "paper_blog_generation_cache" in tables


def test_publish_rollback_and_hide_blog_versions(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    ensure_blog_schema(db_path)
    insert_minimal_paper(db_path)
    first = publish_blog_version(
        db_path,
        paper_key="1706_03762",
        title="Transformer 深度解读",
        slug="1706_03762",
        markdown="# Transformer 深度解读\n\n第一版正文",
        html="<h1>Transformer 深度解读</h1><p>第一版正文</p>",
        outline={"sections": [{"section_key": "intro", "title": "导读"}]},
        image_refs=[],
        generation_meta={"cache_hits": 0, "llm_calls": 8},
        model="fixture",
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash="hash-a",
    )
    second = publish_blog_version(
        db_path,
        paper_key="1706_03762",
        title="Transformer 深度解读新版",
        slug="1706_03762",
        markdown="# Transformer 深度解读新版\n\n第二版正文",
        html="<h1>Transformer 深度解读新版</h1><p>第二版正文</p>",
        outline={"sections": [{"section_key": "intro", "title": "导读"}]},
        image_refs=[],
        generation_meta={"cache_hits": 4, "llm_calls": 4},
        model="fixture",
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash="hash-b",
    )

    current = blog_detail(db_path, "1706_03762")
    assert current["post"]["current_version_id"] == second.version_id
    assert current["post"]["status"] == "published"
    assert [version["version_number"] for version in current["versions"]] == [2, 1]

    rollback_blog_post(db_path, "1706_03762", first.version_id)
    rolled_back = blog_detail(db_path, "1706_03762")
    assert rolled_back["post"]["current_version_id"] == first.version_id
    assert rolled_back["post"]["title"] == "Transformer 深度解读"

    hide_blog_post(db_path, "1706_03762")
    hidden = blog_detail(db_path, "1706_03762")
    assert hidden["post"]["status"] == "hidden"


def test_publish_blog_requires_existing_paper(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    ensure_blog_schema(db_path)

    try:
        publish_blog_version(
            db_path,
            paper_key="missing_paper",
            title="Missing 深度解读",
            slug="missing_paper",
            markdown="# Missing\n\n正文",
            html="<h1>Missing</h1>",
            outline={"sections": []},
            image_refs=[],
            generation_meta={},
            model="fixture",
            prompt_version=BLOG_PROMPT_VERSION,
            source_hash="hash-missing",
        )
    except KeyError as exc:
        assert exc.args[0] == "missing_paper"
    else:
        raise AssertionError("publishing a blog for a missing paper should fail")


def test_build_blog_evidence_pack_uses_facts_provenance_and_artifacts(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)

    assert pack.paper_key == "1706_03762"
    assert "Attention Is All You Need" in pack.title
    assert pack.source_hash
    assert pack.facts
    assert any(fact["evidence_quote"] for fact in pack.facts)
    assert "summary" in pack.artifact_texts or "tldr" in pack.artifact_texts
    assert pack.equations
    assert "source_hash" in pack.as_prompt_payload()


def test_build_blog_evidence_pack_includes_native_layout_artifacts(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    with connect(db_path) as conn:
        paper = conn.execute("select paper_dir from papers where paper_key = '1706_03762'").fetchone()
        paper_dir = Path(paper["paper_dir"])
        layout_dir = tmp_path / "layout"
        layout_dir.mkdir()
        layout_md = layout_dir / "paper.md"
        layout_md.write_text("Native layout markdown with table and figure evidence.", encoding="utf-8")
        layout_asset = layout_dir / "figure.png"
        layout_asset.write_bytes(b"png")
        now = "2026-07-07T00:00:00+00:00"
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values ('1706_03762', 'layout_markdown', ?, 'sha-md', ?, ?)
            """,
            (str(layout_md), layout_md.stat().st_size, now),
        )
        conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, backend, method, status, input_pdf_path, output_dir, started_at, finished_at
            ) values ('1706_03762', 'airesearch_layout', 'pymupdf', 'native', 'completed', '', ?, ?, ?)
            """,
            (str(layout_dir), now, now),
        )
        run_id = conn.execute("select id from paper_layout_runs order by id desc limit 1").fetchone()["id"]
        conn.execute(
            """
            insert into paper_layout_blocks (
                paper_key, run_id, page_index, block_index, block_type,
                bbox_json, text, asset_path, metadata_json, created_at
            ) values ('1706_03762', ?, 0, 3, 'image', '[1,2,3,4]',
                'Figure 1: native parser detected architecture diagram.', ?, ?, ?)
            """,
            (
                run_id,
                str(layout_asset),
                json.dumps({"source_path": str(layout_dir / "paper_layout.json")}),
                now,
            ),
        )
        conn.commit()

    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=100000)

    assert "layout_markdown" in pack.artifact_texts
    assert "Native layout markdown" in pack.artifact_texts["layout_markdown"]
    layout_candidates = [item for item in pack.image_candidates if item.get("artifact_type") == "layout_block"]
    assert layout_candidates
    assert layout_candidates[0]["source_reference"] == "layout_structure_json page=1 block=3"
    assert (paper_dir / layout_candidates[0]["asset_path"]).exists()


def test_layout_visual_candidates_use_only_latest_completed_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    with connect(db_path) as conn:
        paper = conn.execute("select paper_dir from papers where paper_key = '1706_03762'").fetchone()
        paper_dir = Path(paper["paper_dir"])
        layout_dir = tmp_path / "multi-run-layout"
        layout_dir.mkdir()
        for index, (content, caption) in enumerate(
            (
                (b"historical-layout-content", "Figure 1. Historical content."),
                (b"latest-layout-content", "Figure 1. Latest content."),
            ),
            start=1,
        ):
            run_dir = layout_dir / f"run-{index}"
            run_dir.mkdir()
            structure_path = run_dir / "paper_layout.json"
            structure_path.write_text("{}", encoding="utf-8")
            asset = run_dir / "figure.png"
            asset.write_bytes(content)
            timestamp = f"2026-07-13T00:00:0{index}+00:00"
            conn.execute(
                """
                insert into paper_layout_runs (
                    paper_key, provider, backend, method, status, input_pdf_path,
                    output_dir, started_at, finished_at
                ) values (
                    '1706_03762', 'airesearch_layout', 'pymupdf', 'native',
                    'completed', '', ?, ?, ?
                )
                """,
                (str(run_dir), timestamp, timestamp),
            )
            run_id = conn.execute("select last_insert_rowid() as id").fetchone()["id"]
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (
                    '1706_03762', ?, 0, 1, 'image', '[10,20,260,180]',
                    '', ?, ?, ?
                )
                """,
                (
                    run_id,
                    str(asset),
                    json.dumps(
                        {
                            "source_path": str(structure_path),
                            "caption": caption,
                            "quality_score": 0.4,
                        }
                    ),
                    timestamp,
                ),
            )
        conn.commit()

    monkeypatch.setattr("airesearch.paper_blog._layout_pdf_crop_candidates", lambda *_args: [])
    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_figures", lambda **_kwargs: [])
    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_tables", lambda **_kwargs: [])

    first = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)
    second = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)

    assert len(first.image_candidates) == 1
    candidate = first.image_candidates[0]
    assert candidate["caption_seed"] == "Figure 1. Latest content."
    assert Path(candidate["source_path"]).read_bytes() == b"latest-layout-content"
    assert candidate["content_fingerprint"]["sha256"] == hashlib.sha256(b"latest-layout-content").hexdigest()
    paths = [item["source_path"] for item in first.image_candidates]
    fingerprints = [item["content_fingerprint"]["sha256"] for item in first.image_candidates]
    assert len(paths) == len(set(paths)) == 1
    assert len(fingerprints) == len(set(fingerprints)) == 1
    assert first.source_hash == second.source_hash
    assert paper_dir / candidate["asset_path"] == Path(candidate["source_path"])


def test_build_blog_evidence_pack_includes_high_quality_layout_tables_and_equations(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    with connect(db_path) as conn:
        now = "2026-07-13T01:00:00+00:00"
        conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, backend, method, status, input_pdf_path, output_dir, started_at, finished_at
            ) values ('1706_03762', 'airesearch_layout', 'pymupdf', 'native', 'completed', '', '', ?, ?)
            """,
            (now, now),
        )
        run_id = conn.execute("select id from paper_layout_runs order by id desc limit 1").fetchone()["id"]
        blocks = (
            (
                4,
                "interline_equation",
                "L_layout = - sum_i y_i log softmax(z_i)",
                {
                    "equation_id": "layout-eq-1",
                    "equation_role": "loss",
                    "source_reference": "page=2 block=4",
                    "quality_score": 0.92,
                    "quality_reasons": ["math-signal", "equation-length"],
                },
            ),
            (
                5,
                "interline_equation",
                "x = y",
                {
                    "equation_id": "layout-eq-low",
                    "source_reference": "page=2 block=5",
                    "quality_score": 0.41,
                    "quality_reasons": ["short"],
                },
            ),
            (
                6,
                "table",
                "Method    Accuracy\nBaseline  71.2\nOurs      78.4",
                {
                    "caption": "Table 1. Main benchmark results.",
                    "source_reference": "page=3 block=6",
                    "quality_score": 0.9,
                    "quality_reasons": ["table-rows", "structured-table"],
                    "table_markdown": "| Method | Accuracy |\n| --- | --- |\n| Baseline | 71.2 |\n| Ours | 78.4 |",
                },
            ),
            (
                7,
                "table",
                "Noise  0",
                {
                    "caption": "Table 9. Incomplete fragment.",
                    "source_reference": "page=9 block=7",
                    "quality_score": 0.38,
                    "quality_reasons": ["incomplete"],
                    "table_markdown": "| Noise | Value |\n| --- | --- |\n| fragment | 0 |",
                },
            ),
        )
        for block_index, block_type, text, metadata in blocks:
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values ('1706_03762', ?, 1, ?, ?, '[10,20,500,180]', ?, '', ?, ?)
                """,
                (run_id, block_index, block_type, text, json.dumps(metadata), now),
            )
        conn.commit()

    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=100000)

    layout_equations = [equation for equation in pack.equations if equation.get("extraction_method") == "airesearch_layout"]
    assert len(layout_equations) == 1
    assert layout_equations[0]["latex"] == "L_layout = - sum_i y_i log softmax(z_i)"
    assert layout_equations[0]["quality_score"] == 0.92
    assert layout_equations[0]["source_reference"] == "page=2 block=4"
    assert "layout_structured_tables" in pack.artifact_texts
    assert "Main benchmark results" in pack.artifact_texts["layout_structured_tables"]
    assert "| Ours | 78.4 |" in pack.artifact_texts["layout_structured_tables"]
    assert "Incomplete fragment" not in pack.artifact_texts["layout_structured_tables"]
    prompt_payload = pack.as_prompt_payload()
    prompt_layout_equation = next(
        equation for equation in prompt_payload["equations"] if equation.get("extraction_method") == "airesearch_layout"
    )
    assert "source_path" not in prompt_layout_equation
    bounded = OpenAICompatibleBlogProvider._bounded_artifact_texts(pack.artifact_texts, 800)
    assert "layout_structured_tables" in bounded
    assert "| Ours | 78.4 |" in bounded["layout_structured_tables"]


def test_select_blog_images_prefers_high_quality_layout_evidence(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    with connect(db_path) as conn:
        paper = conn.execute("select paper_dir from papers where paper_key = '1706_03762'").fetchone()
        paper_dir = Path(paper["paper_dir"])
        layout_dir = tmp_path / "quality-layout"
        layout_dir.mkdir()
        low_asset = layout_dir / "arrow-only.png"
        high_asset = layout_dir / "full-figure.png"
        low_asset.write_bytes(b"low-layout-png")
        high_asset.write_bytes(b"high-layout-png")
        structure_path = layout_dir / "paper_layout.json"
        structure_path.write_text("{}", encoding="utf-8")
        now = "2026-07-13T00:00:00+00:00"
        conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, backend, method, status, input_pdf_path, output_dir, started_at, finished_at
            ) values ('1706_03762', 'airesearch_layout', 'pymupdf', 'native', 'completed', '', ?, ?, ?)
            """,
            (str(layout_dir), now, now),
        )
        run_id = conn.execute("select id from paper_layout_runs order by id desc limit 1").fetchone()["id"]
        for block_index, asset, caption, quality_score in (
            (1, low_asset, "Figure 1. Tiny arrow fragment.", 0.41),
            (2, high_asset, "Figure 2. Complete system overview.", 0.91),
        ):
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values ('1706_03762', ?, 0, ?, 'image', '[10,20,260,180]', '', ?, ?, ?)
                """,
                (
                    run_id,
                    block_index,
                    str(asset),
                    json.dumps(
                        {
                            "source_path": str(structure_path),
                            "caption": caption,
                            "source_reference": f"page=1 block={block_index}",
                            "evidence_confidence": 0.86,
                            "quality_score": quality_score,
                            "quality_reasons": ["evidence-kind", "caption-linked", "asset"],
                        }
                    ),
                    now,
                ),
            )
        conn.commit()

    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)
    layout_candidates = [item for item in pack.image_candidates if item.get("artifact_type") == "layout_block"]
    selected = select_blog_images(db_path, "1706_03762", max_images=1)

    assert any(candidate["quality_score"] == 0.91 for candidate in layout_candidates)
    assert selected[0]["caption"] == "Figure 2. Complete system overview."
    assert selected[0]["quality_score"] == 0.91
    assert "caption-linked" in selected[0]["quality_reasons"]
    assert (paper_dir / selected[0]["asset_path"]).exists()
    payload = pack.as_prompt_payload()
    prompt_candidate = next(item for item in payload["image_candidates"] if item.get("quality_score") == 0.91)
    assert prompt_candidate["quality_reasons"] == ["evidence-kind", "caption-linked", "asset"]
    assert "source_path" not in prompt_candidate


def test_image_candidates_skip_source_resolvers_when_layout_coverage_is_sufficient(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pdf_figure = make_publishable_layout_candidate(
        tmp_path,
        "pdf-figure-1",
        asset_kind="figure",
        artifact_type="layout_pdf_crop",
    )
    layout_figure = make_publishable_layout_candidate(tmp_path, "layout-figure-2", asset_kind="figure")
    layout_table = make_publishable_layout_candidate(tmp_path, "layout-table-1", asset_kind="table")
    monkeypatch.setattr("airesearch.paper_blog._layout_pdf_crop_candidates", lambda *_args: [pdf_figure])
    monkeypatch.setattr(
        "airesearch.paper_blog._layout_visual_candidates",
        lambda *_args: [layout_figure, layout_table],
    )

    def unexpected_resolver(**_kwargs):
        raise AssertionError("source resolver must not run when layout coverage is sufficient")

    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_figures", unexpected_resolver)
    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_tables", unexpected_resolver)

    first = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)
    second = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)

    expected_paths = [
        pdf_figure["source_path"],
        layout_figure["source_path"],
        layout_table["source_path"],
    ]
    assert [candidate["source_path"] for candidate in first.image_candidates] == expected_paths
    assert [candidate["source_path"] for candidate in second.image_candidates] == expected_paths
    assert first.source_hash == second.source_hash
    assert len(expected_paths) == len(set(expected_paths))
    fingerprints = [candidate["content_fingerprint"]["sha256"] for candidate in first.image_candidates]
    assert len(fingerprints) == len(set(fingerprints))


def test_low_quality_valid_layout_coverage_skips_source_resolvers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    layout_candidates = [
        make_publishable_layout_candidate(
            tmp_path,
            "low-quality-figure-1",
            asset_kind="figure",
            quality_score=0.15,
        ),
        make_publishable_layout_candidate(
            tmp_path,
            "low-quality-figure-2",
            asset_kind="figure",
            quality_score=0.2,
        ),
        make_publishable_layout_candidate(
            tmp_path,
            "low-quality-table-1",
            asset_kind="table",
            quality_score=0.1,
        ),
    ]
    monkeypatch.setattr("airesearch.paper_blog._layout_pdf_crop_candidates", lambda *_args: [])
    monkeypatch.setattr("airesearch.paper_blog._layout_visual_candidates", lambda *_args: layout_candidates)

    def unexpected_resolver(**_kwargs):
        raise AssertionError("valid low-quality layout coverage must suppress source fallback")

    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_figures", unexpected_resolver)
    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_tables", unexpected_resolver)

    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)

    assert pack.image_candidates == layout_candidates


def test_image_candidates_return_layout_before_non_empty_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pdf_figure = make_publishable_layout_candidate(
        tmp_path,
        "pdf-layout-figure",
        asset_kind="figure",
        artifact_type="layout_pdf_crop",
    )
    layout_figure = make_publishable_layout_candidate(tmp_path, "block-layout-figure", asset_kind="figure")
    source_table = make_publishable_layout_candidate(
        tmp_path,
        "source-table-fallback",
        asset_kind="table",
        artifact_type="resolved_table",
    )
    monkeypatch.setattr("airesearch.paper_blog._layout_pdf_crop_candidates", lambda *_args: [pdf_figure])
    monkeypatch.setattr("airesearch.paper_blog._layout_visual_candidates", lambda *_args: [layout_figure])
    monkeypatch.setattr(
        "airesearch.paper_blog._resolved_figure_candidates",
        lambda *_args: (_ for _ in ()).throw(AssertionError("figure fallback must not run")),
    )
    monkeypatch.setattr("airesearch.paper_blog._resolved_table_candidates", lambda *_args: [source_table])

    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)

    assert [candidate["source_path"] for candidate in pack.image_candidates] == [
        pdf_figure["source_path"],
        layout_figure["source_path"],
        source_table["source_path"],
    ]


@pytest.mark.parametrize(
    ("figure_count", "table_count", "expected_calls"),
    [
        (2, 0, ["table"]),
        (1, 1, ["figure"]),
        (0, 0, ["figure", "table"]),
    ],
)
def test_image_candidates_call_only_source_resolver_for_missing_layout_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    figure_count: int,
    table_count: int,
    expected_calls: list[str],
):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    layout_candidates = [
        make_publishable_layout_candidate(tmp_path, f"figure-{index}", asset_kind="figure")
        for index in range(figure_count)
    ]
    layout_candidates.extend(
        make_publishable_layout_candidate(tmp_path, f"table-{index}", asset_kind="table")
        for index in range(table_count)
    )
    monkeypatch.setattr("airesearch.paper_blog._layout_pdf_crop_candidates", lambda *_args: [])
    monkeypatch.setattr("airesearch.paper_blog._layout_visual_candidates", lambda *_args: layout_candidates)
    calls: list[str] = []

    def resolve_figures(**_kwargs):
        calls.append("figure")
        return []

    def resolve_tables(**_kwargs):
        calls.append("table")
        return []

    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_figures", resolve_figures)
    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_tables", resolve_tables)

    pack = build_blog_evidence_pack(db_path, "1706_03762", max_source_chars=4000)

    assert calls == expected_calls
    assert len(pack.image_candidates) == figure_count + table_count


def test_select_blog_images_uses_only_local_existing_assets(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    image_refs = select_blog_images(db_path, "1706_03762", max_images=5)

    assert image_refs
    assert len(image_refs) <= 5
    for image in image_refs:
        assert image["asset_path"]
        assert not image["asset_path"].startswith("http")
        assert Path(image["source_path"]).exists()
        assert image["caption"]
        assert image["section_key"] in {"intro", "background", "method", "architecture", "experiments"}


def test_blog_evidence_extracts_semantic_figures_and_complete_equations(tmp_path: Path):
    paper_db = tmp_path / "paperpipe"
    shutil.copytree(FIXTURE_DB, paper_db)
    paper_dir = paper_db / "papers" / "1706_03762"
    (paper_dir / "source.tex").write_text(
        r"""
\begin{figure}
  \includegraphics[width=.95\linewidth]{figures/figure1.svg}
  \caption{\textbf{Overview of Transformer architecture.} Main encoder-decoder framework.}
\end{figure}
\begin{equation}
\operatorname{Attention}(Q,K,V)=\operatorname{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
\label{eq:attention}
\end{equation}
""",
        encoding="utf-8",
    )
    db_path = tmp_path / "airesearch.sqlite3"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FACT_FIXTURE)

    images = select_blog_images(db_path, "1706_03762", max_images=3)
    pack = build_blog_evidence_pack(db_path, "1706_03762")

    assert images[0]["caption"].startswith("Overview of Transformer architecture")
    assert images[0]["figure_role"] == "framework"
    assert images[0]["section_key"] == "architecture"
    assert any("operatorname{Attention}" in equation["latex"] for equation in pack.equations)


def test_select_blog_images_uses_resolved_records_not_embedded_order(tmp_path: Path, monkeypatch):
    paper_db = tmp_path / "paperpipe"
    shutil.copytree(FIXTURE_DB, paper_db)
    paper_dir = paper_db / "papers" / "1706_03762"
    (paper_dir / "figures" / "figure_01.png").write_bytes(b"embedded-icon")
    (paper_dir / "source.tex").write_text(
        r"""
\begin{figure}
  \includegraphics{img/framework.pdf}
  \caption{Overview of the complete framework.}
  \label{fig:framework}
\end{figure}
""",
        encoding="utf-8",
    )
    db_path = tmp_path / "airesearch.sqlite3"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    output = paper_dir / "blog-assets" / "figures" / "figure-01.webp"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"resolved-webp")
    record = FigureRecord(
        figure_id="fig-1",
        number=1,
        label="fig:framework",
        layout="single-column",
        includes=("img/framework.pdf",),
        caption="Overview of the complete framework.",
        section="Method",
        subsection="",
        role="framework",
        evidence=(),
    )

    def fake_resolve(**kwargs):
        assert kwargs["output_dir"] == paper_dir / "blog-assets" / "figures"
        return [
            ResolvedFigure(
                record=record,
                path=output,
                source_reference="img/framework.pdf",
                extraction_method="local_source",
                confidence=1.0,
                content_sha256="abc123",
                diagnostics=("local-source",),
            )
        ]

    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_figures", fake_resolve)

    images = select_blog_images(db_path, "1706_03762", max_images=5)
    pack = build_blog_evidence_pack(db_path, "1706_03762")

    assert images[0]["figure_number"] == 1
    assert images[0]["source_reference"] == "img/framework.pdf"
    assert images[0]["extraction_method"] == "local_source"
    assert images[0]["source_path"] == str(output)
    assert "figure_01.png" not in images[0]["source_path"]
    assert pack.image_candidates[0]["content_fingerprint"] == {"sha256": "abc123", "size_bytes": len(b"resolved-webp")}


def test_select_blog_images_keeps_main_result_table_with_figures(tmp_path: Path, monkeypatch):
    paper_db = tmp_path / "paperpipe"
    shutil.copytree(FIXTURE_DB, paper_db)
    paper_dir = paper_db / "papers" / "1706_03762"
    (paper_dir / "source.tex").write_text(
        r"""
\begin{figure}
  \includegraphics{img/framework.pdf}
  \caption{Overview of the complete framework.}
\end{figure}
\begin{table*}
  \begin{tabular}{lc}Method & Score \\ ColaVLA & 3.48 \\\end{tabular}
  \caption{Closed-loop simulation results on NeuroNCAP benchmark.}
  \label{tab:closed}
\end{table*}
""",
        encoding="utf-8",
    )
    db_path = tmp_path / "airesearch.sqlite3"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    figure_outputs: list[Path] = []
    for number in range(1, 6):
        output = paper_dir / "blog-assets" / "figures" / f"figure-{number:02d}.webp"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"figure-{number}".encode())
        figure_outputs.append(output)
    table_output = paper_dir / "blog-assets" / "tables" / "table-01.webp"
    table_output.parent.mkdir(parents=True, exist_ok=True)
    table_output.write_bytes(b"table-1")

    figure_roles = ["framework", "motivation", "method", "qualitative", "experiments"]

    def fake_resolve_figures(**_kwargs):
        return [
            ResolvedFigure(
                record=FigureRecord(
                    figure_id=f"fig-{number}",
                    number=number,
                    label=f"fig:{number}",
                    layout="single-column",
                    includes=(f"img/{number}.pdf",),
                    caption=f"{role} figure",
                    section="",
                    subsection="",
                    role=role,
                    evidence=(),
                ),
                path=figure_outputs[number - 1],
                source_reference=f"img/{number}.pdf",
                extraction_method="pdf_crop",
                confidence=0.9,
                content_sha256=f"fig-{number}-hash",
                diagnostics=(),
            )
            for number, role in enumerate(figure_roles, start=1)
        ]

    def fake_resolve_tables(**_kwargs):
        return [
            ResolvedTable(
                record=TableRecord(
                    table_id="tab-1",
                    number=1,
                    label="tab:closed",
                    layout="double-column",
                    caption="Closed-loop simulation results on NeuroNCAP benchmark.",
                    raw_latex="",
                    section="Experiments",
                    subsection="",
                    role="experiments",
                    score=120,
                    caption_position="below",
                    evidence=(),
                ),
                path=table_output,
                source_reference="tab:closed",
                extraction_method="pdf_table_crop",
                confidence=0.91,
                content_sha256="table-hash",
                diagnostics=("fake-crop",),
            )
        ]

    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_figures", fake_resolve_figures)
    monkeypatch.setattr("airesearch.paper_blog.resolve_paper_tables", fake_resolve_tables)

    images = select_blog_images(db_path, "1706_03762")

    assert len(images) == 6
    assert sum(image.get("asset_kind") == "table" for image in images) == 1
    table = next(image for image in images if image.get("asset_kind") == "table")
    assert table["table_number"] == 1
    assert table["table_label"] == "tab:closed"
    assert table["artifact_type"] == "resolved_table"
    assert table["section_key"] == "experiments"
    assert table["source_path"] == str(table_output)


def test_paper_figure_context_extracts_arxiv_id_from_sources(tmp_path: Path):
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "source.tex").write_text("", encoding="utf-8")
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (paper_key, title, ids_json, meta_json, paper_dir, created_at, updated_at)
            values ('paper-a', 'Paper A', '{}', '{}', ?, '2026-06-21', '2026-06-21')
            """,
            (str(paper_dir),),
        )
        conn.execute(
            """
            insert into paper_artifacts (paper_key, artifact_type, path, sha256, size_bytes, updated_at)
            values ('paper-a', 'source_tex', ?, 'hash', 0, '2026-06-21')
            """,
            (str(paper_dir / "source.tex"),),
        )
        conn.execute(
            "insert into paper_sources (paper_key, source_type, source_value, created_at) values (?, ?, ?, ?)",
            ("paper-a", "arxiv_id", "2601.12345", "2026-06-21"),
        )
        conn.commit()
        context = _paper_figure_context(conn, "paper-a")

    assert context is not None
    assert context.arxiv_id == "2601.12345"
    assert context.output_dir == paper_dir / "blog-assets" / "figures"


def test_paper_figure_context_recovers_from_stale_absolute_paper_dir(tmp_path: Path):
    paper_dir = tmp_path / "paperpipe" / "papers" / "migrated-paper"
    paper_dir.mkdir(parents=True)
    source_tex = paper_dir / "source.tex"
    paper_pdf = paper_dir / "paper.pdf"
    source_tex.write_text("", encoding="utf-8")
    paper_pdf.write_bytes(b"%PDF-1.4\n")
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (paper_key, title, ids_json, meta_json, paper_dir, created_at, updated_at)
            values ('migrated-paper', 'Migrated Paper', '{}', '{}', ?, '2026-06-21', '2026-06-21')
            """,
            (str(tmp_path / "old" / "paperpipe" / "papers" / "migrated-paper"),),
        )
        conn.execute(
            """
            insert into paper_artifacts (paper_key, artifact_type, path, sha256, size_bytes, updated_at)
            values ('migrated-paper', 'source_tex', ?, 'hash', 0, '2026-06-21')
            """,
            (str(source_tex),),
        )
        conn.execute(
            """
            insert into paper_artifacts (paper_key, artifact_type, path, sha256, size_bytes, updated_at)
            values ('migrated-paper', 'paper_pdf', ?, 'hash', 0, '2026-06-21')
            """,
            (str(paper_pdf),),
        )
        conn.commit()
        context = _paper_figure_context(conn, "migrated-paper")

    assert context is not None
    assert context.paper_dir == paper_dir.resolve()
    assert context.source_tex == source_tex.resolve()
    assert context.pdf_path == paper_pdf.resolve()
    assert context.output_dir == paper_dir.resolve() / "blog-assets" / "figures"


def test_generate_and_publish_blog_uses_segmented_provider_and_cache(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    provider = FixtureBlogProvider(chars_per_section=520)

    first = generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="fixture-blog",
        target_chars=4200,
    )
    assert first.status == "published"
    assert first.word_count >= 3000
    assert provider.call_count == 9

    first_detail = blog_detail(db_path, "1706_03762")
    assert first_detail["post"]["current_version_id"] == first.version_id

    second_provider = FixtureBlogProvider(chars_per_section=520)
    second = generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=second_provider,
        model="fixture-blog",
        target_chars=4200,
    )
    assert second.status == "published"
    assert second.word_count >= 3000
    assert second_provider.call_count == 0


def test_generation_persists_validated_segments_before_later_section_failure(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class FailsAfterIntroProvider(FixtureBlogProvider):
        def generate_section(self, pack, section, images, *, target_chars):
            if section["section_key"] == "background":
                raise RuntimeError("transient upstream failure")
            return super().generate_section(pack, section, images, target_chars=target_chars)

    with pytest.raises(RuntimeError, match="transient upstream failure"):
        generate_and_publish_blog(
            db_path,
            "1706_03762",
            provider=FailsAfterIntroProvider(chars_per_section=520),
            model="checkpoint-provider",
            target_chars=4200,
        )

    with connect(db_path) as conn:
        cached_keys = [
            row["section_key"]
            for row in conn.execute(
                """
                select section_key from paper_blog_generation_cache
                where paper_key = '1706_03762' and model = 'checkpoint-provider'
                order by id
                """
            )
        ]
        version_count = conn.execute(
            "select count(*) from paper_blog_versions where paper_key = '1706_03762'"
        ).fetchone()[0]

    assert cached_keys == ["outline", "intro"]
    assert version_count == 0

    resumed = FixtureBlogProvider(chars_per_section=520)
    published = generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=resumed,
        model="checkpoint-provider",
        target_chars=4200,
    )

    assert published.status == "published"
    assert resumed.call_count == 7


def test_bad_cached_section_with_replacement_character_is_regenerated_alone(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=FixtureBlogProvider(chars_per_section=520),
        model="replacement-cache-provider",
        target_chars=4200,
    )

    with connect(db_path) as conn:
        cached = conn.execute(
            """
            select response_json, markdown from paper_blog_generation_cache
            where section_key = 'intro'
            """
        ).fetchone()
        cached_payload = json.loads(cached["response_json"])
        bad_markdown = str(cached["markdown"]) + "\ufffd"
        cached_payload["markdown"] = bad_markdown
        conn.execute(
            """
            update paper_blog_generation_cache
            set response_json = ?, markdown = ?
            where section_key = 'intro'
            """,
            (json.dumps(cached_payload, ensure_ascii=False), bad_markdown),
        )
        conn.commit()

    class RecordingProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.generated_sections: list[str] = []

        def generate_section(self, pack, section, images, *, target_chars):
            self.generated_sections.append(str(section["section_key"]))
            return super().generate_section(pack, section, images, target_chars=target_chars)

    provider = RecordingProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="replacement-cache-provider",
        target_chars=4200,
    )

    assert provider.generated_sections == ["intro"]
    assert provider.call_count == 1
    with connect(db_path) as conn:
        refreshed = conn.execute(
            """
            select response_json, markdown from paper_blog_generation_cache
            where section_key = 'intro'
            """
        ).fetchone()
    assert "\ufffd" not in refreshed["markdown"]
    assert "\ufffd" not in json.loads(refreshed["response_json"])["markdown"]


def test_bad_cached_outline_with_replacement_character_is_regenerated_alone(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=FixtureBlogProvider(chars_per_section=520),
        model="replacement-outline-provider",
        target_chars=4200,
    )

    with connect(db_path) as conn:
        cached = conn.execute(
            """
            select response_json from paper_blog_generation_cache
            where section_key = 'outline'
            """
        ).fetchone()
        cached_payload = json.loads(cached["response_json"])
        cached_payload["sections"][0]["purpose"] += "\ufffd"
        conn.execute(
            """
            update paper_blog_generation_cache
            set response_json = ?
            where section_key = 'outline'
            """,
            (json.dumps(cached_payload, ensure_ascii=False),),
        )
        conn.commit()

    provider = FixtureBlogProvider(chars_per_section=520)
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="replacement-outline-provider",
        target_chars=4200,
    )

    assert provider.call_count == 1
    detail = blog_detail(db_path, "1706_03762")
    assert "\ufffd" not in detail["post"]["outline_json"]
    with connect(db_path) as conn:
        refreshed = conn.execute(
            """
            select response_json from paper_blog_generation_cache
            where section_key = 'outline'
            """
        ).fetchone()
    assert "\ufffd" not in refreshed["response_json"]


def test_cached_control_token_is_escaped_without_regeneration(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=FixtureBlogProvider(chars_per_section=520),
        model="control-token-cache-provider",
        target_chars=4200,
    )

    suffix = "\n\n<loc_841> <strong>合法 HTML</strong> $x_1 < y_2$"
    with connect(db_path) as conn:
        cached = conn.execute(
            """
            select response_json, markdown from paper_blog_generation_cache
            where section_key = 'intro'
            """
        ).fetchone()
        cached_payload = json.loads(cached["response_json"])
        cached_payload["markdown"] = str(cached["markdown"]) + suffix
        conn.execute(
            """
            update paper_blog_generation_cache
            set response_json = ?, markdown = ?
            where section_key = 'intro'
            """,
            (
                json.dumps(cached_payload, ensure_ascii=False),
                cached_payload["markdown"],
            ),
        )
        conn.commit()

    provider = FixtureBlogProvider(chars_per_section=520)
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="control-token-cache-provider",
        target_chars=4200,
    )

    markdown = blog_detail(db_path, "1706_03762")["post"]["markdown"]
    assert provider.call_count == 0
    assert "<loc_841>" not in markdown
    assert "&lt;loc_841&gt;" in markdown
    assert "<strong>合法 HTML</strong>" in markdown
    assert "$x_1 < y_2$" in markdown


def test_control_token_escape_is_narrow_and_deterministic():
    markdown = (
        "<loc_841>内容</loc_841> <bbox_12_34> "
        "<strong>合法</strong> <custom-widget>组件</custom-widget> "
        "<loc_841 class=\"keep\"> $x_1 < y_2$ <token_name> "
        "`<loc_841>` \\<loc_841>\n```text\n<loc_841>\n```"
    )

    escaped = _escape_model_control_tokens(markdown)

    assert "&lt;loc_841&gt;内容&lt;/loc_841&gt;" in escaped
    assert "&lt;bbox_12_34&gt;" in escaped
    assert "<strong>合法</strong>" in escaped
    assert "<custom-widget>组件</custom-widget>" in escaped
    assert '<loc_841 class="keep">' in escaped
    assert "$x_1 < y_2$" in escaped
    assert "<token_name>" in escaped
    assert "`<loc_841>`" in escaped
    assert r"\<loc_841>" in escaped
    assert "```text\n<loc_841>\n```" in escaped


def test_openai_provider_filters_corrupt_equations_before_prompt_and_append():
    equations = [
        {"equation_id": "bad-replacement", "latex": "x = \ufffd"},
        {"equation_id": "bad-control", "latex": "x\x10y"},
        {"equation_id": "bad-del", "latex": "x\x7fy"},
        {"equation_id": "bad-c1", "latex": "x\x85y"},
        {"equation_id": "bad-leading-vtab", "latex": "\x0bx = y"},
        {"equation_id": "bad-trailing-formfeed", "latex": "x = y\x0c"},
        {"equation_id": "bad-leading-c1", "latex": "\x85x = y"},
        {"equation_id": "good", "latex": r"x = y + 1"},
    ]

    filtered = OpenAICompatibleBlogProvider._publishable_equations(equations)

    assert filtered == [equations[7]]
    markdown = OpenAICompatibleBlogProvider._append_equation_notes("正文", filtered)
    assert r"x = y + 1" in markdown
    assert "\ufffd" not in markdown
    assert "\x10" not in markdown
    assert "\x7f" not in markdown
    assert "\x85" not in markdown


@pytest.mark.parametrize("control", ["\x0b", "\x0c", "\x85"])
def test_equation_artifact_rejects_controls_before_line_splitting(control: str):
    text = f"```latex\n\\operatorname{{score}}(x){control}= \\frac{{1}}{{1 + e^{{-x}}}}\n```"

    assert _candidate_equations_from_text(text, source_path="equations.md") == []


def test_generation_inserts_section_headings_and_outline_images_with_provenance(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class MissingMarkupProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.image: dict[str, object] = {}

        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            self.image = images[0]
            self.image["caption"] = "Figure [one] unsafe"
            for section in outline["sections"]:
                section["image_ids"] = []
            outline["sections"][0]["image_ids"] = [self.image["image_id"]]
            return outline

        def generate_section(self, pack, section, images, *, target_chars):
            response = super().generate_section(pack, section, images, target_chars=target_chars)
            image_block = (
                f"![{self.image['caption']}]({self.image['asset_path']})\n\n"
                f"图注：{self.image['caption']}"
            )
            response["markdown"] = response["markdown"].replace(image_block, "")
            response["markdown"] = response["markdown"].split("\n", 1)[1].lstrip()
            response["image_ids"] = []
            return response

    provider = MissingMarkupProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="missing-markup-provider",
        target_chars=4200,
    )

    detail = blog_detail(db_path, "1706_03762")
    markdown = detail["post"]["markdown"]
    for _section_key, title in DEFAULT_SECTIONS:
        assert f"## {title}\n" in markdown
    image_path = str(provider.image["asset_path"])
    assert markdown.count(f"]({image_path})") == 1
    assert f"![Figure \\[one\\] unsafe]({image_path})" in markdown
    with connect(db_path) as conn:
        cached = conn.execute(
            "select response_json from paper_blog_generation_cache where section_key = 'intro'"
        ).fetchone()
    intro_response = json.loads(cached["response_json"])
    assert intro_response["markdown"].startswith("## 导读\n")
    assert intro_response["image_ids"] == [provider.image["image_id"]]


def test_generation_suppresses_duplicate_fixture_images_across_sections(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class DuplicateImageProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.image: dict[str, object] = {}

        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            self.image = images[0]
            for section in outline["sections"]:
                section["image_ids"] = []
            outline["sections"][0]["image_ids"] = [self.image["image_id"]]
            outline["sections"][1]["image_ids"] = [self.image["image_id"]]
            return outline

    provider = DuplicateImageProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="duplicate-image-provider",
        target_chars=4200,
    )

    markdown = blog_detail(db_path, "1706_03762")["post"]["markdown"]
    image_path = str(provider.image["asset_path"])
    assert markdown.count(f"]({image_path})") == 1
    assert markdown.count("## 导读\n") == 1
    assert markdown.count("## 背景\n") == 1
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select section_key, response_json from paper_blog_generation_cache
            where section_key in ('intro', 'background') order by section_key
            """
        ).fetchall()
    responses = {row["section_key"]: json.loads(row["response_json"]) for row in rows}
    assert responses["intro"]["image_ids"] == [provider.image["image_id"]]
    assert responses["background"]["image_ids"] == []


def test_generation_appends_first_selected_image_to_intro_when_unassigned(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class UnassignedImageProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.image: dict[str, object] = {}

        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            self.image = images[0]
            for section in outline["sections"]:
                section["image_ids"] = []
            return outline

        def generate_section(self, pack, section, images, *, target_chars):
            response = super().generate_section(pack, section, images, target_chars=target_chars)
            response["image_ids"] = []
            return response

    provider = UnassignedImageProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="unassigned-image-provider",
        target_chars=4200,
    )

    markdown = blog_detail(db_path, "1706_03762")["post"]["markdown"]
    image_path = str(provider.image["asset_path"])
    image_offset = markdown.index(f"]({image_path})")
    assert markdown.index("## 导读\n") < image_offset < markdown.index("## 背景\n")
    assert markdown.count(f"]({image_path})") == 1
    with connect(db_path) as conn:
        cached = conn.execute(
            "select response_json from paper_blog_generation_cache where section_key = 'intro'"
        ).fetchone()
    intro_response = json.loads(cached["response_json"])
    assert intro_response["image_ids"] == [provider.image["image_id"]]


def test_generation_merges_section_and_intro_fallback_provenance_into_final_outline(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class SectionProvenanceProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.fact_ids: list[int] = []
            self.image_id = ""

        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            self.fact_ids = [int(pack.facts[1]["fact_id"]), int(pack.facts[0]["fact_id"])]
            self.image_id = str(images[0]["image_id"])
            for section in outline["sections"]:
                section["fact_ids"] = []
                section["image_ids"] = []
            return outline

        def generate_section(self, pack, section, images, *, target_chars):
            response = super().generate_section(pack, section, images, target_chars=target_chars)
            if section["section_key"] == "intro":
                response["fact_ids"] = [self.fact_ids[0], self.fact_ids[1], self.fact_ids[0]]
            return response

    provider = SectionProvenanceProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="section-provenance-provider",
        target_chars=4200,
    )

    detail = blog_detail(db_path, "1706_03762")
    final_outline = json.loads(detail["post"]["outline_json"])
    intro = next(section for section in final_outline["sections"] if section["section_key"] == "intro")
    assert intro["fact_ids"] == provider.fact_ids
    assert intro["image_ids"] == [provider.image_id]

    with connect(db_path) as conn:
        cached_outline = json.loads(
            conn.execute(
                "select response_json from paper_blog_generation_cache where section_key = 'outline'"
            ).fetchone()["response_json"]
        )
    cached_intro = next(
        section for section in cached_outline["sections"] if section["section_key"] == "intro"
    )
    assert cached_intro["fact_ids"] == []
    assert cached_intro["image_ids"] == []


def test_generation_enriches_empty_outline_to_minimum_fact_coverage(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class EmptyFactOutlineProvider(FixtureBlogProvider):
        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            for section in outline["sections"]:
                section["fact_ids"] = []
            return outline

    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=EmptyFactOutlineProvider(chars_per_section=520),
        model="empty-fact-outline-provider",
        target_chars=4200,
    )

    pack = build_blog_evidence_pack(db_path, "1706_03762")
    final_outline = json.loads(blog_detail(db_path, "1706_03762")["post"]["outline_json"])
    referenced_ids = {
        int(fact_id)
        for section in final_outline["sections"]
        for fact_id in section.get("fact_ids", [])
    }
    required_count = (len(pack.facts) + 1) // 2
    assert len(referenced_ids) >= required_count
    assert all(len(section.get("fact_ids", [])) <= 4 for section in final_outline["sections"])

    with connect(db_path) as conn:
        cached_outline = json.loads(
            conn.execute(
                "select response_json from paper_blog_generation_cache where section_key = 'outline'"
            ).fetchone()["response_json"]
        )
    assert all(section["fact_ids"] == [] for section in cached_outline["sections"])


def test_outline_fact_enrichment_enforces_dynamic_capacity_for_large_fact_sets():
    outline = {
        "title": "Large fact set",
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ],
    }
    facts = [
        {"fact_id": fact_id, "fact_type": "method"}
        for fact_id in range(1, 66)
    ]

    enriched = _outline_with_minimum_fact_coverage(outline, facts)

    referenced_ids = {
        int(fact_id)
        for section in enriched["sections"]
        for fact_id in section["fact_ids"]
    }
    assert len(referenced_ids) == 33
    assert max(len(section["fact_ids"]) for section in enriched["sections"]) == 5
    assert all(len(section["fact_ids"]) <= 5 for section in enriched["sections"])

    duplicate_outline = {
        **outline,
        "sections": [
            {**section, "fact_ids": [1, 2, 3, 4]}
            for section in outline["sections"]
        ],
    }
    deduplicated = _outline_with_minimum_fact_coverage(duplicate_outline, facts)
    deduplicated_ids = {
        int(fact_id)
        for section in deduplicated["sections"]
        for fact_id in section["fact_ids"]
    }
    assert len(deduplicated_ids) == 33
    assert all(len(section["fact_ids"]) <= 5 for section in deduplicated["sections"])

    oversized_outline = {
        **outline,
        "sections": [
            {
                **section,
                "fact_ids": list(range(1, 11)) if index == 0 else [],
            }
            for index, section in enumerate(outline["sections"])
        ],
    }
    capped = _outline_with_minimum_fact_coverage(oversized_outline, facts)
    capped_ids = {
        int(fact_id)
        for section in capped["sections"]
        for fact_id in section["fact_ids"]
    }
    assert len(capped_ids) == 33
    assert all(len(section["fact_ids"]) <= 5 for section in capped["sections"])


def test_outline_fact_enrichment_persists_deduplication_when_coverage_already_met():
    outline = {
        "title": "Duplicate facts",
        "sections": [
            {
                "section_key": key,
                "title": title,
                "fact_ids": [1, 2, 3, 4],
                "image_ids": [],
            }
            for key, title in DEFAULT_SECTIONS
        ],
    }
    facts = [{"fact_id": fact_id, "fact_type": "method"} for fact_id in range(1, 9)]

    enriched = _outline_with_minimum_fact_coverage(outline, facts)

    occurrences = [
        int(fact_id)
        for section in enriched["sections"]
        for fact_id in section["fact_ids"]
    ]
    assert occurrences == [1, 2, 3, 4]


def test_outline_fact_enrichment_prefers_semantic_sections_before_empty_fallbacks():
    outline = {
        "title": "Semantic preference",
        "sections": [
            {
                "section_key": key,
                "title": title,
                "fact_ids": [1] if key == "method" else [],
                "image_ids": [],
            }
            for key, title in DEFAULT_SECTIONS
        ],
    }
    facts = [
        {"fact_id": 1, "fact_type": "method"},
        {"fact_id": 2, "fact_type": "method"},
        {"fact_id": 3, "fact_type": "claim"},
        {"fact_id": 4, "fact_type": "benchmark"},
    ]

    enriched = _outline_with_minimum_fact_coverage(outline, facts)
    by_key = {section["section_key"]: section for section in enriched["sections"]}

    assert by_key["architecture"]["fact_ids"] == [2]
    assert by_key["intro"]["fact_ids"] == []


def test_final_outline_provenance_filters_invalid_ids_and_preserves_order():
    outline = {
        "title": "Test",
        "sections": [
            {"section_key": "intro", "fact_ids": [], "image_ids": []},
        ],
    }
    responses = [
        {
            "section_key": "intro",
            "fact_ids": [2, 999, 1, 2, "invalid"],
            "image_ids": ["img-b", "missing", "img-a", "img-b"],
        }
    ]

    final_outline = _final_outline_with_provenance(
        outline,
        responses,
        facts=[{"fact_id": 1}, {"fact_id": 2}],
        images=[{"image_id": "img-a"}, {"image_id": "img-b"}],
    )

    assert final_outline["sections"][0]["fact_ids"] == [2, 1]
    assert final_outline["sections"][0]["image_ids"] == ["img-b", "img-a"]
    assert outline["sections"][0]["fact_ids"] == []
    assert outline["sections"][0]["image_ids"] == []


def test_generation_encodes_special_image_paths_and_export_rewrites_them(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class SpecialPathProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.image: dict[str, object] = {}

        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            self.image = images[0]
            source_path = Path(str(self.image["source_path"]))
            special_source = tmp_path / "source figures" / f"{source_path.stem} (draft){source_path.suffix}"
            special_source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, special_source)
            self.image["source_path"] = str(special_source)
            self.image["asset_path"] = "blog assets/figure (overview).webp"
            for section in outline["sections"]:
                section["image_ids"] = []
            outline["sections"][0]["image_ids"] = [self.image["image_id"]]
            return outline

        def generate_section(self, pack, section, images, *, target_chars):
            response = super().generate_section(pack, section, images, target_chars=target_chars)
            if section["section_key"] == "intro":
                response["markdown"] = response["markdown"].split("\n\n![", 1)[0] + "\n"
            return response

    provider = SpecialPathProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="special-image-path-provider",
        target_chars=4200,
    )

    markdown = blog_detail(db_path, "1706_03762")["post"]["markdown"]
    encoded_path = urllib.parse.quote(str(provider.image["asset_path"]), safe="/-._~")
    assert f"]({encoded_path})" in markdown
    validate_blog(
        markdown=markdown,
        outline=json.loads(blog_detail(db_path, "1706_03762")["post"]["outline_json"]),
        image_refs=[provider.image],
        facts=build_blog_evidence_pack(db_path, "1706_03762").facts,
    )

    out_path = tmp_path / "export" / "paper-blogs.json"
    exported = export_paper_blogs(db_path, out_path)["blogs"][0]
    exported_path = exported["image_refs"][0]["asset_path"]
    assert " " in exported_path and "(" in exported_path
    assert f"]({urllib.parse.quote(exported_path, safe='/-._~')})" in exported["markdown"]


def test_code_image_examples_do_not_suppress_intro_fallback_or_populate_ids(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class CodeExampleProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=520)
            self.image: dict[str, object] = {}

        def generate_outline(self, pack, images, *, target_chars):
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            self.image = images[0]
            for section in outline["sections"]:
                section["image_ids"] = []
            return outline

        def generate_section(self, pack, section, images, *, target_chars):
            response = super().generate_section(pack, section, images, target_chars=target_chars)
            if section["section_key"] == "background":
                path = self.image["asset_path"]
                response["markdown"] += (
                    f"\n`![inline example]({path})`\n\n"
                    f"```markdown\n![fenced example]({path})\n```\n"
                )
            return response

    provider = CodeExampleProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="code-image-example-provider",
        target_chars=4200,
    )

    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select section_key, response_json from paper_blog_generation_cache
            where section_key in ('intro', 'background') order by section_key
            """
        ).fetchall()
    responses = {row["section_key"]: json.loads(row["response_json"]) for row in rows}
    image_id = provider.image["image_id"]
    image_path = str(provider.image["asset_path"])
    assert responses["background"]["image_ids"] == []
    assert responses["intro"]["image_ids"] == [image_id]
    assert responses["intro"]["markdown"].rstrip().endswith(f"]({image_path})")


def test_section_image_injection_preserves_outline_order():
    images = [
        {"image_id": "img-a", "asset_path": "paper assets/a (one).png", "caption": "A"},
        {"image_id": "img-b", "asset_path": "paper assets/b (two).png", "caption": "B"},
    ]
    response = {"section_key": "intro", "markdown": "正文", "fact_ids": [], "image_ids": []}
    section = {
        "section_key": "intro",
        "title": "导读",
        "fact_ids": [],
        "image_ids": ["img-b", "img-a"],
    }

    _assemble_section_response(
        response,
        section,
        image_by_id={str(image["image_id"]): image for image in images},
        image_by_path={str(image["asset_path"]): image for image in images},
        used_asset_paths=set(),
    )

    b_path = urllib.parse.quote(str(images[1]["asset_path"]), safe="/-._~")
    a_path = urllib.parse.quote(str(images[0]["asset_path"]), safe="/-._~")
    assert response["image_ids"] == ["img-b", "img-a"]
    assert response["markdown"].index(b_path) < response["markdown"].index(a_path)


def test_encoded_existing_image_deduplicates_against_declared_raw_path():
    image = {
        "image_id": "img-1",
        "asset_path": "paper assets/figure (one).png",
        "caption": "Figure one",
    }
    encoded_path = urllib.parse.quote(str(image["asset_path"]), safe="/-._~")
    response = {
        "section_key": "intro",
        "markdown": f"## 导读\n\n![已存在]({encoded_path})",
        "fact_ids": [],
        "image_ids": [],
    }
    section = {
        "section_key": "intro",
        "title": "导读",
        "fact_ids": [],
        "image_ids": ["img-1"],
    }

    _assemble_section_response(
        response,
        section,
        image_by_id={"img-1": image},
        image_by_path={str(image["asset_path"]): image},
        used_asset_paths=set(),
    )

    assert response["markdown"].count(f"]({encoded_path})") == 1
    assert response["image_ids"] == ["img-1"]


def test_escaped_image_syntax_is_not_rendered_or_used_for_provenance():
    image = {
        "image_id": "img-1",
        "asset_path": "paper-assets/figure.png",
        "caption": "Figure",
    }
    response = {
        "section_key": "intro",
        "markdown": r"## 导读\n\n\![示例](paper-assets/figure.png)",
        "fact_ids": [],
        "image_ids": [],
    }
    used_asset_paths: set[str] = set()

    _assemble_section_response(
        response,
        {"section_key": "intro", "title": "导读", "fact_ids": [], "image_ids": []},
        image_by_id={"img-1": image},
        image_by_path={str(image["asset_path"]): image},
        used_asset_paths=used_asset_paths,
    )

    assert response["image_ids"] == []
    assert used_asset_paths == set()
    with pytest.raises(BlogValidationError, match="missing declared local image"):
        validate_blog(
            markdown=("中" * 3000) + r"\n\n\![示例](paper-assets/figure.png)",
            outline={
                "sections": [
                    {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
                    for key, title in DEFAULT_SECTIONS
                ]
            },
            image_refs=[image],
            facts=[],
        )


@pytest.mark.parametrize(
    ("asset_path", "markdown_image"),
    [
        (
            "paper-assets/figure(1).png",
            r'![图](paper-assets/figure\(1\).png "title with \"quotes\"")',
        ),
        (
            "paper-assets/figure(one(two)).png",
            r"![图](paper-assets/figure(one(two)).png 'title with \' quote')",
        ),
        (
            "paper-assets/figure-newline.png",
            "![图](paper-assets/figure-newline.png\n  \"title after newline\")",
        ),
    ],
)
def test_validate_blog_parses_escaped_and_nested_image_destinations(asset_path, markdown_image):
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }
    response_markdown = "## 导读\n\n" + markdown_image

    validate_blog(
        markdown=("中" * 3000) + "\n\n" + markdown_image,
        outline=outline,
        image_refs=[{"image_id": "img-1", "asset_path": asset_path}],
        facts=[],
        section_responses=[
            {
                "section_key": "intro",
                "markdown": response_markdown,
                "fact_ids": [],
                "image_ids": ["img-1"],
            }
        ],
    )


def test_blockquote_fenced_image_is_not_rendered():
    image = {"image_id": "img-1", "asset_path": "paper-assets/figure.png"}
    fenced_example = "> ~~~markdown\n> ![代码示例](paper-assets/figure.png)\n> ~~~"
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match="missing declared local image"):
        validate_blog(
            markdown=("中" * 3000) + "\n\n" + fenced_example,
            outline=outline,
            image_refs=[image],
            facts=[],
        )


@pytest.mark.parametrize("container_closer", ["> ```", "- ```"])
def test_top_level_fence_ignores_container_pseudo_closer(container_closer):
    image = {"image_id": "img-1", "asset_path": "paper-assets/figure.png"}
    markdown = (
        "```markdown\n"
        f"{container_closer}\n"
        "![伪渲染图片](paper-assets/figure.png)\n"
        "```"
    )
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match="missing declared local image"):
        validate_blog(
            markdown=("中" * 3000) + "\n\n" + markdown,
            outline=outline,
            image_refs=[image],
            facts=[],
        )


@pytest.mark.parametrize(
    "prefix",
    [
        "> ~~~markdown\n> 示例代码",
        "10. ~~~markdown\n    示例代码\n    ~~~",
    ],
)
def test_container_fence_end_keeps_following_real_image_visible(prefix):
    image = {"image_id": "img-1", "asset_path": "paper-assets/figure.png"}
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }
    markdown = (
        ("中" * 3000)
        + "\n\n"
        + prefix
        + "\n![真实图片](paper-assets/figure.png)\n"
    )

    validate_blog(markdown=markdown, outline=outline, image_refs=[image], facts=[])


def test_inline_code_closes_on_backtick_after_literal_backslash():
    image = {"image_id": "img-1", "asset_path": "paper-assets/figure.png"}
    inline_code = "`![伪渲染图片](paper-assets/figure.png) \\`"
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match="missing declared local image"):
        validate_blog(
            markdown=("中" * 3000) + "\n\n" + inline_code,
            outline=outline,
            image_refs=[image],
            facts=[],
        )


def test_validate_blog_requires_section_response_h2():
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match="must begin with H2"):
        validate_blog(
            markdown="中" * 3000,
            outline=outline,
            image_refs=[],
            facts=[],
            section_responses=[
                {"section_key": "intro", "markdown": "没有二级标题", "fact_ids": [], "image_ids": []}
            ],
        )


def test_validate_blog_rejects_replacement_character_in_final_markdown():
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match="replacement character"):
        validate_blog(
            markdown=("中" * 3000) + "\ufffd",
            outline=outline,
            image_refs=[],
            facts=[],
        )


def test_validate_blog_rejects_replacement_character_in_section_markdown():
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match="replacement character"):
        validate_blog(
            markdown="中" * 3000,
            outline=outline,
            image_refs=[],
            facts=[],
            section_responses=[
                {
                    "section_key": "intro",
                    "markdown": "## 导读\n\n坏字符：\ufffd",
                    "fact_ids": [],
                    "image_ids": [],
                }
            ],
        )


@pytest.mark.parametrize(
    ("response_markdown", "response_image_ids"),
    [
        ("## 导读\n\n没有图片", ["img-1"]),
        ("## 导读\n\n![实际图片](paper%20assets/figure%20%281%29.png)", []),
        (
            "## 导读\n\n`![代码示例](paper%20assets/figure%20%281%29.png)`\n\n"
            "```markdown\n![代码块](paper%20assets/figure%20%281%29.png)\n```",
            ["img-1"],
        ),
    ],
)
def test_validate_blog_rejects_section_image_provenance_mismatch(
    response_markdown,
    response_image_ids,
):
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }
    image = {"image_id": "img-1", "asset_path": "paper assets/figure (1).png"}
    final_markdown = (
        ("中" * 3000)
        + "\n\n![最终图片](paper%20assets/figure%20%281%29.png)"
    )

    with pytest.raises(BlogValidationError, match="image_ids do not match embedded images"):
        validate_blog(
            markdown=final_markdown,
            outline=outline,
            image_refs=[image],
            facts=[],
            section_responses=[
                {
                    "section_key": "intro",
                    "markdown": response_markdown,
                    "fact_ids": [],
                    "image_ids": response_image_ids,
                }
            ],
        )


def test_validate_blog_accepts_encoded_declared_path_and_image_free_section():
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }
    image = {"image_id": "img-1", "asset_path": "paper assets/figure (1).png"}
    encoded_image = "![图片](paper%20assets/figure%20%281%29.png)"

    validate_blog(
        markdown=("中" * 3000) + "\n\n" + encoded_image,
        outline=outline,
        image_refs=[image],
        facts=[],
        section_responses=[
            {
                "section_key": "intro",
                "markdown": "## 导读\n\n本节没有图片",
                "fact_ids": [],
                "image_ids": [],
            }
        ],
    )


@pytest.mark.parametrize(
    ("markdown_suffix", "image_refs", "error_fragment"),
    [
        ("", [{"image_id": "img-1", "asset_path": "paper-assets/figure.png"}], "missing declared local image"),
        ("![bad](https://example.test/image.png)", [], "external image path"),
        (
            "![bad](paper-assets/undeclared.png)",
            [{"image_id": "img-1", "asset_path": "paper-assets/figure.png"}],
            "undeclared image path",
        ),
    ],
)
def test_validate_blog_rejects_invalid_final_image_usage(markdown_suffix, image_refs, error_fragment):
    outline = {
        "sections": [
            {"section_key": key, "title": title, "fact_ids": [], "image_ids": []}
            for key, title in DEFAULT_SECTIONS
        ]
    }

    with pytest.raises(BlogValidationError, match=error_fragment):
        validate_blog(
            markdown=("中" * 3000) + "\n\n" + markdown_suffix,
            outline=outline,
            image_refs=image_refs,
            facts=[],
        )


def test_generate_and_publish_blog_rejects_short_output_and_preserves_current_version(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    published = generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=FixtureBlogProvider(chars_per_section=520),
        model="fixture-blog",
        target_chars=4200,
    )
    provider = FixtureBlogProvider(chars_per_section=20)

    try:
        generate_and_publish_blog(
            db_path,
            "1706_03762",
            provider=provider,
            model="fixture-blog",
            target_chars=4200,
            force=True,
        )
    except BlogValidationError as exc:
        assert "word count" in str(exc) or "section below target length" in str(exc)
    else:
        raise AssertionError("short generated blog should fail validation")

    detail = blog_detail(db_path, "1706_03762")
    assert detail["post"]["current_version_id"] == published.version_id
    assert [version["version_number"] for version in detail["versions"]] == [1]


def test_admin_blog_generation_job_publishes_and_can_hide_rollback(tmp_path: Path, monkeypatch):
    db_path, paper_db = build_fixture_corpus(tmp_path)
    insert_minimal_paper(db_path, "hidden-paper")
    with connect(db_path) as conn:
        conn.execute(
            "insert into admin_paper_overrides (paper_key, hidden, updated_at) values (?, 1, ?)",
            ("hidden-paper", "2026-06-20T00:00:00+00:00"),
        )
        conn.commit()
    install_test_deploy_runner(monkeypatch)
    deploy_marker = tmp_path / "deploy-marker.txt"
    deploy_script = tmp_path / "deploy.sh"
    write_deploy_script(deploy_script, marker=deploy_marker)
    config = AdminConfig(
        base_path="/niu-secretary/airesearch/admin/",
        db_path=db_path,
        paper_db_path=paper_db,
        project_dir=tmp_path,
        deploy_script=deploy_script,
        papi_executable="papi",
        username="",
        password="",
    )
    result = run_blog_generation_job(
        config,
        job_id=1,
        options={"paperKey": "1706_03762", "provider": "fixture", "targetWordCount": 4200},
    )
    assert "paper_blog_generate completed" in result
    assert (tmp_path / "exports" / "site-current" / "index.html").is_file()
    assert "hidden-paper" not in (tmp_path / "exports" / "site-current" / "api" / "papers.json").read_text(encoding="utf-8")

    detail = admin_blog_detail(db_path, "1706_03762")
    assert detail["post"]["status"] == "published"
    version_id = detail["post"]["current_version_id"]

    admin_hide_blog(db_path, "1706_03762", config=config)
    assert admin_blog_detail(db_path, "1706_03762")["post"]["status"] == "hidden"
    hidden_export = json.loads((tmp_path / "exports" / "site-current" / "paper-blogs.json").read_text(encoding="utf-8"))
    assert hidden_export["blog_count"] == 0

    admin_rollback_blog(db_path, "1706_03762", version_id, config=config)
    assert admin_blog_detail(db_path, "1706_03762")["post"]["status"] == "published"
    restored_export = json.loads((tmp_path / "exports" / "site-current" / "paper-blogs.json").read_text(encoding="utf-8"))
    assert restored_export["blog_count"] == 1
    assert deploy_marker.read_text(encoding="utf-8").splitlines() == ["deployed", "deployed", "deployed"]


def test_list_state_includes_compact_blog_summary(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    insert_minimal_paper(db_path, "hidden-blog")
    insert_minimal_paper(db_path, "paper-without-blog")
    markdown = "# 深度解读\n\n" + ("论文分析内容。" * 800)
    published = publish_blog_version(
        db_path,
        paper_key="1706_03762",
        title="Attention 深度解读",
        slug="attention-blog",
        markdown=markdown,
        html="<h1>Attention 深度解读</h1>",
        outline={"sections": []},
        image_refs=[],
        generation_meta={},
        model="fixture-blog",
        prompt_version="test-v1",
        source_hash="published-source",
    )
    publish_blog_version(
        db_path,
        paper_key="hidden-blog",
        title="Hidden 深度解读",
        slug="hidden-blog",
        markdown=markdown,
        html="<h1>Hidden 深度解读</h1>",
        outline={"sections": []},
        image_refs=[],
        generation_meta={},
        model="fixture-blog",
        prompt_version="test-v1",
        source_hash="hidden-source",
    )
    hide_blog_post(db_path, "hidden-blog")
    with connect(db_path) as conn:
        for status, message in (("publish_failed", "old failure"), ("completed", "new success")):
            conn.execute(
                """
                insert into admin_jobs (
                    job_type, status, message, params_json, current_step, result_json,
                    priority, created_at, started_at, finished_at
                ) values ('paper_blog_generate', ?, ?, ?, '', '{}', 0, ?, ?, ?)
                """,
                (
                    status,
                    message,
                    json.dumps({"paperKey": "1706_03762"}),
                    f"2026-06-20T00:00:0{1 if status == 'publish_failed' else 2}+00:00",
                    "2026-06-20T00:00:00+00:00",
                    "2026-06-20T00:00:03+00:00",
                ),
            )
        conn.execute(
            """
            insert into paper_layout_runs (
                paper_key, provider, provider_version, backend, method, status,
                input_pdf_path, output_dir, artifact_json, stats_json,
                started_at, finished_at
            ) values (
                '1706_03762', 'airesearch_layout', 'v2', 'pymupdf', 'native',
                'completed', '/tmp/paper.pdf', '/tmp/layout', '{}', ?,
                '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:03+00:00'
            )
            """,
            (
                json.dumps(
                    {
                        "artifact_count": 5,
                        "block_count": 18,
                        "summary": {
                            "parser_version": "v2",
                            "page_count": 12,
                            "evidence_ready_blocks": 9,
                            "captioned_visual_blocks": 3,
                            "structured_table_blocks": 2,
                            "equation_blocks": 4,
                        }
                    }
                ),
            ),
        )
        conn.commit()

    summaries = {item["paper_key"]: item for item in list_state(db_path)["papers"]}

    assert summaries["1706_03762"]["blog_status"] == "published"
    assert summaries["1706_03762"]["blog_word_count"] >= 3000
    assert summaries["1706_03762"]["blog_current_version_id"] == published.version_id
    assert summaries["1706_03762"]["blog_updated_at"]
    assert summaries["1706_03762"]["blog_latest_job_status"] == "completed"
    assert summaries["1706_03762"]["blog_latest_job_message"] == "new success"
    assert summaries["1706_03762"]["layout_status"] == "completed"
    assert summaries["1706_03762"]["layout_parser_version"] == "v2"
    assert summaries["1706_03762"]["layout_artifact_count"] == 5
    assert summaries["1706_03762"]["layout_block_count"] == 18
    assert summaries["1706_03762"]["layout_evidence_ready_blocks"] == 9
    assert summaries["1706_03762"]["layout_captioned_visual_blocks"] == 3
    assert summaries["1706_03762"]["layout_structured_table_blocks"] == 2
    assert summaries["1706_03762"]["layout_equation_blocks"] == 4
    assert summaries["1706_03762"]["layout_page_count"] == 12
    assert summaries["hidden-blog"]["blog_status"] == "hidden"
    assert summaries["paper-without-blog"]["blog_status"] == "not_generated"
    assert summaries["paper-without-blog"]["layout_status"] == "not_parsed"
    assert summaries["paper-without-blog"]["layout_evidence_ready_blocks"] == 0
    assert summaries["paper-without-blog"]["blog_word_count"] == 0
    assert summaries["paper-without-blog"]["blog_current_version_id"] is None


def test_ingest_single_paper_auto_queues_layout_parse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from airesearch import admin_server

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    paper_db.mkdir()
    config = make_admin_config(tmp_path, db_path, paper_db)
    monkeypatch.setattr(admin_server, "_ensure_worker", lambda _config: None)

    def fake_papi_run(command, **_kwargs):
        assert command[:2] == ["papi", "add"]
        write_paperpipe_entry(paper_db, "2607_00001")
        return subprocess.CompletedProcess(command, 0, stdout="Added: 2607_00001\n", stderr="")

    monkeypatch.setattr(admin_server.subprocess, "run", fake_papi_run)

    result = ingest_single_paper(
        db_path=db_path,
        paper_db_path=paper_db,
        papi_executable="papi",
        paper_input="2607.00001",
        config=config,
    )

    assert result["status"] == "success"
    assert result["paper_key"] == "2607_00001"
    assert result["layout_job_status"] == "queued"
    assert result["layout_job_id"]
    state = list_state(db_path)
    paper = next(item for item in state["papers"] if item["paper_key"] == "2607_00001")
    assert paper["layout_status"] == "queued"
    with connect(db_path) as conn:
        jobs = conn.execute("select job_type, status, params_json from admin_jobs").fetchall()
    assert len(jobs) == 1
    assert jobs[0]["job_type"] == "paper_layout_parse"
    assert jobs[0]["status"] == "queued"
    assert json.loads(jobs[0]["params_json"])["paperKey"] == "2607_00001"


def test_ingest_single_paper_reuses_active_layout_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from airesearch import admin_server

    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = tmp_path / "paperpipe"
    paper_db.mkdir()
    write_paperpipe_entry(paper_db, "2607_00001")
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    config = make_admin_config(tmp_path, db_path, paper_db)
    monkeypatch.setattr(admin_server, "_ensure_worker", lambda _config: None)
    first_job = admin_server.start_job(config, "paper_layout_parse", {"paperKey": "2607_00001", "force": False})

    def fake_papi_run(command, **_kwargs):
        assert command[:2] == ["papi", "add"]
        return subprocess.CompletedProcess(command, 0, stdout="Already added: 2607_00001\n", stderr="")

    monkeypatch.setattr(admin_server.subprocess, "run", fake_papi_run)

    result = ingest_single_paper(
        db_path=db_path,
        paper_db_path=paper_db,
        papi_executable="papi",
        paper_input="2607.00001",
        config=config,
    )

    assert result["layout_job_status"] == "existing"
    assert result["layout_job_id"] == first_job["job_id"]
    with connect(db_path) as conn:
        count = conn.execute("select count(*) as count from admin_jobs where job_type = 'paper_layout_parse'").fetchone()["count"]
    assert count == 1


def test_export_paper_blogs_outputs_only_published_posts(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    provider = FixtureBlogProvider(chars_per_section=520)
    generate_and_publish_blog(db_path, "1706_03762", provider=provider, model="fixture-blog", target_chars=4200)
    insert_minimal_paper(db_path, "hidden_paper")
    publish_blog_version(
        db_path,
        paper_key="hidden_paper",
        title="Hidden 深度解读",
        slug="hidden_paper",
        markdown="# Hidden 深度解读\n\n隐藏正文",
        html="<h1>Hidden 深度解读</h1><p>隐藏正文</p>",
        outline={"sections": [{"section_key": "intro", "title": "导读"}]},
        image_refs=[],
        generation_meta={},
        model="fixture-blog",
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash="hash-hidden",
    )
    hide_blog_post(db_path, "hidden_paper")

    out_path = tmp_path / "paper-blogs.json"
    result = export_paper_blogs(db_path, out_path)
    payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert result["blog_count"] == 1
    assert payload["blog_count"] == 1
    assert payload["blogs"][0]["paper_key"] == "1706_03762"
    assert payload["blogs"][0]["status"] == "published"
    assert payload["blogs"][0]["markdown"]
    image_refs = payload["blogs"][0]["image_refs"]
    assert image_refs
    for image in image_refs:
        assert image["asset_path"].startswith("paper-assets/blogs/")
        assert "source_path" not in image
        assert (out_path.parent / image["asset_path"]).is_file()


def test_export_suppresses_legacy_layout_fragments_covered_by_complete_figure(tmp_path: Path):
    db_path = tmp_path / "research.db"
    init_db(db_path)
    ensure_blog_schema(db_path)
    insert_minimal_paper(db_path)
    complete = tmp_path / "complete.png"
    fragment = tmp_path / "fragment.png"
    complete.write_bytes(b"complete-figure")
    fragment.write_bytes(b"fragment")
    caption = "Figure 1. Complete architecture overview."
    publish_blog_version(
        db_path,
        paper_key="1706_03762",
        title="Legacy fragments",
        slug="1706_03762",
        markdown=(
            "# Legacy fragments\n\n"
            "![complete](blog-assets/complete.png)\n\n"
            "![fragment](blog-assets/fragment.png)"
        ),
        html="<h1>Legacy fragments</h1>",
        outline={"sections": []},
        image_refs=[
            {
                "image_id": "img-complete",
                "asset_path": "blog-assets/complete.png",
                "source_path": str(complete),
                "caption": caption,
                "artifact_type": "layout_pdf_crop",
                "asset_kind": "figure",
                "figure_number": 1,
                "evidence": [{"page_index": 0}],
            },
            {
                "image_id": "img-fragment",
                "asset_path": "blog-assets/fragment.png",
                "source_path": str(fragment),
                "caption": caption,
                "artifact_type": "layout_block",
                "asset_kind": "figure",
                "evidence": [{"page_index": 0}],
            },
        ],
        generation_meta={},
        model="fixture",
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash="legacy-fragments",
    )

    exported = export_paper_blogs(db_path, tmp_path / "export" / "paper-blogs.json")["blogs"][0]

    assert [image["image_id"] for image in exported["image_refs"]] == ["img-complete"]
    assert "![complete]" in exported["markdown"]
    assert "![fragment]" not in exported["markdown"]


def test_export_preserves_literal_percent_in_declared_filename(tmp_path: Path):
    db_path = tmp_path / "research.db"
    init_db(db_path)
    ensure_blog_schema(db_path)
    insert_minimal_paper(db_path)
    source_path = tmp_path / "figure%20literal.png"
    source_path.write_bytes(b"literal-percent-image")
    asset_path = "blog-assets/figure%20literal.png"
    publish_blog_version(
        db_path,
        paper_key="1706_03762",
        title="Literal percent",
        slug="1706_03762",
        markdown="# Literal percent\n\n![图](blog-assets/figure%2520literal.png\n  \"literal title\")",
        html="<h1>Literal percent</h1>",
        outline={"sections": []},
        image_refs=[
            {
                "image_id": "img-percent",
                "asset_path": asset_path,
                "source_path": str(source_path),
            }
        ],
        generation_meta={},
        model="fixture",
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash="literal-percent",
    )

    exported = export_paper_blogs(db_path, tmp_path / "export" / "paper-blogs.json")["blogs"][0]
    exported_path = exported["image_refs"][0]["asset_path"]
    assert "%20" in exported_path
    assert f"]({urllib.parse.quote(exported_path, safe='/-._~')}\n" in exported["markdown"]
    assert "%2520literal" in exported["markdown"]
    assert '"literal title")' in exported["markdown"]
    assert (tmp_path / "export" / exported_path).is_file()


def test_export_removes_only_images_whose_declared_source_is_unavailable(tmp_path: Path):
    db_path = tmp_path / "research.db"
    init_db(db_path)
    ensure_blog_schema(db_path)
    insert_minimal_paper(db_path)
    missing_asset_path = "blog-assets/missing figure.png"
    markdown = (
        "# Export safety\n\nBefore missing.\n\n"
        "![missing](blog-assets/missing%20figure.png)\n\n"
        "Keep this paragraph and ![user image](user-assets/keep.png) intact.\n\nAfter missing."
    )
    publish_blog_version(
        db_path,
        paper_key="1706_03762",
        title="Export safety",
        slug="1706_03762",
        markdown=markdown,
        html="<h1>Export safety</h1>",
        outline={"sections": []},
        image_refs=[
            {
                "image_id": "img-missing",
                "asset_path": missing_asset_path,
                "source_path": str(tmp_path / "does-not-exist.png"),
            }
        ],
        generation_meta={},
        model="fixture",
        prompt_version=BLOG_PROMPT_VERSION,
        source_hash="missing-export-image",
    )

    exported = export_paper_blogs(db_path, tmp_path / "export" / "paper-blogs.json")["blogs"][0]
    assert exported["image_refs"] == []
    assert "![missing](blog-assets/missing%20figure.png)" not in exported["markdown"]
    assert "![user image](user-assets/keep.png)" in exported["markdown"]
    assert "Before missing." in exported["markdown"]
    assert "After missing." in exported["markdown"]


def test_blog_provider_from_options_supports_openai_compatible_default(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    calls: dict[str, object] = {}

    class DummyProvider:
        name = "dummy"

    def fake_from_env(
        cls,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        api_style: str | None = None,
        proxy_url: str | None = None,
    ):
        calls["model"] = model
        calls["base_url"] = base_url
        calls["api_key_env"] = api_key_env
        calls["api_style"] = api_style
        calls["proxy_url"] = proxy_url
        return DummyProvider()

    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "test-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_MODEL", "env-blog-model")
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://blog.example/v1")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_STYLE", "responses")
    monkeypatch.setenv("AIRESEARCH_BLOG_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setattr(OpenAICompatibleBlogProvider, "from_env", classmethod(fake_from_env))

    provider, model = _blog_provider_from_options(
        {
            "provider": "openai-compatible",
            "base_url": "https://attacker.invalid/v1",
            "api_style": "chat_completions",
            "proxy_url": "http://attacker.invalid:8080",
        }
    )

    assert isinstance(provider, DummyProvider)
    assert model == "env-blog-model"
    assert calls == {
        "model": "env-blog-model",
        "base_url": "https://blog.example/v1",
        "api_key_env": "OPENAI_API_KEY",
        "api_style": "responses",
        "proxy_url": "http://127.0.0.1:7890",
    }


def test_blog_provider_from_options_ignores_untrusted_transport_options_without_trusted_env(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    calls: dict[str, object] = {}

    class DummyProvider:
        name = "dummy"

    def fake_from_env(
        cls,
        *,
        model: str | None = None,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        api_style: str | None = None,
        proxy_url: str | None = None,
    ):
        calls.update(
            {
                "model": model,
                "base_url": base_url,
                "api_key_env": api_key_env,
                "api_style": api_style,
                "proxy_url": proxy_url,
            }
        )
        return DummyProvider()

    monkeypatch.setattr(OpenAICompatibleBlogProvider, "from_env", classmethod(fake_from_env))

    provider, model = _blog_provider_from_options(
        {
            "provider": "openai-compatible",
            "endpoint": "https://attacker.invalid/v1/responses",
            "base_url": "https://attacker.invalid/v1",
            "api_style": "responses",
            "proxy": "http://attacker.invalid:8080",
            "proxy_url": "http://attacker.invalid:8080",
        }
    )

    assert isinstance(provider, DummyProvider)
    assert model == "deepseek-v4-pro"
    assert calls == {
        "model": "deepseek-v4-pro",
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
        "api_style": None,
        "proxy_url": "",
    }


def test_blog_provider_default_model_matches_configured_deepseek_model(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    monkeypatch.setenv("TRANSLATE_API_KEY", "test-key")
    monkeypatch.setenv("TRANSLATE_BASE_URL", "https://api.deepseek.com")

    provider = OpenAICompatibleBlogProvider.from_env()

    assert provider.model == "deepseek-v4-pro"
    from niu_core.llm_client import compat

    _base, _key, _model = compat.resolve("blog")
    assert provider.api_key == _key, "yaml(compat) 应压过历史通用 TRANSLATE_* key"
    assert provider.base_url.rstrip("/") == str(_base).rstrip("/")


def test_blog_provider_defaults_from_unified_gateway_config(monkeypatch):
    """With no blog env vars, defaults resolve from config/models.yaml (unified)."""
    clear_blog_provider_env(monkeypatch)
    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "test-key")

    provider = OpenAICompatibleBlogProvider.from_env()

    #Unified config drives the default; the fixture config's base_url wins.
    assert provider.model, "default model must resolve from unified config or fallback"
    assert provider.base_url, "default base_url must resolve from unified config or fallback"


def test_blog_transport_normalizes_deepseek_base_url():
    assert (
        OpenAICompatibleBlogTransport._normalize_base_url("https://api.deepseek.com")
        == "https://api.deepseek.com/v1"
    )


def test_chat_blog_transport_builds_request_and_parses_fenced_json(monkeypatch):
    requests: list[tuple[urllib.request.Request, float]] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "```json\n{\"ok\": true}\n```"},
                        }
                    ]
                }
            ).encode()

    def fake_urlopen(request, *, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    messages = [{"role": "system", "content": "Return JSON only."}]

    result = OpenAICompatibleBlogTransport().complete_json(
        model="test-model",
        base_url="https://api.example.test/v1/",
        api_key="chat-test-key",
        messages=messages,
        max_output_tokens=321,
    )

    assert result == {"ok": True}
    request, timeout = requests[0]
    headers = {name.lower(): value for name, value in request.header_items()}
    payload = json.loads(request.data.decode())
    assert request.full_url == "https://api.example.test/v1/chat/completions"
    assert request.get_method() == "POST"
    assert headers == {
        "authorization": "Bearer chat-test-key",
        "content-type": "application/json",
        "user-agent": "OpenClaw/1.0",
        "accept": "application/json",
    }
    assert timeout == 120
    assert payload == {
        "model": "test-model",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 321,
        "response_format": {"type": "json_object"},
    }


def test_chat_blog_transport_rejects_fenced_non_object_json(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"choices":[{"finish_reason":"stop","message":{"content":"```json\\n[]\\n```"}}]}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(BlogValidationError, match="JSON must be an object"):
        OpenAICompatibleBlogTransport().complete_json(
            model="test-model",
            base_url="https://api.example.test/v1",
            api_key="chat-test-key",
            messages=[],
            max_output_tokens=100,
        )


def test_responses_blog_transport_builds_request_and_parses_output():
    http = RecordingResponsesHTTP(
        {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": '{"title":"测试","sections":[]}'},
                    ]
                }
            ]
        }
    )
    transport = OpenAIResponsesBlogTransport(
        proxy_url="http://127.0.0.1:7890",
        http_transport=http,
    )

    result = transport.complete_json(
        model="gpt-5.6-luna",
        base_url="https://opencode.ai/zen/go/v1/responses",
        api_key="secret-test-key",
        messages=[{"role": "system", "content": "Return JSON only."}],
        max_output_tokens=4000,
    )

    assert result == {"title": "测试", "sections": []}
    request = http.requests[0]
    assert request["endpoint"] == "https://opencode.ai/zen/go/v1/responses"
    assert request["headers"] == {
        "authorization": "Bearer secret-test-key",
        "content-type": "application/json",
        "User-Agent": "OpenClaw/1.0",
        "Accept": "application/json",
    }
    assert request["proxy_url"] == "http://127.0.0.1:7890"
    assert request["payload"]["model"] == "gpt-5.6-luna"
    assert request["payload"]["max_output_tokens"] == 4000
    assert request["payload"]["input"][0]["content"][0] == {
        "type": "input_text",
        "text": "Return JSON only.",
    }


def test_responses_blog_transport_normalizes_v1_endpoint_and_top_level_fenced_json():
    http = RecordingResponsesHTTP({"output_text": "```json\n{\"ok\": true}\n```"})
    transport = OpenAIResponsesBlogTransport(http_transport=http)

    result = transport.complete_json(
        model="gpt-5.6-luna",
        base_url="https://opencode.ai/zen/go/v1/",
        api_key="test-key",
        messages=[{"role": "user", "content": "Return JSON."}],
        max_output_tokens=100,
    )

    assert result == {"ok": True}
    assert http.requests[0]["endpoint"] == "https://opencode.ai/zen/go/v1/responses"
    assert http.requests[0]["proxy_url"] == ""


@pytest.mark.parametrize(
    ("response", "error_fragment"),
    [
        ({"output_text": ""}, "empty output"),
        ({"output_text": "not json"}, "invalid JSON"),
        ({"output_text": "[]"}, "JSON object"),
        ({"output": "invalid"}, "empty output"),
    ],
)
def test_responses_blog_transport_rejects_invalid_output(response, error_fragment):
    transport = OpenAIResponsesBlogTransport(http_transport=RecordingResponsesHTTP(response))

    with pytest.raises(BlogValidationError, match=error_fragment):
        transport.complete_json(
            model="gpt-5.6-luna",
            base_url="https://opencode.ai/zen/go/v1",
            api_key="test-key",
            messages=[],
            max_output_tokens=100,
        )


def test_responses_blog_transport_redacts_key_from_http_failure():
    key = "responses-secret-key"

    def failing_http(*_args):
        raise RuntimeError(f"upstream rejected bearer {key}")

    transport = OpenAIResponsesBlogTransport(http_transport=failing_http)

    with pytest.raises(BlogValidationError) as captured:
        transport.complete_json(
            model="gpt-5.6-luna",
            base_url="https://opencode.ai/zen/go/v1/responses",
            api_key=key,
            messages=[],
            max_output_tokens=100,
        )

    assert key not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_responses_blog_transport_does_not_chain_malformed_secret_output():
    key = "malformed-output-secret"
    transport = OpenAIResponsesBlogTransport(
        http_transport=RecordingResponsesHTTP({"output_text": f'{{"value":"{key}"'})
    )

    with pytest.raises(BlogValidationError) as captured:
        transport.complete_json(
            model="gpt-5.6-luna",
            base_url="https://opencode.ai/zen/go/v1/responses",
            api_key=key,
            messages=[],
            max_output_tokens=100,
        )

    assert key not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


@pytest.mark.parametrize("proxy_url", ["", "http://127.0.0.1:7890"])
def test_responses_default_http_installs_proxy_handler_only_when_configured(monkeypatch, proxy_url):
    calls: list[object] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"output_text":"{\\"ok\\":true}"}'

    class FakeOpener:
        def open(self, _request, *, timeout):
            calls.append(("opener", timeout))
            return FakeResponse()

    def fake_build_opener(handler):
        calls.append(handler)
        return FakeOpener()

    def fake_urlopen(_request, *, timeout):
        calls.append(("urlopen", timeout))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build_opener)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = OpenAIResponsesBlogTransport(proxy_url=proxy_url).complete_json(
        model="gpt-5.6-luna",
        base_url="https://opencode.ai/zen/go/v1",
        api_key="test-key",
        messages=[],
        max_output_tokens=100,
    )

    assert result == {"ok": True}
    proxy_handlers = [call for call in calls if isinstance(call, urllib.request.ProxyHandler)]
    assert len(proxy_handlers) == (1 if proxy_url else 0)
    assert ("opener", 120.0) in calls if proxy_url else ("urlopen", 120.0) in calls


def test_chat_blog_transport_redacts_key_from_http_error(monkeypatch):
    key = "chat-secret-key"

    def failing_urlopen(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "https://api.example.test/v1/chat/completions",
            401,
            "unauthorized",
            {},
            io.BytesIO(f'{{"error":"invalid key {key}"}}'.encode()),
        )

    monkeypatch.setattr(urllib.request, "urlopen", failing_urlopen)

    with pytest.raises(BlogValidationError) as captured:
        OpenAICompatibleBlogTransport().complete_json(
            model="test-model",
            base_url="https://api.example.test/v1",
            api_key=key,
            messages=[],
            max_output_tokens=100,
        )

    assert key not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_blog_provider_uses_requested_key_env_before_openai_translate_and_assistant(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    monkeypatch.setenv("CUSTOM_BLOG_KEY", "requested-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("TRANSLATE_API_KEY", "translate-key")
    monkeypatch.setenv("NIU_ASSISTANT_API_KEY", "assistant-key")

    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "blog-key")
    blog_provider = OpenAICompatibleBlogProvider.from_env(
        api_key_env="CUSTOM_BLOG_KEY",
        transport=RecordingOpenAITransport(),
    )

    assert blog_provider.api_key == "blog-key"

    monkeypatch.delenv("AIRESEARCH_BLOG_API_KEY")
    provider = OpenAICompatibleBlogProvider.from_env(
        api_key_env="CUSTOM_BLOG_KEY",
        transport=RecordingOpenAITransport(),
    )

    assert provider.api_key == "requested-key"


def test_blog_provider_env_precedence_and_assistant_fallback(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    # 2026-09-16 item 2：yaml(compat) 是默认源，验证「助手环境兜底」需先把 compat 断空
    monkeypatch.setattr(
        "niu_core.llm_client.compat.resolve",
        lambda logic_model, env=None: ("", "", ""),
    )
    monkeypatch.setenv("NIU_ASSISTANT_API_KEY", "assistant-key")
    monkeypatch.setenv("NIU_ASSISTANT_MODEL", "assistant-model")
    monkeypatch.setenv("NIU_ASSISTANT_API_BASE", "https://assistant.example/v1/responses")

    assistant_provider = OpenAICompatibleBlogProvider.from_env()

    assert assistant_provider.api_key == "assistant-key"
    assert assistant_provider.model == "assistant-model"
    assert assistant_provider.base_url == "https://assistant.example/v1/responses"
    assert isinstance(assistant_provider.transport, OpenAIResponsesBlogTransport)

    monkeypatch.setenv("TRANSLATE_API_KEY", "translate-key")
    monkeypatch.setenv("TRANSLATE_BASE_URL", "https://translate.example/v1")
    translate_provider = OpenAICompatibleBlogProvider.from_env()

    assert translate_provider.api_key == "translate-key"
    assert translate_provider.base_url == "https://translate.example/v1"

    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.example/v1")
    openai_provider = OpenAICompatibleBlogProvider.from_env()

    assert openai_provider.api_key == "openai-key"
    assert openai_provider.base_url == "https://translate.example/v1"

    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "blog-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_MODEL", "blog-model")
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://blog.example/v1")
    blog_provider = OpenAICompatibleBlogProvider.from_env()

    assert blog_provider.api_key == "blog-key"
    assert blog_provider.model == "blog-model"
    assert blog_provider.base_url == "https://blog.example/v1"


def test_blog_provider_explicit_values_and_injected_transport_win(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    injected = RecordingOpenAITransport()
    monkeypatch.setenv("AIRESEARCH_BLOG_MODEL", "blog-model")
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://blog.example/v1")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "blog-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_STYLE", "responses")

    provider = OpenAICompatibleBlogProvider.from_env(
        model="explicit-model",
        base_url="https://explicit.example/v1",
        api_style="responses",
        transport=injected,
    )

    assert provider.model == "explicit-model"
    assert provider.base_url == "https://explicit.example/v1"
    assert provider.transport is injected


def test_blog_provider_explicit_style_and_proxy_beat_env_when_constructing_transport(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "blog-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://opencode.ai/zen/go/v1")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_STYLE", "chat_completions")
    monkeypatch.setenv("AIRESEARCH_BLOG_PROXY", "http://env-proxy.invalid:8080")

    provider = OpenAICompatibleBlogProvider.from_env(
        api_style="responses",
        proxy_url="http://127.0.0.1:7890",
    )

    assert isinstance(provider.transport, OpenAIResponsesBlogTransport)
    assert provider.transport.proxy_url == "http://127.0.0.1:7890"


def test_blog_provider_responses_style_propagates_proxy(monkeypatch):
    clear_blog_provider_env(monkeypatch)
    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "blog-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://opencode.ai/zen/go/v1")
    monkeypatch.setenv("AIRESEARCH_BLOG_API_STYLE", "responses")
    monkeypatch.setenv("AIRESEARCH_BLOG_PROXY", "http://127.0.0.1:7890")

    provider = OpenAICompatibleBlogProvider.from_env()

    assert isinstance(provider.transport, OpenAIResponsesBlogTransport)
    assert provider.transport.proxy_url == "http://127.0.0.1:7890"


def test_openai_compatible_blog_provider_uses_env_and_injected_transport(tmp_path: Path, monkeypatch):
    clear_blog_provider_env(monkeypatch)
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    transport = RecordingOpenAITransport()

    monkeypatch.setenv("AIRESEARCH_BLOG_API_KEY", "blog-key")
    monkeypatch.setenv("AIRESEARCH_BLOG_MODEL", "blog-model")
    monkeypatch.setenv("AIRESEARCH_BLOG_BASE_URL", "https://blog.example/v1")

    provider = OpenAICompatibleBlogProvider.from_env(transport=transport)

    outline = provider.generate_outline(pack, [], target_chars=4200)
    section = provider.generate_section(pack, outline["sections"][0], [], target_chars=500)

    assert provider.model == "blog-model"
    assert provider.api_key == "blog-key"
    assert provider.base_url == "https://blog.example/v1"
    assert outline["sections"]
    assert section["markdown"].startswith("## 导读")
    assert len(transport.requests) == 2
    assert transport.requests[0]["model"] == "blog-model"
    assert transport.requests[0]["base_url"] == "https://blog.example/v1"
    assert transport.requests[0]["api_key"] == "blog-key"
    assert "Return JSON" in str(transport.requests[0]["messages"][0]["content"])
    assert "Use only supplied evidence" in str(transport.requests[0]["messages"][0]["content"])
    assert "English terms in parentheses on first use" in str(transport.requests[0]["messages"][0]["content"])
    assert "required_sections" in str(transport.requests[0]["messages"][1]["content"])
    assert "Generate paper blog outline" in str(transport.requests[0]["messages"][1]["content"])


def test_openai_compatible_blog_provider_returns_json_requests(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    transport = RecordingOpenAITransport()
    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        base_url="https://api.example.test/v1",
        transport=transport,
    )

    outline = provider.generate_outline(pack, [], target_chars=4200)
    section = provider.generate_section(pack, outline["sections"][0], [], target_chars=500)

    assert outline["sections"]
    assert section["markdown"].startswith("## 导读")
    assert transport.requests[0]["model"] == "test-model"
    assert transport.requests[0]["base_url"] == "https://api.example.test/v1"
    assert "Return JSON" in str(transport.requests[0]["messages"][0]["content"])


def test_openai_compatible_blog_provider_bounds_and_sanitizes_cloud_payload(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    transport = RecordingOpenAITransport()
    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=transport,
    )

    outline = provider.generate_outline(pack, select_blog_images(db_path, "1706_03762"), target_chars=4200)
    provider.generate_section(
        pack,
        outline["sections"][0],
        select_blog_images(db_path, "1706_03762"),
        target_chars=500,
    )

    outline_payload = json.loads(str(transport.requests[0]["messages"][-1]["content"]).split("payload:\n", 1)[1])
    section_payload = json.loads(str(transport.requests[1]["messages"][-1]["content"]).split("payload:\n", 1)[1])
    assert sum(len(text) for text in outline_payload["paper"]["artifact_texts"].values()) <= OUTLINE_SOURCE_CHAR_LIMIT
    assert sum(len(text) for text in section_payload["artifact_texts"].values()) <= SECTION_SOURCE_CHAR_LIMIT
    assert "source_path" not in outline_payload["paper"]["facts"][0]
    assert all("source_path" not in image for image in outline_payload["images"])
    assert all("source_path" not in image for image in section_payload["images"])
    assert all("source_path" not in link for link in outline_payload["paper"]["code_links"])
    assert outline_payload["paper"]["equations"]
    assert section_payload["equations"] == []
    assert transport.requests[0]["max_output_tokens"] == OUTLINE_MAX_OUTPUT_TOKENS
    assert 1200 <= transport.requests[1]["max_output_tokens"] <= SECTION_MAX_OUTPUT_TOKENS


def test_openai_provider_preserves_outline_image_order_for_prompt_and_fallback(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    first_image = select_blog_images(db_path, "1706_03762")[0]
    second_image = dict(first_image)
    second_image["image_id"] = "ordered-second-image"
    second_image["asset_path"] = "blog-assets/figures/ordered-second.webp"
    images = [first_image, second_image]

    class MissingImageIdsTransport:
        def __init__(self):
            self.messages: list[dict[str, str]] = []

        def complete_json(self, **kwargs):
            self.messages = kwargs["messages"]
            return {"section_key": "intro", "markdown": "## 导读\n\n正文"}

    transport = MissingImageIdsTransport()
    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=transport,
    )
    ordered_ids = [str(images[1]["image_id"]), str(images[0]["image_id"])]
    section = {
        "section_key": "intro",
        "title": "导读",
        "fact_ids": [],
        "image_ids": ordered_ids,
    }

    result = provider.generate_section(pack, section, images, target_chars=500)

    payload = json.loads(transport.messages[-1]["content"].split("payload:\n", 1)[1])
    assert [str(image["image_id"]) for image in payload["images"]] == ordered_ids
    assert result["image_ids"] == ordered_ids


def test_openai_provider_requires_model_confirmed_fact_provenance(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    required_ids = [int(pack.facts[1]["fact_id"]), int(pack.facts[0]["fact_id"])]

    class MissingFactIdsTransport:
        def complete_json(self, **_kwargs):
            return {"markdown": "## 核心方法\n\n" + "技术分析。" * 300}

    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=MissingFactIdsTransport(),
    )

    with pytest.raises(BlogValidationError, match="missing required fact_ids"):
        provider.generate_section(
            pack,
            {
                "section_key": "method",
                "title": "核心方法",
                "fact_ids": required_ids,
                "image_ids": [],
            },
            [],
            target_chars=500,
        )


def test_openai_provider_rejects_unsupplied_facts_for_empty_section(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    unexpected_id = int(pack.facts[0]["fact_id"])

    class UnexpectedFactIdsTransport:
        def __init__(self):
            self.payload = {}

        def complete_json(self, **kwargs):
            self.payload = json.loads(kwargs["messages"][-1]["content"].split("payload:\n", 1)[1])
            return {
                "markdown": "## 延伸阅读\n\n" + "技术分析。" * 300,
                "fact_ids": [unexpected_id],
                "image_ids": [],
            }

    transport = UnexpectedFactIdsTransport()
    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=transport,
    )

    with pytest.raises(BlogValidationError, match="do not match supplied facts"):
        provider.generate_section(
            pack,
            {
                "section_key": "further_reading",
                "title": "延伸阅读",
                "fact_ids": [],
                "image_ids": [],
            },
            [],
            target_chars=500,
        )
    assert transport.payload["facts"] == []


def test_openai_provider_preserves_supplied_fact_order_in_prompt(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    required_ids = [int(pack.facts[1]["fact_id"]), int(pack.facts[0]["fact_id"])]

    class EchoFactIdsTransport:
        def __init__(self):
            self.payload = {}

        def complete_json(self, **kwargs):
            self.payload = json.loads(kwargs["messages"][-1]["content"].split("payload:\n", 1)[1])
            return {
                "markdown": "## 核心方法\n\n" + "技术分析。" * 300,
                "fact_ids": required_ids,
                "image_ids": [],
            }

    transport = EchoFactIdsTransport()
    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=transport,
    )

    result = provider.generate_section(
        pack,
        {
            "section_key": "method",
            "title": "核心方法",
            "fact_ids": required_ids,
            "image_ids": [],
        },
        [],
        target_chars=500,
    )

    assert [int(fact["fact_id"]) for fact in transport.payload["facts"]] == required_ids
    assert result["fact_ids"] == required_ids


def test_deepseek_blog_requests_disable_thinking():
    payload = OpenAICompatibleBlogTransport._request_payload(
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        messages=[{"role": "user", "content": "return json"}],
        max_output_tokens=100,
    )

    assert payload["thinking"] == {"type": "disabled"}


def test_non_deepseek_blog_requests_do_not_send_thinking():
    payload = OpenAICompatibleBlogTransport._request_payload(
        model="qwen3.7-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        messages=[{"role": "user", "content": "return json"}],
        max_output_tokens=100,
    )

    assert "thinking" not in payload


def test_outline_alias_is_normalized_to_required_sections(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    result = OpenAICompatibleBlogProvider._normalize_outline_result(
        {
            "outline": [
                {"section_key": "intro", "title": "导读", "content": "先讲清楚问题。"},
                {"section_key": "method", "title": "核心方法", "content": "拆解方法。"},
            ]
        },
        pack,
    )

    assert result["title"] == "Attention Is All You Need 深度解读"
    assert [section["section_key"] for section in result["sections"]] == [key for key, _title in DEFAULT_SECTIONS]
    assert result["sections"][0]["summary"] == "先讲清楚问题。"
    assert result["sections"][2]["summary"] == "拆解方法。"
    assert result["sections"][1]["fact_ids"] == []
    assert result["sections"][1]["image_ids"] == []


def test_section_content_alias_is_wrapped_as_markdown(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")

    class ContentOnlyTransport:
        def complete_json(self, **_kwargs):
            return {"section_key": "intro", "content": "这一节只返回 content 字段。"}

    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=ContentOnlyTransport(),
    )
    section = {"section_key": "intro", "title": "导读", "fact_ids": [], "image_ids": []}

    normalized = provider.generate_section(pack, section, [], target_chars=500)

    assert normalized["markdown"].startswith("## 导读")
    assert "这一节只返回 content 字段。" in normalized["markdown"]


def test_method_section_appends_equations_when_model_omits_them(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")

    class ContentOnlyTransport:
        def complete_json(self, **_kwargs):
            return {"section_key": "method", "content": "这一节解释方法但模型忘了写公式。"}

    provider = OpenAICompatibleBlogProvider(
        model="test-model",
        api_key="test-key",
        transport=ContentOnlyTransport(),
    )
    section = {"section_key": "method", "title": "核心方法", "fact_ids": [], "image_ids": []}

    normalized = provider.generate_section(pack, section, [], target_chars=500)

    assert display_math_block_count(normalized["markdown"]) >= 1
    assert "关键公式" in normalized["markdown"]


def test_evidence_hash_tracks_paper_card_and_image_content(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    first = build_blog_evidence_pack(db_path, "1706_03762")
    assert first.paper_card["paper_key"] == "1706_03762"
    assert first.image_candidates[0]["content_fingerprint"]["sha256"]

    with connect(db_path) as conn:
        conn.execute("update paper_cards set venue = 'Changed Venue' where paper_key = '1706_03762'")
        conn.commit()
    second = build_blog_evidence_pack(db_path, "1706_03762")
    assert second.source_hash != first.source_hash

    image_path = Path(second.image_candidates[0]["source_path"])
    image_path.write_bytes(image_path.read_bytes() + b"\nchanged\n")
    third = build_blog_evidence_pack(db_path, "1706_03762")
    assert third.source_hash != second.source_hash


def test_evidence_hash_ignores_image_mtime_when_content_is_unchanged(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    first = build_blog_evidence_pack(db_path, "1706_03762")
    image_path = Path(first.image_candidates[0]["source_path"])
    os.utime(image_path, (image_path.stat().st_atime + 120, image_path.stat().st_mtime + 120))

    second = build_blog_evidence_pack(db_path, "1706_03762")

    assert second.source_hash == first.source_hash


def test_generation_requires_summary_or_tldr_grounding(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    with connect(db_path) as conn:
        conn.execute(
            "delete from paper_artifacts where paper_key = ? and artifact_type in ('summary', 'tldr')",
            ("1706_03762",),
        )
        conn.commit()

    with pytest.raises(BlogValidationError, match="summary/tldr"):
        generate_and_publish_blog(
            db_path,
            "1706_03762",
            provider=FixtureBlogProvider(),
            model="fixture-blog",
        )


def test_invalid_section_retries_twice_and_only_valid_outline_is_cached(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class InvalidSectionProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__()
            self.section_attempts = 0

        def generate_section(self, pack, section, images, *, target_chars):
            self.section_attempts += 1
            response = super().generate_section(pack, section, images, target_chars=target_chars)
            response["fact_ids"] = [999999]
            return response

    provider = InvalidSectionProvider()
    with pytest.raises(BlogValidationError, match="invalid section fact reference"):
        generate_and_publish_blog(
            db_path,
            "1706_03762",
            provider=provider,
            model="invalid-provider",
        )
    assert provider.section_attempts == 3
    with connect(db_path) as conn:
        cached_keys = [
            row["section_key"]
            for row in conn.execute(
                "select section_key from paper_blog_generation_cache order by id"
            )
        ]
    assert cached_keys == ["outline"]


def test_short_section_retries_until_long_enough(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    pack = build_blog_evidence_pack(db_path, "1706_03762")
    section = {"section_key": "intro", "title": "导读", "fact_ids": [], "image_ids": []}

    class ShortThenLongProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=80)
            self.section_attempts = 0

        def generate_section(self, pack, section, images, *, target_chars):
            self.section_attempts += 1
            if self.section_attempts >= 3:
                self.chars_per_section = 520
            return super().generate_section(pack, section, images, target_chars=target_chars)

    provider = ShortThenLongProvider()
    response, calls = _generate_validated_section_with_retries(
        provider,
        pack,
        section,
        [],
        target_chars=500,
    )

    assert calls == 3
    assert response["section_key"] == "intro"


def test_invalid_outline_retries_twice_and_is_not_cached(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class InvalidOutlineProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__()
            self.outline_attempts = 0

        def generate_outline(self, pack, images, *, target_chars):
            self.outline_attempts += 1
            return {"title": "无效提纲", "sections": []}

    provider = InvalidOutlineProvider()
    with pytest.raises(BlogValidationError, match="missing required sections"):
        generate_and_publish_blog(
            db_path,
            "1706_03762",
            provider=provider,
            model="invalid-outline-provider",
        )
    assert provider.outline_attempts == 3
    with connect(db_path) as conn:
        cache_count = conn.execute("select count(*) from paper_blog_generation_cache").fetchone()[0]
    assert cache_count == 0


def test_generation_clamps_blog_and_section_targets_and_ignores_extra_outline_sections(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)

    class TargetRecordingProvider(FixtureBlogProvider):
        def __init__(self):
            super().__init__(chars_per_section=1200)
            self.outline_target = 0
            self.section_targets = []

        def generate_outline(self, pack, images, *, target_chars):
            self.outline_target = target_chars
            outline = super().generate_outline(pack, images, target_chars=target_chars)
            for section in outline["sections"]:
                section["target_chars"] = 999999
            outline["sections"].append(
                {"section_key": "untrusted-extra", "fact_ids": [999999], "image_ids": ["remote"]}
            )
            return outline

        def generate_section(self, pack, section, images, *, target_chars):
            self.section_targets.append(target_chars)
            return super().generate_section(pack, section, images, target_chars=target_chars)

    provider = TargetRecordingProvider()
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=provider,
        model="target-provider",
        target_chars=99,
    )
    assert provider.outline_target == 3000
    assert provider.section_targets == [1400] * 8


def test_admin_blog_detail_returns_latest_job_and_generation_meta(tmp_path: Path):
    db_path, _paper_db = build_fixture_corpus(tmp_path)
    published = generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=FixtureBlogProvider(chars_per_section=520),
        model="fixture-blog",
        target_chars=4200,
    )
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into admin_jobs (
                job_type, status, message, log, params_json, current_step, result_json,
                priority, created_at, started_at, finished_at
            ) values ('paper_blog_generate', 'publish_failed', 'publish failed', 'trace', ?, 'publishing', ?, 0,
                      '2026-06-19T00:00:00+00:00', '2026-06-19T00:00:00+00:00', '2026-06-19T00:01:00+00:00')
            """,
            (json.dumps({"paperKey": "1706_03762", "force": False}), json.dumps({"version": 1})),
        )
        conn.commit()

    detail = admin_blog_detail(db_path, "1706_03762")
    assert detail["post"]["current_version_id"] == published.version_id
    assert detail["generation_meta"]["target_chars"] == 4200
    assert detail["latest_job"]["status"] == "publish_failed"
    assert detail["latest_job"]["params"]["paperKey"] == "1706_03762"
    assert detail["latest_job"]["result"] == {"version": 1}
    assert detail["latest_job"]["log"] == "trace"


def test_generation_deploy_failure_preserves_published_version(tmp_path: Path, monkeypatch):
    db_path, paper_db = build_fixture_corpus(tmp_path)
    install_test_deploy_runner(monkeypatch)
    deploy_script = tmp_path / "deploy.sh"
    write_deploy_script(deploy_script, exit_code=9)
    config = AdminConfig(
        base_path="/niu-secretary/airesearch/admin/",
        db_path=db_path,
        paper_db_path=paper_db,
        project_dir=tmp_path,
        deploy_script=deploy_script,
        papi_executable="papi",
        username="",
        password="",
    )

    with pytest.raises(PaperBlogPublishError, match="deploy failed with code 9") as exc_info:
        run_blog_generation_job(
            config,
            job_id=1,
            options={"paperKey": "1706_03762", "provider": "fixture", "targetWordCount": 4200},
        )

    assert exc_info.value.result["versionNumber"] == 1
    detail = admin_blog_detail(db_path, "1706_03762")
    assert detail["post"]["status"] == "published"
    assert detail["post"]["current_version_id"] == exc_info.value.result["versionId"]


def test_worker_marks_publish_failed_but_preserves_published_version(tmp_path: Path, monkeypatch):
    from airesearch import admin_server

    db_path, paper_db = build_fixture_corpus(tmp_path)
    install_test_deploy_runner(monkeypatch)
    deploy_script = tmp_path / "deploy.sh"
    write_deploy_script(deploy_script, exit_code=9)
    config = AdminConfig(
        base_path="/niu-secretary/airesearch/admin/",
        db_path=db_path,
        paper_db_path=paper_db,
        project_dir=tmp_path,
        deploy_script=deploy_script,
        papi_executable="papi",
        username="",
        password="",
    )
    admin_server.ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into admin_jobs (
                job_type, status, message, params_json, current_step, result_json,
                priority, created_at, started_at
            ) values ('paper_blog_generate', 'queued', 'waiting', ?, '', '{}', 0,
                      '2026-06-19T00:00:00+00:00', '2026-06-19T00:00:00+00:00')
            """,
            (json.dumps({"paperKey": "1706_03762", "provider": "fixture", "targetWordCount": 4200}),),
        )
        conn.commit()
    _worker_loop(config)

    with connect(db_path) as conn:
        job = conn.execute("select status, message, log, result_json from admin_jobs order by id desc limit 1").fetchone()
    assert job["status"] == "publish_failed"
    assert "version 1 was saved" in job["message"]
    assert "deploy failed with code 9" in job["log"]
    assert "deploy-result" in job["log"]
    assert json.loads(job["result_json"])["versionNumber"] == 1
    assert admin_blog_detail(db_path, "1706_03762")["post"]["status"] == "published"


def test_mark_interrupted_jobs_also_closes_running_ingest_batches(tmp_path: Path):
    from airesearch import admin_server

    db_path, _paper_db = build_fixture_corpus(tmp_path)
    admin_server.ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into admin_jobs (
                job_type, status, message, params_json, current_step, result_json,
                priority, created_at, started_at
            ) values ('search_ingest', 'running', 'export-candidate-review', '{}',
                      'export-candidate-review', '{}', 0,
                      '2026-08-12T02:08:05+00:00', '2026-08-12T02:08:05+00:00')
            """
        )
        cursor = conn.execute(
            """
            insert into ingest_runs (manifest_path, total_items, started_at, status)
            values ('manifests/approved-launch-refresh-current.txt', 2,
                    '2026-08-12T02:09:35+00:00', 'running')
            """
        )
        run_id = int(cursor.lastrowid)
        conn.executemany(
            """
            insert into ingest_items (run_id, line_number, raw_input, status, started_at)
            values (?, ?, ?, 'running', '2026-08-12T02:09:35+00:00')
            """,
            [(run_id, 1, "https://arxiv.org/abs/2606.10305"), (run_id, 2, "https://arxiv.org/abs/2606.06390")],
        )
        conn.commit()

    admin_server._mark_interrupted_jobs(db_path)

    with connect(db_path) as conn:
        job = conn.execute("select status, message, finished_at from admin_jobs").fetchone()
        run = conn.execute(
            "select status, success_count, failed_count, finished_at from ingest_runs where id = ?",
            (run_id,),
        ).fetchone()
        item_statuses = [
            dict(row)
            for row in conn.execute(
                "select status, error, finished_at from ingest_items where run_id = ? order by id",
                (run_id,),
            )
        ]
    assert job["status"] == "failed"
    assert job["message"] == "interrupted by admin service restart"
    assert job["finished_at"]
    assert run["status"] == "partial_failure"
    assert run["success_count"] == 0
    assert run["failed_count"] == 2
    assert all(item["status"] == "failed" for item in item_statuses)
    assert all(item["error"] == "interrupted by admin service restart" for item in item_statuses)
    assert all(item["finished_at"] for item in item_statuses)


def test_synchronous_hide_reports_publish_failure_after_preserving_db_change(tmp_path: Path, monkeypatch):
    from airesearch import admin_server

    db_path, paper_db = build_fixture_corpus(tmp_path)
    generate_and_publish_blog(
        db_path,
        "1706_03762",
        provider=FixtureBlogProvider(chars_per_section=520),
        model="fixture-blog",
        target_chars=4200,
    )
    config = AdminConfig(
        base_path="/niu-secretary/airesearch/admin/",
        db_path=db_path,
        paper_db_path=paper_db,
        project_dir=tmp_path,
        deploy_script=tmp_path / "deploy.sh",
        papi_executable="papi",
        username="",
        password="",
    )
    monkeypatch.setattr(admin_server, "_rebuild_paper_blog_site", lambda _config: (_ for _ in ()).throw(RuntimeError("read only")))

    with pytest.raises(PaperBlogPublishError, match="blog was hidden.*publish failed"):
        admin_hide_blog(db_path, "1706_03762", config=config)
    detail = admin_blog_detail(db_path, "1706_03762")
    assert detail["post"]["status"] == "hidden"
    assert detail["latest_job"]["job_type"] == "paper_blog_publish"
    assert detail["latest_job"]["status"] == "publish_failed"
    assert detail["latest_job"]["params"]["operation"] == "hide"

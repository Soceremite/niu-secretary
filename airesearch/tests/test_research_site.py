import json
from html.parser import HTMLParser
from pathlib import Path
from time import perf_counter

from airesearch.research_site import (
    _paper_layout_formula_quality,
    build_navigation_index,
    build_provenance_index,
    build_search_index,
    export_report_site,
    render_report_site,
)


def test_layout_formula_quality_requires_valid_completed_formula_ocr():
    assert (
        _paper_layout_formula_quality(
            {
                "latex": "Attention(Q,K,V)=softmax(QK^T)V",
                "quality_score": 0.96,
                "formula_ocr_status": "completed",
            }
        )
        == "good"
    )
    assert _paper_layout_formula_quality({"latex": "x_t = f(x)", "quality_score": 0.95}) == "review"
    assert (
        _paper_layout_formula_quality(
            {
                "latex": r"L = K + \sum_{s=1}^{S}|\mathcal I_s|,\ L > 0",
                "quality_score": 1.0,
                "source_kind": "paperpipe_equations",
            }
        )
        == "good"
    )
    assert _paper_layout_formula_quality({"latex": "\\ mathbf{x", "quality_score": 0.99}) == "fallback"
    assert (
        _paper_layout_formula_quality(
            {"latex": "Initial frame X0 T = 1s T = 3s T = 5s", "quality_score": 0.99}
        )
        == "fallback"
    )


class _NodeCounter(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.nodes = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes += 1


def make_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    paper_asset_dir = bundle_dir / "paper-assets" / "1706_03762"
    paper_asset_dir.mkdir(parents=True)
    (paper_asset_dir / "summary.md").write_text("Transformer summary in English.", encoding="utf-8")
    (paper_asset_dir / "tldr.md").write_text("English TLDR for attention paper.", encoding="utf-8")
    (paper_asset_dir / "summary.zh.md").write_text("Transformer 中文摘要。", encoding="utf-8")
    (paper_asset_dir / "tldr.zh.md").write_text("注意力论文中文 TLDR。", encoding="utf-8")
    cover_dir = bundle_dir / "paper-assets" / "covers"
    cover_dir.mkdir(parents=True)
    (cover_dir / "1706_03762.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300'><rect width='400' height='300' fill='#111827'/><circle cx='200' cy='140' r='80' fill='#d4a957'/><text x='200' y='270' fill='#f9fafb' text-anchor='middle' font-size='24'>Attention</text></svg>",
        encoding="utf-8",
    )
    (bundle_dir / "digest.md").write_text("# Digest\n\nA short report.\n", encoding="utf-8")
    (bundle_dir / "digest.json").write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_key": "1706_03762",
                        "title": "Attention Is All You Need",
                        "authors": ["Ashish Vaswani", "Noam Shazeer"],
                        "year": 2017,
                        "code_links": [
                            {
                                "url": "https://github.com/attention/transformer",
                                "source_path": "/tmp/1706_03762/source.tex",
                            }
                        ],
                        "facts": {
                            "method": [
                                {
                                    "fact_id": 1,
                                    "confidence": 0.96,
                                    "statement": "Uses scaled dot-product attention.",
                                    "evidence_quote": "Attention evidence in English.",
                                    "evidence_source_path": "/tmp/1706_03762/summary.md",
                                }
                            ]
                        },
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "clusters.md").write_text("# Clusters\n\nMultimodal agent cluster notes.\n", encoding="utf-8")
    (bundle_dir / "fact-translations.json").write_text(
        json.dumps(
            [
                {
                    "fact_id": 1,
                    "lang": "zh",
                    "paper_key": "1706_03762",
                    "fact_type": "method",
                    "statement": "使用缩放点积注意力。",
                    "evidence_quote": "中文证据。",
                    "model": "fixture",
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "clusters.json").write_text(
        json.dumps(
            {
                "clusters": [
                    {
                        "cluster_id": "cluster_1",
                        "title": "Attention methods",
                        "facts": [
                            {
                                "paper_key": "paper_b",
                                "statement": "A cluster fact.",
                                "evidence_source_path": "/tmp/paper_b/source.md",
                            }
                        ],
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "gap-analysis.md").write_text("# Gap Analysis\n\nLong raw gap report.\n", encoding="utf-8")
    (bundle_dir / "gap-analysis.json").write_text(
        json.dumps(
            {
                "paper_count": 2,
                "fact_count": 3,
                "missing_evidence_source_path_count": 1,
                "fact_type_coverage": [
                    {"fact_type": "method", "coverage_ratio": 1.0, "paper_count": 2, "fact_count": 2},
                    {"fact_type": "dataset", "coverage_ratio": 0.5, "paper_count": 1, "fact_count": 1},
                ],
                "low_coverage_fact_types": [
                    {"fact_type": "dataset", "coverage_ratio": 0.5, "paper_count": 1, "fact_count": 1}
                ],
                "papers": [
                    {
                        "paper_key": "1706_03762",
                        "title": "Attention Is All You Need",
                        "year": 2017,
                        "missing_fact_types": ["dataset"],
                        "missing_evidence_source_path_count": 1,
                        "has_code_links": False,
                    },
                    {
                        "paper_key": "paper_b",
                        "title": "Paper B",
                        "year": 2026,
                        "missing_fact_types": [],
                        "missing_evidence_source_path_count": 0,
                        "has_code_links": True,
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "synthesis.md").write_text("# Synthesis\n\nLong raw synthesis report.\n", encoding="utf-8")
    (bundle_dir / "synthesis.json").write_text(
        json.dumps(
            {
                "paper_count": 2,
                "fact_count": 3,
                "extraction_target_count": 5,
                "extraction_targets": ["method", "dataset", "benchmark", "claim", "limitation"],
                "missing_evidence_source_path_count": 1,
                "papers_without_code_links": 1,
                "papers_missing_fact_types": 1,
                "required_fact_types": ["method", "dataset", "benchmark", "claim", "limitation"],
                "strong_coverage": {
                    "name": "strong",
                    "fact_types": [
                        {"fact_type": "method", "coverage_ratio": 1.0, "paper_count": 2, "fact_count": 2}
                    ],
                },
                "moderate_coverage": {"name": "moderate", "fact_types": []},
                "weak_coverage": {
                    "name": "weak",
                    "fact_types": [
                        {"fact_type": "dataset", "coverage_ratio": 0.5, "paper_count": 1, "fact_count": 1}
                    ],
                },
                "synthesis_notes": [
                    {
                        "fact_type": "dataset",
                        "coverage_ratio": 0.5,
                        "paper_count": 1,
                        "fact_count": 1,
                        "note": "Under-covered; treat conclusions as provisional.",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "narrative.md").write_text("# Narrative\n\nLong raw narrative report.\n", encoding="utf-8")
    (bundle_dir / "narrative.json").write_text(
        json.dumps(
            {
                "paper_count": 2,
                "fact_count": 3,
                "finding_count": 1,
                "action_count": 1,
                "executive_summary": [
                    "The current corpus contains 2 papers and 3 extracted research facts.",
                    "Follow-up work should prioritize extraction targets.",
                ],
                "supported_areas": ["Method is represented in 2/2 papers."],
                "provisional_areas": ["Dataset is represented in 1/2 papers."],
                "representative_findings": [
                    {
                        "fact_type": "method",
                        "confidence": 0.96,
                        "paper_key": "1706_03762",
                        "paper_title": "Attention Is All You Need",
                        "statement": "Uses scaled dot-product attention.",
                        "evidence_quote": "Scaled dot-product attention is used.",
                        "evidence_source_path": "/tmp/1706_03762/source.tex",
                    }
                ],
                "priority_actions": [
                    {
                        "priority_score": 55,
                        "paper_key": "paper_b",
                        "title": "Paper B",
                        "action": "Review paper_b for missing fact types.",
                    }
                ],
                "evidence_cautions": ["1 fact lacks evidence source paths."],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 2,
                "report_count": 3,
                "artifact_count": 6,
                "artifacts": [
                    {
                        "name": "digest",
                        "title": "Research Digest",
                        "markdown_path": "digest.md",
                        "json_path": "digest.json",
                        "paper_count": 1,
                        "fact_count": 2,
                        "extra_counts": {},
                    },
                    {
                        "name": "research_clusters",
                        "title": "Research Clusters",
                        "markdown_path": "clusters.md",
                        "json_path": "clusters.json",
                        "paper_count": 1,
                        "fact_count": 2,
                        "extra_counts": {"cluster_count": 1},
                    },
                    {
                        "name": "gap-analysis",
                        "title": "Gap Analysis",
                        "markdown_path": "gap-analysis.md",
                        "json_path": "gap-analysis.json",
                        "paper_count": 2,
                        "fact_count": 3,
                        "extra_counts": {},
                    },
                    {
                        "name": "synthesis",
                        "title": "Research Synthesis",
                        "markdown_path": "synthesis.md",
                        "json_path": "synthesis.json",
                        "paper_count": 2,
                        "fact_count": 3,
                        "extra_counts": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "paper-assets.json").write_text(
        json.dumps(
            [
                {
                    "paper_key": "1706_03762",
                    "title": "Attention Is All You Need",
                    "artifact_types": ["summary", "summary_zh", "tldr", "tldr_zh", "cover"],
                    "ids": {"arxiv_id": "1706.03762"},
                    "citation_keys": [],
                    "summary_path": "paper-assets/1706_03762/summary.md",
                    "tldr_path": "paper-assets/1706_03762/tldr.md",
                    "summary_zh_path": "paper-assets/1706_03762/summary.zh.md",
                    "tldr_zh_path": "paper-assets/1706_03762/tldr.zh.md",
                    "cover_path": "paper-assets/covers/1706_03762.svg",
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "paper-layout-evidence.json").write_text(
        json.dumps(
            [
                {
                    "paper_key": "1706_03762",
                    "api_version": "layout-evidence-v1",
                    "latest_run": {
                        "id": 7,
                        "status": "completed",
                        "provider": "airesearch_layout",
                        "provider_version": "fixture",
                        "finished_at": "2026-06-10T00:01:00+00:00",
                    },
                    "summary": {
                        "document_type": "digital",
                        "page_count": 8,
                        "block_count": 120,
                        "asset_count": 3,
                        "equation_blocks": 1,
                        "structured_table_blocks": 1,
                        "high_quality_table_blocks": 1,
                        "high_quality_equation_blocks": 1,
                        "high_quality_evidence_blocks": 2,
                        "block_types": {"text": 118, "interline_equation": 1, "table": 1},
                    },
                    "ocr": {
                        "mode": "auto",
                        "languages": "eng+chi_sim",
                        "available": True,
                        "pages_attempted": 1,
                        "pages_succeeded": 1,
                        "block_count": 4,
                        "engines": ["tesseract"],
                    },
                    "formula_ocr": {
                        "mode": "auto",
                        "configured": True,
                        "blocks_attempted": 1,
                        "blocks_succeeded": 1,
                        "blocks_rejected": 0,
                        "models": ["fixture-formula"],
                    },
                    "equations": [
                        {
                            "block_id": 1,
                            "page": 3,
                            "block_index": 4,
                            "quality_score": 0.96,
                            "source_reference": "page 3, block 4",
                            "asset_path": "assets/equation.png",
                            "equation_id": "eq-attn",
                            "role": "attention",
                            "latex": "Attention(Q,K,V)=softmax(QK^T)V",
                            "formula_ocr_status": "completed",
                            "formula_ocr_model": "fixture-formula",
                        }
                    ],
                    "tables": [
                        {
                            "block_id": 2,
                            "page": 6,
                            "block_index": 2,
                            "quality_score": 0.91,
                            "source_reference": "page 6, block 2",
                            "asset_path": "assets/table.png",
                            "caption": "Table 1. Benchmark results on translation tasks.",
                            "table_markdown": "| Model | BLEU |\n| --- | --- |\n| Transformer | 28.4 |",
                            "table_rows": [["Model", "BLEU"], ["<Transformer>", "28.4"]],
                            "row_count": 2,
                            "column_count": 2,
                            "reconstruction_method": "geometry+text",
                            "display_quality": "good",
                            "preview_truncated": False,
                            "has_html": True,
                        },
                        {
                            "block_id": 3,
                            "page": 7,
                            "block_index": 3,
                            "quality_score": 0.42,
                            "source_reference": "page 7, block 3",
                            "asset_path": "",
                            "caption": "Low-confidence parser fallback.",
                            "table_markdown": "Unstructured table-like text",
                            "table_rows": [],
                            "row_count": 0,
                            "column_count": 0,
                            "reconstruction_method": "text_spacing_v1",
                            "display_quality": "fallback",
                            "preview_truncated": False,
                            "has_html": False,
                        },
                    ],
                    "limits": {"equations": 6, "tables": 4},
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "layout-evidence-graph.json").write_text(
        json.dumps(
            {
                "schema_version": "evidence-graph-v1",
                "extractor_name": "layout_evidence_graph",
                "extractor_version": "fixture",
                "papers": [
                    {
                        "schema_version": "evidence-graph-v1",
                        "extractor_name": "layout_evidence_graph",
                        "extractor_version": "fixture",
                        "paper_key": "1706_03762",
                        "available": True,
                        "summary": {
                            "fact_count": 1,
                            "evidence_count": 1,
                            "relation_count": 1,
                            "supported_relation_count": 1,
                            "unlinked_fact_count": 0,
                            "truncated": False,
                        },
                        "facts": [
                            {
                                "key": "research_fact:1706_03762:1",
                                "fact_id": 1,
                                "fact_type": "method",
                                "name": "Attention",
                                "statement": "The model uses scaled dot-product attention.",
                                "confidence": 0.96,
                                "evidence": [
                                    {
                                        "evidence_key": "layout_evidence:1706_03762:7:1",
                                        "match_method": "strict_token",
                                        "score": 0.88,
                                    }
                                ],
                                "linked": True,
                            }
                        ],
                        "evidence": [
                            {
                                "key": "layout_evidence:1706_03762:7:1",
                                "evidence_type": "layout_equation",
                                "block_type": "interline_equation",
                                "run_id": 7,
                                "block_id": 1,
                                "page_index": 2,
                                "page_number": 3,
                                "block_index": 4,
                                "preview": "Attention(Q,K,V)=softmax(QK^T)V",
                                "caption": "",
                                "quality_score": 0.96,
                            }
                        ],
                        "relations": [
                            {
                                "source_key": "research_fact:1706_03762:1",
                                "relation": "supported_by",
                                "target_key": "layout_evidence:1706_03762:7:1",
                                "match_method": "strict_token",
                                "score": 0.88,
                            }
                        ],
                        "unlinked_fact_keys": [],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle_dir


def test_render_report_site_embeds_manifest_and_markdown(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    html = render_report_site(bundle_dir)

    assert "<title>AIResearch 研知库</title>" in html
    assert "研知库 · 总览" in html
    assert "AIResearch 研知库" in html
    assert 'data-search-root="."' in html
    assert 'data-search-scope' in html
    assert "papers/index.html" in html
    assert "clusters/index.html" in html
    assert "site-manifest.json" in html
    assert "Attention Is All You Need" in html
    assert "Attention methods" in html
    assert "data-lang-toggle-button" in html
    assert "lucide lucide-languages" not in html
    assert "No short summary available yet." not in html


def test_build_search_index_extracts_artifact_metadata_and_snippets(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    entries = build_search_index(bundle_dir)

    assert [entry["name"] for entry in entries] == ["digest", "research_clusters", "gap-analysis", "synthesis"]
    assert entries[0]["title"] == "Research Digest"
    assert entries[0]["type"] == "digest"
    assert entries[0]["markdown_path"] == "digest.md"
    assert entries[0]["json_path"] == "digest.json"
    assert entries[0]["snippet"] == "# Digest A short report."
    assert "research digest" in entries[0]["search_text"]
    assert entries[1]["type"] == "cluster"
    assert "multimodal agent cluster" in entries[1]["search_text"]
    assert len(entries[0]["search_text"]) < 500


def test_build_provenance_index_extracts_papers_evidence_and_code_links(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    entries = build_provenance_index(bundle_dir)

    labels = [entry["label"] for entry in entries]
    assert labels == [
        "Code: 1706_03762 -> https://github.com/attention/transformer",
        "Evidence: 1706_03762 -> /tmp/1706_03762/summary.md",
        "Paper: 1706_03762",
        "Paper: 1706_03762",
        "Paper: paper_b",
        "Evidence: paper_b -> /tmp/paper_b/source.md",
        "Paper: paper_b",
    ]
    assert entries[0]["id"] == "prov-0001"
    assert entries[0]["report_name"] == "digest"
    assert entries[0]["json_path"] == "digest.json"
    assert entries[0]["type"] == "code"
    assert entries[0]["paper_key"] == "1706_03762"
    assert entries[0]["source_path"] == "/tmp/1706_03762/source.tex"
    assert entries[0]["url"] == "https://github.com/attention/transformer"
    assert entries[5]["report_name"] == "research_clusters"
    assert entries[5]["type"] == "evidence"


def test_build_navigation_index_extracts_papers_and_clusters(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    index = build_navigation_index(bundle_dir)

    assert index["papers"] == [
        {
            "paper_key": "1706_03762",
            "title": "Attention Is All You Need",
            "report_name": "digest",
            "report_title": "Research Digest",
            "fact_count": 1,
        },
        {
            "paper_key": "paper_b",
            "title": "paper_b",
            "report_name": "research_clusters",
            "report_title": "Research Clusters",
            "fact_count": 0,
        },
    ]
    assert index["clusters"] == [
        {
            "cluster_id": "cluster_1",
            "title": "Attention methods",
            "report_name": "research_clusters",
            "report_title": "Research Clusters",
            "fact_count": 1,
            "paper_count": 1,
        }
    ]


def test_export_report_site_writes_index_html(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    site = export_report_site(bundle_dir)

    assert site.out_path == bundle_dir / "index.html"
    assert site.report_count == 3
    assert site.artifact_count > 10
    assert "AIResearch 研知库" in site.out_path.read_text(encoding="utf-8")
    assert (bundle_dir / "assets" / "site.css").exists()
    assert (bundle_dir / "assets" / "site.js").exists()
    assert (bundle_dir / "assets" / "d3.v7.min.js").exists()
    assert (bundle_dir / "assets" / "d3.LICENSE").exists()
    assert (bundle_dir / "api" / "stats.json").exists()
    assert (bundle_dir / "api" / "papers.json").exists()
    assert (bundle_dir / "api" / "papers" / "1706_03762.json").exists()
    assert (bundle_dir / "api" / "relations-graph.json").exists()
    assert (bundle_dir / "api" / "starmap.json").exists()
    assert (bundle_dir / "digest" / "index.html").exists()
    assert (bundle_dir / "papers" / "index.html").exists()
    assert (bundle_dir / "papers" / "1706_03762.html").exists()
    assert (bundle_dir / "clusters" / "index.html").exists()
    assert (bundle_dir / "clusters" / "cluster_1.html").exists()
    assert (bundle_dir / "starmap" / "index.html").exists()
    map_html = (bundle_dir / "map" / "index.html").read_text(encoding="utf-8")
    assert 'data-research-map="../api/relations-graph.json"' in map_html
    assert 'class="research-map"' in map_html
    assert '../assets/d3.v7.min.js' in map_html
    starmap_html = (bundle_dir / "starmap" / "index.html").read_text(encoding="utf-8")
    assert 'data-starmap-source="../api/starmap.json"' in starmap_html
    digest_html = (bundle_dir / "digest" / "index.html").read_text(encoding="utf-8")
    assert "Research Digest" in digest_html
    assert "Recent papers" in digest_html
    assert "High-confidence findings" in digest_html
    assert "A short report." not in digest_html
    papers_html = (bundle_dir / "papers" / "index.html").read_text(encoding="utf-8")
    assert 'data-papers-source="../api/papers.json"' in papers_html
    assert "Loading papers" in papers_html
    assert "author-filter" in papers_html
    assert "Attention Is All You Need" not in papers_html
    paper_detail_html = (bundle_dir / "papers" / "1706_03762.html").read_text(encoding="utf-8")
    assert "paper-assets/covers/1706_03762.svg" in paper_detail_html
    assert 'data-lang="zh"' in paper_detail_html
    assert "使用缩放点积注意力。" in paper_detail_html
    assert "实验与评测" in paper_detail_html
    assert "Formulas" in paper_detail_html
    assert "Attention(Q,K,V)=softmax(QK^T)V" in paper_detail_html
    assert "\\[Attention(Q,K,V)=softmax(QK^T)V\\]" in paper_detail_html
    assert "Benchmark results on translation tasks." in paper_detail_html
    assert 'class="paper-layout-data-table"' in paper_detail_html
    assert "&lt;Transformer&gt;" in paper_detail_html
    assert "结构化预览" in paper_detail_html
    assert "文本降级" in paper_detail_html
    assert "Unstructured table-like text" in paper_detail_html
    assert "OCR / Layout" in paper_detail_html
    assert "证据关系" in paper_detail_html
    assert 'class="paper-layout-panel paper-evidence-graph"' in paper_detail_html
    assert 'class="paper-layout-compact paper-evidence-graph-summary"' in paper_detail_html
    assert 'href="#layout-formula-1"' in paper_detail_html
    assert 'id="layout-formula-1"' in paper_detail_html
    assert "词元匹配" in paper_detail_html
    paper_payload = json.loads((bundle_dir / "api" / "papers" / "1706_03762.json").read_text(encoding="utf-8"))
    assert paper_payload["facts"]["method"][0]["statement_zh"] == "使用缩放点积注意力。"
    assert paper_payload["layout_evidence"]["summary"]["equation_blocks"] == 1
    assert paper_payload["layout_evidence"]["tables"][0]["row_count"] == 2
    assert paper_payload["layout_evidence"]["tables"][0]["table_rows"][1][0] == "<Transformer>"
    assert paper_payload["evidence_graph"]["schema_version"] == "evidence-graph-v1"
    assert paper_payload["evidence_graph"]["facts"][0]["evidence"][0]["match_method"] == "strict_token"
    assert "/tmp/" not in json.dumps(paper_payload["evidence_graph"], ensure_ascii=False)
    site_css = (bundle_dir / "assets" / "site.css").read_text(encoding="utf-8")
    assert 'grid-template-areas: "meta statement" "meta evidence"' in site_css
    assert ".paper-evidence-graph-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }" in site_css
    assert len(papers_html.encode("utf-8")) < 30_000
    gaps_html = (bundle_dir / "gaps" / "index.html").read_text(encoding="utf-8")
    assert "Research Gaps" in gaps_html
    assert "Fact coverage" in gaps_html
    assert "Priority papers" in gaps_html
    assert "Long raw gap report" not in gaps_html
    synthesis_html = (bundle_dir / "synthesis" / "index.html").read_text(encoding="utf-8")
    assert "Research Synthesis" in synthesis_html
    assert "Readiness checks" in synthesis_html
    assert "Strong coverage" in synthesis_html
    assert "Synthesis notes" in synthesis_html
    assert "Long raw synthesis report" not in synthesis_html
    narrative_html = (bundle_dir / "narrative" / "index.html").read_text(encoding="utf-8")
    assert "Narrative Report" in narrative_html
    assert "Executive summary" in narrative_html
    assert "Representative findings" in narrative_html
    assert "Priority actions" in narrative_html
    assert "Long raw narrative report" not in narrative_html


def test_site_without_graph_artifact_returns_empty_versioned_graph(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)
    (bundle_dir / "layout-evidence-graph.json").unlink()

    export_report_site(bundle_dir)

    payload = json.loads((bundle_dir / "api" / "papers" / "1706_03762.json").read_text(encoding="utf-8"))
    assert payload["evidence_graph"]["schema_version"] == "evidence-graph-v1"
    assert payload["evidence_graph"]["available"] is False
    assert payload["evidence_graph"]["facts"] == []
    site_manifest_path = bundle_dir / "site-manifest.json"
    assert site_manifest_path.exists()
    site_manifest = json.loads(site_manifest_path.read_text(encoding="utf-8"))
    assert "artifact-ledger.json" not in site_manifest["publish_files"]
    assert "api/search-index.json" in site_manifest["publish_files"]
    assert "api/relations-graph.json" in site_manifest["publish_files"]
    assert "api/starmap.json" in site_manifest["publish_files"]
    assert "assets/d3.v7.min.js" in site_manifest["publish_files"]
    assert "paper-assets/covers/1706_03762.svg" in site_manifest["publish_files"]
    lightweight_search = json.loads((bundle_dir / "api" / "search-index.json").read_text(encoding="utf-8"))
    paper_search = next(entry for entry in lightweight_search if entry["id"] == "1706_03762")
    assert "Attention Is All You Need".lower() in paper_search["title_terms"]
    assert "ashish vaswani" in paper_search["author_terms"]
    assert "scaled dot-product" in paper_search["method_terms"]
    assert paper_search["year_terms"] == "2017"
    search_index_path = bundle_dir / "search-index.json"
    assert search_index_path.exists()
    payload = json.loads(search_index_path.read_text(encoding="utf-8"))
    assert [entry["name"] for entry in payload] == ["digest", "research_clusters", "gap-analysis", "synthesis"]
    provenance_index_path = bundle_dir / "provenance-index.json"
    assert provenance_index_path.exists()
    provenance_payload = json.loads(provenance_index_path.read_text(encoding="utf-8"))
    assert [entry["id"] for entry in provenance_payload] == [
        "prov-0001",
        "prov-0002",
        "prov-0003",
        "prov-0004",
        "prov-0005",
        "prov-0006",
        "prov-0007",
    ]
    navigation_index_path = bundle_dir / "navigation-index.json"
    assert navigation_index_path.exists()
    navigation_payload = json.loads(navigation_index_path.read_text(encoding="utf-8"))
    assert [entry["paper_key"] for entry in navigation_payload["papers"]] == ["1706_03762", "paper_b"]
    assert [entry["cluster_id"] for entry in navigation_payload["clusters"]] == ["cluster_1"]


def test_paper_detail_renders_single_deep_reading_tab_with_inline_local_images(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)
    (bundle_dir / "paper-blogs.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-06-19T00:00:00+00:00",
                "blog_count": 1,
                "blogs": [
                    {
                        "paper_key": "1706_03762",
                        "title": "Attention Is All You Need 深度解读",
                        "status": "published",
                        "word_count": 3600,
                        "model": "fixture-blog",
                        "prompt_version": "paper_blog.zh_engineer.v1",
                        "updated_at": "2026-06-19T00:00:00+00:00",
                        "markdown": (
                            "# Attention Is All You Need 深度解读\n\n"
                            "### 开篇要点\n\n"
                            "没有二级标题时的三级标题应升级为目录顶层。\n\n"
                            "## 导读\n\n"
                            "工程长文正文，包含 **重点**、*解释* 与 `model.forward()`。\n\n"
                            "### 关键机制\n\n"
                            "机制解释正文。\n\n"
                            "- 第一项\n- 第二项\n\n"
                            "```python\nprint('<safe>')\n```\n\n"
                            "$$\nAttention(Q,K,V)=softmax(QK^T)V\n$$\n\n"
                            "参见公式（\\ref{eq:first_pass}），以及 $\\mathbf Q^{*}$。\n\n"
                            "这里引用图[img-3]继续说明关键架构。\n\n"
                            "[论文链接](https://arxiv.org/abs/1706.03762)\n\n"
                            "<script>alert('unsafe')</script>\n\n"
                            "![Transformer 论文封面](source/cover.svg)\n\n"
                            "![外部图片](https://example.com/hotlinked.png)\n"
                        ),
                        "html": (
                            "<h1>Attention Is All You Need 深度解读</h1>"
                            "<h2>导读</h2><p>工程长文正文。</p>"
                            '<img src="https://example.com/generated-hotlink.png" alt="hotlink">'
                        ),
                        "outline": {
                            "sections": [
                                {"section_key": "intro", "title": "导读"},
                            ]
                        },
                        "image_refs": [
                            {
                                "image_id": "img-1",
                                "asset_path": "paper-assets/covers/1706_03762.svg",
                                "caption": "Transformer 论文封面",
                                "section_key": "intro",
                            },
                            {
                                "image_id": "img-2",
                                "asset_path": "https://example.com/hotlinked.png",
                                "caption": "外部图片",
                                "section_key": "intro",
                            },
                            {
                                "image_id": "img-3",
                                "asset_path": "paper-assets/covers/1706_03762.svg",
                                "caption": "关键架构图",
                                "section_key": "architecture",
                            },
                        ],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    site = export_report_site(bundle_dir)
    detail_path = site.out_path.parent / "papers" / "1706_03762.html"
    html_text = detail_path.read_text(encoding="utf-8")
    paper_payload = json.loads((site.out_path.parent / "api" / "papers" / "1706_03762.json").read_text(encoding="utf-8"))

    assert 'role="tab" data-paper-mode-button="deep-reading"' in html_text
    assert ">深度解读</button>" in html_text
    assert 'class="paper-blog-detail-link" href="1706_03762.html"' in html_text
    assert "论文详情" in html_text
    site_js = (site.out_path.parent / "assets" / "site.js").read_text(encoding="utf-8")
    site_css = (site.out_path.parent / "assets" / "site.css").read_text(encoding="utf-8")
    assert "is-deep-reading-only" in site_js
    assert "is-deep-reading-only" in site_css
    assert "deepReadingOnly" in site_js
    assert 'data-paper-deep-reading-only-label="深度解读"' in html_text
    assert "paper-detail-deep-reading-back" in html_text
    assert "paper-detail.is-deep-reading-only .paper-mode-toggle" in site_css
    assert "paper-detail.is-deep-reading-only .paper-mode-workbench" in site_css
    assert "paper-detail.is-deep-reading-only .paper-mode-immersive" in site_css
    assert ".paper-detail.is-deep-reading-only .paper-mode-deep-reading" in site_css
    assert "grid-template-columns: minmax(184px, 220px) minmax(0, 760px)" in site_css
    assert ".paper-detail.is-deep-reading-only .paper-blog-toc" in site_css
    assert "max-width: min(100%, 680px)" in site_css
    assert "width: auto" in site_css
    assert html_text.count('data-paper-blog-section') == 1
    assert html_text.count("工程长文正文") == 1
    assert "Attention Is All You Need 深度解读" in html_text
    assert 'class="paper-blog-equation" data-paper-blog-equation' in html_text
    assert '<pre class="paper-blog-equation"><code>' not in html_text
    assert "window.MathJax" in html_text
    assert "mathjax@3/es5/tex-chtml.js" in html_text
    assert "inlineMath: [['$', '$'], ['\\\\(', '\\\\)']]" in html_text
    assert "displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]" in html_text
    assert "textsc: ['\\\\mathrm{#1}', 1]" in html_text
    assert "typeset: false" in html_text
    assert "document.querySelectorAll('.paper-blog-prose, .paper-layout-formula')" in html_text
    assert "window.MathJax.typesetPromise(mathSections)" in html_text
    assert "$$\nAttention(Q,K,V)=softmax(QK^T)V\n$$" in html_text
    assert "参见公式（相关公式）" in html_text
    assert "$\\mathbf Q^{*}$" in html_text
    assert "Q^{<em>" not in html_text
    assert "\\ref{eq:first_pass}" not in html_text
    assert "Attention(Q,K,V)=softmax" in html_text
    assert "paper-assets/covers/1706_03762.svg" in html_text
    assert html_text.count("data-paper-blog-image") == 2
    assert "关键架构图" in html_text
    assert "图[img-3]" not in html_text
    assert 'class="paper-blog-toc"' in html_text
    assert 'href="#开篇要点"' in html_text
    assert '<h3 id="开篇要点">1. 开篇要点</h3>' in html_text
    assert 'href="#导读"' in html_text
    assert '<h2 id="导读">2. 导读</h2>' in html_text
    assert '<h3 id="关键机制">2.1 关键机制</h3>' in html_text
    blog_image_position = html_text.index("data-paper-blog-image")
    assert html_text.index('<h2 id="导读">2. 导读</h2>') < blog_image_position
    assert blog_image_position < html_text.index("工程长文正文")
    assert "<strong>重点</strong>" in html_text
    assert "<em>解释</em>" in html_text
    assert "<code>model.forward()</code>" in html_text
    assert '<pre><code class="language-python">print(&#x27;&lt;safe&gt;&#x27;)</code></pre>' in html_text
    assert "<ul><li>第一项</li><li>第二项</li></ul>" in html_text
    assert 'href="https://arxiv.org/abs/1706.03762" rel="noopener noreferrer"' in html_text
    assert "&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;" in html_text
    assert "<script>alert('unsafe')</script>" not in html_text
    assert "https://example.com/generated-hotlink.png" not in html_text
    assert "https://example.com/hotlinked.png" not in html_text
    assert 'data-paper-blog-toc' in html_text
    assert 'data-paper-blog-toc-toggle' in html_text
    assert 'aria-controls="paper-blog-toc-list"' in html_text
    assert paper_payload["blog"]["paper_key"] == "1706_03762"
    assert paper_payload["blog"]["status"] == "published"

    css = (site.out_path.parent / "assets" / "site.css").read_text(encoding="utf-8")
    js = (site.out_path.parent / "assets" / "site.js").read_text(encoding="utf-8")
    assert ".paper-blog-toc {\n  position: fixed;" in css
    assert ".paper-blog-toc.is-collapsed" in css
    assert ".paper-blog-prose {\n  display: grid;\n  min-width: 0;" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert "max-width: 100%;\n  overflow-x: auto;" in css
    assert ".paper-blog-prose > p:has(mjx-container)" in css
    assert ".paper-mode-deep-reading:has(.paper-blog-toc)" not in css
    assert "--paper-blog-toc-width: 270px;" in css
    assert "font-size: 14px;" in css
    assert "background: rgba(248, 250, 247, 0.78);" in css
    assert "bottom: 16px;" in css
    assert "setupPaperBlogToc" in js
    assert "window.matchMedia('(max-width: 880px)')" in js
    assert "document.body.appendChild(toc)" not in js
    assert "if (mobileQuery.matches) return true;" in js
    assert "展开目录" in js


def test_blog_index_lists_published_deep_reading_posts(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)
    (bundle_dir / "paper-blogs.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-06-19T00:00:00+00:00",
                "blog_count": 1,
                "blogs": [
                    {
                        "paper_key": "1706_03762",
                        "title": "Attention Is All You Need 深度解读",
                        "status": "published",
                        "word_count": 3600,
                        "model": "fixture-blog",
                        "prompt_version": "paper_blog.zh_engineer.v1",
                        "updated_at": "2026-06-19T00:00:00+00:00",
                        "markdown": "# Attention Is All You Need 深度解读\n\n## 导读\n\n工程长文正文。",
                    },
                    {
                        "paper_key": "hidden_paper",
                        "title": "Hidden Blog",
                        "status": "hidden",
                        "word_count": 3000,
                        "updated_at": "2026-06-19T00:00:00+00:00",
                        "markdown": "# Hidden\n\nShould not be listed.",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    site = export_report_site(bundle_dir)
    root_html = site.out_path.read_text(encoding="utf-8")
    blogs_path = site.out_path.parent / "blogs" / "index.html"
    blogs_html = blogs_path.read_text(encoding="utf-8")

    assert '<a href="blogs/index.html"><span data-lang="en">Blog</span><span data-lang="zh">深度解读</span></a>' in root_html
    assert '<a href="../blogs/index.html" aria-current="page"><span data-lang="en">Blog</span><span data-lang="zh">深度解读</span></a>' in blogs_html
    assert "深度解读博客" in blogs_html
    assert "Attention Is All You Need 深度解读" in blogs_html
    assert "Attention Is All You Need" in blogs_html
    assert "3600 字" in blogs_html
    assert 'href="../papers/1706_03762.html#deep-reading"' in blogs_html
    assert 'href="../papers/1706_03762.html"' in blogs_html
    assert "Hidden Blog" not in blogs_html


def test_paper_detail_omits_deep_reading_section_without_blog(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    site = export_report_site(bundle_dir)
    detail_path = site.out_path.parent / "papers" / "1706_03762.html"
    html_text = detail_path.read_text(encoding="utf-8")
    paper_payload = json.loads((site.out_path.parent / "api" / "papers" / "1706_03762.json").read_text(encoding="utf-8"))

    assert 'data-paper-mode-button="deep-reading"' not in html_text
    assert 'data-paper-blog-section' not in html_text
    assert 'id="paper-deep-reading"' not in html_text
    assert paper_payload["blog"] is None


def test_report_site_acceptance_budgets(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    export_report_site(bundle_dir)

    index_html = (bundle_dir / "index.html").read_text(encoding="utf-8")
    papers_html = (bundle_dir / "papers" / "index.html").read_text(encoding="utf-8")
    css = (bundle_dir / "assets" / "site.css").read_text(encoding="utf-8")
    search_payload = json.loads((bundle_dir / "api" / "search-index.json").read_text(encoding="utf-8"))

    counter = _NodeCounter()
    counter.feed(index_html)
    assert counter.nodes < 2_000
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in index_html
    assert "@media (max-width: 880px)" in css
    assert "data-papers-source" in papers_html
    assert len(papers_html.encode("utf-8")) < 30_000

    started = perf_counter()
    hits = [
        entry
        for entry in search_payload
        if "attention" in (entry.get("terms") or "").lower()
        or "attention" in (entry.get("title") or "").lower()
    ]
    elapsed_ms = (perf_counter() - started) * 1000
    assert hits
    assert elapsed_ms < 100

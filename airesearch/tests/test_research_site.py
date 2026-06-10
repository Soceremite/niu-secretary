import json
from pathlib import Path

from airesearch.research_site import (
    build_navigation_index,
    build_provenance_index,
    build_search_index,
    export_report_site,
    render_report_site,
)


def make_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "digest.md").write_text("# Digest\n\nA short report.\n", encoding="utf-8")
    (bundle_dir / "digest.json").write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_key": "1706_03762",
                        "title": "Attention Is All You Need",
                        "code_links": [
                            {
                                "url": "https://github.com/attention/transformer",
                                "source_path": "/tmp/1706_03762/source.tex",
                            }
                        ],
                        "facts": {
                            "method": [
                                {
                                    "statement": "Uses scaled dot-product attention.",
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
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 2,
                "report_count": 2,
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
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return bundle_dir


def test_render_report_site_embeds_manifest_and_markdown(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    html = render_report_site(bundle_dir)

    assert "<title>AIResearch Report</title>" in html
    assert "Research Digest" in html
    assert "# Digest" in html
    assert "digest.json" in html
    assert 'id="site-search"' in html
    assert 'id="site-filter"' in html
    assert 'id="site-result-count"' in html
    assert "search-index.json" in html
    assert "provenance-index.json" in html
    assert "navigation-index.json" in html
    assert 'id="provenance"' in html
    assert 'id="corpus-navigation"' in html
    assert "Corpus Navigation" in html
    assert "Attention Is All You Need" in html
    assert "Attention methods" in html
    assert 'href="#digest"' in html
    assert "Evidence: 1706_03762" in html
    assert "https://github.com/attention/transformer" in html
    assert 'data-report-name="digest"' in html
    assert 'data-report-type="digest"' in html
    assert 'data-nav-name="research_clusters"' in html


def test_build_search_index_extracts_artifact_metadata_and_snippets(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    entries = build_search_index(bundle_dir)

    assert [entry["name"] for entry in entries] == ["digest", "research_clusters"]
    assert entries[0]["title"] == "Research Digest"
    assert entries[0]["type"] == "digest"
    assert entries[0]["markdown_path"] == "digest.md"
    assert entries[0]["json_path"] == "digest.json"
    assert entries[0]["snippet"] == "# Digest A short report."
    assert "research digest" in entries[0]["search_text"]
    assert entries[1]["type"] == "cluster"
    assert "multimodal agent cluster" in entries[1]["search_text"]


def test_build_provenance_index_extracts_papers_evidence_and_code_links(tmp_path: Path):
    bundle_dir = make_bundle(tmp_path)

    entries = build_provenance_index(bundle_dir)

    labels = [entry["label"] for entry in entries]
    assert labels == [
        "Code: 1706_03762 -> https://github.com/attention/transformer",
        "Evidence: 1706_03762 -> /tmp/1706_03762/summary.md",
        "Paper: 1706_03762",
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
    assert entries[3]["report_name"] == "research_clusters"
    assert entries[3]["type"] == "evidence"


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
    assert site.report_count == 2
    assert site.artifact_count == 10
    assert "AIResearch Report" in site.out_path.read_text(encoding="utf-8")
    search_index_path = bundle_dir / "search-index.json"
    assert search_index_path.exists()
    payload = json.loads(search_index_path.read_text(encoding="utf-8"))
    assert [entry["name"] for entry in payload] == ["digest", "research_clusters"]
    provenance_index_path = bundle_dir / "provenance-index.json"
    assert provenance_index_path.exists()
    provenance_payload = json.loads(provenance_index_path.read_text(encoding="utf-8"))
    assert [entry["id"] for entry in provenance_payload] == [
        "prov-0001",
        "prov-0002",
        "prov-0003",
        "prov-0004",
        "prov-0005",
    ]
    navigation_index_path = bundle_dir / "navigation-index.json"
    assert navigation_index_path.exists()
    navigation_payload = json.loads(navigation_index_path.read_text(encoding="utf-8"))
    assert [entry["paper_key"] for entry in navigation_payload["papers"]] == ["1706_03762", "paper_b"]
    assert [entry["cluster_id"] for entry in navigation_payload["clusters"]] == ["cluster_1"]

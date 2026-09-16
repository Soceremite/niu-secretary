from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from airesearch.formula_ocr import FormulaOCRValidationError, is_likely_formula, normalize_formula_latex


@dataclass(frozen=True)
class ReportSite:
    bundle_dir: Path
    out_path: Path
    report_count: int
    artifact_count: int


@dataclass(frozen=True)
class BlogTocItem:
    level: int
    title: str
    number: str
    anchor: str


@dataclass(frozen=True)
class BlogArticleRender:
    html: str
    toc: list[BlogTocItem]


@dataclass(frozen=True)
class SearchIndexEntry:
    name: str
    title: str
    type: str
    markdown_path: str
    json_path: str
    snippet: str
    search_text: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "title": self.title,
            "type": self.type,
            "markdown_path": self.markdown_path,
            "json_path": self.json_path,
            "snippet": self.snippet,
            "search_text": self.search_text,
        }


@dataclass(frozen=True)
class ProvenanceIndexEntry:
    id: str
    report_name: str
    report_title: str
    json_path: str
    type: str
    paper_key: str
    source_path: str
    url: str
    label: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "report_name": self.report_name,
            "report_title": self.report_title,
            "json_path": self.json_path,
            "type": self.type,
            "paper_key": self.paper_key,
            "source_path": self.source_path,
            "url": self.url,
            "label": self.label,
        }


@dataclass(frozen=True)
class NavigationPaperEntry:
    paper_key: str
    title: str
    report_name: str
    report_title: str
    fact_count: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "paper_key": self.paper_key,
            "title": self.title,
            "report_name": self.report_name,
            "report_title": self.report_title,
            "fact_count": self.fact_count,
        }


@dataclass(frozen=True)
class NavigationClusterEntry:
    cluster_id: str
    title: str
    report_name: str
    report_title: str
    fact_count: int
    paper_count: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "cluster_id": self.cluster_id,
            "title": self.title,
            "report_name": self.report_name,
            "report_title": self.report_title,
            "fact_count": self.fact_count,
            "paper_count": self.paper_count,
        }


def _load_manifest(bundle_dir: Path) -> dict[str, Any]:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"missing bundle manifest: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("bundle manifest must be a JSON object")
    return payload


def _read_text_if_present(bundle_dir: Path, relative_path: str) -> str:
    path = bundle_dir / relative_path
    if not path.exists():
        return f"Missing artifact: {relative_path}\n"
    return path.read_text(encoding="utf-8")


def _collapse_text(value: str) -> str:
    return " ".join(value.split())


def _snippet(value: str, limit: int = 260) -> str:
    collapsed = _collapse_text(value)
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 1)].rstrip() + "..."


def _compact_string(value: Any) -> str:
    if value is None:
        return ""
    return _collapse_text(str(value))


def _multiline_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _artifact_type(name: str) -> str:
    normalized = name.lower().replace("-", "_")
    if "digest" in normalized:
        return "digest"
    if "map" in normalized:
        return "map"
    if "gap" in normalized:
        return "gap"
    if "synthesis" in normalized:
        return "synthesis"
    if "narrative" in normalized:
        return "narrative"
    if "cluster" in normalized:
        return "cluster"
    if "review" in normalized:
        return "review"
    return "report"


def build_search_index(bundle_dir: Path) -> list[dict[str, str]]:
    manifest = _load_manifest(bundle_dir)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("bundle manifest artifacts must be a list")

    entries: list[dict[str, str]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = str(artifact.get("name", "report"))
        title = str(artifact.get("title", name))
        markdown_path = str(artifact.get("markdown_path", ""))
        json_path = str(artifact.get("json_path", ""))
        markdown = _read_text_if_present(bundle_dir, markdown_path) if markdown_path else ""
        snippet = _snippet(markdown, limit=180)
        search_text = _collapse_text(
            " ".join(
                [
                    name,
                    title,
                    _artifact_type(name),
                    markdown_path,
                    json_path,
                    snippet,
                ]
            )
        ).lower()
        entries.append(
            SearchIndexEntry(
                name=name,
                title=title,
                type=_artifact_type(name),
                markdown_path=markdown_path,
                json_path=json_path,
                snippet=snippet,
                search_text=search_text,
            ).as_dict()
        )
    return entries


def _read_json_if_present(bundle_dir: Path, relative_path: str) -> Any | None:
    path = bundle_dir / relative_path
    if not relative_path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _provenance_label(entry_type: str, paper_key: str, source_path: str, url: str) -> str:
    if entry_type == "code":
        prefix = "Code"
        target = url
    elif entry_type == "evidence":
        prefix = "Evidence"
        target = source_path
    else:
        prefix = "Paper"
        target = paper_key
    if paper_key and target and target != paper_key:
        return f"{prefix}: {paper_key} -> {target}"
    return f"{prefix}: {target or paper_key}"


def _provenance_key(entry: ProvenanceIndexEntry) -> tuple[str, str, str, str, str]:
    return (
        entry.report_name,
        entry.type,
        entry.paper_key,
        entry.source_path,
        entry.url,
    )


def _make_provenance_entry(
    *,
    report_name: str,
    report_title: str,
    json_path: str,
    entry_type: str,
    paper_key: str,
    source_path: str = "",
    url: str = "",
) -> ProvenanceIndexEntry | None:
    paper_key = _compact_string(paper_key)
    source_path = _compact_string(source_path)
    url = _compact_string(url)
    if not paper_key and not source_path and not url:
        return None
    return ProvenanceIndexEntry(
        id="",
        report_name=report_name,
        report_title=report_title,
        json_path=json_path,
        type=entry_type,
        paper_key=paper_key,
        source_path=source_path,
        url=url,
        label=_provenance_label(entry_type, paper_key, source_path, url),
    )


def _collect_provenance_entries(
    value: Any,
    *,
    report_name: str,
    report_title: str,
    json_path: str,
    inherited_paper_key: str = "",
) -> list[ProvenanceIndexEntry]:
    entries: list[ProvenanceIndexEntry] = []
    if isinstance(value, dict):
        paper_key = _compact_string(value.get("paper_key")) or inherited_paper_key
        if "paper_key" in value:
            entry = _make_provenance_entry(
                report_name=report_name,
                report_title=report_title,
                json_path=json_path,
                entry_type="paper",
                paper_key=paper_key,
            )
            if entry is not None:
                entries.append(entry)

        evidence_source_path = _compact_string(value.get("evidence_source_path"))
        if evidence_source_path:
            entry = _make_provenance_entry(
                report_name=report_name,
                report_title=report_title,
                json_path=json_path,
                entry_type="evidence",
                paper_key=paper_key,
                source_path=evidence_source_path,
            )
            if entry is not None:
                entries.append(entry)

        code_links = value.get("code_links")
        if isinstance(code_links, list):
            for code_link in code_links:
                if not isinstance(code_link, dict):
                    continue
                url = _compact_string(code_link.get("url"))
                source_path = _compact_string(code_link.get("source_path"))
                link_paper_key = _compact_string(code_link.get("paper_key")) or paper_key
                if url:
                    entry = _make_provenance_entry(
                        report_name=report_name,
                        report_title=report_title,
                        json_path=json_path,
                        entry_type="code",
                        paper_key=link_paper_key,
                        source_path=source_path,
                        url=url,
                    )
                    if entry is not None:
                        entries.append(entry)

        for child_value in value.values():
            entries.extend(
                _collect_provenance_entries(
                    child_value,
                    report_name=report_name,
                    report_title=report_title,
                    json_path=json_path,
                    inherited_paper_key=paper_key,
                )
            )
    elif isinstance(value, list):
        for child_value in value:
            entries.extend(
                _collect_provenance_entries(
                    child_value,
                    report_name=report_name,
                    report_title=report_title,
                    json_path=json_path,
                    inherited_paper_key=inherited_paper_key,
                )
            )
    return entries


def build_provenance_index(bundle_dir: Path) -> list[dict[str, str]]:
    manifest = _load_manifest(bundle_dir)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("bundle manifest artifacts must be a list")

    by_key: dict[tuple[str, str, str, str, str], ProvenanceIndexEntry] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = str(artifact.get("name", "report"))
        title = str(artifact.get("title", name))
        json_path = str(artifact.get("json_path", ""))
        payload = _read_json_if_present(bundle_dir, json_path)
        if payload is None:
            continue
        for entry in _collect_provenance_entries(
            payload,
            report_name=name,
            report_title=title,
            json_path=json_path,
        ):
            by_key.setdefault(_provenance_key(entry), entry)

    sorted_entries = sorted(
        by_key.values(),
        key=lambda entry: (
            entry.report_name,
            entry.type,
            entry.paper_key,
            entry.source_path,
            entry.url,
        ),
    )
    return [
        ProvenanceIndexEntry(
            id=f"prov-{index:04d}",
            report_name=entry.report_name,
            report_title=entry.report_title,
            json_path=entry.json_path,
            type=entry.type,
            paper_key=entry.paper_key,
            source_path=entry.source_path,
            url=entry.url,
            label=entry.label,
        ).as_dict()
        for index, entry in enumerate(sorted_entries, start=1)
    ]


def _count_fact_like_values(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        for key, child in value.items():
            if key in {"facts", "items"} and isinstance(child, list):
                total += len(child)
            elif key in {"method", "dataset", "benchmark", "claim", "limitation"} and isinstance(child, list):
                total += len(child)
            elif isinstance(child, (dict, list)):
                total += _count_fact_like_values(child)
        return total
    if isinstance(value, list):
        return sum(_count_fact_like_values(child) for child in value)
    return 0


def _collect_navigation_entries(
    value: Any,
    *,
    report_name: str,
    report_title: str,
) -> tuple[dict[str, NavigationPaperEntry], dict[str, NavigationClusterEntry]]:
    papers: dict[str, NavigationPaperEntry] = {}
    clusters: dict[str, NavigationClusterEntry] = {}

    def visit(child: Any) -> None:
        if isinstance(child, dict):
            paper_key = _compact_string(child.get("paper_key"))
            if paper_key:
                title = _compact_string(child.get("title")) or paper_key
                candidate = NavigationPaperEntry(
                    paper_key=paper_key,
                    title=title,
                    report_name=report_name,
                    report_title=report_title,
                    fact_count=_count_fact_like_values(child),
                )
                current = papers.get(paper_key)
                if current is None or candidate.fact_count > current.fact_count:
                    papers[paper_key] = candidate

            cluster_id = _compact_string(child.get("cluster_id") or child.get("id"))
            if cluster_id and ("facts" in child or "members" in child):
                facts = child.get("facts")
                members = child.get("members")
                fact_items = facts if isinstance(facts, list) else members if isinstance(members, list) else []
                paper_keys = {
                    _compact_string(item.get("paper_key"))
                    for item in fact_items
                    if isinstance(item, dict) and _compact_string(item.get("paper_key"))
                }
                title = _compact_string(child.get("title") or child.get("label")) or cluster_id
                clusters[cluster_id] = NavigationClusterEntry(
                    cluster_id=cluster_id,
                    title=title,
                    report_name=report_name,
                    report_title=report_title,
                    fact_count=len(fact_items),
                    paper_count=len(paper_keys),
                )

            for nested in child.values():
                visit(nested)
        elif isinstance(child, list):
            for nested in child:
                visit(nested)

    visit(value)
    return papers, clusters


def build_navigation_index(bundle_dir: Path) -> dict[str, list[dict[str, str | int]]]:
    manifest = _load_manifest(bundle_dir)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("bundle manifest artifacts must be a list")

    papers_by_key: dict[str, NavigationPaperEntry] = {}
    clusters_by_id: dict[str, NavigationClusterEntry] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = str(artifact.get("name", "report"))
        title = str(artifact.get("title", name))
        json_path = str(artifact.get("json_path", ""))
        payload = _read_json_if_present(bundle_dir, json_path)
        if payload is None:
            continue
        papers, clusters = _collect_navigation_entries(
            payload,
            report_name=name,
            report_title=title,
        )
        for paper_key, entry in papers.items():
            current = papers_by_key.get(paper_key)
            if current is None or entry.fact_count > current.fact_count:
                papers_by_key[paper_key] = entry
        clusters_by_id.update(clusters)

    return {
        "papers": [
            entry.as_dict()
            for entry in sorted(
                papers_by_key.values(),
                key=lambda item: (item.title.lower(), item.paper_key),
            )
        ],
        "clusters": [
            entry.as_dict()
            for entry in sorted(
                clusters_by_id.values(),
                key=lambda item: (item.report_name, item.cluster_id),
            )
        ],
    }


def _render_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f'<span class="metric-label">{html.escape(label)}</span>'
        f'<strong>{html.escape(str(value))}</strong>'
        "</div>"
    )


def _render_artifact_nav(artifacts: list[dict[str, Any]]) -> str:
    links = []
    for artifact in artifacts:
        name = str(artifact.get("name", "report"))
        title = str(artifact.get("title", name))
        report_type = _artifact_type(name)
        links.append(
            f'<a href="#{html.escape(name)}" data-nav-name="{html.escape(name)}" '
            f'data-report-type="{html.escape(report_type)}">{html.escape(title)}</a>'
        )
    return "\n".join(links)


def _render_provenance_links(entries: list[dict[str, str]]) -> str:
    if not entries:
        return '<p class="empty-state">No provenance links found in report JSON artifacts.</p>'
    items = []
    for entry in entries[:200]:
        label = html.escape(entry.get("label", "Provenance"))
        entry_id = html.escape(entry.get("id", ""))
        report_name = html.escape(entry.get("report_name", ""))
        report_title = html.escape(entry.get("report_title", "Report"))
        json_path = html.escape(entry.get("json_path", ""))
        entry_type = html.escape(entry.get("type", "source"))
        target = html.escape(entry.get("url") or entry.get("source_path") or entry.get("paper_key") or "")
        items.append(
            f"""
            <li id="{entry_id}" data-provenance-type="{entry_type}">
              <a href="#{report_name}">{report_title}</a>
              <span class="provenance-label">{label}</span>
              <span class="provenance-target">{target}</span>
              <a href="{json_path}">JSON</a>
            </li>
            """
        )
    return "<ul class=\"provenance-list\">" + "\n".join(items) + "</ul>"


def _render_navigation_panel(index: dict[str, list[dict[str, str | int]]]) -> str:
    papers = index.get("papers", [])
    clusters = index.get("clusters", [])
    paper_items = []
    for paper in papers[:200]:
        title = html.escape(str(paper.get("title", paper.get("paper_key", "Paper"))))
        paper_key = html.escape(str(paper.get("paper_key", "")))
        report_name = html.escape(str(paper.get("report_name", "")))
        fact_count = html.escape(str(paper.get("fact_count", 0)))
        paper_items.append(
            f'<li><a href="#{report_name}">{title}</a><span>{paper_key}</span><strong>{fact_count}</strong></li>'
        )
    cluster_items = []
    for cluster in clusters[:120]:
        title = html.escape(str(cluster.get("title", cluster.get("cluster_id", "Cluster"))))
        cluster_id = html.escape(str(cluster.get("cluster_id", "")))
        report_name = html.escape(str(cluster.get("report_name", "")))
        fact_count = html.escape(str(cluster.get("fact_count", 0)))
        paper_count = html.escape(str(cluster.get("paper_count", 0)))
        cluster_items.append(
            f'<li><a href="#{report_name}">{title}</a><span>{cluster_id}</span><strong>{fact_count} facts / {paper_count} papers</strong></li>'
        )
    paper_list = "\n".join(paper_items) or '<li class="empty-state">No papers found.</li>'
    cluster_list = "\n".join(cluster_items) or '<li class="empty-state">No clusters found.</li>'
    return f"""
      <section id="corpus-navigation" class="navigation-panel" aria-labelledby="corpus-navigation-heading">
        <div class="navigation-heading">
          <h2 id="corpus-navigation-heading">Corpus Navigation</h2>
          <a href="navigation-index.json">Index JSON</a>
        </div>
        <div class="navigation-grid">
          <div>
            <h3>Papers <span>{len(papers)}</span></h3>
            <ul>{paper_list}</ul>
          </div>
          <div>
            <h3>Clusters <span>{len(clusters)}</span></h3>
            <ul>{cluster_list}</ul>
          </div>
        </div>
      </section>
    """


def render_report_site(bundle_dir: Path) -> str:
    manifest = _load_manifest(bundle_dir)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("bundle manifest artifacts must be a list")
    search_index = build_search_index(bundle_dir)
    provenance_index = build_provenance_index(bundle_dir)
    navigation_index = build_navigation_index(bundle_dir)
    search_by_name = {entry["name"]: entry for entry in search_index}

    metrics = "\n".join(
        [
            _render_metric("Papers", manifest.get("paper_count", 0)),
            _render_metric("Facts", manifest.get("fact_count", 0)),
            _render_metric("Reports", manifest.get("report_count", len(artifacts))),
            _render_metric("Files", manifest.get("artifact_count", 0)),
        ]
    )

    sections = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = str(artifact.get("name", "report"))
        title = str(artifact.get("title", name))
        report_type = _artifact_type(name)
        markdown_path = str(artifact.get("markdown_path", ""))
        json_path = str(artifact.get("json_path", ""))
        markdown = _read_text_if_present(bundle_dir, markdown_path) if markdown_path else ""
        search_text = search_by_name.get(name, {}).get("search_text", "")
        extra_counts = artifact.get("extra_counts", {})
        extras = ""
        if isinstance(extra_counts, dict) and extra_counts:
            extras = "".join(_render_metric(str(key), value) for key, value in extra_counts.items())
        sections.append(
            f"""
            <section id="{html.escape(name)}" class="report-section" data-report-name="{html.escape(name)}" data-report-type="{html.escape(report_type)}" data-search-text="{html.escape(search_text)}">
              <div class="section-heading">
                <h2>{html.escape(title)}</h2>
                <div class="artifact-links">
                  <a href="{html.escape(markdown_path)}">Markdown</a>
                  <a href="{html.escape(json_path)}">JSON</a>
                </div>
              </div>
              <div class="mini-metrics">{extras}</div>
              <pre>{html.escape(markdown)}</pre>
            </section>
            """
        )

    generated_at = html.escape(str(manifest.get("generated_at", "unknown")))
    nav = _render_artifact_nav([artifact for artifact in artifacts if isinstance(artifact, dict)])
    filter_options = "\n".join(
        f'<option value="{html.escape(report_type)}">{html.escape(report_type.title())}</option>'
        for report_type in sorted({entry["type"] for entry in search_index})
    )
    provenance_links = _render_provenance_links(provenance_index)
    navigation_panel = _render_navigation_panel(navigation_index)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIResearch Report</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1f2933;
      --muted: #5f6b7a;
      --line: #d9e2ec;
      --panel: #f7f9fb;
      --accent: #0f766e;
      --warm: #8a5a21;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #ffffff;
      line-height: 1.55;
    }}
    header {{
      padding: 40px 32px 24px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #f7fbfa 0%, #ffffff 100%);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .subtitle {{ margin: 0; color: var(--muted); }}
    .layout {{
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
      gap: 28px;
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px 32px 48px;
    }}
    nav {{
      position: sticky;
      top: 16px;
      align-self: start;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 16px;
      border: 1px solid var(--line);
      background: var(--panel);
    }}
    nav a, .artifact-links a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 650;
    }}
    nav a:hover, .artifact-links a:hover {{ text-decoration: underline; }}
    .metrics, .mini-metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin: 18px 0 0;
    }}
    .mini-metrics {{
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      margin: 0 0 14px;
    }}
    .metric {{
      border: 1px solid var(--line);
      background: #ffffff;
      padding: 10px 12px;
    }}
    .metric-label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
    }}
    main {{ min-width: 0; }}
    .site-tools {{
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 180px auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }}
    .site-tools input,
    .site-tools select {{
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--ink);
      padding: 8px 10px;
      font: inherit;
    }}
    .result-count {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .is-hidden {{ display: none !important; }}
    .provenance-panel {{
      margin: 0 0 18px;
      padding: 14px 0 18px;
      border-bottom: 1px solid var(--line);
    }}
    .provenance-heading {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 8px;
    }}
    .provenance-actions {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      white-space: nowrap;
    }}
    .provenance-heading h2 {{ font-size: 18px; }}
    .empty-state {{ color: var(--muted); margin: 0; }}
    .provenance-list {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
      max-height: 280px;
      overflow: auto;
    }}
    .provenance-list li {{
      display: grid;
      grid-template-columns: minmax(140px, 0.8fr) minmax(180px, 1.2fr) minmax(180px, 1fr) auto;
      gap: 10px;
      align-items: baseline;
      padding: 8px 0;
      border-top: 1px solid var(--line);
      font-size: 13px;
    }}
    .provenance-label, .provenance-target {{
      overflow-wrap: anywhere;
    }}
    .provenance-target {{
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    .navigation-panel {{
      margin: 0 0 18px;
      padding: 14px 0 18px;
      border-bottom: 1px solid var(--line);
    }}
    .navigation-heading {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 10px;
    }}
    .navigation-heading h2 {{ font-size: 18px; }}
    .navigation-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .navigation-grid h3 {{
      margin: 0 0 8px;
      font-size: 14px;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .navigation-grid h3 span {{ color: var(--ink); }}
    .navigation-grid ul {{
      display: grid;
      gap: 7px;
      margin: 0;
      padding: 0;
      list-style: none;
      max-height: 240px;
      overflow: auto;
    }}
    .navigation-grid li {{
      display: grid;
      grid-template-columns: minmax(160px, 1fr) minmax(100px, 0.55fr) auto;
      gap: 8px;
      align-items: baseline;
      padding: 7px 0;
      border-top: 1px solid var(--line);
      font-size: 13px;
    }}
    .navigation-grid li span {{
      color: var(--muted);
      overflow-wrap: anywhere;
    }}
    .report-section {{
      padding: 24px 0 34px;
      border-bottom: 1px solid var(--line);
    }}
    .section-heading {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 12px;
    }}
    h2 {{
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .artifact-links {{
      display: flex;
      gap: 12px;
      white-space: nowrap;
    }}
    pre {{
      margin: 0;
      padding: 18px;
      overflow: auto;
      white-space: pre-wrap;
      border: 1px solid var(--line);
      background: #fbfcfd;
      font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    @media (max-width: 860px) {{
      header {{ padding: 28px 18px 18px; }}
      h1 {{ font-size: 28px; }}
      .layout {{ display: block; padding: 16px 18px 36px; }}
      nav {{ position: static; margin-bottom: 18px; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .site-tools {{ grid-template-columns: 1fr; }}
      .provenance-heading {{ display: block; }}
      .provenance-list li {{ grid-template-columns: 1fr; }}
      .navigation-heading {{ display: block; }}
      .navigation-grid {{ grid-template-columns: 1fr; }}
      .navigation-grid li {{ grid-template-columns: 1fr; }}
      .section-heading {{ display: block; }}
      .artifact-links {{ margin-top: 8px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>AIResearch Report</h1>
    <p class="subtitle">Generated {generated_at}</p>
    <div class="metrics">{metrics}</div>
  </header>
  <div class="layout">
    <nav>{nav}</nav>
    <main>
      <div class="site-tools" role="search">
        <input id="site-search" type="search" aria-label="Search reports" placeholder="Search reports, papers, facts, clusters" autocomplete="off">
        <select id="site-filter" aria-label="Report type filter">
          <option value="all">All types</option>
          {filter_options}
        </select>
        <span id="site-result-count" class="result-count">{len(sections)} reports</span>
      </div>
      <section id="provenance" class="provenance-panel" aria-labelledby="provenance-heading">
        <div class="provenance-heading">
          <h2 id="provenance-heading">Provenance</h2>
          <div class="provenance-actions">
            <span class="result-count">{len(provenance_index)} links</span>
            <a href="provenance-index.json">Index JSON</a>
          </div>
        </div>
        {provenance_links}
      </section>
      {navigation_panel}
      {"".join(sections)}
    </main>
  </div>
  <script>
    (() => {{
      const searchInput = document.getElementById("site-search");
      const typeFilter = document.getElementById("site-filter");
      const resultCount = document.getElementById("site-result-count");
      const sections = Array.from(document.querySelectorAll(".report-section"));
      const navLinks = Array.from(document.querySelectorAll("nav a[data-nav-name]"));
      let searchIndex = new Map();

      const applyFilter = () => {{
        const query = (searchInput.value || "").trim().toLowerCase();
        const reportType = typeFilter.value || "all";
        let visibleCount = 0;

        sections.forEach((section) => {{
          const name = section.dataset.reportName || "";
          const indexedText = searchIndex.get(name) || "";
          const haystack = indexedText || section.dataset.searchText || section.textContent.toLowerCase();
          const typeMatches = reportType === "all" || section.dataset.reportType === reportType;
          const queryMatches = !query || haystack.includes(query);
          const visible = typeMatches && queryMatches;
          section.classList.toggle("is-hidden", !visible);
          if (visible) visibleCount += 1;
        }});

        navLinks.forEach((link) => {{
          const name = link.dataset.navName || "";
          const target = sections.find((section) => section.dataset.reportName === name);
          link.classList.toggle("is-hidden", !target || target.classList.contains("is-hidden"));
        }});

        resultCount.textContent = `${{visibleCount}} report${{visibleCount === 1 ? "" : "s"}}`;
      }};

      fetch("search-index.json")
        .then((response) => response.ok ? response.json() : [])
        .then((entries) => {{
          searchIndex = new Map(entries.map((entry) => [entry.name, entry.search_text || ""]));
          applyFilter();
        }})
        .catch(() => applyFilter());

      searchInput.addEventListener("input", applyFilter);
      typeFilter.addEventListener("change", applyFilter);
      applyFilter();
    }})();
  </script>
</body>
</html>
"""


def export_report_site(bundle_dir: Path, out_path: Path | None = None) -> ReportSite:
    target = out_path or (bundle_dir / "index.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    html_text = render_report_site(bundle_dir)
    target.write_text(html_text, encoding="utf-8")
    search_index_path = target.parent / "search-index.json"
    search_index_path.write_text(
        json.dumps(build_search_index(bundle_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    provenance_index_path = target.parent / "provenance-index.json"
    provenance_index_path.write_text(
        json.dumps(build_provenance_index(bundle_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    navigation_index_path = target.parent / "navigation-index.json"
    navigation_index_path.write_text(
        json.dumps(build_navigation_index(bundle_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = _load_manifest(bundle_dir)
    return ReportSite(
        bundle_dir=bundle_dir,
        out_path=target,
        report_count=int(manifest.get("report_count", 0)),
        artifact_count=int(manifest.get("artifact_count", 0)) + 4,
    )


FACT_TYPES = ("method", "claim", "limitation", "dataset", "benchmark")
# 「最近上新」判定窗口：入库时间在该天数内 → 卡片打 NEW 标
NEW_PAPER_WINDOW_DAYS = 14
SITE_MANIFEST_FILE = "site-manifest.json"
SITE_ASSET_VERSION = "20260815-yantao-public-theme-v1"
D3_ASSET_PATH = Path(__file__).with_name("assets") / "d3.v7.min.js"
D3_LICENSE_PATH = Path(__file__).with_name("assets") / "d3.LICENSE"


def _slug(value: str) -> str:
    safe = []
    for character in value.strip().lower():
        if character.isalnum():
            safe.append(character)
        elif character in {"-", "_", "."}:
            safe.append(character)
        elif character.isspace():
            safe.append("-")
    slug = "".join(safe).strip("-._")
    return slug or "item"


def _json_script(value: Any) -> str:
    return html.escape(json.dumps(value, ensure_ascii=False), quote=False)


def _site_payloads(bundle_dir: Path) -> dict[str, Any]:
    manifest = _load_manifest(bundle_dir)
    payloads: dict[str, Any] = {"manifest": manifest}
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("bundle manifest artifacts must be a list")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = str(artifact.get("name", ""))
        json_path = str(artifact.get("json_path", ""))
        if name and json_path:
            payloads[name] = _read_json_if_present(bundle_dir, json_path)
    paper_assets = _read_json_if_present(bundle_dir, "paper-assets.json")
    if isinstance(paper_assets, list):
        payloads["paper_assets"] = paper_assets
    fact_translations = _read_json_if_present(bundle_dir, "fact-translations.json")
    if isinstance(fact_translations, list):
        payloads["fact_translations"] = fact_translations
    paper_blogs = _read_json_if_present(bundle_dir, "paper-blogs.json")
    if isinstance(paper_blogs, dict):
        payloads["paper_blogs"] = paper_blogs
    paper_layout_evidence = _read_json_if_present(bundle_dir, "paper-layout-evidence.json")
    if isinstance(paper_layout_evidence, list):
        payloads["paper_layout_evidence"] = paper_layout_evidence
    layout_evidence_graph = _read_json_if_present(bundle_dir, "layout-evidence-graph.json")
    if isinstance(layout_evidence_graph, dict):
        payloads["layout_evidence_graph"] = layout_evidence_graph
    return payloads


def _read_bundle_text(bundle_dir: Path, relative_path: str) -> str:
    if not relative_path:
        return ""
    path = bundle_dir / relative_path
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _paper_assets_lookup(payloads: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payloads.get("paper_assets", [])
    if not isinstance(rows, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        paper_key = _compact_string(row.get("paper_key"))
        if paper_key:
            lookup[paper_key] = row
    return lookup


def _paper_layout_evidence_lookup(payloads: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payloads.get("paper_layout_evidence", [])
    if not isinstance(rows, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        paper_key = _compact_string(row.get("paper_key"))
        if paper_key:
            lookup[paper_key] = row
    return lookup


def _empty_evidence_graph(paper_key: str) -> dict[str, Any]:
    return {
        "schema_version": "evidence-graph-v1",
        "extractor_name": "layout_evidence_graph",
        "extractor_version": "",
        "paper_key": paper_key,
        "available": False,
        "summary": {
            "fact_count": 0,
            "evidence_count": 0,
            "relation_count": 0,
            "supported_relation_count": 0,
            "unlinked_fact_count": 0,
            "truncated": False,
        },
        "facts": [],
        "evidence": [],
        "relations": [],
        "unlinked_fact_keys": [],
    }


def _layout_evidence_graph_lookup(payloads: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = payloads.get("layout_evidence_graph")
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("papers")
    if not isinstance(rows, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        paper_key = _compact_string(row.get("paper_key"))
        if paper_key:
            lookup[paper_key] = row
    return lookup


def _fact_translations_lookup(payloads: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = payloads.get("fact_translations", [])
    if not isinstance(rows, list):
        return {}
    lookup: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            fact_id = int(row.get("fact_id") or 0)
        except (TypeError, ValueError):
            continue
        if fact_id > 0:
            lookup[fact_id] = row
    return lookup


def _paper_blogs_lookup(payloads: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = payloads.get("paper_blogs")
    if not isinstance(payload, dict):
        return {}
    blogs = payload.get("blogs")
    if not isinstance(blogs, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for blog in blogs:
        if not isinstance(blog, dict):
            continue
        paper_key = _compact_string(blog.get("paper_key"))
        if paper_key and blog.get("status") == "published":
            lookup[paper_key] = blog
    return lookup


def _digest_papers(payloads: dict[str, Any], bundle_dir: Path) -> list[dict[str, Any]]:
    digest = payloads.get("digest")
    if not isinstance(digest, dict):
        return []
    papers = digest.get("papers", [])
    if not isinstance(papers, list):
        return []
    assets_lookup = _paper_assets_lookup(payloads)
    layout_evidence_lookup = _paper_layout_evidence_lookup(payloads)
    evidence_graph_lookup = _layout_evidence_graph_lookup(payloads)
    fact_translation_lookup = _fact_translations_lookup(payloads)
    blog_lookup = _paper_blogs_lookup(payloads)
    merged: list[dict[str, Any]] = []
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        paper_key = _compact_string(paper.get("paper_key"))
        asset = assets_lookup.get(paper_key, {})
        if asset:
            enriched = dict(paper)
            enriched["summary_en"] = _read_bundle_text(bundle_dir, _compact_string(asset.get("summary_path")))
            enriched["tldr_en"] = _read_bundle_text(bundle_dir, _compact_string(asset.get("tldr_path")))
            enriched["summary_zh"] = _read_bundle_text(bundle_dir, _compact_string(asset.get("summary_zh_path")))
            enriched["tldr_zh"] = _read_bundle_text(bundle_dir, _compact_string(asset.get("tldr_zh_path")))
            enriched["cover_path"] = _compact_string(asset.get("cover_path"))
            enriched["cover_source_kind"] = _compact_string(asset.get("cover_source_kind"))
            enriched["cover_asset_kind"] = _compact_string(asset.get("cover_asset_kind"))
            enriched["cover_caption"] = _compact_string(asset.get("cover_caption"))
            enriched["cover_source_reference"] = _compact_string(asset.get("cover_source_reference"))
            enriched["cover_reason"] = _compact_string(asset.get("cover_reason"))
            try:
                enriched["cover_score"] = float(asset.get("cover_score") or 0)
            except (TypeError, ValueError):
                enriched["cover_score"] = 0
        else:
            enriched = dict(paper)
        facts = enriched.get("facts", {})
        if isinstance(facts, dict) and fact_translation_lookup:
            localized: dict[str, Any] = {}
            for fact_type, typed in facts.items():
                if not isinstance(typed, list):
                    localized[fact_type] = typed
                    continue
                localized_rows: list[dict[str, Any]] = []
                for fact in typed:
                    if not isinstance(fact, dict):
                        continue
                    row = dict(fact)
                    try:
                        fact_id = int(row.get("fact_id") or 0)
                    except (TypeError, ValueError):
                        fact_id = 0
                    translation = fact_translation_lookup.get(fact_id, {})
                    if translation:
                        row["statement_zh"] = _compact_string(translation.get("statement"))
                        row["evidence_quote_zh"] = _compact_string(translation.get("evidence_quote"))
                    localized_rows.append(row)
                localized[fact_type] = localized_rows
            enriched["facts"] = localized
        layout_evidence = layout_evidence_lookup.get(paper_key)
        if layout_evidence:
            enriched["layout_evidence"] = layout_evidence
        enriched["evidence_graph"] = evidence_graph_lookup.get(paper_key) or _empty_evidence_graph(paper_key)
        blog = blog_lookup.get(paper_key)
        if blog:
            enriched["blog"] = blog
        merged.append(enriched)
    return merged


def _cluster_items(payloads: dict[str, Any]) -> list[dict[str, Any]]:
    clusters = payloads.get("clusters") or payloads.get("research_clusters")
    if not isinstance(clusters, dict):
        return []
    items = clusters.get("clusters", [])
    if not isinstance(items, list):
        return []
    return [cluster for cluster in items if isinstance(cluster, dict)]


def _fact_items(paper: dict[str, Any]) -> list[dict[str, Any]]:
    facts = paper.get("facts", {})
    if not isinstance(facts, dict):
        return []
    items: list[dict[str, Any]] = []
    for fact_type in FACT_TYPES:
        typed = facts.get(fact_type, [])
        if not isinstance(typed, list):
            continue
        for fact in typed:
            if isinstance(fact, dict):
                row = dict(fact)
                row.setdefault("fact_type", fact_type)
                items.append(row)
    return items


def _fact_counts(paper: dict[str, Any]) -> dict[str, int]:
    facts = paper.get("facts", {})
    if not isinstance(facts, dict):
        return {fact_type: 0 for fact_type in FACT_TYPES}
    return {
        fact_type: len(facts.get(fact_type, [])) if isinstance(facts.get(fact_type), list) else 0
        for fact_type in FACT_TYPES
    }


def _paper_summary(paper: dict[str, Any]) -> dict[str, Any]:
    paper_key = _compact_string(paper.get("paper_key"))
    title = _compact_string(paper.get("title")) or paper_key
    authors = paper.get("authors", [])
    if not isinstance(authors, list):
        authors = []
    code_links = paper.get("code_links", [])
    if not isinstance(code_links, list):
        code_links = []
    facts = _fact_items(paper)
    tldr = _compact_string(paper.get("tldr_en") or paper.get("tldr") or paper.get("summary_en") or paper.get("summary") or paper.get("abstract"))
    if not tldr and facts:
        tldr = _compact_string(facts[0].get("statement"))
    tldr_zh = _compact_string(paper.get("tldr_zh") or paper.get("summary_zh"))
    ids = paper.get("ids", {})
    arxiv_id = _compact_string(ids.get("arxiv_id")) if isinstance(ids, dict) else ""
    total_facts = len(facts)
    try:
        cover_score = float(paper.get("cover_score") or 0)
    except (TypeError, ValueError):
        cover_score = 0.0
    # 日期标签：入库时间（added_at）+ 发表时间（published_date），ISO 串截前 10 位成 YYYY-MM-DD
    published_day = _compact_string(paper.get("published_date"))[:10]
    added_day = _compact_string(paper.get("added_at"))[:10]
    is_new = False
    if added_day:
        try:
            is_new = datetime.fromisoformat(added_day).replace(tzinfo=UTC) >= datetime.now(UTC) - timedelta(days=NEW_PAPER_WINDOW_DAYS)
        except ValueError:
            is_new = False
    date_parts = []
    if added_day:
        date_parts.append(f"入库 {added_day}")
    if published_day:
        date_parts.append(f"发表 {published_day}")
    return {
        "paper_key": paper_key,
        "slug": _slug(paper_key),
        "title": title,
        "authors": [_compact_string(author) for author in authors if _compact_string(author)],
        "year": int(paper.get("year") or 0),
        "venue": _compact_string(paper.get("venue")),
        "published_date": published_day,
        "added_at": added_day,
        "date_label": " · ".join(date_parts),
        "is_new": is_new,
        "tldr": _snippet(tldr, limit=220),
        "tldr_zh": _snippet(tldr_zh, limit=220),
        "summary_en": _snippet(_compact_string(paper.get("summary_en") or paper.get("summary")), limit=640),
        "summary_zh": _snippet(_compact_string(paper.get("summary_zh")), limit=640),
        "fact_count": total_facts,
        "fact_counts": _fact_counts(paper),
        "code_link_count": len(code_links),
        "arxiv_id": arxiv_id,
        "cover_path": _compact_string(paper.get("cover_path")),
        "cover_source_kind": _compact_string(paper.get("cover_source_kind")),
        "cover_asset_kind": _compact_string(paper.get("cover_asset_kind")),
        "cover_caption": _compact_string(paper.get("cover_caption")),
        "cover_source_reference": _compact_string(paper.get("cover_source_reference")),
        "cover_reason": _compact_string(paper.get("cover_reason")),
        "cover_score": cover_score,
        "detail_path": f"papers/{_slug(paper_key)}.html",
        "api_path": f"api/papers/{_slug(paper_key)}.json",
        "layout_counts": _paper_layout_counts(paper),
    }


def _paper_layout_counts(paper: dict[str, Any]) -> dict[str, int]:
    evidence = paper.get("layout_evidence") if isinstance(paper.get("layout_evidence"), dict) else {}
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    return {
        "equations": int(summary.get("equation_blocks") or 0),
        "tables": int(summary.get("structured_table_blocks") or 0),
        "ocr_blocks": int((evidence.get("ocr") if isinstance(evidence.get("ocr"), dict) else {}).get("block_count") or 0),
        "evidence_blocks": int(summary.get("high_quality_evidence_blocks") or 0),
    }


CODE_LINK_NOISE_PATTERNS = (
    "cvpr-org/author-kit",
    "cvpr-org/latex-template",
    "cvpr-org/cvpr-template",
    "cvpr-org/cvpr",
    "latex3/latex2e",
    "acl-org/acl-style-files",
    "openreview/openreview-py",
)


def _code_link_score(link: dict[str, Any], paper: dict[str, Any]) -> int:
    url = _compact_string(link.get("url")).rstrip("/")
    if not url:
        return -1000
    lowered_url = url.lower()
    if any(pattern in lowered_url for pattern in CODE_LINK_NOISE_PATTERNS):
        return -500

    parsed = urlparse(url)
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    owner = _compact_string(link.get("owner") or (path_parts[0] if path_parts else ""))
    repo = _compact_string(link.get("repo") or (path_parts[1] if len(path_parts) > 1 else ""))
    title = _compact_string(paper.get("title")).lower()
    paper_key = _compact_string(paper.get("paper_key")).lower().replace("_", "-")
    authors = paper.get("authors", [])
    author_tokens = []
    if isinstance(authors, list):
        for author in authors[:4]:
            author_tokens.extend(token.lower() for token in _compact_string(author).replace("-", " ").split() if len(token) >= 3)

    repo_norm = repo.lower().replace("_", "-")
    owner_norm = owner.lower()
    score = 0
    if parsed.netloc.lower().endswith("github.com"):
        score += 20
    if repo_norm and repo_norm in title:
        score += 45
    if paper_key and (paper_key in repo_norm or repo_norm in paper_key):
        score += 35
    if repo_norm and any(token in repo_norm for token in author_tokens):
        score += 12
    if owner_norm and any(token in owner_norm for token in author_tokens):
        score += 8
    if any(word in repo_norm for word in ("template", "style", "author-kit", "latex", "camera-ready", "proceedings")):
        score -= 140
    return score


def _primary_code_link(paper: dict[str, Any]) -> dict[str, Any] | None:
    links = paper.get("code_links", [])
    if not isinstance(links, list):
        return None
    seen: set[str] = set()
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            continue
        url = _compact_string(link.get("url")).rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        score = _code_link_score(link, paper)
        if score > -100:
            candidates.append((score, -index, {**link, "url": url}))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def _paper_detail_payload(paper: dict[str, Any]) -> dict[str, Any]:
    summary = _paper_summary(paper)
    blog = paper.get("blog") if isinstance(paper.get("blog"), dict) else None
    facts_by_type: dict[str, list[dict[str, Any]]] = {fact_type: [] for fact_type in FACT_TYPES}
    for fact in _fact_items(paper):
        fact_type = _compact_string(fact.get("fact_type")) or "fact"
        facts_by_type.setdefault(fact_type, []).append(
            {
                "fact_type": fact_type,
                "statement": _compact_string(fact.get("statement")),
                "statement_zh": _compact_string(fact.get("statement_zh")),
                "confidence": fact.get("confidence"),
                "evidence_quote": _snippet(_compact_string(fact.get("evidence_quote")), limit=360),
                "evidence_quote_zh": _snippet(_compact_string(fact.get("evidence_quote_zh")), limit=360),
                "evidence_source_path": _compact_string(fact.get("evidence_source_path")),
                "evidence_artifact_type": _compact_string(fact.get("evidence_artifact_type")),
            }
        )
    return {
        **summary,
        "ids": paper.get("ids", {}) if isinstance(paper.get("ids"), dict) else {},
        "artifact_types": paper.get("artifact_types", []) if isinstance(paper.get("artifact_types"), list) else [],
        "code_links": paper.get("code_links", []) if isinstance(paper.get("code_links"), list) else [],
        "primary_code_link": _primary_code_link(paper),
        "summary_full_en": _multiline_string(paper.get("summary_en") or paper.get("summary")),
        "summary_full_zh": _multiline_string(paper.get("summary_zh")),
        "tldr_full_zh": _multiline_string(paper.get("tldr_zh")),
        "facts": facts_by_type,
        "layout_evidence": paper.get("layout_evidence") if isinstance(paper.get("layout_evidence"), dict) else {},
        "evidence_graph": (
            paper.get("evidence_graph")
            if isinstance(paper.get("evidence_graph"), dict)
            else _empty_evidence_graph(_compact_string(paper.get("paper_key")))
        ),
        "blog": blog,
    }


def _cluster_summary(cluster: dict[str, Any]) -> dict[str, Any]:
    cluster_id = _compact_string(cluster.get("cluster_id") or cluster.get("id"))
    facts = cluster.get("facts", [])
    if not isinstance(facts, list):
        facts = []
    paper_keys = {
        _compact_string(fact.get("paper_key"))
        for fact in facts
        if isinstance(fact, dict) and _compact_string(fact.get("paper_key"))
    }
    title = _compact_string(cluster.get("label") or cluster.get("title")) or cluster_id
    fact_type = _compact_string(cluster.get("fact_type")) or "mixed"
    return {
        "cluster_id": cluster_id,
        "slug": _slug(cluster_id),
        "title": title,
        "fact_type": fact_type,
        "fact_count": int(cluster.get("fact_count") or len(facts)),
        "paper_count": int(cluster.get("paper_count") or len(paper_keys)),
        "average_confidence": float(cluster.get("average_confidence") or 0),
        "detail_path": f"clusters/{_slug(cluster_id)}.html",
        "top_facts": [
            {
                "paper_key": _compact_string(fact.get("paper_key")),
                "paper_title": _compact_string(fact.get("paper_title")),
                "statement": _snippet(_compact_string(fact.get("statement")), limit=220),
                "confidence": fact.get("confidence"),
            }
            for fact in facts[:5]
            if isinstance(fact, dict)
        ],
    }


def _stats_payload(payloads: dict[str, Any], papers: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    manifest = payloads["manifest"]
    gap = payloads.get("gap-analysis")
    low_coverage = []
    if isinstance(gap, dict) and isinstance(gap.get("low_coverage_fact_types"), list):
        low_coverage = gap["low_coverage_fact_types"]
    years = [int(paper.get("year") or 0) for paper in papers if int(paper.get("year") or 0) > 0]
    return {
        "generated_at": manifest.get("generated_at", "unknown"),
        "paper_count": int(manifest.get("paper_count", len(papers))),
        "fact_count": int(manifest.get("fact_count", sum(_paper_summary(paper)["fact_count"] for paper in papers))),
        "cluster_count": len(clusters),
        "report_count": int(manifest.get("report_count", 0)),
        "latest_year": max(years) if years else 0,
        "low_coverage_fact_types": low_coverage[:5],
    }


def _lightweight_search_entries(
    papers: list[dict[str, Any]], clusters: list[dict[str, Any]], stats: dict[str, Any]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for paper in papers:
        summary = _paper_summary(paper)
        facts = _fact_items(paper)
        fact_terms = " ".join(_compact_string(fact.get("statement")) for fact in facts[:12])
        authors = " ".join(summary["authors"])
        method_terms = " ".join(_compact_string(fact.get("statement")) for fact in facts if fact.get("fact_type") == "method")
        dataset_terms = " ".join(_compact_string(fact.get("statement")) for fact in facts if fact.get("fact_type") == "dataset")
        year_terms = str(summary["year"] or "")
        entries.append(
            {
                "id": summary["paper_key"],
                "type": "paper",
                "title": summary["title"],
                "subtitle": ", ".join(summary["authors"][:3]),
                "snippet": summary["tldr"],
                "url": summary["detail_path"],
                "terms": _collapse_text(
                    f"{summary['paper_key']} {summary['title']} {authors} {year_terms} {summary['tldr']} {fact_terms}"
                ).lower(),
                "title_terms": _collapse_text(f"{summary['paper_key']} {summary['title']}").lower(),
                "author_terms": _collapse_text(authors).lower(),
                "method_terms": _collapse_text(method_terms).lower(),
                "dataset_terms": _collapse_text(dataset_terms).lower(),
                "year_terms": year_terms,
            }
        )
    for cluster in clusters[:300]:
        summary = _cluster_summary(cluster)
        cluster_terms = _collapse_text(
            f"{summary['cluster_id']} {summary['title']} {summary['fact_type']} "
            + " ".join(fact["statement"] for fact in summary["top_facts"])
        ).lower()
        entries.append(
            {
                "id": summary["cluster_id"],
                "type": "cluster",
                "title": summary["title"],
                "subtitle": f"{summary['fact_count']} facts / {summary['paper_count']} papers",
                "snippet": " ".join(fact["statement"] for fact in summary["top_facts"][:2]),
                "url": summary["detail_path"],
                "terms": cluster_terms,
                "title_terms": _collapse_text(f"{summary['cluster_id']} {summary['title']}").lower(),
                "author_terms": "",
                "method_terms": cluster_terms if summary["fact_type"] == "method" else "",
                "dataset_terms": cluster_terms if summary["fact_type"] == "dataset" else "",
                "year_terms": "",
            }
        )
    entries.append(
        {
            "id": "dashboard",
            "type": "site",
            "title": "AIResearch dashboard",
            "subtitle": f"{stats['paper_count']} papers / {stats['fact_count']} facts",
            "snippet": "Research corpus dashboard, gaps, clusters, map, synthesis, and narrative.",
            "url": "index.html",
            "terms": "dashboard papers facts clusters gaps synthesis narrative research",
            "title_terms": "dashboard airesearch",
            "author_terms": "",
            "method_terms": "",
            "dataset_terms": "",
            "year_terms": "",
        }
    )
    return entries


FACT_TYPE_LABELS = {
    "method": ("Method", "方法"),
    "dataset": ("Dataset", "数据集"),
    "benchmark": ("Benchmark", "基准"),
    "claim": ("Claim", "结论"),
    "limitation": ("Limitation", "局限"),
}

FACT_TYPE_NAV_LABELS = {
    "method": ("Method", "方法"),
    "dataset": ("Data", "数据"),
    "benchmark": ("Bench", "基准"),
    "claim": ("Claim", "结论"),
    "limitation": ("Limit", "局限"),
}


def _lang_text(en: str, zh: str, *, tag: str = "span", cls: str = "") -> str:
    class_attr = f' class="{cls}"' if cls else ""
    return (
        f'<{tag}{class_attr} data-lang="en">{html.escape(en)}</{tag}>'
        f'<{tag}{class_attr} data-lang="zh">{html.escape(zh or en)}</{tag}>'
    )


def _lang_paragraph(en: str, zh: str, *, cls: str = "") -> str:
    class_attr = f' class="{cls}"' if cls else ""
    return (
        f'<p{class_attr} data-lang="en">{html.escape(en)}</p>'
        f'<p{class_attr} data-lang="zh">{html.escape(zh or en)}</p>'
    )


def _strip_paper_structure_section(markdown: str) -> str:
    source_lines = markdown.splitlines()
    lines: list[str] = []
    index = 0
    while index < len(source_lines):
        raw_line = source_lines[index]
        line = raw_line.strip()
        heading = line.lower()
        if heading in {"## paper structure", "## 论文结构"}:
            index += 1
            while index < len(source_lines):
                next_line = source_lines[index].strip()
                if next_line.startswith("## ") or next_line.startswith("---"):
                    break
                index += 1
            continue
        if line.startswith("---"):
            probe = index + 1
            while probe < len(source_lines) and not source_lines[probe].strip():
                probe += 1
            if probe < len(source_lines) and source_lines[probe].lstrip().startswith("- "):
                index = probe + 1
                while index < len(source_lines) and not source_lines[index].strip().startswith("---"):
                    index += 1
                if index < len(source_lines) and source_lines[index].strip().startswith("---"):
                    index += 1
                continue
        lines.append(raw_line)
        index += 1
    return "\n".join(lines).strip()


def _strip_summary_front_matter(markdown: str) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    metadata_prefixes = (
        "**arxiv:**",
        "**authors:**",
        "**published:**",
        "**categories:**",
        "**doi:**",
        "**venue:**",
    )
    for raw_line in lines:
        line = raw_line.strip()
        lowered = line.lower()
        if lowered.startswith("# "):
            continue
        if any(lowered.startswith(prefix) for prefix in metadata_prefixes):
            continue
        kept.append(raw_line)
    return "\n".join(kept).strip()


def _lang_markdown(en: str, zh: str, *, cls: str = "", strip_paper_structure: bool = False) -> str:
    class_attr = f' class="{cls}"' if cls else ""
    if strip_paper_structure:
        en = _strip_summary_front_matter(_strip_paper_structure_section(en))
        zh = _strip_summary_front_matter(_strip_paper_structure_section(zh or en))
    return (
        f'<div{class_attr} data-lang="en">{_markdown_to_blocks(en)}</div>'
        f'<div{class_attr} data-lang="zh">{_markdown_to_blocks(zh or en)}</div>'
    )


def _page_shell(*, title: str, body: str, current: str, depth: int = 0, extra_script: str = "") -> str:
    prefix = "../" * depth
    nav_items = [
        ("dashboard", f"{prefix}index.html", "Dashboard", "总览"),
        ("papers", f"{prefix}papers/index.html", "Papers", "论文"),
        ("blogs", f"{prefix}blogs/index.html", "Blog", "深度解读"),
        ("digest", f"{prefix}digest/index.html", "Digest", "简报"),
        ("clusters", f"{prefix}clusters/index.html", "Clusters", "聚类"),
        ("map", f"{prefix}map/index.html", "Map", "图谱"),
        ("starmap", f"{prefix}starmap/index.html", "Starmap", "星图"),
        ("gaps", f"{prefix}gaps/index.html", "Gaps", "空白"),
        ("synthesis", f"{prefix}synthesis/index.html", "Synthesis", "综述"),
        ("narrative", f"{prefix}narrative/index.html", "Narrative", "叙事"),
    ]
    nav_parts = []
    for key, href, label_en, label_zh in nav_items:
        current_attr = ' aria-current="page"' if key == current else ""
        nav_parts.append(
            f'<a href="{href}"{current_attr}>'
            f'<span data-lang="en">{label_en}</span><span data-lang="zh">{label_zh}</span></a>'
        )
    nav = "\n".join(nav_parts)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="AIResearch static research dashboard with paper, evidence, cluster, and gap navigation.">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/site.css?v={SITE_ASSET_VERSION}">
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true,
        macros: {{
          textsc: ['\\\\mathrm{{#1}}', 1]
        }}
      }},
      options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
      }},
      startup: {{
        typeset: false
      }}
    }};
    window.addEventListener('DOMContentLoaded', function() {{
      if (!window.MathJax.startup || !window.MathJax.startup.promise) return;
      window.MathJax.startup.promise.then(function() {{
        var mathSections = Array.from(document.querySelectorAll('.paper-blog-prose, .paper-layout-formula'));
        if (mathSections.length) window.MathJax.typesetPromise(mathSections);
      }});
    }});
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
  <script defer src="{prefix}assets/site.js?v={SITE_ASSET_VERSION}"></script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="topbar theme-topbar">
    <a class="brand" href="{prefix}index.html"><span>牛秘书</span><strong>AIResearch</strong></a>
    <nav aria-label="AIResearch sections">{nav}</nav>
    <div class="topbar-actions">
      <a class="home-link" href="/niu-secretary/">返回主页</a>
      <button class="lang-toggle" type="button" data-lang-toggle-button aria-label="切换到中文" aria-pressed="false">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lang-toggle-icon" aria-hidden="true">
          <path d="m5 8 6 6"></path><path d="m4 14 6-6 2-3"></path><path d="M2 5h12"></path><path d="M7 2h1"></path><path d="m22 22-5-10-5 10"></path><path d="M14 18h6"></path>
        </svg>
        <span data-lang-toggle-label>简</span>
      </button>
    </div>
  </header>
  <main id="main">{body}</main>
  <footer class="site-footer theme-footer">
    <span>AIResearch 研知库</span>
    <a href="{prefix}manifest.json">Bundle manifest</a>
    <a href="{prefix}{SITE_MANIFEST_FILE}">Site manifest</a>
  </footer>
  <script>
    window.aiResearchSelectFactPanel = function(button) {{
      var mode = button && button.closest ? button.closest('[data-paper-mode]') : null;
      if (!mode) return false;
      var factType = button.dataset.paperFactButton;
      mode.querySelectorAll('[data-fact-section]').forEach(function(section) {{
        section.hidden = section.dataset.factSection !== factType;
      }});
      mode.querySelectorAll('[data-paper-fact-button]').forEach(function(item) {{
        item.setAttribute('aria-pressed', String(item === button));
      }});
      var target = mode.querySelector('[data-fact-section="' + factType + '"]');
      if (target) target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      return false;
    }};
  </script>
  {extra_script}
</body>
</html>
"""


def _metric_card(label: str, value: Any, hint: str = "") -> str:
    return (
        '<div class="metric-card reveal">'
        f'<span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong>'
        f'<small>{html.escape(hint)}</small>'
        "</div>"
    )


def _paper_card(summary: dict[str, Any], *, prefix: str = "") -> str:
    authors = ", ".join(summary["authors"][:3]) or "Unknown authors"
    badges = "".join(
        f'<span class="fact-chip {fact_type}">{fact_type} {count}</span>'
        for fact_type, count in summary["fact_counts"].items()
        if count
    )
    cover = '<div class="paper-cover-wrap paper-card-media paper-cover-empty" aria-hidden="true"></div>'
    if summary.get("cover_path"):
        cover = (
            '<div class="paper-cover-wrap paper-card-media">'
            f'<img class="paper-cover" src="{prefix}{html.escape(summary["cover_path"])}" alt="{html.escape(summary["title"])} cover" loading="lazy">'
            "</div>"
        )
    new_badge = '<span class="new-badge">NEW</span>' if summary.get("is_new") else ""
    date_label = _compact_string(summary.get("date_label"))
    dates_html = f'<p class="paper-dates">📅 {html.escape(date_label)}</p>' if date_label else ""
    return f"""
    <article class="paper-card paper-post-card reveal" data-year="{summary['year']}" data-added="{html.escape(summary.get('added_at') or '')}" data-published="{html.escape(summary.get('published_date') or '')}" data-fact-count="{summary['fact_count']}">
      {cover}
      <div class="paper-card-body paper-card-content">
        <a class="paper-title" href="{prefix}{html.escape(summary['detail_path'])}">{html.escape(summary['title'])}</a>
        <p class="paper-meta">{new_badge}{html.escape(authors)} · {html.escape(str(summary['year'] or 'n.d.'))} · {html.escape(summary['paper_key'])}</p>
        {dates_html}
        {_lang_paragraph(summary['tldr'] or 'No short summary available yet.', summary.get('tldr_zh') or summary['tldr'])}
        <div class="chip-row">{badges or '<span class="fact-chip">no facts</span>'}</div>
      </div>
    </article>
    """


def _cluster_card(summary: dict[str, Any], *, prefix: str = "") -> str:
    return f"""
    <article class="cluster-card reveal">
      <a class="paper-title" href="{prefix}{html.escape(summary['detail_path'])}">{html.escape(summary['title'])}</a>
      <p class="paper-meta">{html.escape(summary['fact_type'])} · {summary['fact_count']} facts · {summary['paper_count']} papers</p>
      <p>{html.escape(summary['top_facts'][0]['statement'] if summary['top_facts'] else 'No cluster evidence yet.')}</p>
    </article>
    """


def _dashboard_page(payloads: dict[str, Any], papers: list[dict[str, Any]], clusters: list[dict[str, Any]], stats: dict[str, Any]) -> str:
    summaries = sorted((_paper_summary(paper) for paper in papers), key=lambda item: (item["year"], item["paper_key"]), reverse=True)
    cluster_summaries = sorted((_cluster_summary(cluster) for cluster in clusters), key=lambda item: item["fact_count"], reverse=True)
    metrics = "".join(
        [
            _metric_card("Papers", stats["paper_count"], f"Latest year {stats['latest_year'] or 'n.d.'}"),
            _metric_card("Facts", stats["fact_count"], "audited evidence rows"),
            _metric_card("Clusters", stats["cluster_count"], "knowledge groups"),
            _metric_card("Reports", stats["report_count"], "static research artifacts"),
        ]
    )
    # 「最近上新」= 按入库时间倒序（不是按发表年份），让最新收进来的工作排在最前
    newest = sorted(
        summaries,
        key=lambda item: (item.get("added_at") or "", item.get("paper_key") or ""),
        reverse=True,
    )
    recent = "\n".join(_paper_card(summary) for summary in newest[:5])
    top_clusters = "\n".join(_cluster_card(summary) for summary in cluster_summaries[:5])
    low_coverage = stats.get("low_coverage_fact_types", [])
    gap_items = "\n".join(
        f'<li><strong>{html.escape(str(item.get("fact_type", "gap")))}</strong><span>{float(item.get("coverage_ratio", 0)):.0%} coverage</span></li>'
        for item in low_coverage
        if isinstance(item, dict)
    ) or "<li><strong>No critical gaps</strong><span>coverage is balanced</span></li>"
    body = f"""
    <section class="hero">
      <div>
        <p class="eyebrow">研知库 · 总览</p>
        <h1>AIResearch 研知库</h1>
        <p>{stats["paper_count"]} 篇论文，{stats["fact_count"]} 条证据，从混沌中提炼结构。</p>
      </div>
      <form class="global-search" role="search" data-search-root="." aria-label="Search the research corpus">
        <label for="global-search-input">Search corpus</label>
        <select data-search-scope aria-label="Search dimension">
          <option value="all">All</option>
          <option value="title">Title</option>
          <option value="author">Author</option>
          <option value="method">Method</option>
          <option value="dataset">Dataset</option>
          <option value="year">Year</option>
        </select>
        <input id="global-search-input" type="search" placeholder="Search papers, facts, clusters" autocomplete="off">
        <div class="search-results" aria-live="polite"></div>
      </form>
    </section>
    <section class="metrics-grid" aria-label="Corpus metrics">{metrics}</section>
    <section class="dashboard-grid">
      <div>
        <div class="section-title"><h2>最近上新 · Recently added</h2><a href="papers/index.html">View all</a></div>
        <div class="stack">{recent}</div>
      </div>
      <aside>
        <div class="section-title"><h2>Top clusters</h2><a href="clusters/index.html">Browse</a></div>
        <div class="stack">{top_clusters}</div>
        <div class="gap-panel reveal">
          <h2>Gap alerts</h2>
          <ul>{gap_items}</ul>
        </div>
      </aside>
    </section>
    """
    return _page_shell(title="AIResearch 研知库", body=body, current="dashboard")


def _papers_page(papers: list[dict[str, Any]]) -> str:
    summaries = sorted((_paper_summary(paper) for paper in papers), key=lambda item: (item["year"], item["paper_key"]), reverse=True)
    years = sorted({summary["year"] for summary in summaries if summary["year"]}, reverse=True)
    authors = sorted({author for summary in summaries for author in summary["authors"] if author})
    year_options = "\n".join(f'<option value="{year}">{year}</option>' for year in years)
    author_options = "\n".join(f'<option value="{html.escape(author.lower())}">{html.escape(author)}</option>' for author in authors[:250])
    body = f"""
    <section class="page-heading">
      <p class="eyebrow">论文库</p>
      <h1>Papers</h1>
      <p>每一篇都是一块拼图，等待被放入正确的位置。</p>
    </section>
    <section class="toolbar" data-paper-controls>
      <input type="search" id="paper-filter" placeholder="Filter visible papers" aria-label="Filter papers">
      <select id="year-filter" aria-label="Filter by year"><option value="all">All years</option>{year_options}</select>
      <select id="type-filter" aria-label="Filter by fact type"><option value="all">All fact types</option>{''.join(f'<option value="{t}">{t}</option>' for t in FACT_TYPES)}</select>
      <select id="author-filter" aria-label="Filter by author"><option value="all">All authors</option>{author_options}</select>
      <select id="sort-order" aria-label="Sort papers">
        <option value="added">最新入库</option>
        <option value="published">最新发表</option>
        <option value="year">发表年份</option>
        <option value="title">标题</option>
      </select>
      <select id="date-basis" aria-label="日期口径">
        <option value="added">按入库时间</option>
        <option value="published">按发表时间</option>
      </select>
      <input type="date" id="date-from" aria-label="起始日期">
      <input type="date" id="date-to" aria-label="结束日期">
      <button type="button" id="recent-30" class="ghost-button">近 30 天上新</button>
      <span id="paper-count" class="result-count">{len(summaries)} papers</span>
    </section>
    <section class="paper-list" data-page-size="20" data-papers-source="../api/papers.json">
      <p class="empty-state">Loading papers...</p>
    </section>
    <nav class="pager" aria-label="Paper pagination"><button id="prev-page" type="button">Previous</button><span id="page-label">Page 1</span><button id="next-page" type="button">Next</button></nav>
    """
    return _page_shell(title="Papers / AIResearch", body=body, current="papers", depth=1)


def _blog_index_items(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for paper in papers:
        blog = paper.get("blog") if isinstance(paper.get("blog"), dict) else None
        if not blog or blog.get("status") != "published":
            continue
        summary = _paper_summary(paper)
        items.append(
            {
                **summary,
                "blog_title": _compact_string(blog.get("title")) or f"{summary['title']} 深度解读",
                "blog_word_count": int(blog.get("word_count") or 0),
                "blog_updated_at": _compact_string(blog.get("updated_at")),
                "blog_model": _compact_string(blog.get("model")),
            }
        )
    return sorted(items, key=lambda item: (item["blog_updated_at"], item["year"], item["paper_key"]), reverse=True)


def _blog_index_card(item: dict[str, Any]) -> str:
    authors = ", ".join(item["authors"][:3]) or "Unknown authors"
    meta_parts = [
        f"{int(item['blog_word_count'])} 字" if int(item["blog_word_count"]) else "",
        _compact_string(item.get("blog_model")),
        _compact_string(item.get("blog_updated_at")),
    ]
    meta = " · ".join(part for part in meta_parts if part)
    cover = '<div class="blog-card-cover blog-card-media blog-card-cover-empty" aria-hidden="true"></div>'
    if item.get("cover_path"):
        cover = (
            '<div class="blog-card-cover blog-card-media">'
            f'<img src="../{html.escape(item["cover_path"], quote=True)}" alt="{html.escape(item["title"], quote=True)} cover" loading="lazy">'
            "</div>"
        )
    return f"""
    <article class="blog-card blog-post-card reveal">
      {cover}
      <div class="blog-card-body">
        <p class="eyebrow">深度解读</p>
        <h2><a href="../{html.escape(item['detail_path'])}#deep-reading">{html.escape(item['blog_title'])}</a></h2>
        <p class="paper-meta">{html.escape(item['title'])} · {html.escape(authors)} · {html.escape(str(item['year'] or 'n.d.'))}</p>
        {_lang_paragraph(item["tldr"] or "No short summary available yet.", item.get("tldr_zh") or item["tldr"])}
        <div class="blog-card-footer">
          <span>{html.escape(meta or "已发布")}</span>
          <span class="blog-card-links">
            <a href="../{html.escape(item['detail_path'])}#deep-reading">阅读全文</a>
            <a href="../{html.escape(item['detail_path'])}">论文详情</a>
          </span>
        </div>
      </div>
    </article>
    """


def _blogs_page(papers: list[dict[str, Any]]) -> str:
    items = _blog_index_items(papers)
    cards = "\n".join(_blog_index_card(item) for item in items)
    body = f"""
    <section class="page-heading blog-page-heading">
      <p class="eyebrow">深度解读博客</p>
      <h1>Blog</h1>
      <p>集中浏览已经生成并发布的论文深度解读长文，从论文列表直接进入对应的深度解读章节。</p>
    </section>
    <section class="blog-index-stats" aria-label="Blog summary">
      <span class="result-count">{len(items)} 篇已发布深度解读</span>
      <a href="../papers/index.html">查看全部论文</a>
    </section>
    <section class="blog-index-list">{cards or '<p class="empty-state">暂无已发布的深度解读博客。</p>'}</section>
    """
    return _page_shell(title="Blog / AIResearch", body=body, current="blogs", depth=1)


def _local_blog_asset_path(value: Any) -> str:
    asset_path = _compact_string(value).replace("\\", "/")
    if not asset_path or asset_path.startswith(("/", "//")):
        return ""
    parsed = urlparse(asset_path)
    if parsed.scheme or parsed.netloc:
        return ""
    decoded_path = unquote(parsed.path).replace("\\", "/")
    parts = [part for part in decoded_path.split("/") if part]
    if not parts or parts[0] != "paper-assets" or any(part in {".", ".."} for part in parts):
        return ""
    return "/".join(parts)


def _safe_blog_link(value: str) -> str:
    href = html.unescape(value.strip())
    if not href or any(ord(char) <= 32 or ord(char) == 127 for char in href):
        return ""
    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https", "mailto"}:
        return ""
    if parsed.netloc and not parsed.scheme:
        return ""
    if not parsed.scheme and (
        href.startswith(("/", "//", "\\"))
        or any(part == ".." for part in href.replace("\\", "/").split("/"))
    ):
        return ""
    return href


def _blog_inline_markdown(value: str) -> str:
    value = re.sub(r"\\(?:eq)?ref\{[^{}]+\}", "相关公式", value)
    rendered: list[str] = []
    cursor = 0
    while cursor < len(value):
        if value[cursor] == "$" and not value.startswith("$$", cursor):
            closing = value.find("$", cursor + 1)
            if closing != -1:
                rendered.append(html.escape(value[cursor:closing + 1]))
                cursor = closing + 1
                continue
        if value[cursor] == "`":
            closing = value.find("`", cursor + 1)
            if closing != -1:
                rendered.append(f"<code>{html.escape(value[cursor + 1:closing])}</code>")
                cursor = closing + 1
                continue
        if value.startswith("**", cursor):
            closing = value.find("**", cursor + 2)
            if closing != -1:
                rendered.append(f"<strong>{_blog_inline_markdown(value[cursor + 2:closing])}</strong>")
                cursor = closing + 2
                continue
        if value[cursor] == "*":
            closing = value.find("*", cursor + 1)
            if closing != -1:
                rendered.append(f"<em>{_blog_inline_markdown(value[cursor + 1:closing])}</em>")
                cursor = closing + 1
                continue
        if value[cursor] == "[":
            label_end = value.find("](", cursor + 1)
            href_end = value.find(")", label_end + 2) if label_end != -1 else -1
            if label_end != -1 and href_end != -1:
                label = _blog_inline_markdown(value[cursor + 1:label_end])
                href = _safe_blog_link(value[label_end + 2:href_end])
                if href:
                    external = urlparse(href).scheme.lower() in {"http", "https"}
                    attrs = ' rel="noopener noreferrer" target="_blank"' if external else ""
                    rendered.append(f'<a href="{html.escape(href, quote=True)}"{attrs}>{label}</a>')
                else:
                    rendered.append(label)
                cursor = href_end + 1
                continue
        rendered.append(html.escape(value[cursor]))
        cursor += 1
    return "".join(rendered)


def _paper_blog_image(image: dict[str, Any]) -> str:
    asset_path = _local_blog_asset_path(image.get("asset_path"))
    if not asset_path:
        return ""
    caption = _compact_string(image.get("caption")) or "论文配图"
    return (
        '<figure class="paper-blog-image" data-paper-blog-image>'
        f'<img src="../{html.escape(asset_path, quote=True)}" alt="{html.escape(caption, quote=True)}" loading="lazy">'
        f"<figcaption>{html.escape(caption)}</figcaption>"
        "</figure>"
    )


def _paper_blog_equation(lines: list[str]) -> str:
    latex = html.escape("\n".join(lines))
    return (
        '<div class="paper-blog-equation" data-paper-blog-equation>\n'
        f"$$\n{latex}\n$$\n"
        "</div>"
    )


def _paper_blog_code_block(lines: list[str], language: str) -> str:
    safe_language = re.sub(r"[^a-zA-Z0-9_+-]", "", language)[:32] or "text"
    language_attr = f' class="language-{html.escape(safe_language, quote=True)}"'
    return (
        '<div class="paper-blog-code-block" data-paper-blog-code>\n'
        '  <div class="paper-blog-code-bar">\n'
        '    <span class="paper-blog-code-dots" aria-hidden="true">'
        '<i></i><i></i><i></i></span>\n'
        f'    <span class="paper-blog-code-language">{html.escape(safe_language)}</span>\n'
        '    <button class="paper-blog-code-copy" type="button" data-paper-blog-copy>复制</button>\n'
        '  </div>\n'
        f'  <pre><code{language_attr}>{html.escape(chr(10).join(lines))}</code></pre>\n'
        '</div>'
    )


def _paper_blog_markdown(blog: dict[str, Any]) -> str:
    markdown = _multiline_string(blog.get("markdown"))
    image_refs = [
        image
        for image in blog.get("image_refs", [])
        if isinstance(image, dict) and _local_blog_asset_path(image.get("asset_path"))
    ] if isinstance(blog.get("image_refs"), list) else []
    images_by_caption: dict[str, list[dict[str, Any]]] = {}
    images_by_id: dict[str, dict[str, Any]] = {}
    for image in image_refs:
        image_id = _compact_string(image.get("image_id")).casefold()
        if image_id:
            images_by_id[image_id] = image
        caption_key = _compact_string(image.get("caption")).casefold()
        if caption_key:
            images_by_caption.setdefault(caption_key, []).append(image)
    outline = blog.get("outline") if isinstance(blog.get("outline"), dict) else {}
    section_keys = {
        _compact_string(section.get("title")).casefold(): _compact_string(section.get("section_key"))
        for section in outline.get("sections", [])
        if isinstance(section, dict) and _compact_string(section.get("title"))
    } if isinstance(outline.get("sections"), list) else {}
    used_images: set[int] = set()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_kind = ""
    list_items: list[str] = []
    code_lines: list[str] = []
    code_language = ""
    in_code = False
    math_lines: list[str] = []
    in_math = False
    explicit_images: dict[int, dict[str, Any]] = {}
    caption_offsets: dict[str, int] = {}
    for line_number, raw_line in enumerate(markdown.splitlines()):
        image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", raw_line.strip())
        if not image_match:
            continue
        caption_key = image_match.group(1).strip().casefold()
        offset = caption_offsets.get(caption_key, 0)
        candidates = images_by_caption.get(caption_key, [])
        if offset < len(candidates):
            explicit_images[line_number] = candidates[offset]
            caption_offsets[caption_key] = offset + 1

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(paragraph)
            image_markers = re.findall(r"\bimg-\d+\b", text, flags=re.IGNORECASE)
            display_text = re.sub(r"\[?\bimg-\d+\b\]?", "", text, flags=re.IGNORECASE)
            blocks.append(f"<p>{_blog_inline_markdown(display_text)}</p>")
            for image_marker in image_markers:
                image = images_by_id.get(image_marker.casefold())
                if image and id(image) not in used_images:
                    rendered = _paper_blog_image(image)
                    if rendered:
                        blocks.append(rendered)
                        used_images.add(id(image))
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_kind
        if list_items:
            blocks.append(f"<{list_kind}>" + "".join(f"<li>{item}</li>" for item in list_items) + f"</{list_kind}>")
            list_items.clear()
        list_kind = ""

    def add_section_images(section_key: str) -> None:
        for image in image_refs:
            marker = id(image)
            if marker in used_images or _compact_string(image.get("section_key")) != section_key:
                continue
            rendered = _paper_blog_image(image)
            if rendered:
                blocks.append(rendered)
                used_images.add(marker)

    for line_number, raw_line in enumerate(markdown.splitlines()):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                blocks.append(_paper_blog_code_block(code_lines, code_language))
                code_lines.clear()
                code_language = ""
                in_code = False
            else:
                code_language = re.sub(r"[^a-zA-Z0-9_+-]", "", stripped[3:].strip())[:32]
                in_code = True
            continue
        if stripped == "$$":
            flush_paragraph()
            flush_list()
            if in_math:
                blocks.append(_paper_blog_equation(math_lines))
                math_lines.clear()
                in_math = False
            else:
                in_math = True
            continue
        if in_math:
            math_lines.append(raw_line)
            continue
        if in_code:
            code_lines.append(raw_line)
            continue
        if not stripped:
            flush_paragraph()
            flush_list()
            continue
        image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            flush_paragraph()
            flush_list()
            image = explicit_images.get(line_number)
            if image and id(image) not in used_images:
                blocks.append(_paper_blog_image(image))
                used_images.add(id(image))
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            blocks.append(f"<h{level}>{_blog_inline_markdown(title)}</h{level}>")
            section_key = section_keys.get(title.casefold(), "")
            if section_key:
                add_section_images(section_key)
            continue
        unordered = re.match(r"^[-*+]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if unordered or ordered:
            flush_paragraph()
            next_kind = "ul" if unordered else "ol"
            if list_kind and list_kind != next_kind:
                flush_list()
            list_kind = next_kind
            list_items.append(_blog_inline_markdown((unordered or ordered).group(1)))
            continue
        if list_kind:
            flush_list()
        if stripped.startswith("图注："):
            continue
        paragraph.append(stripped)

    if in_code:
        blocks.append(_paper_blog_code_block(code_lines, code_language))
    if in_math:
        blocks.append(_paper_blog_equation(math_lines))
    flush_paragraph()
    flush_list()
    return "\n".join(blocks) or '<p class="empty-state">暂无深度解读正文。</p>'


def _strip_heading_number(value: str) -> str:
    return re.sub(r"^\s*\d+(?:\.\d+)*[.)、]\s*", "", value).strip()


def _blog_heading_anchor(value: str, used: set[str]) -> str:
    normalized = _strip_heading_number(html.unescape(re.sub(r"<[^>]+>", "", value))).casefold()
    pieces = re.findall(r"[\w\u4e00-\u9fff]+", normalized, flags=re.UNICODE)
    slug = "-".join(pieces)[:64].strip("-") or "section"
    anchor = slug
    index = 2
    while anchor in used:
        anchor = f"{slug}-{index}"
        index += 1
    used.add(anchor)
    return anchor


def _number_blog_headings(article_html: str) -> BlogArticleRender:
    toc: list[BlogTocItem] = []
    used: set[str] = set()
    h2_count = 0
    h3_count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal h2_count, h3_count
        level = int(match.group(1))
        attrs = match.group(2) or ""
        content = match.group(3)
        if level == 1:
            return match.group(0)
        plain_title = _strip_heading_number(html.unescape(re.sub(r"<[^>]+>", "", content))).strip()
        if not plain_title:
            return match.group(0)
        if level == 2:
            h2_count += 1
            h3_count = 0
            number = str(h2_count)
        elif level == 3 and h2_count == 0:
            h2_count += 1
            number = str(h2_count)
        elif level == 3:
            if h2_count == 0:
                h2_count = 1
            h3_count += 1
            number = f"{h2_count}.{h3_count}"
        else:
            return match.group(0)

        anchor = _blog_heading_anchor(plain_title, used)
        toc_level = 2 if level == 3 and "." not in number else level
        toc.append(BlogTocItem(toc_level, plain_title, number, anchor))
        attrs_without_id = re.sub(r"\s+id=(['\"]).*?\1", "", attrs)
        separator = "." if "." not in number else ""
        return (
            f'<h{level}{attrs_without_id} id="{html.escape(anchor, quote=True)}">'
            f"{number}{separator} {_blog_inline_markdown(plain_title)}</h{level}>"
        )

    rendered = re.sub(r"<h([123])([^>]*)>(.*?)</h\1>", replace, article_html, flags=re.S | re.I)
    return BlogArticleRender(rendered, toc)


def _paper_blog_info(blog: dict[str, Any]) -> str:
    word_count = int(blog.get("word_count") or 0)
    minutes = max(1, round(word_count / 500)) if word_count else 1
    rows = [
        ("预计阅读", f"{minutes} 分钟"),
        ("文章字数", f"{word_count:,} 字" if word_count else "未统计"),
        ("生成模型", _compact_string(blog.get("model")) or "未记录"),
        ("更新时间", _compact_string(blog.get("updated_at")) or "未记录"),
    ]
    items = "\n".join(
        "<div>"
        f"<dt>{html.escape(label)}</dt>"
        f"<dd>{html.escape(value)}</dd>"
        "</div>"
        for label, value in rows
    )
    return f"""
      <section class="paper-blog-info" aria-label="文章信息">
        <h3>文章信息</h3>
        <dl>{items}</dl>
      </section>
    """


def _paper_blog_toc(toc: list[BlogTocItem], *, info_html: str = "") -> str:
    if not toc:
        return ""
    list_id = "paper-blog-toc-list"
    items = "\n".join(
        (
            f'<a class="paper-blog-toc-link level-{item.level}" '
            f'href="#{html.escape(item.anchor, quote=True)}">'
            f'<span>{html.escape(item.number)}</span>'
            f'<b>{html.escape(item.title)}</b>'
            "</a>"
        )
        for item in toc
    )
    return f"""
      <aside class="article-aside paper-blog-aside">
      <nav class="paper-blog-toc" aria-label="深度解读目录" data-paper-blog-toc>
        <button class="paper-blog-toc-toggle" type="button" aria-expanded="true" aria-controls="{list_id}" data-paper-blog-toc-toggle>
          <span class="paper-blog-toc-toggle-icon" aria-hidden="true"></span>
          <strong>文章目录</strong>
        </button>
        <div id="{list_id}" class="paper-blog-toc-list" data-paper-blog-toc-list>{items}</div>
      </nav>
      {info_html}
      </aside>
    """


def _paper_blog_neighbor_card(label: str, paper: dict[str, Any] | None) -> str:
    if not paper:
        return (
            '<div class="neighbor-card paper-blog-neighbor is-empty">'
            f'<span class="paper-blog-neighbor-label">{html.escape(label)}</span>'
            '<span class="paper-blog-neighbor-empty">没有更多解读</span>'
            '</div>'
        )
    paper_key = _compact_string(paper.get("paper_key"))
    slug = _compact_string(paper.get("slug")) or _slug(paper_key)
    title = _compact_string(paper.get("title")) or paper_key or "下一篇解读"
    return (
        '<div class="neighbor-card paper-blog-neighbor">'
        f'<span class="paper-blog-neighbor-label">{html.escape(label)}</span>'
        f'<a href="{html.escape(slug, quote=True)}.html#deep-reading">{html.escape(title)}</a>'
        '</div>'
    )


def _paper_blog_footer(
    detail: dict[str, Any],
    previous: dict[str, Any] | None,
    next_paper: dict[str, Any] | None,
) -> str:
    fact_counts = detail.get("fact_counts") if isinstance(detail.get("fact_counts"), dict) else {}
    tags = ["深度解读"]
    for fact_type in FACT_TYPES:
        if int(fact_counts.get(fact_type) or 0) > 0:
            tags.append(FACT_TYPE_LABELS.get(fact_type, (fact_type.title(), fact_type))[1])
    tag_html = "".join(
        f'<span class="paper-blog-tag{" paper-blog-tag-accent" if index == 0 else ""}">{html.escape(tag)}</span>'
        for index, tag in enumerate(tags[:6])
    )
    return f"""
      <footer class="article-footer paper-blog-footer">
        <div class="article-tags paper-blog-tags">
          <span class="meta-label paper-blog-footer-label">标签</span>
          <div class="paper-blog-tag-list">{tag_html}</div>
        </div>
        <nav class="article-neighbors paper-blog-neighbors" aria-label="深度解读文章导航">
          {_paper_blog_neighbor_card("上一篇", previous)}
          {_paper_blog_neighbor_card("下一篇", next_paper)}
        </nav>
        <section class="comments paper-blog-comments" id="comments" aria-labelledby="paper-blog-comments-title">
          <div class="paper-blog-comments-head">
            <div>
              <p class="paper-blog-comments-kicker">COMMENTS</p>
              <h3 id="paper-blog-comments-title">读者评论</h3>
            </div>
            <span class="paper-blog-comments-count">0</span>
          </div>
          <div class="paper-blog-comments-empty">
            <strong>暂无评论</strong>
            <span>这篇解读还没有评论。</span>
          </div>
        </section>
      </footer>
    """


def _paper_blog_section(
    detail: dict[str, Any],
    *,
    previous: dict[str, Any] | None = None,
    next_paper: dict[str, Any] | None = None,
) -> str:
    blog = detail.get("blog") if isinstance(detail.get("blog"), dict) else None
    if not blog:
        return ""
    title = _compact_string(blog.get("title")) or f"{detail['title']} 深度解读"
    detail_href = f"{html.escape(_compact_string(detail.get('slug')) or detail['paper_key'])}.html"
    meta_items = [
        f"{int(blog.get('word_count') or 0)} 字",
        _compact_string(blog.get("model")),
        _compact_string(blog.get("updated_at")),
    ]
    meta = " · ".join(item for item in meta_items if item)
    article = _number_blog_headings(_paper_blog_markdown(blog))
    return f"""
    <section class="paper-blog-section" data-paper-blog-section>
      <div class="paper-blog-meta">
        <p class="eyebrow">深度解读</p>
        <h1 class="paper-blog-title">{html.escape(title)}</h1>
        <div class="paper-blog-meta-row">
          <p>{html.escape(meta)}</p>
          <a class="paper-blog-detail-link" href="{detail_href}">论文详情</a>
        </div>
      </div>
      <div class="article-layout paper-blog-layout">
        <article class="article-main paper-blog-prose">{article.html}</article>
        {_paper_blog_toc(article.toc, info_html=_paper_blog_info(blog))}
      </div>
      {_paper_blog_footer(detail, previous, next_paper)}
    </section>
    """


def _layout_safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _paper_layout_fact_rows(detail: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    facts = detail.get("facts") if isinstance(detail.get("facts"), dict) else {}
    for fact_type in ("benchmark", "dataset"):
        for fact in facts.get(fact_type, []) if isinstance(facts.get(fact_type), list) else []:
            if not isinstance(fact, dict):
                continue
            statement = _compact_string(fact.get("statement"))
            if not statement:
                continue
            rows.append(
                {
                    "kind": fact_type,
                    "statement": statement,
                    "statement_zh": _compact_string(fact.get("statement_zh")) or statement,
                    "evidence": _snippet(_compact_string(fact.get("evidence_quote")), limit=220),
                    "evidence_zh": _snippet(_compact_string(fact.get("evidence_quote_zh")), limit=220),
                }
            )
    return rows[:6]


def _paper_layout_metric(label: str, value: Any) -> str:
    return f'<span class="paper-layout-metric"><b>{html.escape(str(value))}</b><small>{html.escape(label)}</small></span>'


def _paper_layout_quality_badge(quality: str, *, evidence_kind: str = "table") -> str:
    normalized = quality if quality in {"good", "review", "fallback"} else "review"
    labels = {
        "table": {
            "good": "结构化预览",
            "review": "需要复核",
            "fallback": "文本降级",
        },
        "formula": {
            "good": "高可信公式",
            "review": "自动提取",
            "fallback": "低可信文本",
        },
    }
    label = labels.get(evidence_kind, labels["table"])[normalized]
    return f'<span class="paper-layout-quality {normalized}">{label}</span>'


def _paper_layout_formula_quality(equation: dict[str, Any]) -> str:
    latex = _compact_string(equation.get("latex"))
    malformed_command = bool(re.search(r"\\\s+[A-Za-z]", latex))
    unbalanced = latex.count("{") != latex.count("}") or latex.count("(") != latex.count(")")
    source_kind = _compact_string(equation.get("source_kind"))
    canonical_source = source_kind == "paperpipe_equations"
    try:
        normalize_formula_latex(latex)
    except FormulaOCRValidationError:
        return "fallback"
    if len(latex) < 8:
        return "fallback"
    if canonical_source:
        return "good"
    if (
        not is_likely_formula(latex)
        or malformed_command
        or unbalanced
        or latex.endswith("\\")
    ):
        return "fallback"
    try:
        score = float(equation.get("quality_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    formula_ocr_status = _compact_string(equation.get("formula_ocr_status")).lower()
    if formula_ocr_status in {"completed", "succeeded", "accepted"} and score >= 0.85:
        return "good"
    if score >= 0.65:
        return "review"
    return "fallback"


def _paper_layout_table_anchor(table: dict[str, Any]) -> str:
    block_id = _layout_safe_int(table.get("block_id"))
    if block_id:
        return f"layout-table-{block_id}"
    return f"layout-table-{_layout_safe_int(table.get('page'))}-{_layout_safe_int(table.get('block_index'))}"


def _paper_layout_formula_anchor(equation: dict[str, Any]) -> str:
    block_id = _layout_safe_int(equation.get("block_id"))
    if block_id:
        return f"layout-formula-{block_id}"
    return f"layout-formula-{_layout_safe_int(equation.get('page'))}-{_layout_safe_int(equation.get('block_index'))}"


def _paper_evidence_graph_html(detail: dict[str, Any]) -> str:
    graph = detail.get("evidence_graph") if isinstance(detail.get("evidence_graph"), dict) else {}
    facts = graph.get("facts") if isinstance(graph.get("facts"), list) else []
    evidence_rows = graph.get("evidence") if isinstance(graph.get("evidence"), list) else []
    summary = graph.get("summary") if isinstance(graph.get("summary"), dict) else {}
    evidence_by_key = {
        _compact_string(item.get("key")): item
        for item in evidence_rows
        if isinstance(item, dict) and _compact_string(item.get("key"))
    }
    layout = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    visible_equations = {
        _layout_safe_int(item.get("block_id"))
        for item in layout.get("equations", [])
        if isinstance(item, dict) and _layout_safe_int(item.get("block_id"))
    }
    visible_tables = {
        _layout_safe_int(item.get("block_id"))
        for item in layout.get("tables", [])
        if isinstance(item, dict) and _layout_safe_int(item.get("block_id"))
    }
    fact_labels = {
        "method": "方法",
        "claim": "结论",
        "limitation": "局限",
        "dataset": "数据集",
        "benchmark": "评测",
    }
    evidence_labels = {
        "layout_figure": "图像",
        "layout_table": "表格",
        "layout_equation": "公式",
    }
    method_labels = {
        "direct_provenance": "显式引用",
        "normalized_containment": "文本包含",
        "strict_token": "词元匹配",
    }
    rendered_facts: list[str] = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_type = _compact_string(fact.get("fact_type")) or "fact"
        statement = _compact_string(fact.get("statement"))
        if not statement:
            continue
        links: list[str] = []
        fact_evidence = fact.get("evidence") if isinstance(fact.get("evidence"), list) else []
        for relation in fact_evidence[:3]:
            if not isinstance(relation, dict):
                continue
            evidence_key = _compact_string(relation.get("evidence_key"))
            evidence = evidence_by_key.get(evidence_key)
            if evidence is None:
                continue
            evidence_type = _compact_string(evidence.get("evidence_type"))
            block_id = _layout_safe_int(evidence.get("block_id"))
            target = ""
            if evidence_type == "layout_equation" and block_id in visible_equations:
                target = f"layout-formula-{block_id}"
            elif evidence_type == "layout_table" and block_id in visible_tables:
                target = f"layout-table-{block_id}"
            page_number = _layout_safe_int(evidence.get("page_number"))
            source_label = evidence_labels.get(evidence_type, "证据")
            if page_number:
                source_label += f" · 第 {page_number} 页"
            method = method_labels.get(
                _compact_string(relation.get("match_method")),
                _compact_string(relation.get("match_method")) or "自动关联",
            )
            try:
                score = float(relation.get("score") or 0)
            except (TypeError, ValueError):
                score = 0.0
            preview = _snippet(_compact_string(evidence.get("preview")), limit=180) or source_label
            content = (
                f'<span class="paper-evidence-link-meta"><b>{html.escape(source_label)}</b>'
                f'<small>{html.escape(method)} · {score:.2f}</small></span>'
                f'<span class="paper-evidence-preview">{html.escape(preview)}</span>'
            )
            if target:
                links.append(
                    f'<li><a class="paper-evidence-link" href="#{html.escape(target)}">{content}</a></li>'
                )
            else:
                links.append(f'<li><div class="paper-evidence-reference">{content}</div></li>')
        try:
            confidence = float(fact.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0.0
        relation_html = (
            f'<ul class="paper-evidence-links">{"".join(links)}</ul>'
            if links
            else '<p class="paper-evidence-unlinked">尚未找到满足阈值的版面证据</p>'
        )
        rendered_facts.append(
            f"""
            <article class="paper-evidence-fact-row">
              <div class="paper-evidence-fact-meta">
                <span class="fact-chip {html.escape(fact_type)}">{html.escape(fact_labels.get(fact_type, fact_type))}</span>
                <span>{confidence:.2f}</span>
              </div>
              <p>{html.escape(statement)}</p>
              {relation_html}
            </article>
            """
        )
    metrics = (
        _paper_layout_metric("facts", _layout_safe_int(summary.get("fact_count")))
        + _paper_layout_metric("evidence", _layout_safe_int(summary.get("evidence_count")))
        + _paper_layout_metric("links", _layout_safe_int(summary.get("supported_relation_count")))
    )
    return f"""
    <section id="evidence-relations" class="paper-layout-panel paper-evidence-graph">
      <div class="paper-layout-panel-head">
        <p class="eyebrow">证据关系</p>
        <h2>Facts to evidence</h2>
      </div>
      <div class="paper-layout-compact paper-evidence-graph-summary">{metrics}</div>
      <div class="paper-evidence-facts">{''.join(rendered_facts)}</div>
      {'' if rendered_facts else '<p class="empty-state">暂无可展示的事实与版面证据关联。</p>'}
    </section>
    """


def _paper_layout_experiment_html(detail: dict[str, Any]) -> str:
    facts = _paper_layout_fact_rows(detail)
    evidence = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    tables = evidence.get("tables") if isinstance(evidence.get("tables"), list) else []
    result_tables = [
        table
        for table in tables
        if isinstance(table, dict)
        and any(token in _compact_string(table.get("caption")).lower() for token in ("result", "benchmark", "evaluation", "ablation", "score"))
    ][:2]
    fact_html = "".join(
        f"""
        <li>
          <span class="fact-chip {html.escape(row['kind'])}">{html.escape(row['kind'])}</span>
          {_lang_paragraph(row['statement'], row['statement_zh'])}
          <blockquote>{_lang_text(row['evidence'] or 'No evidence quote captured.', row['evidence_zh'] or row['evidence'] or 'No evidence quote captured.', tag='span')}</blockquote>
        </li>
        """
        for row in facts
    )
    table_html = "".join(
        f"""
        <li>
          <span class="paper-layout-source">Table · {html.escape(_compact_string(table.get('source_reference')))}</span>
          <p>{html.escape(_snippet(_compact_string(table.get('caption')), limit=220) or 'Result table detected by layout parser.')}</p>
          <a class="paper-layout-jump" href="#{html.escape(_paper_layout_table_anchor(table))}">查看表格证据</a>
        </li>
        """
        for table in result_tables
    )
    return f"""
    <section class="paper-layout-panel paper-layout-experiments">
      <div class="paper-layout-panel-head">
        <p class="eyebrow">实验与评测</p>
        <h2>Experiments</h2>
      </div>
      <ul class="paper-layout-list">{fact_html}{table_html or ''}</ul>
      {'' if (fact_html or table_html) else '<p class="empty-state">暂无结构化实验、数据集或 benchmark 证据。</p>'}
    </section>
    """


def _paper_layout_equations_html(detail: dict[str, Any]) -> str:
    evidence = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    equations = evidence.get("equations") if isinstance(evidence.get("equations"), list) else []
    rows = []
    for equation in equations[:6]:
        if not isinstance(equation, dict):
            continue
        latex = _compact_string(equation.get("latex"))
        if not latex:
            continue
        quality = _paper_layout_formula_quality(equation)
        if quality == "fallback":
            continue
        role = _compact_string(equation.get("role")) or "formula"
        rows.append(
            f"""
            <article id="{html.escape(_paper_layout_formula_anchor(equation))}" class="paper-layout-code-card">
              <div class="paper-layout-code-head">
                <strong>{html.escape(_compact_string(equation.get('equation_id')) or 'equation')}</strong>
                <span>{html.escape(_compact_string(equation.get('source_reference')))}</span>
              </div>
              <div class="paper-layout-card-meta">
                {_paper_layout_quality_badge(quality, evidence_kind='formula')}
                <span>{html.escape(role)}</span>
              </div>
              <div class="paper-layout-formula" aria-label="{html.escape(latex)}">\\[{html.escape(latex)}\\]</div>
              <details class="paper-layout-raw">
                <summary>原始 LaTeX</summary>
                <pre><code>{html.escape(latex)}</code></pre>
              </details>
            </article>
            """
        )
    return f"""
    <section class="paper-layout-panel">
      <div class="paper-layout-panel-head">
        <p class="eyebrow">公式</p>
        <h2>Formulas</h2>
      </div>
      <div class="paper-layout-code-grid">{''.join(rows)}</div>
      {'' if rows else '<p class="empty-state">暂无可展示的高质量公式识别结果。</p>'}
    </section>
    """


def _paper_layout_tables_html(detail: dict[str, Any]) -> str:
    evidence = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    tables = evidence.get("tables") if isinstance(evidence.get("tables"), list) else []
    rows = []
    for table in tables[:4]:
        if not isinstance(table, dict):
            continue
        table_markdown = _compact_string(table.get("table_markdown"))
        caption = _compact_string(table.get("caption"))
        if not table_markdown and not caption:
            continue
        shape = f"{_layout_safe_int(table.get('row_count'))} x {_layout_safe_int(table.get('column_count'))}"
        raw_rows = table.get("table_rows") if isinstance(table.get("table_rows"), list) else []
        safe_rows: list[list[str]] = []
        for raw_row in raw_rows[:12]:
            if not isinstance(raw_row, list):
                continue
            cells = [_compact_string(cell)[:160] for cell in raw_row[:12]]
            if any(cells):
                safe_rows.append(cells)
        quality = _compact_string(table.get("display_quality"))
        if quality not in {"good", "review", "fallback"}:
            quality = "good" if len(safe_rows) >= 2 and _layout_safe_int(table.get("column_count")) >= 2 else "fallback"
        table_preview = ""
        if len(safe_rows) >= 2:
            header = "".join(f'<th scope="col">{html.escape(cell)}</th>' for cell in safe_rows[0])
            body = "".join(
                "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
                for row in safe_rows[1:]
            )
            table_preview = f"""
              <div class="paper-layout-table-wrap" tabindex="0" aria-label="结构化表格预览">
                <table class="paper-layout-data-table">
                  <thead><tr>{header}</tr></thead>
                  <tbody>{body}</tbody>
                </table>
              </div>
              {'<p class="paper-layout-preview-note">仅显示前 12 行、12 列，完整结构可在管理台证据检查器查看。</p>' if table.get('preview_truncated') else ''}
            """
        else:
            table_preview = f'<pre class="paper-layout-table-fallback"><code>{html.escape(table_markdown or caption)}</code></pre>'
        method = _compact_string(table.get("reconstruction_method")) or "unknown"
        rows.append(
            f"""
            <article id="{html.escape(_paper_layout_table_anchor(table))}" class="paper-layout-code-card paper-layout-table-card">
              <div class="paper-layout-code-head">
                <strong>{html.escape(shape)}</strong>
                <span>{html.escape(_compact_string(table.get('source_reference')))}</span>
              </div>
              <div class="paper-layout-card-meta">
                {_paper_layout_quality_badge(quality)}
                <span>{html.escape(method)}</span>
              </div>
              {f'<p>{html.escape(_snippet(caption, limit=260))}</p>' if caption else ''}
              {table_preview}
            </article>
            """
        )
    return f"""
    <section class="paper-layout-panel">
      <div class="paper-layout-panel-head">
        <p class="eyebrow">表格</p>
        <h2>Tables</h2>
      </div>
      <div class="paper-layout-code-grid">{''.join(rows)}</div>
      {'' if rows else '<p class="empty-state">暂无可展示的结构化表格重建结果。</p>'}
    </section>
    """


def _paper_layout_status_html(detail: dict[str, Any]) -> str:
    evidence = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    ocr = evidence.get("ocr") if isinstance(evidence.get("ocr"), dict) else {}
    formula_ocr = evidence.get("formula_ocr") if isinstance(evidence.get("formula_ocr"), dict) else {}
    latest_run = evidence.get("latest_run") if isinstance(evidence.get("latest_run"), dict) else {}
    metrics = [
        _paper_layout_metric("pages", _layout_safe_int(summary.get("page_count"))),
        _paper_layout_metric("blocks", _layout_safe_int(summary.get("block_count"))),
        _paper_layout_metric("formulas", _layout_safe_int(summary.get("equation_blocks"))),
        _paper_layout_metric("tables", _layout_safe_int(summary.get("structured_table_blocks"))),
        _paper_layout_metric("ocr blocks", _layout_safe_int(ocr.get("block_count"))),
        _paper_layout_metric("formula OCR", _layout_safe_int(formula_ocr.get("blocks_succeeded"))),
    ]
    status_items = [
        ("Run", _compact_string(latest_run.get("status")) or "not parsed"),
        ("Document", _compact_string(summary.get("document_type")) or "unknown"),
        ("OCR", f"{_compact_string(ocr.get('mode')) or 'off'} · {_layout_safe_int(ocr.get('pages_succeeded'))}/{_layout_safe_int(ocr.get('pages_attempted'))} pages"),
        ("Formula OCR", f"{_compact_string(formula_ocr.get('mode')) or 'off'} · {_layout_safe_int(formula_ocr.get('blocks_succeeded'))} accepted"),
    ]
    return f"""
    <section class="paper-layout-panel">
      <div class="paper-layout-panel-head">
        <p class="eyebrow">OCR / Layout</p>
        <h2>Parsing status</h2>
      </div>
      <div class="paper-layout-metrics">{''.join(metrics)}</div>
      <dl class="paper-layout-status">
        {''.join(f'<div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>' for label, value in status_items)}
      </dl>
    </section>
    """


def _paper_layout_evidence_html(detail: dict[str, Any]) -> str:
    evidence = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    if not evidence:
        return """
        <section class="paper-layout-suite">
          <section class="paper-layout-panel">
            <div class="paper-layout-panel-head">
              <p class="eyebrow">Layout v2</p>
              <h2>结构化解析</h2>
            </div>
            <p class="empty-state">这篇论文还没有可展示的 layout/OCR/公式/表格解析结果。</p>
          </section>
        </section>
        """
    return (
        '<section class="paper-layout-suite" aria-label="Layout evidence">'
        f"{_paper_layout_experiment_html(detail)}"
        f"{_paper_evidence_graph_html(detail)}"
        f"{_paper_layout_equations_html(detail)}"
        f"{_paper_layout_tables_html(detail)}"
        f"{_paper_layout_status_html(detail)}"
        "</section>"
    )


def _paper_layout_compact_html(detail: dict[str, Any]) -> str:
    evidence = detail.get("layout_evidence") if isinstance(detail.get("layout_evidence"), dict) else {}
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    if not evidence:
        return '<p class="empty-state">No layout evidence exported yet.</p>'
    return (
        '<div class="paper-layout-compact">'
        f"{_paper_layout_metric('formulas', _layout_safe_int(summary.get('equation_blocks')))}"
        f"{_paper_layout_metric('tables', _layout_safe_int(summary.get('structured_table_blocks')))}"
        f"{_paper_layout_metric('evidence', _layout_safe_int(summary.get('high_quality_evidence_blocks')))}"
        "</div>"
    )


def _paper_detail_page(
    paper: dict[str, Any],
    *,
    previous: dict[str, Any] | None = None,
    next_paper: dict[str, Any] | None = None,
) -> str:
    detail = _paper_detail_payload(paper)
    authors = ", ".join(detail["authors"]) or "Unknown authors"
    arxiv = ""
    if detail["arxiv_id"]:
        arxiv_id = html.escape(detail["arxiv_id"])
        arxiv = (
            f'<a class="meta-icon-link arxiv-paper-link" href="https://arxiv.org/abs/{arxiv_id}" '
            f'aria-label="arXiv paper: {arxiv_id}" title="arXiv {arxiv_id}" rel="noopener noreferrer" target="_blank">'
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<path d="M7.15 4.1h9.7c1.18 0 2.15.97 2.15 2.15v11.5c0 1.18-.97 2.15-2.15 2.15h-9.7A2.15 2.15 0 0 1 5 17.75V6.25C5 5.07 5.97 4.1 7.15 4.1Zm.25 2.15v11.5h9.2V6.25H7.4Z"/>'
            '<path d="M8.82 15.7 11.24 12 8.94 8.3h1.88l1.37 2.37 1.45-2.37h1.74l-2.32 3.56 2.42 3.84h-1.89l-1.47-2.53-1.55 2.53H8.82Z"/>'
            "</svg>"
            "</a>"
        )
    primary_code_link = detail.get("primary_code_link")
    code_link = ""
    if isinstance(primary_code_link, dict) and primary_code_link.get("url"):
        code_label = _compact_string(primary_code_link.get("repo")) or "Code"
        code_href = html.escape(_compact_string(primary_code_link["url"]))
        code_label_escaped = html.escape(code_label)
        code_link = (
            f'<a class="meta-icon-link github-code-link" href="{code_href}" '
            f'aria-label="GitHub repository: {code_label_escaped}" title="{code_label_escaped}" rel="noopener noreferrer" target="_blank">'
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.52 2.87 8.35 6.84 9.71.5.09.68-.22.68-.49 0-.24-.01-1.04-.01-1.89-2.78.62-3.37-1.22-3.37-1.22-.45-1.19-1.11-1.5-1.11-1.5-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.89 1.56 2.34 1.11 2.91.85.09-.66.35-1.11.63-1.37-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.31.1-2.72 0 0 .84-.28 2.75 1.05A9.33 9.33 0 0 1 12 6.93c.85 0 1.7.12 2.5.35 1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.46.1 2.72.64.72 1.03 1.64 1.03 2.76 0 3.95-2.34 4.82-4.57 5.08.36.32.68.94.68 1.9 0 1.37-.01 2.47-.01 2.81 0 .27.18.59.69.49A10.04 10.04 0 0 0 22 12.25C22 6.58 17.52 2 12 2Z"/>'
            "</svg>"
            "</a>"
        )
    meta_icons = []
    if arxiv:
        meta_icons.append(arxiv)
    if code_link:
        meta_icons.append(code_link)
    meta_html = html.escape(authors)
    if meta_icons:
        meta_html += '<span class="meta-icon-group">' + "".join(meta_icons) + "</span>"
    detail_date_label = _compact_string(detail.get("date_label"))
    if detail_date_label:
        meta_html += f' · <span class="paper-dates">📅 {html.escape(detail_date_label)}</span>'
    def fact_sections_html(anchor_prefix: str) -> str:
        sections = []
        for index, fact_type in enumerate(FACT_TYPES):
            fact_rows = []
            for fact in detail["facts"].get(fact_type, []):
                confidence = fact.get("confidence")
                conf_class = "low"
                if isinstance(confidence, (int, float)) and confidence >= 0.9:
                    conf_class = "high"
                elif isinstance(confidence, (int, float)) and confidence >= 0.7:
                    conf_class = "mid"
                fact_rows.append(
                    f"""
                    <li class="fact-row">
                      <div><span class="fact-chip {fact_type}">{fact_type}</span><strong class="confidence {conf_class}">{html.escape(str(confidence or 'n/a'))}</strong></div>
                      {_lang_paragraph(fact['statement'], fact.get('statement_zh') or fact['statement'])}
                      <blockquote>{_lang_text(fact['evidence_quote'] or 'No evidence quote captured.', fact.get('evidence_quote_zh') or fact['evidence_quote'] or 'No evidence quote captured.', tag='span')}</blockquote>
                    </li>
                    """
                )
            label_en, label_zh = FACT_TYPE_LABELS.get(fact_type, (fact_type.title(), fact_type))
            sections.append(
                f"""
                <section id="{html.escape(anchor_prefix)}-{html.escape(fact_type)}" class="paper-fact-section" data-fact-section="{html.escape(fact_type)}"{' hidden' if index else ''}>
                  <div class="paper-fact-section-head">
                    <h2>{_lang_text(label_en, label_zh, tag='span')}</h2>
                    <span>{len(detail["facts"].get(fact_type, []))}</span>
                  </div>
                  <ul>{''.join(fact_rows) or '<li class="empty-state">No facts in this category.</li>'}</ul>
                </section>
                """
            )
        return f'<div class="paper-fact-sections">{"".join(sections)}</div>'
    cover = ""
    if detail.get("cover_path"):
        cover = (
            '<div class="paper-hero-cover">'
            f'<img class="paper-hero-image" src="../{html.escape(detail["cover_path"])}" alt="{html.escape(detail["title"])} cover">'
            "</div>"
        )
    summary_block = ""
    if detail.get("summary_full_en") or detail.get("summary_full_zh"):
        summary_block = (
            '<section class="paper-summary-block">'
            '<p class="eyebrow">完整摘要</p>'
            '<h2>Summary</h2>'
            f'{_lang_markdown(detail.get("summary_full_en") or detail["tldr"] or "No summary available yet.", detail.get("summary_full_zh") or detail.get("tldr_full_zh") or detail.get("summary_full_en") or detail["tldr"], cls="paper-summary-prose", strip_paper_structure=True)}'
            "</section>"
        )
    blog_section = _paper_blog_section(detail, previous=previous, next_paper=next_paper)
    blog_tab = (
        '<button id="paper-tab-deep-reading" type="button" role="tab" data-paper-mode-button="deep-reading" '
        'aria-controls="paper-deep-reading" aria-selected="false" aria-pressed="false" tabindex="-1">深度解读</button>'
        if blog_section else ""
    )
    blog_mode = (
        '<article id="paper-deep-reading" class="paper-mode paper-mode-deep-reading" '
        'data-paper-mode="deep-reading" role="tabpanel" aria-labelledby="paper-tab-deep-reading" hidden>'
        f"{blog_section}</article>"
        if blog_section else ""
    )
    layout_evidence = _paper_layout_evidence_html(detail)
    layout_compact = _paper_layout_compact_html(detail)
    def fact_count_cards(anchor_prefix: str) -> str:
        cards = []
        for fact_type in FACT_TYPES:
            label_en, label_zh = FACT_TYPE_NAV_LABELS.get(fact_type, FACT_TYPE_LABELS.get(fact_type, (fact_type.title(), fact_type)))
            count = len(detail["facts"].get(fact_type, []))
            cards.append(
                f'<button class="paper-fact-stat" type="button" data-paper-fact-button="{html.escape(fact_type)}" '
                f'data-paper-fact-target="{html.escape(anchor_prefix)}-{html.escape(fact_type)}" '
                f'aria-pressed="{str(fact_type == FACT_TYPES[0]).lower()}" onclick="return window.aiResearchSelectFactPanel(this)">'
                f'{_lang_text(label_en, label_zh, tag="span")}'
                f"<strong>{count}</strong>"
                "</button>"
            )
        return "".join(cards)
    cover_style = ""
    if detail.get("cover_path"):
        cover_style = f' style="--paper-cover-image: url(../{html.escape(detail["cover_path"])});"'
    deep_reading_anchor = '<span id="deep-reading" class="paper-deep-reading-anchor" aria-hidden="true"></span>' if blog_section else ""
    deep_reading_bar = (
        '<div class="paper-detail-deep-reading-bar" data-paper-deep-reading-only-label="深度解读">'
        '<a class="paper-detail-deep-reading-back" href="'
        f'{html.escape(_compact_string(detail.get("slug")) or detail["paper_key"])}.html'
        '">论文详情</a>'
        '<span>深度解读</span>'
        "</div>"
        if blog_section else ""
    )
    body = f"""
    <section class="paper-detail paper-detail-mode-shell" data-paper-detail-view>
      {deep_reading_anchor}
      <div class="paper-detail-topbar">
        <a class="back-link" href="index.html">Back to papers</a>
        {deep_reading_bar}
        <div class="paper-mode-toggle" role="tablist" aria-label="Paper detail views">
          <button id="paper-tab-workbench" type="button" role="tab" data-paper-mode-button="workbench" aria-controls="paper-workbench" aria-selected="true" aria-pressed="true" tabindex="0">Workbench</button>
          <button id="paper-tab-immersive" type="button" role="tab" data-paper-mode-button="immersive" aria-controls="paper-immersive" aria-selected="false" aria-pressed="false" tabindex="-1">Immersive</button>
          {blog_tab}
        </div>
      </div>

      <article id="paper-workbench" class="paper-mode paper-mode-workbench" data-paper-mode="workbench" role="tabpanel" aria-labelledby="paper-tab-workbench">
        <aside class="paper-workbench-sidebar">
          <p class="eyebrow">{html.escape(detail['paper_key'])} · {html.escape(str(detail['year'] or 'n.d.'))}</p>
          <h1 class="paper-detail-title">{html.escape(detail['title'])}</h1>
          <p class="paper-meta paper-detail-meta">{meta_html}</p>
          {_lang_paragraph(detail['tldr'] or 'No short summary available yet.', detail.get('tldr_zh') or detail['tldr'], cls='paper-side-abstract')}
          <div class="paper-fact-stats" aria-label="Fact section navigation">{fact_count_cards("workbench")}</div>
        </aside>
        <main class="paper-workbench-main">
          {cover}
          {fact_sections_html("workbench")}
          {layout_evidence}
        </main>
        <aside class="paper-workbench-aside">
          {summary_block}
        </aside>
      </article>

      <article id="paper-immersive" class="paper-mode paper-mode-immersive" data-paper-mode="immersive" role="tabpanel" aria-labelledby="paper-tab-immersive" hidden>
        <section class="paper-immersive-stage"{cover_style}>
          <div class="paper-immersive-content">
            <p class="eyebrow">{html.escape(detail['paper_key'])} · {html.escape(str(detail['year'] or 'n.d.'))}</p>
            <h1 class="paper-detail-title">{html.escape(detail['title'])}</h1>
            <p class="paper-meta paper-detail-meta">{meta_html}</p>
            {_lang_paragraph(detail['tldr'] or 'No short summary available yet.', detail.get('tldr_zh') or detail['tldr'], cls='lead')}
            <div class="paper-fact-stats" aria-label="Fact section navigation">{fact_count_cards("immersive")}</div>
          </div>
        </section>
        <section class="paper-immersive-evidence">
          <div>
            <p class="eyebrow">Evidence</p>
            {_lang_markdown(detail.get("summary_full_en") or detail.get("summary_en") or detail["tldr"] or "No summary available yet.", detail.get("summary_full_zh") or detail.get("tldr_full_zh") or detail.get("summary_full_en") or detail.get("summary_en") or detail["tldr"], cls="paper-evidence-summary", strip_paper_structure=True)}
            {layout_compact}
          </div>
          <div class="paper-immersive-evidence-main">
            {fact_sections_html("immersive")}
          </div>
        </section>
      </article>
      {blog_mode}
    </section>
    """
    return _page_shell(title=f"{detail['title']} / AIResearch", body=body, current="papers", depth=1)


def _clusters_page(clusters: list[dict[str, Any]]) -> str:
    summaries = sorted((_cluster_summary(cluster) for cluster in clusters), key=lambda item: item["fact_count"], reverse=True)
    cards = "\n".join(_cluster_card(summary, prefix="../") for summary in summaries[:300])
    body = f"""
    <section class="page-heading"><p class="eyebrow">知识聚落</p><h1>Clusters</h1><p>相似的方法自然聚集，形成可辨识的研究脉络。</p></section>
    <section class="cluster-grid">{cards or '<p class="empty-state">No clusters available.</p>'}</section>
    """
    return _page_shell(title="Clusters / AIResearch", body=body, current="clusters", depth=1)


def _cluster_detail_page(cluster: dict[str, Any], papers: list[dict[str, Any]]) -> str:
    summary = _cluster_summary(cluster)
    facts = cluster.get("facts", []) if isinstance(cluster.get("facts"), list) else []
    paper_lookup = {_paper_summary(paper)["paper_key"]: _paper_summary(paper) for paper in papers}
    facts_by_paper: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        paper_key = _compact_string(fact.get("paper_key"))
        if paper_key:
            facts_by_paper.setdefault(paper_key, []).append(fact)

    def cluster_paper_card(paper_key: str, paper_facts: list[dict[str, Any]]) -> str:
        paper_summary = paper_lookup.get(paper_key)
        if paper_summary is None:
            paper_summary = {
                "paper_key": paper_key,
                "title": paper_key,
                "authors": [],
                "year": 0,
                "tldr": "No paper summary available yet.",
                "tldr_zh": "",
                "detail_path": f"papers/{_slug(paper_key)}.html",
                "cover_path": "",
            }
        authors = ", ".join(paper_summary["authors"][:3]) or "Unknown authors"
        cover = '<div class="paper-cover-wrap paper-cover-empty" aria-hidden="true"></div>'
        if paper_summary.get("cover_path"):
            cover = (
                '<div class="paper-cover-wrap">'
                f'<img class="paper-cover" src="../{html.escape(paper_summary["cover_path"])}" alt="{html.escape(paper_summary["title"])} cover" loading="lazy">'
                "</div>"
            )
        fact_items = "".join(
            f'<li>{_lang_paragraph(_compact_string(fact.get("statement")) or "No cluster-specific statement captured.", _compact_string(fact.get("statement_zh")) or _compact_string(fact.get("statement")) or "No cluster-specific statement captured.")}</li>'
            for fact in paper_facts
        )
        return f"""
        <article class="paper-card cluster-paper-card reveal">
          {cover}
          <div class="paper-card-body">
            <div class="paper-card-head">
              <a class="paper-title" href="../{html.escape(paper_summary['detail_path'])}">{html.escape(paper_summary['title'])}</a>
              <a class="detail-link" href="../{html.escape(paper_summary['detail_path'])}">Detail</a>
            </div>
            <p class="paper-meta">{html.escape(authors)} · {html.escape(str(paper_summary['year'] or 'n.d.'))} · {html.escape(paper_key)}</p>
            {_lang_paragraph(paper_summary.get('tldr') or 'No short summary available yet.', paper_summary.get('tldr_zh') or paper_summary.get('tldr') or 'No short summary available yet.')}
            <div class="cluster-evidence">
              <span class="fact-chip {html.escape(summary['fact_type'])}">{html.escape(summary['fact_type'])}</span>
              <ul>{fact_items}</ul>
            </div>
          </div>
        </article>
        """

    rows = "".join(
        cluster_paper_card(paper_key, paper_facts)
        for paper_key, paper_facts in sorted(facts_by_paper.items(), key=lambda item: item[0])
    )
    body = f"""
    <section class="paper-detail">
      <a class="back-link" href="index.html">Back to clusters</a>
      <p class="eyebrow">{html.escape(summary['cluster_id'])}</p>
      <h1>{html.escape(summary['title'])}</h1>
      <p class="lead">{summary['fact_count']} facts across {summary['paper_count']} papers. Average confidence {summary['average_confidence']:.2f}.</p>
      <section class="cluster-paper-list">{rows or '<p class="empty-state">No facts available.</p>'}</section>
    </section>
    """
    return _page_shell(title=f"{summary['title']} / AIResearch", body=body, current="clusters", depth=1)


def _research_graph_payload(payloads: dict[str, Any], papers: list[dict[str, Any]]) -> dict[str, Any]:
    map_payload = payloads.get("map")
    paper_lookup = {_paper_summary(paper)["paper_key"]: _paper_summary(paper) for paper in papers}
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()

    def add_node(node: dict[str, Any]) -> None:
        current = nodes.get(node["id"])
        if current is None or int(node.get("size", 1)) > int(current.get("size", 1)):
            nodes[node["id"]] = node

    if isinstance(map_payload, dict) and isinstance(map_payload.get("sections"), list):
        for section in map_payload["sections"]:
            if not isinstance(section, dict):
                continue
            fact_type = _compact_string(section.get("fact_type")) or "fact"
            items = section.get("items", [])
            if not isinstance(items, list):
                continue
            ranked_items = sorted(
                [item for item in items if isinstance(item, dict)],
                key=lambda item: (int(item.get("paper_count") or 0), int(item.get("fact_count") or 0)),
                reverse=True,
            )[:12]
            for item in ranked_items:
                topic_key = _compact_string(item.get("key") or item.get("label"))
                if not topic_key:
                    continue
                topic_id = f"topic:{_slug(fact_type)}:{_slug(topic_key)[:48]}"
                topic_label = _snippet(_compact_string(item.get("label") or topic_key), limit=96)
                topic_size = max(1, int(item.get("fact_count") or 1))
                add_node(
                    {
                        "id": topic_id,
                        "kind": "topic",
                        "group": fact_type,
                        "label": topic_label,
                        "size": topic_size,
                        "subtitle": f"{int(item.get('paper_count') or 0)} papers / {topic_size} facts",
                    }
                )
                item_papers = item.get("papers", [])
                if not isinstance(item_papers, list):
                    continue
                for item_paper in item_papers[:8]:
                    if not isinstance(item_paper, dict):
                        continue
                    paper_key = _compact_string(item_paper.get("paper_key"))
                    if not paper_key:
                        continue
                    paper_summary = paper_lookup.get(paper_key)
                    title = _compact_string(item_paper.get("title")) or (paper_summary or {}).get("title", paper_key)
                    paper_id = f"paper:{paper_key}"
                    add_node(
                        {
                            "id": paper_id,
                            "kind": "paper",
                            "group": "paper",
                            "label": _snippet(title, limit=84),
                            "size": int((paper_summary or {}).get("fact_count", 1)) or 1,
                            "subtitle": f"{paper_key} · {item_paper.get('year') or (paper_summary or {}).get('year') or 'n.d.'}",
                            "url": f"../papers/{_slug(paper_key)}.html",
                        }
                    )
                    edge_key = (topic_id, paper_id)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({"source": topic_id, "target": paper_id, "weight": 1, "group": fact_type})

    return {
        "nodes": sorted(nodes.values(), key=lambda node: (node["kind"], node["group"], node["label"]))[:180],
        "edges": edges[:360],
    }


def _starmap_payload(payloads: dict[str, Any], papers: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    cluster_lookup: dict[str, dict[str, Any]] = {}
    paper_cluster_ids: dict[str, str] = {}
    for index, cluster in enumerate(clusters[:24]):
        summary = _cluster_summary(cluster)
        cluster_id = summary["cluster_id"] or f"cluster_{index + 1}"
        cluster_lookup[cluster_id] = {
            "id": cluster_id,
            "label": summary["title"],
            "label_en": summary["title"],
            "label_zh": summary["title"],
            "color": ["#d4a957", "#5ba3b3", "#7d7cf2", "#4ca56b", "#d17f65", "#9d7fd1"][index % 6],
            "papers": [],
        }
        for fact in cluster.get("facts", []) if isinstance(cluster.get("facts"), list) else []:
            if not isinstance(fact, dict):
                continue
            paper_key = _compact_string(fact.get("paper_key"))
            if paper_key and paper_key not in paper_cluster_ids:
                paper_cluster_ids[paper_key] = cluster_id
                cluster_lookup[cluster_id]["papers"].append(paper_key)

    asset_lookup = _paper_assets_lookup(payloads)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    paper_nodes: dict[str, dict[str, Any]] = {}
    author_nodes: set[str] = set()
    id_to_paper: dict[str, str] = {}
    title_to_paper: dict[str, str] = {}

    for paper in papers:
        summary = _paper_summary(paper)
        paper_key = summary["paper_key"]
        cluster_id = paper_cluster_ids.get(paper_key, "unclustered")
        if cluster_id not in cluster_lookup:
            cluster_lookup[cluster_id] = {
                "id": cluster_id,
                "label": "Unclustered",
                "label_en": "Unclustered",
                "label_zh": "未聚类",
                "color": "#7f8a96",
                "papers": [],
            }
        if paper_key not in cluster_lookup[cluster_id]["papers"]:
            cluster_lookup[cluster_id]["papers"].append(paper_key)
        asset = asset_lookup.get(paper_key, {})
        ids = asset.get("ids", {}) if isinstance(asset.get("ids"), dict) else summary.get("ids", {})
        arxiv_id = _compact_string(ids.get("arxiv_id")) if isinstance(ids, dict) else ""
        if arxiv_id:
            id_to_paper[arxiv_id.replace(".", "_")] = paper_key
            id_to_paper[arxiv_id] = paper_key
        title_to_paper[summary["title"].lower()] = paper_key
        node = {
            "id": f"paper:{paper_key}",
            "kind": "paper",
            "group": cluster_id,
            "paper_key": paper_key,
            "label": summary["title"],
            "label_en": summary["title"],
            "label_zh": summary.get("title_zh") or summary["title"],
            "year": summary["year"],
            "size": max(6, min(22, summary["fact_count"] + 5)),
            "fact_count": summary["fact_count"],
            "url": f"../papers/{summary['slug']}.html",
            "authors": summary["authors"],
            "tldr": summary["tldr"],
            "tldr_zh": summary.get("tldr_zh") or summary["tldr"],
            "cover_path": f"../{summary['cover_path']}" if summary.get("cover_path") else "",
            "cluster_id": cluster_id,
        }
        paper_nodes[paper_key] = node
        nodes.append(node)

    for paper in papers:
        summary = _paper_summary(paper)
        paper_id = f"paper:{summary['paper_key']}"
        for author in summary["authors"][:8]:
            author_key = _slug(author)[:48]
            author_id = f"author:{author_key}"
            if author_id not in author_nodes:
                nodes.append(
                    {
                        "id": author_id,
                        "kind": "author",
                        "group": "author",
                        "label": author,
                        "label_en": author,
                        "label_zh": author,
                        "size": 5,
                    }
                )
                author_nodes.add(author_id)
            edge_key = (paper_id, author_id, "author")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({"source": paper_id, "target": author_id, "type": "author", "weight": 1})
        for fact in _fact_items(paper):
            fact_type = _compact_string(fact.get("fact_type"))
            if fact_type not in {"method", "dataset"}:
                continue
            fact_key = _slug(_compact_string(fact.get("name") or fact.get("statement")))[:48]
            if not fact_key:
                continue
            target_id = f"{fact_type}:{fact_key}"
            if not any(node["id"] == target_id for node in nodes):
                nodes.append(
                    {
                        "id": target_id,
                        "kind": fact_type,
                        "group": fact_type,
                        "label": _snippet(_compact_string(fact.get("name") or fact.get("statement")), limit=56),
                        "label_en": _snippet(_compact_string(fact.get("name") or fact.get("statement")), limit=56),
                        "label_zh": _snippet(_compact_string(fact.get("name") or fact.get("statement")), limit=56),
                        "size": 5,
                    }
                )
            edge_key = (paper_id, target_id, fact_type)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({"source": paper_id, "target": target_id, "type": fact_type, "weight": 1})

    for paper_key, paper_node in paper_nodes.items():
        asset = asset_lookup.get(paper_key, {})
        citation_keys = asset.get("citation_keys", []) if isinstance(asset.get("citation_keys"), list) else []
        for citation_key in citation_keys[:24]:
            normalized = _compact_string(citation_key)
            target_paper = id_to_paper.get(normalized) or id_to_paper.get(normalized.replace(".", "_")) or title_to_paper.get(normalized.lower())
            if not target_paper or target_paper == paper_key or target_paper not in paper_nodes:
                continue
            edge_key = (paper_node["id"], paper_nodes[target_paper]["id"], "citation")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({"source": paper_node["id"], "target": paper_nodes[target_paper]["id"], "type": "citation", "weight": 1})

    return {
        "clusters": list(cluster_lookup.values())[:24],
        "nodes": nodes[:420],
        "edges": edges[:840],
    }


def _starmap_page(payload: dict[str, Any]) -> str:
    cluster_count = len(payload.get("clusters", [])) if isinstance(payload.get("clusters"), list) else 0
    node_count = len(payload.get("nodes", [])) if isinstance(payload.get("nodes"), list) else 0
    edge_count = len(payload.get("edges", [])) if isinstance(payload.get("edges"), list) else 0
    body = f"""
    <section class="page-heading">
      <p class="eyebrow">星云星图</p>
      <h1>Starmap</h1>
      <p>每颗星是一篇论文，星云是一个方向，连线是它们的命运。</p>
    </section>
    <section class="starmap-shell" data-starmap-source="../api/starmap.json">
      <aside class="starmap-sidebar">
        <div class="map-stats">
          <span><strong>{cluster_count}</strong> clusters</span>
          <span><strong>{node_count}</strong> nodes</span>
          <span><strong>{edge_count}</strong> links</span>
        </div>
        <div class="map-controls" aria-label="Starmap filters">
          <button type="button" data-starmap-filter="all" aria-pressed="true">All</button>
          <button type="button" data-starmap-filter="author">Author</button>
          <button type="button" data-starmap-filter="method">Method</button>
          <button type="button" data-starmap-filter="dataset">Dataset</button>
          <button type="button" data-starmap-filter="citation">Citation</button>
        </div>
        <div class="map-selection starmap-selection" aria-live="polite">
          <strong>Select a node</strong>
          <p>Click a paper or relation node to inspect its neighborhood.</p>
        </div>
      </aside>
      <div class="starmap-canvas-wrap">
        <svg class="starmap-canvas" role="img" aria-label="Paper starmap"></svg>
      </div>
    </section>
    """
    return _page_shell(
        title="Starmap / AIResearch",
        body=body,
        current="starmap",
        depth=1,
        extra_script='<script src="../assets/d3.v7.min.js"></script>',
    )


def _map_page(graph: dict[str, Any]) -> str:
    topic_count = sum(1 for node in graph.get("nodes", []) if isinstance(node, dict) and node.get("kind") == "topic")
    paper_count = sum(1 for node in graph.get("nodes", []) if isinstance(node, dict) and node.get("kind") == "paper")
    edge_count = len(graph.get("edges", [])) if isinstance(graph.get("edges"), list) else 0
    body = f"""
    <section class="page-heading">
      <p class="eyebrow">关系图谱</p>
      <h1>Map</h1>
      <p>论文之间的引力，可视化为一张网。</p>
    </section>
    <section class="map-shell" data-research-map="../api/relations-graph.json">
      <aside class="map-sidebar">
        <h2>Map scope</h2>
        <div class="map-stats">
          <span><strong>{topic_count}</strong> topics</span>
          <span><strong>{paper_count}</strong> papers</span>
          <span><strong>{edge_count}</strong> links</span>
        </div>
        <div class="map-controls" aria-label="Map filters">
          <button type="button" data-map-filter="all" aria-pressed="true">All</button>
          {''.join(f'<button type="button" data-map-filter="{fact_type}">{fact_type}</button>' for fact_type in FACT_TYPES)}
        </div>
        <div class="map-selection" aria-live="polite">
          <strong>Select a node</strong>
          <p>Click a topic or paper to inspect its local neighborhood.</p>
        </div>
      </aside>
      <div class="map-canvas-wrap">
        <svg class="research-map" role="img" aria-label="Research topic and paper graph"></svg>
      </div>
    </section>
    <section class="report-details">
      <h2>Raw map report</h2>
      <p>Open the generated Markdown or JSON artifact when you need the full deterministic report.</p>
      <p><a href="../map.md">Markdown</a> · <a href="../map.json">JSON</a></p>
    </section>
    """
    return _page_shell(
        title="Research Map / AIResearch",
        body=body,
        current="map",
        depth=1,
        extra_script='<script src="../assets/d3.v7.min.js"></script>',
    )


def _gap_page(gap_payload: Any) -> str:
    if not isinstance(gap_payload, dict):
        gap_payload = {}
    coverage = gap_payload.get("fact_type_coverage", [])
    if not isinstance(coverage, list):
        coverage = []
    papers = gap_payload.get("papers", [])
    if not isinstance(papers, list):
        papers = []
    missing_type_rows = [
        paper for paper in papers
        if isinstance(paper, dict) and paper.get("missing_fact_types")
    ]
    evidence_rows = [
        paper for paper in papers
        if isinstance(paper, dict) and int(paper.get("missing_evidence_source_path_count") or 0) > 0
    ]
    no_code_rows = [
        paper for paper in papers
        if isinstance(paper, dict) and not bool(paper.get("has_code_links"))
    ]

    def metric(label: str, value: Any, hint: str) -> str:
        return f"""
        <div class="metric-card reveal">
          <span>{html.escape(label)}</span>
          <strong>{html.escape(str(value))}</strong>
          <small>{html.escape(hint)}</small>
        </div>
        """

    def coverage_row(item: dict[str, Any]) -> str:
        fact_type = _compact_string(item.get("fact_type")) or "fact"
        ratio = float(item.get("coverage_ratio") or 0)
        percent = max(0, min(100, round(ratio * 100)))
        return f"""
        <li class="coverage-row">
          <div>
            <span class="fact-chip {html.escape(fact_type)}">{html.escape(fact_type)}</span>
            <strong>{percent}%</strong>
          </div>
          <div class="coverage-track" aria-label="{html.escape(fact_type)} coverage {percent}%">
            <span style="width: {percent}%"></span>
          </div>
          <p>{html.escape(str(item.get("paper_count", 0)))} papers · {html.escape(str(item.get("fact_count", 0)))} facts</p>
        </li>
        """

    def paper_gap_row(paper: dict[str, Any]) -> str:
        paper_key = _compact_string(paper.get("paper_key"))
        title = _compact_string(paper.get("title")) or paper_key
        missing = paper.get("missing_fact_types", [])
        if not isinstance(missing, list):
            missing = []
        tags = "".join(f'<span class="fact-chip">{html.escape(_compact_string(item))}</span>' for item in missing[:5])
        evidence_missing = int(paper.get("missing_evidence_source_path_count") or 0)
        code = "code linked" if bool(paper.get("has_code_links")) else "no code link"
        return f"""
        <li class="gap-paper-row">
          <a href="../papers/{html.escape(_slug(paper_key))}.html">{html.escape(title)}</a>
          <span>{html.escape(paper_key)} · {html.escape(str(paper.get("year") or "n.d."))}</span>
          <div class="chip-row">{tags or '<span class="fact-chip">complete fact types</span>'}</div>
          <small>{evidence_missing} missing evidence paths · {html.escape(code)}</small>
        </li>
        """

    coverage_html = "\n".join(coverage_row(item) for item in coverage if isinstance(item, dict))
    priority_rows = sorted(
        missing_type_rows,
        key=lambda paper: (len(paper.get("missing_fact_types", [])), int(paper.get("missing_evidence_source_path_count") or 0)),
        reverse=True,
    )[:30]
    priority_html = "\n".join(paper_gap_row(paper) for paper in priority_rows) or '<li class="empty-state">No missing fact-type gaps found.</li>'
    evidence_html = "\n".join(paper_gap_row(paper) for paper in evidence_rows[:20]) or '<li class="empty-state">No missing evidence paths found.</li>'
    no_code_html = "\n".join(paper_gap_row(paper) for paper in no_code_rows[:20]) or '<li class="empty-state">All papers have code links.</li>'

    body = f"""
    <section class="page-heading">
      <p class="eyebrow">空白地图</p>
      <h1>Gaps</h1>
      <p>缺失的不是数据，是尚未被提出的正确问题。</p>
    </section>
    <section class="metrics-grid" aria-label="Gap metrics">
      {metric("Papers", gap_payload.get("paper_count", 0), "in the current gap report")}
      {metric("Missing types", len(missing_type_rows), "papers missing at least one required fact type")}
      {metric("No code link", len(no_code_rows), "papers without repository evidence")}
      {metric("Evidence gaps", gap_payload.get("missing_evidence_source_path_count", 0), "facts missing source paths")}
    </section>
    <section class="gap-layout">
      <div class="gap-coverage-panel reveal">
        <div class="section-title"><h2>Fact coverage</h2><a href="../gap-analysis.json">JSON</a></div>
        <ul>{coverage_html or '<li class="empty-state">No coverage data available.</li>'}</ul>
      </div>
      <aside class="gap-coverage-panel gap-lowest-panel reveal">
        <h2>Lowest coverage</h2>
        <p>The lowest fact types should be reviewed first because they reduce cross-paper comparison quality.</p>
        <ul>{''.join(coverage_row(item) for item in sorted([item for item in coverage if isinstance(item, dict)], key=lambda item: float(item.get("coverage_ratio") or 0))[:3])}</ul>
      </aside>
    </section>
    <section class="gap-columns">
      <div class="gap-coverage-panel reveal">
        <h2>Priority papers</h2>
        <ul class="gap-paper-list">{priority_html}</ul>
      </div>
      <div class="gap-coverage-panel reveal">
        <h2>Evidence path gaps</h2>
        <ul class="gap-paper-list">{evidence_html}</ul>
      </div>
      <div class="gap-coverage-panel reveal">
        <h2>Code-link gaps</h2>
        <ul class="gap-paper-list">{no_code_html}</ul>
      </div>
    </section>
    <section class="report-details">
      <h2>Raw gap report</h2>
      <p>Open the deterministic Markdown or JSON artifact for the full export.</p>
      <p><a href="../gap-analysis.md">Markdown</a> · <a href="../gap-analysis.json">JSON</a></p>
    </section>
    """
    return _page_shell(title="Research Gaps / AIResearch", body=body, current="gaps", depth=1)


def _digest_page(papers: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> str:
    summaries = sorted(
        (_paper_summary(paper) for paper in papers),
        key=lambda item: (item["year"], item["fact_count"], item["paper_key"]),
        reverse=True,
    )
    cluster_summaries = sorted(
        (_cluster_summary(cluster) for cluster in clusters),
        key=lambda item: (item["paper_count"], item["fact_count"]),
        reverse=True,
    )
    high_confidence: list[dict[str, Any]] = []
    for paper in papers:
        paper_summary = _paper_summary(paper)
        for fact in _fact_items(paper):
            confidence = fact.get("confidence")
            if isinstance(confidence, (int, float)) and confidence >= 0.95:
                high_confidence.append(
                    {
                        "paper": paper_summary,
                        "fact_type": _compact_string(fact.get("fact_type")),
                        "statement": _snippet(_compact_string(fact.get("statement")), limit=180),
                        "confidence": confidence,
                    }
                )
    high_confidence = sorted(
        high_confidence,
        key=lambda item: (float(item["confidence"]), item["paper"]["year"], item["paper"]["paper_key"]),
        reverse=True,
    )[:12]

    def digest_paper_item(summary: dict[str, Any]) -> str:
        authors = ", ".join(summary["authors"][:2]) or "Unknown authors"
        return f"""
        <article class="digest-paper reveal">
          <a class="paper-title" href="../{html.escape(summary['detail_path'])}">{html.escape(summary['title'])}</a>
          <p>{html.escape(summary['tldr'] or 'No short summary available yet.')}</p>
          <span>{html.escape(str(summary['year'] or 'n.d.'))} · {html.escape(authors)} · {summary['fact_count']} facts</span>
        </article>
        """

    def cluster_item(summary: dict[str, Any]) -> str:
        return f"""
        <li>
          <a href="../{html.escape(summary['detail_path'])}">{html.escape(summary['title'])}</a>
          <span>{html.escape(summary['fact_type'])} · {summary['paper_count']} papers · {summary['fact_count']} facts</span>
        </li>
        """

    def finding_item(item: dict[str, Any]) -> str:
        paper = item["paper"]
        fact_type = _compact_string(item["fact_type"]) or "fact"
        return f"""
        <li class="finding-row">
          <div><span class="fact-chip {html.escape(fact_type)}">{html.escape(fact_type)}</span><strong>{float(item['confidence']):.2f}</strong></div>
          <p>{html.escape(item['statement'])}</p>
          <a href="../{html.escape(paper['detail_path'])}">{html.escape(paper['title'])}</a>
        </li>
        """

    newest = sorted(
        summaries,
        key=lambda item: (item.get("added_at") or "", item.get("paper_key") or ""),
        reverse=True,
    )
    latest = "\n".join(digest_paper_item(summary) for summary in newest[:8])
    top_clusters = "\n".join(cluster_item(summary) for summary in cluster_summaries[:12])
    findings = "\n".join(finding_item(item) for item in high_confidence)
    year_counts: dict[int, int] = {}
    for summary in summaries:
        if summary["year"]:
            year_counts[summary["year"]] = year_counts.get(summary["year"], 0) + 1
    timeline = "\n".join(
        f'<li><strong>{year}</strong><span>{count} papers</span></li>'
        for year, count in sorted(year_counts.items(), reverse=True)[:6]
    )
    body = f"""
    <section class="page-heading">
      <p class="eyebrow">研究简报</p>
      <h1>Digest</h1>
      <p>最近入库的论文，和它们带来的新信号。</p>
    </section>
    <section class="digest-layout">
      <aside class="digest-sidebar reveal">
        <h2>Timeline</h2>
        <ul>{timeline or '<li class="empty-state">No year data.</li>'}</ul>
        <h2>Topic clusters</h2>
        <ul>{top_clusters or '<li class="empty-state">No clusters available.</li>'}</ul>
      </aside>
      <div class="digest-main">
        <section>
          <div class="section-title"><h2>Recent papers</h2><a href="../papers/index.html">Browse all papers</a></div>
          <div class="digest-paper-grid">{latest}</div>
        </section>
        <section class="digest-findings reveal">
          <div class="section-title"><h2>High-confidence findings</h2><a href="../digest.json">JSON</a></div>
          <ul>{findings or '<li class="empty-state">No high-confidence findings available.</li>'}</ul>
        </section>
      </div>
    </section>
    <section class="report-details">
      <h2>Raw digest report</h2>
      <p>Open the deterministic Markdown or JSON artifact for the full export.</p>
      <p><a href="../digest.md">Markdown</a> · <a href="../digest.json">JSON</a></p>
    </section>
    """
    return _page_shell(title="Research Digest / AIResearch", body=body, current="digest", depth=1)


def _coverage_group_items(synthesis: dict[str, Any], group_name: str) -> list[dict[str, Any]]:
    group = synthesis.get(group_name)
    if not isinstance(group, dict):
        return []
    fact_types = group.get("fact_types", [])
    if not isinstance(fact_types, list):
        return []
    return [item for item in fact_types if isinstance(item, dict)]


def _synthesis_page(synthesis: Any) -> str:
    if not isinstance(synthesis, dict):
        synthesis = {}
    paper_count = int(synthesis.get("paper_count") or 0)
    fact_count = int(synthesis.get("fact_count") or 0)
    target_count = int(synthesis.get("extraction_target_count") or 0)
    missing_evidence_count = int(synthesis.get("missing_evidence_source_path_count") or 0)
    papers_without_code = int(synthesis.get("papers_without_code_links") or 0)
    papers_missing_types = int(synthesis.get("papers_missing_fact_types") or 0)
    strong_items = _coverage_group_items(synthesis, "strong_coverage")
    moderate_items = _coverage_group_items(synthesis, "moderate_coverage")
    weak_items = _coverage_group_items(synthesis, "weak_coverage")
    notes = synthesis.get("synthesis_notes", [])
    if not isinstance(notes, list):
        notes = []
    targets = synthesis.get("extraction_targets", [])
    if not isinstance(targets, list):
        targets = []
    required_types = synthesis.get("required_fact_types", [])
    if not isinstance(required_types, list):
        required_types = []

    def pct(value: Any) -> str:
        try:
            return f"{float(value) * 100:.0f}%"
        except (TypeError, ValueError):
            return "0%"

    def coverage_row(item: dict[str, Any]) -> str:
        fact_type = _compact_string(item.get("fact_type")) or "fact"
        ratio = max(0.0, min(float(item.get("coverage_ratio") or 0), 1.0))
        return f"""
        <li class="synthesis-coverage-row">
          <div><span class="fact-chip {html.escape(fact_type)}">{html.escape(fact_type)}</span><strong>{pct(ratio)}</strong></div>
          <div class="coverage-track" aria-label="{html.escape(fact_type)} coverage {pct(ratio)}"><span style="width: {ratio * 100:.1f}%"></span></div>
          <p>{int(item.get("paper_count") or 0)} papers · {int(item.get("fact_count") or 0)} facts</p>
        </li>
        """

    def note_row(item: dict[str, Any]) -> str:
        fact_type = _compact_string(item.get("fact_type")) or "fact"
        return f"""
        <li class="synthesis-note">
          <div><span class="fact-chip {html.escape(fact_type)}">{html.escape(fact_type)}</span><strong>{pct(item.get("coverage_ratio"))}</strong></div>
          <p>{html.escape(_compact_string(item.get("note")) or "No synthesis note available.")}</p>
        </li>
        """

    def target_row(item: Any) -> str:
        if isinstance(item, dict):
            label = _compact_string(item.get("fact_type") or item.get("name") or item.get("target"))
            count = item.get("count") or item.get("paper_count") or item.get("fact_count")
            detail = f"{int(count)} entries" if isinstance(count, (int, float)) else "tracked target"
        else:
            label = _compact_string(item)
            detail = "tracked target"
        label = label or "target"
        return f"<li><span>{html.escape(label)}</span><small>{html.escape(detail)}</small></li>"

    coverage_html = "".join(
        f"""
        <article class="synthesis-band reveal">
          <h2>{label}</h2>
          <p>{description}</p>
          <ul>{''.join(coverage_row(item) for item in items) or '<li class="empty-state">No fact types in this band.</li>'}</ul>
        </article>
        """
        for label, description, items in [
            ("Strong coverage", "Use these fact types as the backbone for cross-paper synthesis.", strong_items),
            ("Moderate coverage", "Useful evidence, but broad claims should keep paper-level caveats.", moderate_items),
            ("Weak coverage", "Prioritize extraction and review before leaning on these claims.", weak_items),
        ]
    )
    note_html = "".join(note_row(item) for item in notes if isinstance(item, dict))
    target_html = "".join(target_row(item) for item in targets[:12])
    required_html = "".join(
        f'<span class="fact-chip {html.escape(_compact_string(item))}">{html.escape(_compact_string(item))}</span>'
        for item in required_types
        if _compact_string(item)
    )
    evidence_gap_ratio = (missing_evidence_count / fact_count) if fact_count else 0
    code_gap_ratio = (papers_without_code / paper_count) if paper_count else 0
    type_gap_ratio = (papers_missing_types / paper_count) if paper_count else 0
    body = f"""
    <section class="page-heading">
      <p class="eyebrow">综合研判</p>
      <h1>Synthesis</h1>
      <p>跨论文的趋势、风险和机会，浓缩为可执行的判断。</p>
    </section>
    <section class="metrics-grid">
      {_metric_card("Papers", paper_count, "Corpus size")}
      {_metric_card("Facts", fact_count, "Extracted evidence")}
      {_metric_card("Targets", target_count or len(required_types), "Required fact types")}
      {_metric_card("Evidence gaps", missing_evidence_count, "Facts without source paths")}
    </section>
    <section class="synthesis-layout">
      <div class="synthesis-main">{coverage_html}</div>
      <aside class="synthesis-aside reveal">
        <h2>Readiness checks</h2>
        <div class="synthesis-risk">
          <span>Missing fact types</span><strong>{papers_missing_types}</strong>
          <div class="coverage-track"><span style="width: {type_gap_ratio * 100:.1f}%"></span></div>
          <small>{pct(type_gap_ratio)} of papers need at least one required fact type.</small>
        </div>
        <div class="synthesis-risk">
          <span>No code link</span><strong>{papers_without_code}</strong>
          <div class="coverage-track"><span style="width: {code_gap_ratio * 100:.1f}%"></span></div>
          <small>{pct(code_gap_ratio)} of papers have no repository link.</small>
        </div>
        <div class="synthesis-risk">
          <span>Missing evidence path</span><strong>{missing_evidence_count}</strong>
          <div class="coverage-track"><span style="width: {evidence_gap_ratio * 100:.1f}%"></span></div>
          <small>{pct(evidence_gap_ratio)} of facts need source-path repair.</small>
        </div>
        <h2>Required types</h2>
        <div class="chip-row">{required_html or '<span class="empty-state">No required fact types listed.</span>'}</div>
      </aside>
    </section>
    <section class="synthesis-notes reveal">
      <div class="section-title"><h2>Synthesis notes</h2><a href="../synthesis.json">JSON</a></div>
      <ul>{note_html or '<li class="empty-state">No synthesis notes available.</li>'}</ul>
    </section>
    <section class="synthesis-targets reveal">
      <div class="section-title"><h2>Extraction targets</h2><a href="../synthesis.md">Markdown</a></div>
      <ul>{target_html or '<li class="empty-state">No extraction targets listed.</li>'}</ul>
    </section>
    <section class="report-details">
      <h2>Raw synthesis report</h2>
      <p>Open the deterministic Markdown or JSON artifact for the full export.</p>
      <p><a href="../synthesis.md">Markdown</a> · <a href="../synthesis.json">JSON</a></p>
    </section>
    """
    return _page_shell(title="Research Synthesis / AIResearch", body=body, current="synthesis", depth=1)


def _narrative_page(narrative: Any) -> str:
    if not isinstance(narrative, dict):
        narrative = {}
    paper_count = int(narrative.get("paper_count") or 0)
    fact_count = int(narrative.get("fact_count") or 0)
    finding_count = int(narrative.get("finding_count") or 0)
    action_count = int(narrative.get("action_count") or 0)
    summary = narrative.get("executive_summary", [])
    supported = narrative.get("supported_areas", [])
    provisional = narrative.get("provisional_areas", [])
    findings = narrative.get("representative_findings", [])
    actions = narrative.get("priority_actions", [])
    cautions = narrative.get("evidence_cautions", [])
    if not isinstance(summary, list):
        summary = []
    if not isinstance(supported, list):
        supported = []
    if not isinstance(provisional, list):
        provisional = []
    if not isinstance(findings, list):
        findings = []
    if not isinstance(actions, list):
        actions = []
    if not isinstance(cautions, list):
        cautions = []

    def text_item(value: Any) -> str:
        return f"<li>{html.escape(_compact_string(value) or 'No detail available.')}</li>"

    def finding_row(item: Any) -> str:
        if not isinstance(item, dict):
            return ""
        fact_type = _compact_string(item.get("fact_type")) or "fact"
        confidence = item.get("confidence")
        try:
            confidence_label = f"{float(confidence):.2f}"
        except (TypeError, ValueError):
            confidence_label = "n/a"
        paper_key = _compact_string(item.get("paper_key")) or "paper"
        title = _compact_string(item.get("paper_title")) or paper_key
        statement = _compact_string(item.get("statement")) or "No statement available."
        quote = _compact_string(item.get("evidence_quote")) or ""
        source_path = _compact_string(item.get("evidence_source_path")) or ""
        source_name = Path(source_path).name if source_path else "No source path"
        return f"""
        <li class="narrative-finding">
          <div class="narrative-finding-head">
            <span class="fact-chip {html.escape(fact_type)}">{html.escape(fact_type)}</span>
            <strong>{html.escape(confidence_label)}</strong>
          </div>
          <p>{html.escape(statement)}</p>
          <small>{html.escape(title)} · {html.escape(paper_key)}</small>
          {f'<blockquote>{html.escape(quote)}</blockquote>' if quote else ''}
          <code>{html.escape(source_name)}</code>
        </li>
        """

    def action_row(item: Any) -> str:
        if not isinstance(item, dict):
            return ""
        score = int(item.get("priority_score") or 0)
        title = _compact_string(item.get("title")) or _compact_string(item.get("paper_key")) or "Untitled paper"
        key = _compact_string(item.get("paper_key")) or "paper"
        action = _compact_string(item.get("action")) or "Review this paper."
        return f"""
        <li class="narrative-action">
          <div><strong>{score}</strong><span>priority</span></div>
          <p><b>{html.escape(title)}</b><small>{html.escape(key)}</small>{html.escape(action)}</p>
        </li>
        """

    summary_html = "".join(text_item(item) for item in summary)
    supported_html = "".join(text_item(item) for item in supported)
    provisional_html = "".join(text_item(item) for item in provisional)
    findings_html = "".join(finding_row(item) for item in findings[:8])
    actions_html = "".join(action_row(item) for item in actions[:8])
    cautions_html = "".join(text_item(item) for item in cautions)

    body = f"""
    <section class="page-heading narrative-heading">
      <p class="eyebrow">叙事线索</p>
      <h1>Narrative</h1>
      <p>把离散的发现串成一条有方向的故事。</p>
    </section>
    <section class="metrics-grid">
      {_metric_card("Papers", paper_count, "Corpus size")}
      {_metric_card("Facts", fact_count, "Extracted evidence")}
      {_metric_card("Findings", finding_count or len(findings), "Representative items")}
      {_metric_card("Actions", action_count or len(actions), "Priority follow-up")}
    </section>
    <section class="narrative-layout">
      <div class="narrative-main">
        <article class="narrative-panel reveal">
          <div class="section-title"><h2>Executive summary</h2><a href="../narrative.json">JSON</a></div>
          <ul class="narrative-list">{summary_html or '<li class="empty-state">No executive summary available.</li>'}</ul>
        </article>
        <section class="narrative-coverage-grid">
          <article class="narrative-panel reveal">
            <h2>Well supported</h2>
            <ul class="narrative-list">{supported_html or '<li class="empty-state">No supported areas listed.</li>'}</ul>
          </article>
          <article class="narrative-panel reveal">
            <h2>Provisional</h2>
            <ul class="narrative-list">{provisional_html or '<li class="empty-state">No provisional areas listed.</li>'}</ul>
          </article>
        </section>
        <article class="narrative-panel reveal">
          <div class="section-title"><h2>Representative findings</h2><a href="../papers/index.html">Papers</a></div>
          <ul class="narrative-findings">{findings_html or '<li class="empty-state">No representative findings available.</li>'}</ul>
        </article>
      </div>
      <aside class="narrative-aside reveal">
        <h2>Evidence cautions</h2>
        <ul class="narrative-list caution-list">{cautions_html or '<li class="empty-state">No evidence cautions listed.</li>'}</ul>
        <h2>Priority actions</h2>
        <ul class="narrative-actions">{actions_html or '<li class="empty-state">No priority actions listed.</li>'}</ul>
      </aside>
    </section>
    <section class="report-details">
      <h2>Raw narrative report</h2>
      <p>Open the deterministic Markdown or JSON artifact for the full export.</p>
      <p><a href="../narrative.md">Markdown</a> · <a href="../narrative.json">JSON</a></p>
    </section>
    """
    return _page_shell(title="Narrative Report / AIResearch", body=body, current="narrative", depth=1)


def _report_page(title: str, current: str, markdown: str, json_path: str, depth: int = 1) -> str:
    body = f"""
    <section class="page-heading">
      <p class="eyebrow">Report view</p>
      <h1>{html.escape(title)}</h1>
      <p><a href="../{html.escape(json_path)}">Raw JSON</a></p>
    </section>
    <article class="report-prose">{_markdown_to_blocks(markdown)}</article>
    """
    return _page_shell(title=f"{title} / AIResearch", body=body, current=current, depth=depth)


def _markdown_to_blocks(markdown: str) -> str:
    blocks = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            blocks.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            blocks.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("- "):
            blocks.append(f"<p class=\"bullet\">{html.escape(line[2:])}</p>")
        else:
            blocks.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(blocks) or '<p class="empty-state">No report content available.</p>'


SITE_CSS = """
:root {
  color-scheme: light;
  --bg-base: #fafaf8;
  --bg-surface: #ffffff;
  --bg-sunken: #f3f2ef;
  --bg-sidebar: #f7f6f3;
  --ink-primary: #1a1a1a;
  --ink-body: #37352f;
  --ink-secondary: #6b6b6b;
  --ink-muted: #9b9b9b;
  --accent: #0f7b6c;
  --accent-light: #e6f4f1;
  --accent-hover: #0a5d52;
  --tag-method: #2e6fba;
  --tag-claim: #b45309;
  --tag-limitation: #dc2626;
  --tag-dataset: #7c3aed;
  --tag-benchmark: #0891b2;
  --border: #e8e7e4;
  --border-strong: #d4d3cf;
  --shadow-sm: 0 1px 3px rgba(15, 45, 40, 0.05);
  --shadow-md: 0 10px 24px rgba(15, 45, 40, 0.09);
  --font-heading: "Source Serif 4", "Noto Serif SC", Georgia, serif;
  --font-body: "Aptos", "Noto Sans SC", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; overflow-x: hidden; }
body {
  margin: 0;
  overflow-x: hidden;
  color: var(--ink-body);
  background:
    radial-gradient(circle at 12% 0%, rgba(15, 123, 108, 0.08), transparent 28rem),
    linear-gradient(180deg, #ffffff 0, var(--bg-base) 34rem);
  font: 15px/1.55 var(--font-body);
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.28;
  background-image: linear-gradient(rgba(26,26,26,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(26,26,26,0.025) 1px, transparent 1px);
  background-size: 24px 24px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); text-decoration: underline; }
img {
  display: block;
  max-width: 100%;
  height: auto;
  object-fit: contain;
}
button, input, select { font: inherit; }
button, input, select, a { transition: border-color 150ms ease, background 150ms ease, color 150ms ease, box-shadow 150ms ease, transform 150ms ease; }
button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible { outline: 3px solid rgba(15,123,108,0.28); outline-offset: 2px; }
.skip-link { position: fixed; left: 16px; top: -60px; z-index: 5; padding: 8px 10px; background: var(--accent); color: white; }
.skip-link:focus { top: 12px; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 62px;
  padding: 0 28px;
  border-bottom: 1px solid var(--border);
  background: rgba(250,250,248,0.88);
  backdrop-filter: blur(10px);
}
.brand { display: flex; gap: 8px; align-items: baseline; color: var(--ink-primary); }
.brand span { color: var(--ink-secondary); }
.brand strong { font-family: var(--font-heading); font-size: 21px; }
.topbar nav { display: flex; flex: 1 1 auto; min-width: 0; gap: 4px; overflow-x: auto; }
.topbar nav a { padding: 8px 10px; border-radius: 6px; color: var(--ink-secondary); white-space: nowrap; }
.topbar nav a[aria-current="page"], .topbar nav a:hover { background: var(--accent-light); color: var(--accent-hover); text-decoration: none; }
.topbar-actions { display: inline-flex; align-items: center; gap: 8px; flex: 0 0 auto; }
.home-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 13px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--ink-primary);
  background: #fff;
  white-space: nowrap;
}
.home-link:hover { background: var(--accent-light); color: var(--accent-hover); text-decoration: none; }
.lang-toggle {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 32px;
  min-width: 74px;
  padding: 0 16px;
  border: 0;
  border-radius: 999px;
  background: #f4f3f0;
  color: #111;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.lang-toggle:hover { background: rgba(244,243,240,0.8); }
.lang-toggle[aria-pressed="true"] {
  background: var(--accent-light);
  color: var(--accent-hover);
}
.lang-toggle-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}
body [data-lang="zh"] { display: none !important; }
html[data-lang="zh"] body [data-lang="en"] { display: none !important; }
html[data-lang="zh"] body [data-lang="zh"] { display: revert !important; }
body [data-lang="en"] + [data-lang="zh"] { margin-top: 0; }
main { width: min(1240px, calc(100% - 40px)); margin: 0 auto; padding: 28px 0 56px; position: relative; }
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 440px);
  gap: 32px;
  align-items: end;
  padding: 38px 0 22px;
}
h1, h2, h3 { color: var(--ink-primary); font-family: var(--font-heading); line-height: 1.12; letter-spacing: 0; text-wrap: balance; }
h1 { margin: 0 0 12px; font-size: clamp(34px, 5vw, 62px); }
h2 { margin: 0; font-size: 25px; }
h3 { margin: 22px 0 8px; font-size: 18px; }
.hero p, .page-heading p, .lead { max-width: 68ch; color: var(--ink-secondary); font-size: 17px; }
.eyebrow { margin: 0 0 8px; color: var(--accent); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.global-search, .toolbar {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
  padding: 14px;
}
.global-search label { display: block; margin-bottom: 8px; color: var(--ink-secondary); font-size: 13px; }
input, select {
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: #fff;
  color: var(--ink-body);
  padding: 8px 10px;
}
.search-results { display: grid; gap: 8px; margin-top: 10px; }
.search-hit { display: block; padding: 8px; border-radius: 6px; background: var(--bg-sunken); }
.search-hit small, .paper-meta, .result-count { color: var(--ink-secondary); font-size: 13px; }
.new-badge { display: inline-block; margin-right: 6px; padding: 1px 6px; border-radius: 999px; background: #c0392b; color: #fff; font-size: 10px; font-weight: 700; letter-spacing: .05em; vertical-align: 1px; }
.paper-dates { color: var(--ink-secondary); font-size: 12px; letter-spacing: .01em; }
.ghost-button { padding: 6px 12px; border: 1px solid var(--line, #d8d2c4); border-radius: 999px; background: transparent; color: var(--ink-secondary); font-size: 12px; cursor: pointer; }
.ghost-button:hover { border-color: var(--accent); color: var(--accent); }
.metrics-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 16px 0 24px; }
.metric-card, .paper-card, .cluster-card, .gap-panel, .related-panel {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}
.metric-card { padding: 14px 16px; }
.metric-card span, .metric-card small { display: block; color: var(--ink-secondary); }
.metric-card strong { display: block; margin: 6px 0 2px; color: var(--ink-primary); font: 700 30px/1 var(--font-mono); font-variant-numeric: tabular-nums; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 22px; align-items: start; }
.section-title { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: 0 0 12px; }
.stack { display: grid; gap: 12px; }
.paper-card, .cluster-card { padding: 14px; display: grid; gap: 12px; }
.paper-card { grid-template-columns: 176px minmax(0, 1fr); align-items: start; }
.paper-card-body { min-width: 0; display: grid; gap: 8px; align-content: start; }
.paper-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.detail-link { flex: 0 0 auto; font-size: 13px; font-weight: 700; }
.paper-cover-wrap {
  position: relative;
  width: 100%;
  max-width: 176px;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border: 1px solid rgba(212, 169, 87, 0.42);
  border-radius: 6px;
  background: linear-gradient(180deg, rgba(30, 24, 13, 0.08), rgba(30, 24, 13, 0.02));
}
.paper-cover {
  display: block;
  width: 100%;
  height: 100%;
  max-height: 180px;
  object-fit: cover;
}
.paper-cover-empty::after {
  content: "AIResearch";
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--ink-muted);
  font: 700 12px/1 var(--font-mono);
  letter-spacing: .08em;
}
.paper-card:hover, .cluster-card:hover { border-color: var(--accent); box-shadow: var(--shadow-md); transform: translateY(-1px); }
.paper-title {
  color: var(--ink-primary);
  font-weight: 700;
  font-size: 16px;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.paper-card-body > p[data-lang] {
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.blog-index-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.blog-index-list { display: grid; gap: 16px; }
.blog-card {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}
.blog-card:hover { border-color: var(--accent); box-shadow: var(--shadow-md); transform: translateY(-1px); }
.blog-card-cover {
  min-height: 190px;
  border-right: 1px solid var(--border);
  background: var(--bg-sunken);
}
.blog-card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.blog-card-cover-empty {
  background:
    linear-gradient(135deg, rgba(15, 123, 108, 0.14), transparent 45%),
    linear-gradient(315deg, rgba(212, 169, 87, 0.18), transparent 42%),
    var(--bg-sunken);
}
.blog-card-body {
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 20px;
  min-width: 0;
}
.blog-card-body h2 { font-size: 23px; }
.blog-card-body h2 a { color: var(--ink-primary); }
.blog-card-body > p[data-lang] {
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.blog-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
  color: var(--ink-secondary);
  font-size: 13px;
}
.blog-card-footer a { flex: 0 0 auto; font-weight: 700; }
.blog-card-links { display: inline-flex; align-items: center; gap: 10px; flex: 0 0 auto; }
.blog-card-links a + a { color: var(--ink-secondary); font-weight: 600; }
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 2px; }
.fact-chip { display: inline-flex; align-items: center; min-height: 20px; padding: 2px 8px; border-radius: 3px; background: var(--bg-sunken); color: var(--ink-secondary); font-size: 11px; font-weight: 700; text-transform: uppercase; }
.fact-chip.method { background: var(--tag-method); color: white; }
.fact-chip.claim { background: #f6d7a7; color: #61340a; }
.fact-chip.limitation { background: var(--tag-limitation); color: white; }
.fact-chip.dataset { background: var(--tag-dataset); color: white; }
.fact-chip.benchmark { background: var(--tag-benchmark); color: white; }
.gap-panel { margin-top: 16px; padding: 14px; }
.gap-panel ul, .related-panel ul { list-style: none; padding: 0; margin: 10px 0 0; display: grid; gap: 8px; }
.gap-panel li { display: flex; justify-content: space-between; gap: 10px; border-top: 1px solid var(--border); padding-top: 8px; }
.page-heading { padding: 26px 0 18px; }
.toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) 150px 180px 190px auto; gap: 10px; align-items: center; margin-bottom: 14px; }
.paper-list { display: grid; gap: 12px; }
.paper-list .paper-card[hidden] { display: none; }
.pager { display: flex; justify-content: center; align-items: center; gap: 12px; margin: 20px 0 0; }
.pager button { border: 1px solid var(--border-strong); background: white; border-radius: 6px; padding: 8px 12px; cursor: pointer; }
.pager button:hover { border-color: var(--accent); color: var(--accent); }
.paper-detail {
  width: min(1460px, calc(100vw - 20px));
  max-width: none;
  margin-left: 50%;
  transform: translateX(-50%);
  padding: 26px 0;
}
.paper-detail-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}
.paper-deep-reading-anchor {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
}
.paper-detail-deep-reading-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}
.paper-detail-deep-reading-bar span {
  color: var(--ink);
  font-size: 13px;
  font-weight: 800;
}
.paper-detail-deep-reading-back {
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  padding: 7px 12px;
  background: #fff;
  color: var(--ink-secondary);
  font-size: 13px;
  font-weight: 800;
}
.paper-detail.is-deep-reading-only .back-link,
.paper-detail.is-deep-reading-only .paper-mode-toggle,
.paper-detail:has(#deep-reading:target) .back-link,
.paper-detail:has(#deep-reading:target) .paper-mode-toggle,
.paper-detail:has(#paper-deep-reading:target) .back-link,
.paper-detail:has(#paper-deep-reading:target) .paper-mode-toggle {
  display: none;
}
.paper-detail.is-deep-reading-only .paper-blog-detail-link,
.paper-detail:has(#deep-reading:target) .paper-blog-detail-link,
.paper-detail:has(#paper-deep-reading:target) .paper-blog-detail-link {
  display: none;
}
.paper-detail.is-deep-reading-only .paper-detail-deep-reading-bar,
.paper-detail:has(#deep-reading:target) .paper-detail-deep-reading-bar,
.paper-detail:has(#paper-deep-reading:target) .paper-detail-deep-reading-bar {
  display: flex;
}
.paper-detail.is-deep-reading-only .paper-mode-workbench,
.paper-detail.is-deep-reading-only .paper-mode-immersive,
.paper-detail:has(#deep-reading:target) .paper-mode-workbench,
.paper-detail:has(#deep-reading:target) .paper-mode-immersive,
.paper-detail:has(#paper-deep-reading:target) .paper-mode-workbench,
.paper-detail:has(#paper-deep-reading:target) .paper-mode-immersive {
  display: none !important;
}
.paper-detail:has(#deep-reading:target) .paper-mode-deep-reading,
.paper-detail:has(#paper-deep-reading:target) .paper-mode-deep-reading {
  display: block !important;
}
.paper-mode-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgba(255,255,255,0.78);
}
.paper-mode-toggle button {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--ink-secondary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 7px 12px;
}
.paper-mode-toggle button[aria-pressed="true"] {
  background: var(--accent-light);
  color: var(--accent-hover);
}
.paper-mode[hidden] { display: none !important; }
.paper-mode-deep-reading {
  --paper-blog-toc-width: 250px;
  width: min(1220px, 100%);
  margin: 0 auto;
  min-width: 0;
  max-width: 100%;
}
.paper-detail.is-deep-reading-only .paper-mode-deep-reading {
  width: min(1220px, calc(100vw - 28px));
  margin-left: auto;
  margin-right: auto;
}
.paper-detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 690px) minmax(280px, 1fr);
  gap: 28px;
  align-items: start;
}
.paper-detail-main { min-width: 0; }
.paper-detail-aside {
  min-width: 0;
  position: sticky;
  top: 86px;
}
.paper-mode-workbench {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr) minmax(340px, 390px);
  gap: 20px;
  align-items: start;
}
.paper-workbench-sidebar,
.paper-workbench-main,
.paper-workbench-aside {
  min-width: 0;
}
.paper-workbench-sidebar,
.paper-workbench-aside {
  position: sticky;
  top: 86px;
}
.paper-workbench-sidebar {
  padding: 2px 18px 0 0;
  border-right: 1px solid rgba(141, 129, 103, 0.26);
}
.paper-workbench-main {
  display: grid;
  gap: 18px;
  padding: 0;
  background: transparent;
}
.paper-side-abstract {
  max-width: none;
  margin: 16px 0 0;
  padding: 13px 14px;
  border: 1px solid rgba(15, 123, 108, 0.16);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(255,255,255,0.88), rgba(247,251,248,0.92));
  color: var(--ink-secondary);
  font-size: 14px;
  line-height: 1.68;
  overflow-wrap: anywhere;
}
.paper-workbench-aside {
  display: grid;
  gap: 14px;
}
.paper-detail-title {
  max-width: 820px;
  margin: 0 0 10px;
  font-size: clamp(21px, 2vw, 28px);
  line-height: 1.18;
}
.paper-detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: baseline;
}
.meta-icon-group {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin-left: 6px;
  vertical-align: -5px;
}
.paper-detail-meta a {
  color: var(--accent);
  font-weight: 700;
  text-decoration: none;
}
.paper-detail-meta a:hover { text-decoration: underline; }
.meta-icon-link {
  display: inline-flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: var(--ink-primary);
}
.meta-icon-link svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}
.meta-icon-link:hover {
  color: var(--accent);
  background: rgba(15, 123, 108, 0.08);
  text-decoration: none;
}
.arxiv-paper-link {
  color: #b31b1b;
}
.paper-hero-cover {
  margin: 0;
  width: 100%;
  overflow: hidden;
  border: 1px solid rgba(212, 169, 87, 0.42);
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(30, 24, 13, 0.08), rgba(30, 24, 13, 0.02)),
    #fff;
  box-shadow: 0 18px 46px rgba(49, 40, 24, 0.10);
}
.paper-hero-image { display: block; width: 100%; height: auto; object-fit: contain; }
.paper-workbench-sidebar .paper-detail-title { font-size: clamp(20px, 1.75vw, 24px); }
.paper-fact-stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  margin-top: 12px;
}
.paper-fact-stat {
  display: inline-flex;
  justify-content: center;
  align-items: baseline;
  gap: 5px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: rgba(255,255,255,0.78);
  padding: 7px 8px;
  color: inherit;
  font: inherit;
  text-decoration: none;
  transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
  cursor: pointer;
  min-width: 0;
}
.paper-fact-stat:hover,
.paper-fact-stat:focus-visible,
.paper-fact-stat[aria-pressed="true"] {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 108, 0.42);
  background: rgba(244, 250, 247, 0.94);
  outline: none;
}
.paper-fact-stat span {
  display: inline;
  color: var(--ink-secondary);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  white-space: nowrap;
}
.paper-fact-stat strong {
  display: inline;
  margin: 0;
  color: var(--ink-primary);
  font: 800 15px/1 var(--font-mono);
}
.paper-summary-block {
  margin: 0 0 24px;
  padding: 16px 16px 18px;
  border: 1px solid rgba(15, 123, 108, 0.2);
  border-radius: 6px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,247,0.96)),
    var(--bg-surface);
  box-shadow: 0 14px 34px rgba(31, 41, 55, 0.08);
  overflow: hidden;
}
.paper-workbench-aside .paper-summary-block {
  max-height: calc(100vh - 116px);
  overflow: auto;
}
.paper-summary-block h2 {
  margin: 4px 0 12px;
  font-size: 22px;
  line-height: 1.15;
}
.paper-summary-prose h1,
.paper-summary-prose h2,
.paper-summary-prose h3 {
  margin: 14px 0 8px;
  color: var(--ink-primary);
  font-size: 16px;
  line-height: 1.25;
}
.paper-summary-prose h1:first-child { margin-top: 0; }
.paper-summary-prose p {
  margin: 0;
  color: var(--ink-primary);
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.paper-summary-prose p + p { margin-top: 8px; }
.paper-summary-prose .bullet {
  padding-left: 12px;
  border-left: 2px solid rgba(15, 123, 108, 0.22);
  color: var(--ink-secondary);
}
.paper-layout-suite {
  display: grid;
  gap: 14px;
}
.paper-layout-panel {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 15px;
  border: 1px solid rgba(15, 123, 108, 0.18);
  border-radius: 6px;
  background: rgba(255,255,255,0.82);
  box-shadow: 0 10px 26px rgba(31, 41, 55, 0.06);
}
.paper-layout-panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.paper-layout-panel-head h2 {
  font-size: 18px;
}
.paper-layout-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.paper-layout-list li {
  display: grid;
  gap: 6px;
  padding: 10px 0 0;
  border-top: 1px solid rgba(141, 129, 103, 0.18);
}
.paper-layout-list li:first-child {
  padding-top: 0;
  border-top: 0;
}
.paper-layout-list p {
  margin: 0;
  color: var(--ink-primary);
  line-height: 1.62;
}
.paper-layout-list blockquote {
  margin: 0;
  padding-left: 10px;
  border-left: 2px solid rgba(15, 123, 108, 0.2);
  color: var(--ink-secondary);
  font-size: 13px;
}
.paper-evidence-graph-summary { margin-top: 0; }
.paper-evidence-facts {
  display: grid;
}
.paper-evidence-fact-row {
  display: grid;
  grid-template-columns: minmax(96px, 108px) minmax(0, 1fr);
  grid-template-areas: "meta statement" "meta evidence";
  column-gap: 12px;
  row-gap: 8px;
  align-items: start;
  min-width: 0;
  padding: 13px 0;
  border-top: 1px solid var(--border);
}
.paper-evidence-fact-row:first-child { border-top: 0; }
.paper-evidence-fact-row > * { min-width: 0; }
.paper-evidence-fact-meta {
  grid-area: meta;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--ink-secondary);
  font: 700 12px/1.4 var(--font-mono);
}
.paper-evidence-fact-row > p {
  margin: 0;
  color: var(--ink-primary);
  line-height: 1.58;
  overflow-wrap: anywhere;
}
.paper-evidence-fact-row > p:not(.paper-evidence-unlinked) { grid-area: statement; }
.paper-evidence-links {
  grid-area: evidence;
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.paper-evidence-link,
.paper-evidence-reference {
  display: grid;
  grid-template-columns: minmax(108px, max-content) minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  min-width: 0;
  padding-left: 10px;
  border-left: 2px solid rgba(15, 123, 108, 0.28);
}
.paper-evidence-link { color: var(--ink-primary); }
.paper-evidence-link:hover { border-left-color: var(--accent); color: var(--accent-hover); }
.paper-evidence-link-meta { display: grid; gap: 2px; }
.paper-evidence-link-meta b { color: inherit; font-size: 12px; }
.paper-evidence-link-meta small { color: var(--ink-secondary); font: 700 10px/1.4 var(--font-mono); }
.paper-evidence-preview {
  color: var(--ink-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.paper-evidence-unlinked {
  grid-area: evidence;
  margin: 0;
  color: #8a5a0a;
  font-size: 12px;
}
.paper-layout-code-card[id] { scroll-margin-top: 84px; }
.paper-layout-source {
  color: var(--ink-secondary);
  font: 700 12px/1.4 var(--font-mono);
}
.paper-layout-jump {
  justify-self: start;
  color: var(--accent-hover);
  font-size: 12px;
  font-weight: 800;
}
.paper-layout-code-grid {
  display: grid;
  gap: 10px;
}
.paper-layout-code-card {
  display: grid;
  gap: 8px;
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(141, 129, 103, 0.24);
  border-radius: 6px;
  background: var(--bg-sunken);
}
.paper-layout-code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--ink-secondary);
  font-size: 12px;
}
.paper-layout-code-head strong {
  color: var(--accent-hover);
  font-family: var(--font-mono);
}
.paper-layout-card-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  color: var(--ink-secondary);
  font: 700 11px/1.4 var(--font-mono);
}
.paper-layout-quality {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 7px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-family: var(--font-sans);
  font-weight: 800;
}
.paper-layout-quality.good {
  border-color: #17705f;
  background: #dff3ec;
  color: #0b4d40;
}
.paper-layout-quality.review {
  border-color: #9b6816;
  background: #fff1c9;
  color: #684407;
}
.paper-layout-quality.fallback {
  border-color: #a64b45;
  background: #fce4e1;
  color: #762d28;
}
.paper-layout-code-card p {
  margin: 0;
  color: var(--ink-secondary);
  font-size: 13px;
  line-height: 1.5;
}
.paper-layout-code-card pre {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  border: 1px solid rgba(31, 41, 55, 0.08);
  border-radius: 4px;
  background: #202522;
  padding: 10px;
  color: #eef4ef;
  font-size: 12px;
  line-height: 1.55;
}
.paper-layout-code-card code {
  color: inherit;
  white-space: pre-wrap;
}
.paper-layout-formula {
  min-height: 64px;
  overflow-x: auto;
  padding: 14px 10px;
  border: 1px solid rgba(31, 41, 55, 0.1);
  border-radius: 4px;
  background: #fff;
  color: var(--ink-primary);
  text-align: center;
}
.paper-layout-formula mjx-container {
  margin: 0 !important;
  font-size: 100% !important;
}
.paper-layout-raw summary {
  cursor: pointer;
  color: var(--ink-secondary);
  font-size: 12px;
  font-weight: 800;
}
.paper-layout-raw pre {
  margin-top: 8px;
}
.paper-layout-table-wrap {
  max-width: 100%;
  overflow: auto;
  border: 1px solid rgba(31, 41, 55, 0.12);
  border-radius: 4px;
  background: #fff;
}
.paper-layout-data-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  color: var(--ink-primary);
  font-size: 12px;
  line-height: 1.45;
}
.paper-layout-data-table th,
.paper-layout-data-table td {
  min-width: 104px;
  max-width: 240px;
  padding: 8px 10px;
  border-right: 1px solid rgba(31, 41, 55, 0.1);
  border-bottom: 1px solid rgba(31, 41, 55, 0.1);
  overflow-wrap: anywhere;
  text-align: left;
  vertical-align: top;
}
.paper-layout-data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #eaf4f0;
  color: #173f37;
  font-weight: 850;
}
.paper-layout-data-table tr:last-child td { border-bottom: 0; }
.paper-layout-data-table th:last-child,
.paper-layout-data-table td:last-child { border-right: 0; }
.paper-layout-preview-note {
  color: var(--ink-secondary) !important;
  font-size: 11px !important;
}
.paper-layout-table-fallback {
  border-color: rgba(166, 75, 69, 0.24) !important;
  background: #322725 !important;
}
.paper-layout-metrics,
.paper-layout-compact {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.paper-layout-metrics {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}
.paper-layout-metric {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 8px;
  border: 1px solid rgba(141, 129, 103, 0.2);
  border-radius: 6px;
  background: rgba(248,250,247,0.84);
}
.paper-layout-metric b {
  color: var(--ink-primary);
  font: 800 16px/1 var(--font-mono);
}
.paper-layout-metric small {
  color: var(--ink-secondary);
  font-size: 11px;
  text-transform: uppercase;
}
.paper-layout-status {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 14px;
  margin: 0;
}
.paper-layout-status div {
  min-width: 0;
}
.paper-layout-status dt {
  color: var(--ink-secondary);
  font-size: 12px;
  font-weight: 800;
}
.paper-layout-status dd {
  margin: 3px 0 0;
  color: var(--ink-primary);
  overflow-wrap: anywhere;
}
.paper-layout-compact {
  margin-top: 16px;
}
.paper-blog-section {
  display: grid;
  min-width: 0;
  max-width: 100%;
  gap: 14px;
  padding: clamp(18px, 3vw, 36px);
  border: 1px solid rgba(15, 123, 108, 0.2);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: 0 14px 34px rgba(31, 41, 55, 0.08);
}
.paper-detail.is-deep-reading-only .paper-blog-section {
  padding: clamp(18px, 2.4vw, 28px);
  border: 0;
  background: transparent;
  box-shadow: none;
}
.paper-blog-meta {
  min-width: 0;
  max-width: 100%;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.paper-blog-meta h2 {
  margin: 4px 0 8px;
  font-size: 22px;
  line-height: 1.18;
}
.paper-blog-meta h1.paper-blog-title {
  margin: 4px 0 10px;
  max-width: 780px;
  font-size: clamp(28px, 3.3vw, 44px);
  line-height: 1.1;
}
.paper-blog-meta p:last-child {
  margin: 0;
  color: var(--ink-secondary);
  font-size: 13px;
}
.paper-blog-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.paper-blog-meta-row p {
  margin: 0;
  color: var(--ink-secondary);
  font-size: 13px;
}
.paper-blog-detail-link {
  flex: 0 0 auto;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  padding: 6px 11px;
  background: #fff;
  font-size: 13px;
  font-weight: 700;
}
.paper-blog-prose {
  display: grid;
  min-width: 0;
  width: 100%;
  gap: 10px;
  max-width: 780px;
  line-height: 1.82;
}
.paper-detail.is-deep-reading-only .paper-blog-prose {
  width: min(100%, 780px);
  max-width: 780px;
}
.paper-blog-layout {
  display: grid;
  min-width: 0;
  max-width: 100%;
  grid-template-columns: minmax(0, 1fr) minmax(220px, var(--paper-blog-toc-width));
  gap: clamp(28px, 4vw, 68px);
  align-items: start;
}
.paper-blog-layout:not(:has(.paper-blog-toc)) {
  grid-template-columns: minmax(0, 780px);
}
.paper-detail.is-deep-reading-only .paper-blog-layout {
  grid-template-columns: minmax(0, 1fr) minmax(220px, var(--paper-blog-toc-width));
  gap: clamp(28px, 4vw, 68px);
  align-items: start;
}
.paper-detail.is-deep-reading-only .paper-blog-layout:has(.paper-blog-toc.is-collapsed) {
  grid-template-columns: minmax(0, 1fr) 48px;
  gap: 24px;
}
.paper-blog-toc {
  position: sticky;
  top: 88px;
  grid-column: 2;
  grid-row: 1;
  z-index: 4;
  display: grid;
  gap: 10px;
  width: 100%;
  max-height: calc(100vh - 120px);
  overflow: auto;
  padding: 16px 14px 16px 18px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(247, 246, 243, 0.82);
  box-shadow: 0 12px 28px rgba(31, 41, 55, 0.08);
  backdrop-filter: blur(12px);
  transition: width .18s ease, padding .18s ease, box-shadow .18s ease, background .18s ease;
}
.paper-detail.is-deep-reading-only .paper-blog-toc {
  top: 88px;
}
.paper-blog-toc.is-collapsed {
  width: 48px;
  padding: 10px 8px;
  overflow: visible;
  background: var(--bg-sidebar);
}
.paper-detail.is-deep-reading-only .paper-blog-toc.is-collapsed {
  width: 48px;
  padding: 10px 8px;
}
.paper-blog-toc-toggle {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  width: 100%;
  min-height: 32px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ink-primary);
  cursor: pointer;
  padding: 4px 6px;
  text-align: left;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-toggle {
  padding: 4px 6px;
}
.paper-blog-toc-toggle:hover,
.paper-blog-toc-toggle:focus-visible {
  background: var(--accent-light);
  outline: none;
}
.paper-blog-toc-toggle-icon {
  position: relative;
  width: 18px;
  height: 18px;
  border: 1px solid rgba(15, 123, 108, 0.38);
  border-radius: 4px;
  background: white;
}
.paper-blog-toc-toggle-icon::before,
.paper-blog-toc-toggle-icon::after {
  content: "";
  position: absolute;
  left: 4px;
  right: 4px;
  top: 8px;
  height: 2px;
  border-radius: 999px;
  background: var(--accent);
}
.paper-blog-toc-toggle-icon::after {
  transform: rotate(90deg);
  transition: transform .18s ease;
}
.paper-blog-toc:not(.is-collapsed) .paper-blog-toc-toggle-icon::after {
  transform: rotate(0deg);
}
.paper-blog-toc strong {
  color: var(--ink-primary);
  font-size: 15px;
}
.paper-blog-toc-list {
  display: grid;
  gap: 5px;
  min-width: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-list {
  gap: 2px;
  padding-top: 8px;
}
.paper-blog-toc.is-collapsed .paper-blog-toc-list,
.paper-blog-toc.is-collapsed .paper-blog-toc-toggle strong {
  display: none;
}
.paper-blog-toc-link {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 8px;
  align-items: baseline;
  padding: 7px 0;
  color: var(--ink-secondary);
  text-decoration: none;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-link {
  padding: 6px 0;
}
.paper-blog-toc-link:hover,
.paper-blog-toc-link:focus-visible {
  color: var(--accent-hover);
  outline: none;
}
.paper-blog-toc-link.is-active {
  color: var(--accent-hover);
}
.paper-blog-toc-link.is-active span {
  font-weight: 850;
}
.paper-blog-toc-link.is-active b {
  font-weight: 800;
}
.paper-blog-toc-link span {
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 13px;
}
.paper-blog-toc-link b {
  overflow-wrap: anywhere;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
}
.paper-blog-toc-link.level-3 {
  grid-template-columns: 48px minmax(0, 1fr);
  padding-left: 12px;
}
.paper-blog-prose h1,
.paper-blog-prose h2,
.paper-blog-prose h3 {
  scroll-margin-top: 92px;
  margin: 10px 0 2px;
  color: var(--ink-primary);
  line-height: 1.26;
}
.paper-blog-prose h1 { font-size: 24px; }
.paper-blog-prose h2 { font-size: 20px; }
.paper-blog-prose h3 { font-size: 17px; }
.paper-blog-prose p {
  margin: 0;
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
}
.paper-blog-prose ul,
.paper-blog-prose ol {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 24px;
}
.paper-blog-prose code {
  border-radius: 4px;
  background: var(--bg-sunken);
  padding: 2px 5px;
  font: 0.92em/1.5 var(--font-mono);
}
.paper-blog-prose pre {
  margin: 2px 0;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #202522;
  padding: 16px;
  color: #eef4ef;
}
.paper-blog-prose pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}
.paper-blog-code-block {
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(31, 41, 55, 0.18);
  border-radius: 8px;
  background: #202522;
  box-shadow: 0 8px 20px rgba(31, 41, 55, 0.08);
}
.paper-blog-code-bar {
  display: flex;
  align-items: center;
  min-height: 34px;
  gap: 10px;
  padding: 5px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
  background: #29332f;
  color: #cbd8d1;
  font: 700 11px/1.2 var(--font-mono);
}
.paper-blog-code-dots {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}
.paper-blog-code-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8caaa0;
}
.paper-blog-code-language {
  color: #dbe9e1;
  text-transform: lowercase;
}
.paper-blog-code-copy {
  margin-left: auto;
  border: 1px solid rgba(219, 233, 225, 0.24);
  border-radius: 4px;
  padding: 4px 7px;
  background: rgba(255, 255, 255, 0.04);
  color: #dbe9e1;
  cursor: pointer;
  font: inherit;
}
.paper-blog-code-copy:hover,
.paper-blog-code-copy:focus-visible {
  border-color: rgba(219, 233, 225, 0.55);
  background: rgba(255, 255, 255, 0.1);
  outline: none;
}
.paper-blog-code-block pre {
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}
.paper-blog-equation {
  margin: 8px 0;
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 12px 4px;
  text-align: center;
}
.paper-blog-equation mjx-container[display="true"] {
  min-width: max-content;
  margin: 0;
}
.paper-blog-prose > p:has(mjx-container) {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
}
.paper-blog-prose > p:has(mjx-container[display="true"]) mjx-container[display="true"] {
  min-width: max-content;
}
.paper-blog-prose a { color: var(--accent-hover); }
.paper-blog-image {
  display: grid;
  gap: 8px;
  justify-items: center;
  margin: 4px 0 10px;
}
.paper-blog-image img {
  width: auto;
  max-width: min(100%, 680px);
  height: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: white;
}
.paper-blog-image figcaption {
  justify-self: stretch;
  max-width: min(100%, 680px);
  color: var(--ink-secondary);
  font-size: 13px;
}
.paper-blog-prose > h1:first-child {
  display: none;
}
.paper-blog-footer {
  display: grid;
  gap: 22px;
  margin-top: 12px;
  padding-top: 22px;
  border-top: 1px solid var(--border);
}
.paper-blog-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.paper-blog-footer-label,
.paper-blog-neighbor-label {
  color: var(--ink-secondary);
  font-size: 12px;
  font-weight: 800;
}
.paper-blog-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.paper-blog-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 8px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--bg-sunken);
  color: var(--ink-secondary);
  font-size: 12px;
  font-weight: 700;
}
.paper-blog-tag-accent {
  border-color: rgba(15, 123, 108, 0.3);
  background: var(--accent-light);
  color: var(--accent-hover);
}
.paper-blog-neighbors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.paper-blog-neighbor {
  display: grid;
  min-width: 0;
  gap: 6px;
  min-height: 72px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-sunken);
}
.paper-blog-neighbor a {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--ink-primary);
  font-weight: 750;
  line-height: 1.4;
}
.paper-blog-neighbor a:hover { color: var(--accent-hover); }
.paper-blog-neighbor-empty {
  color: var(--ink-muted);
  font-size: 13px;
}
.paper-blog-comments {
  display: grid;
  gap: 14px;
  padding-top: 4px;
}
.paper-blog-comments-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
}
.paper-blog-comments-kicker {
  margin: 0 0 4px;
  color: var(--accent);
  font: 800 11px/1.2 var(--font-mono);
  letter-spacing: .08em;
}
.paper-blog-comments h3 {
  margin: 0;
  color: var(--ink-primary);
  font-size: 20px;
}
.paper-blog-comments-count {
  display: inline-grid;
  min-width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--bg-sunken);
  color: var(--ink-secondary);
  font: 700 12px/1 var(--font-mono);
}
.paper-blog-comments-empty {
  display: grid;
  gap: 4px;
  padding: 18px;
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
  background: rgba(248, 250, 247, 0.72);
  color: var(--ink-secondary);
}
.paper-blog-comments-empty strong { color: var(--ink-primary); }
.paper-mode-immersive {
  overflow: hidden;
  border-radius: 12px;
  background: #16140f;
  color: #f8f3e5;
}
.paper-immersive-stage {
  position: relative;
  min-height: 500px;
  padding: 24px;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(22,20,15,.99), rgba(22,20,15,.9) 45%, rgba(22,20,15,.36) 68%, rgba(22,20,15,.18)),
    var(--paper-cover-image, none) center right / min(610px, 48%) auto no-repeat,
    #16140f;
}
.paper-immersive-content {
  position: relative;
  z-index: 1;
  width: min(590px, 47%);
  padding-top: 12px;
}
.paper-mode-immersive .paper-detail-title {
  color: #fff8e8;
  font-size: clamp(28px, 3.2vw, 40px);
  line-height: 1.09;
}
.paper-mode-immersive .paper-detail-meta,
.paper-mode-immersive .eyebrow {
  color: #d8cfb8;
}
.paper-mode-immersive .meta-icon-link {
  background: rgba(255,255,255,.1);
  color: #f5e9c8;
}
.paper-mode-immersive .paper-fact-stats {
  max-width: 640px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-top: 24px;
}
.paper-mode-immersive .paper-fact-stat {
  border-color: rgba(255,255,255,.18);
  background: rgba(255,255,255,.08);
}
.paper-mode-immersive .paper-fact-stat span { color: #d8cfb8; }
.paper-mode-immersive .paper-fact-stat strong { color: #fff8e8; }
.paper-mode-immersive .paper-fact-stat:hover,
.paper-mode-immersive .paper-fact-stat:focus-visible,
.paper-mode-immersive .paper-fact-stat[aria-pressed="true"] {
  border-color: rgba(255,255,255,.42);
  background: rgba(255,255,255,.14);
}

/* ============ Yantao-style theme overrides ============ */
:root {
  --bg-base: #fafaf8;
  --bg-surface: #ffffff;
  --bg-sunken: #f3f2ef;
  --bg-sidebar: #f7f6f3;
  --ink-primary: #1a1a1a;
  --ink-body: #37352f;
  --ink-secondary: #6b6b6b;
  --ink-muted: #9b9b9b;
  --accent: #0f7b6c;
  --accent-light: #e6f4f1;
  --accent-hover: #0a5d52;
  --border: #e8e7e4;
  --border-strong: #d4d3cf;
  --shadow-sm: 0 1px 3px rgba(15, 45, 40, 0.05);
  --shadow-md: 0 10px 24px rgba(15, 45, 40, 0.09);
  --font-heading: "Noto Serif SC", "Source Serif 4", Georgia, serif;
  --font-body: "Noto Sans SC", "Aptos", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", monospace;
}
body {
  color: var(--ink-body);
  background:
    radial-gradient(circle at 12% 0%, rgba(15, 123, 108, 0.06), transparent 26rem),
    linear-gradient(180deg, #ffffff 0, var(--bg-base) 34rem);
  font: 15px/1.6 var(--font-body);
}
body::before {
  opacity: 0.22;
  background-image:
    linear-gradient(rgba(26,26,26,0.022) 1px, transparent 1px),
    linear-gradient(90deg, rgba(26,26,26,0.022) 1px, transparent 1px);
  background-size: 24px 24px;
}
main {
  width: min(1240px, calc(100% - 40px));
  margin: 0 auto;
  padding: 26px 0 54px;
}
.topbar {
  min-height: 58px;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  background: rgba(250, 250, 248, 0.88);
  backdrop-filter: blur(10px);
}
.brand strong {
  font-family: var(--font-heading);
  font-size: 20px;
  letter-spacing: 0;
}
.topbar nav { gap: 6px; }
.topbar nav a {
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--ink-secondary);
}
.topbar nav a[aria-current="page"],
.topbar nav a:hover {
  background: var(--accent-light);
  color: var(--accent-hover);
}
.home-link,
.lang-toggle,
.paper-detail-deep-reading-back,
.paper-blog-detail-link,
.pager button {
  border-radius: 6px;
}
.home-link {
  border-color: var(--border);
  background: #fff;
}
.lang-toggle {
  background: #f4f3f0;
  color: #111;
}
.lang-toggle[aria-pressed="true"] {
  background: var(--accent-light);
  color: var(--accent-hover);
}
.site-footer {
  width: min(1240px, calc(100% - 40px));
  margin: 0 auto;
  padding: 20px 0 34px;
  border-top: 1px solid var(--border);
  color: var(--ink-secondary);
}
h1, h2, h3 {
  font-family: var(--font-heading);
  line-height: 1.12;
  letter-spacing: 0;
  text-wrap: balance;
}
h1 { font-size: clamp(34px, 4.8vw, 60px); }
h2 { font-size: 24px; }
h3 { font-size: 18px; }
.hero,
.page-heading {
  padding: 28px 0 18px;
}
.hero {
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 28px;
}
.hero p,
.page-heading p,
.lead {
  max-width: 65ch;
  color: var(--ink-secondary);
  font-size: 16px;
}
.eyebrow {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.global-search,
.toolbar,
.metric-card,
.paper-card,
.cluster-card,
.blog-card,
.gap-panel,
.related-panel,
.paper-layout-panel,
.paper-summary-block,
.paper-layout-code-card,
.paper-layout-table-wrap,
.paper-layout-formula,
.paper-layout-data-table {
  border-radius: 6px;
  box-shadow: none;
}
.global-search,
.toolbar,
.metric-card,
.paper-card,
.cluster-card,
.blog-card,
.gap-panel,
.related-panel,
.paper-layout-panel,
.paper-summary-block,
.paper-layout-code-card,
.paper-layout-table-wrap {
  border: 1px solid var(--border);
  background: var(--bg-surface);
}
.global-search,
.toolbar {
  padding: 14px;
}
.metrics-grid {
  gap: 12px;
  margin: 16px 0 24px;
}
.metric-card {
  padding: 14px 16px;
}
.metric-card strong {
  font: 700 28px/1 var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.paper-card,
.cluster-card {
  padding: 14px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
}
.paper-card:hover,
.cluster-card:hover,
.blog-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow-md);
}
.blog-card {
  border: 1px solid var(--border);
  background: var(--bg-surface);
  box-shadow: none;
}
.blog-card-body {
  padding: 18px;
}
.blog-card-body h2 {
  font-size: 22px;
}
.blog-card-cover {
  border-right: 1px solid var(--border);
}
.paper-detail {
  width: min(1240px, calc(100vw - 32px));
  margin: 0 auto;
  transform: none;
  padding: 22px 0 44px;
}
.paper-detail-topbar {
  margin-bottom: 16px;
}
.paper-mode-toggle {
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: rgba(255,255,255,0.82);
}
.paper-mode-toggle button {
  border-radius: 6px;
}
.paper-mode-toggle button[aria-pressed="true"] {
  background: var(--accent-light);
  color: var(--accent-hover);
}
.paper-detail-layout {
  grid-template-columns: minmax(0, 700px) minmax(240px, 260px);
  gap: 28px;
}
.paper-detail-aside {
  top: 92px;
}
.paper-mode-deep-reading {
  width: min(1240px, 100%);
  margin: 0 auto;
}
.paper-detail.is-deep-reading-only .paper-mode-deep-reading {
  width: min(1240px, calc(100vw - 32px));
  margin: 0 auto;
}
.paper-detail.is-deep-reading-only .paper-blog-section {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.paper-detail.is-deep-reading-only .paper-blog-layout {
  grid-template-columns: minmax(0, 1fr) minmax(230px, 260px);
  gap: 32px;
}
.paper-detail.is-deep-reading-only .paper-blog-layout:has(.paper-blog-toc.is-collapsed) {
  grid-template-columns: minmax(0, 1fr) 48px;
  gap: 24px;
}
.paper-detail.is-deep-reading-only .paper-blog-prose {
  width: 100%;
  max-width: 780px;
}
.paper-detail.is-deep-reading-only .paper-blog-toc {
  top: 92px;
  padding: 14px 12px 14px 16px;
  border-radius: 6px;
  background: rgba(247, 246, 243, 0.92);
  box-shadow: 0 12px 28px rgba(31, 41, 55, 0.08);
}
.paper-blog-section {
  display: grid;
  gap: 22px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.paper-blog-meta {
  padding-bottom: 0;
  border-bottom: 0;
}
.paper-blog-title {
  margin: 4px 0 10px;
  max-width: 880px;
  font-size: clamp(28px, 3vw, 44px);
  line-height: 1.12;
}
.paper-blog-meta-row {
  align-items: flex-start;
  gap: 10px;
}
.paper-blog-meta-row p {
  color: var(--ink-secondary);
  font-size: 13px;
}
.paper-blog-detail-link {
  padding: 5px 10px;
  border: 1px solid var(--border-strong);
  background: #fff;
  color: var(--ink-primary);
  font-weight: 700;
}
.article-layout,
.paper-blog-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(230px, 260px);
  gap: 32px;
  align-items: start;
}
.article-aside,
.paper-blog-aside {
  position: sticky;
  top: 92px;
  align-self: start;
}
.article-main,
.paper-blog-prose {
  min-width: 0;
  width: 100%;
  max-width: 780px;
  line-height: 1.82;
}
.paper-blog-prose > h1:first-child {
  display: none;
}
.paper-blog-prose h1,
.paper-blog-prose h2,
.paper-blog-prose h3 {
  scroll-margin-top: 92px;
  margin: 10px 0 2px;
  color: var(--ink-primary);
  line-height: 1.26;
}
.paper-blog-prose h1 { font-size: 24px; }
.paper-blog-prose h2 { font-size: 20px; }
.paper-blog-prose h3 { font-size: 17px; }
.paper-blog-prose p {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 15px;
  line-height: 1.8;
}
.paper-blog-prose ul,
.paper-blog-prose ol {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 24px;
}
.paper-blog-prose code {
  border-radius: 4px;
  background: var(--bg-sunken);
  padding: 2px 5px;
  font: 0.92em/1.5 var(--font-mono);
}
.paper-blog-prose pre {
  margin: 2px 0;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #202522;
  padding: 16px;
  color: #eef4ef;
}
.paper-blog-code-block {
  overflow: hidden;
  border: 1px solid rgba(31, 41, 55, 0.18);
  border-radius: 6px;
  background: #202522;
  box-shadow: none;
}
.paper-blog-code-bar {
  min-height: 34px;
  padding: 5px 10px;
  background: #29332f;
  color: #cbd8d1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}
.paper-blog-code-language {
  color: #dbe9e1;
}
.paper-blog-code-copy {
  border-radius: 4px;
  color: #dbe9e1;
}
.paper-blog-image {
  gap: 8px;
  margin: 4px 0 10px;
}
.paper-blog-image img {
  max-width: min(100%, 640px);
  border: 1px solid var(--border);
  border-radius: 6px;
  background: white;
}
.paper-blog-footer,
.article-footer {
  display: grid;
  gap: 20px;
  margin-top: 12px;
  padding-top: 22px;
  border-top: 1px solid var(--border);
}
.article-tags,
.paper-blog-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.paper-blog-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.paper-blog-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 8px;
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  background: var(--bg-sunken);
  color: var(--ink-secondary);
  font-size: 12px;
  font-weight: 700;
}
.paper-blog-tag-accent {
  border-color: rgba(15, 123, 108, 0.3);
  background: var(--accent-light);
  color: var(--accent-hover);
}
.article-neighbors,
.paper-blog-neighbors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.neighbor-card,
.paper-blog-neighbor {
  display: grid;
  min-width: 0;
  gap: 6px;
  min-height: 72px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-sunken);
}
.neighbor-card a,
.paper-blog-neighbor a {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--ink-primary);
  font-weight: 700;
  line-height: 1.42;
}
.paper-blog-neighbor-empty {
  color: var(--ink-secondary);
  font-size: 13px;
}
.comments,
.paper-blog-comments {
  display: grid;
  gap: 14px;
}
.paper-blog-comments-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
}
.paper-blog-comments-kicker {
  margin: 0 0 4px;
  color: var(--accent);
  font: 800 11px/1.2 var(--font-mono);
  letter-spacing: 0.08em;
}
.paper-blog-comments h3 {
  margin: 0;
  font-size: 20px;
}
.paper-blog-comments-count {
  min-width: 28px;
  height: 28px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--bg-sunken);
  color: var(--ink-secondary);
  font: 700 12px/1 var(--font-mono);
}
.paper-blog-comments-empty {
  display: grid;
  gap: 4px;
  padding: 16px;
  border: 1px dashed var(--border-strong);
  border-radius: 6px;
  background: rgba(255,255,255,0.78);
  color: var(--ink-secondary);
}
.paper-blog-comments-empty strong {
  color: var(--ink-primary);
}
.paper-blog-toc {
  position: sticky;
  top: 92px;
  z-index: 4;
  display: grid;
  gap: 10px;
  width: 100%;
  max-height: calc(100vh - 126px);
  overflow: auto;
  padding: 14px 12px 14px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: rgba(247, 246, 243, 0.92);
  box-shadow: 0 12px 28px rgba(31, 41, 55, 0.08);
}
.paper-blog-toc-toggle {
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 8px;
  min-height: 32px;
  border-radius: 6px;
}
.paper-blog-toc-toggle:hover,
.paper-blog-toc-toggle:focus-visible {
  background: var(--accent-light);
}
.paper-blog-toc-toggle-icon {
  border: 1px solid rgba(15, 123, 108, 0.38);
  border-radius: 4px;
  background: #fff;
}
.paper-blog-toc-toggle-icon::before,
.paper-blog-toc-toggle-icon::after {
  background: var(--accent);
}
.paper-blog-toc strong {
  color: var(--ink-primary);
  font-size: 15px;
}
.paper-blog-toc-list {
  gap: 2px;
  padding-top: 8px;
}
.paper-blog-toc-link {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 8px;
  align-items: baseline;
  padding: 6px 0;
  color: var(--ink-secondary);
}
.paper-blog-toc-link:hover,
.paper-blog-toc-link:focus-visible,
.paper-blog-toc-link.is-active {
  color: var(--accent-hover);
}
.paper-blog-toc-link span {
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 13px;
}
.paper-blog-toc-link b {
  font-size: 14px;
  line-height: 1.35;
}
.paper-blog-toc-link.level-3 {
  grid-template-columns: 48px minmax(0, 1fr);
  padding-left: 12px;
}
.paper-layout-panel h2 {
  font-size: 18px;
}
.paper-summary-block {
  padding: 16px 16px 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.92), rgba(248,250,247,0.96)),
    var(--bg-surface);
}
.paper-summary-block h2 {
  margin: 4px 0 12px;
  font-size: 22px;
}
.paper-summary-prose p {
  margin: 0;
  color: var(--ink-primary);
  font-size: 14px;
  line-height: 1.7;
}
.paper-layout-code-card {
  padding: 10px;
  background: var(--bg-sunken);
}
.paper-layout-code-card pre {
  max-height: 260px;
  margin: 0;
  border: 1px solid rgba(31, 41, 55, 0.08);
  border-radius: 4px;
  background: #202522;
  padding: 10px;
  color: #eef4ef;
  font-size: 12px;
  line-height: 1.55;
}
.paper-layout-formula {
  min-height: 64px;
  padding: 14px 10px;
  border: 1px solid rgba(31, 41, 55, 0.1);
  background: #fff;
}
.paper-layout-table-wrap {
  overflow: auto;
  border: 1px solid rgba(31, 41, 55, 0.12);
  background: #fff;
}
.paper-layout-data-table {
  width: max-content;
  min-width: 100%;
  font-size: 12px;
  line-height: 1.45;
}
.paper-layout-data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #eaf4f0;
  color: #173f37;
  font-weight: 850;
}
.paper-layout-data-table th,
.paper-layout-data-table td {
  min-width: 104px;
  max-width: 240px;
  padding: 8px 10px;
  border-right: 1px solid rgba(31, 41, 55, 0.1);
  border-bottom: 1px solid rgba(31, 41, 55, 0.1);
}
.paper-layout-data-table tr:last-child td { border-bottom: 0; }
.paper-layout-data-table th:last-child,
.paper-layout-data-table td:last-child { border-right: 0; }
.paper-layout-preview-note {
  color: var(--ink-secondary) !important;
  font-size: 11px !important;
}
.paper-layout-quality.good {
  border-color: #17705f;
  background: #dff3ec;
  color: #0b4d40;
}
.paper-layout-quality.review {
  border-color: #9b6816;
  background: #fff1c9;
  color: #684407;
}
.paper-layout-quality.fallback {
  border-color: #a64b45;
  background: #fce4e1;
  color: #762d28;
}

/* ============ Yantao-style Memphis article finish ============ */
:root {
  --theme-ink: #111;
  --theme-cream: #fff9ee;
  --theme-paper: #fff;
  --theme-yellow: #f7d358;
  --theme-pink: #ff71ce;
  --theme-teal: #86ccca;
  --theme-blue: #5d8bd8;
  --theme-red: #ef476f;
  --theme-shadow-black: 6px 6px 0 #111;
  --memphis-border: #2f2f2f;
  --memphis-shadow: 5px 5px 0 rgba(47, 47, 47, 0.16);
  --memphis-soft-shadow: 3px 3px 0 rgba(47, 47, 47, 0.06);
  --accent-warm: #ffd166;
}
body {
  background:
    radial-gradient(circle at 12% 0%, rgba(15, 123, 108, 0.06), transparent 26rem),
    linear-gradient(180deg, #ffffff 0, #fbf7ea 38rem, var(--bg-base) 100%);
}
body::before {
  opacity: 0.32;
  background-size: 20px 20px;
}
.theme-card,
.theme-panel {
  border: 3px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: var(--theme-shadow-black);
}
.theme-control {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  color: var(--theme-ink);
}
.theme-topbar {
  min-height: 78px;
  padding: 0 36px;
  border-bottom: 3px solid var(--theme-ink);
  background: var(--theme-cream);
  box-shadow: 0 4px 0 rgba(17, 17, 17, 0.1);
  backdrop-filter: none;
}
.theme-topbar .brand strong {
  color: var(--theme-ink);
  font-family: "Archivo Black", "Noto Sans SC", system-ui, sans-serif;
}
.theme-topbar .brand span {
  color: #665b4b;
  font-weight: 700;
}
.theme-topbar nav a {
  border: 2px solid transparent;
  border-radius: 0;
}
.theme-topbar nav a[aria-current="page"] {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-yellow);
  color: var(--theme-ink);
  box-shadow: 3px 3px 0 rgba(17, 17, 17, 0.18);
}
.theme-topbar nav a:hover {
  border-color: var(--theme-ink);
  background: var(--theme-teal);
  color: var(--theme-ink);
}
.home-link,
.lang-toggle {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: #fff;
  color: var(--theme-ink);
}
.home-link:hover,
.lang-toggle:hover,
.lang-toggle[aria-pressed="true"] {
  background: var(--theme-pink);
  color: var(--theme-ink);
}
.theme-footer {
  padding: 18px 20px;
  border: 3px solid var(--theme-ink);
  border-width: 3px 0 0;
  background: var(--theme-cream);
}
.hero .eyebrow,
.page-heading .eyebrow,
.paper-blog-meta .eyebrow {
  display: inline-block;
  width: fit-content;
  padding: 3px 8px;
  border: 1px solid rgba(47, 47, 47, 0.36);
  border-radius: 3px;
  background: var(--accent-warm);
  color: var(--ink-primary);
  box-shadow: 2px 2px 0 rgba(47, 47, 47, 0.12);
}
.topbar nav a[aria-current="page"] {
  border: 1px solid rgba(15, 123, 108, 0.16);
}
.global-search,
.toolbar,
.metric-card,
.paper-card,
.cluster-card,
.blog-card,
.gap-panel,
.related-panel,
.paper-layout-panel,
.paper-summary-block {
  border-color: rgba(47, 47, 47, 0.14);
  box-shadow: var(--memphis-soft-shadow);
}
.paper-card:hover,
.cluster-card:hover,
.blog-card:hover {
  box-shadow: 4px 4px 0 rgba(47, 47, 47, 0.12);
}
.metric-card,
.cluster-card,
.gap-panel,
.related-panel,
.global-search,
.toolbar {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 4px 4px 0 rgba(17, 17, 17, 0.18);
}
.metric-card:nth-child(2n) { box-shadow: 5px 5px 0 var(--theme-yellow); }
.metric-card:nth-child(3n) { box-shadow: 5px 5px 0 var(--theme-teal); }
.toolbar input,
.toolbar select,
.global-search input,
.global-search select,
.pager button {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: #fff;
}
.pager button:hover,
.pager button:focus-visible {
  background: var(--theme-yellow);
  color: var(--theme-ink);
}
.fact-chip {
  border: 1px solid rgba(17, 17, 17, 0.52);
  border-radius: 0;
}
.fact-chip.method {
  background: var(--theme-blue);
  color: #fff;
}
.paper-layout-panel,
.paper-summary-block,
.paper-layout-code-card,
.paper-layout-table-wrap,
.paper-layout-formula,
.paper-layout-data-table,
.paper-evidence-graph {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 4px 4px 0 rgba(17, 17, 17, 0.13);
  transform: none;
}
.paper-layout-table-wrap,
.paper-layout-code-card,
.paper-layout-formula {
  overflow-x: auto;
}
.paper-layout-data-table th {
  background: var(--theme-yellow);
  color: var(--theme-ink);
}
.map-shell,
.starmap-shell {
  border: 3px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 6px 6px 0 var(--theme-blue);
}
.map-sidebar,
.starmap-sidebar {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-cream);
}
.map-controls,
.starmap-controls,
.map-legend,
.starmap-legend {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-cream);
}
.report-prose,
.digest-prose,
.synthesis-prose,
.narrative-prose {
  border: 3px solid var(--theme-ink);
  border-left: 8px solid var(--theme-yellow);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 5px 5px 0 rgba(17, 17, 17, 0.14);
}

/* Yantao home post-stack treatment for research paper cards. */
.paper-list {
  width: min(850px, 100%);
  gap: 18px;
}
.paper-post-card.reveal {
  grid-template-columns: 170px minmax(0, 1fr);
  gap: 20px;
  min-height: 172px;
  padding: 18px;
  border: 3px solid #111;
  border-radius: 0;
  background: #fff;
  box-shadow: 8px 8px 0 #222;
  transform: rotate(-0.8deg);
  transform-origin: center;
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.paper-post-card.reveal:nth-child(2n) {
  box-shadow: 8px 8px 0 #ff71ce;
  transform: rotate(0.7deg);
}
.paper-post-card.reveal:nth-child(3n) {
  box-shadow: 8px 8px 0 #86ccca;
}
.paper-post-card.reveal:hover {
  border-color: #111;
  box-shadow: 8px 11px 0 #222;
  transform: rotate(0) translateY(-4px);
}
.paper-post-card.reveal:nth-child(2n):hover {
  box-shadow: 8px 11px 0 #ff71ce;
}
.paper-post-card.reveal:nth-child(3n):hover {
  box-shadow: 8px 11px 0 #86ccca;
}
.paper-post-card .paper-card-media {
  align-self: center;
  width: 170px;
  max-width: 170px;
  min-height: 124px;
  aspect-ratio: 4 / 3;
  border: 1px solid #111;
  border-radius: 12px;
  background: #f6ecd9;
}
.paper-post-card .paper-cover {
  max-height: none;
}
.paper-post-card .paper-cover-empty::after {
  color: #45413b;
  font-size: 11px;
  letter-spacing: 0.08em;
}
.paper-post-card .paper-card-content {
  min-height: 132px;
  gap: 7px;
}
.paper-post-card .paper-title {
  color: #171717;
  font-family: "Archivo Black", "Noto Sans SC", "PingFang SC", system-ui, sans-serif;
  font-size: 18px;
  line-height: 1.16;
  letter-spacing: 0;
  -webkit-line-clamp: 2;
}
.paper-post-card .paper-title:hover {
  color: #0f7b6c;
  text-decoration-color: #f7d358;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}
.paper-post-card .paper-meta {
  margin: 0;
  color: #655d52;
  font-size: 12px;
  line-height: 1.45;
}
.paper-post-card .paper-card-body > p[data-lang] {
  margin: 1px 0 0;
  color: #3d3933;
  font-size: 13px;
  line-height: 1.52;
  -webkit-line-clamp: 2;
}
.paper-post-card .chip-row {
  align-self: end;
  margin-top: 2px;
}
.paper-post-card .fact-chip {
  min-height: 19px;
  border: 1px solid rgba(17, 17, 17, 0.22);
  border-radius: 0;
  font-size: 10px;
}
.blog-index-list {
  width: min(850px, 100%);
  gap: 18px;
}
.blog-post-card.reveal {
  grid-template-columns: 170px minmax(0, 1fr);
  gap: 20px;
  padding: 18px;
  overflow: visible;
  border: 3px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 8px 8px 0 var(--theme-ink);
  transform: rotate(-0.7deg);
}
.blog-post-card.reveal:nth-child(2n) {
  box-shadow: 8px 8px 0 var(--theme-pink);
  transform: rotate(0.7deg);
}
.blog-post-card.reveal:nth-child(3n) {
  box-shadow: 8px 8px 0 var(--theme-teal);
}
.blog-post-card.reveal:hover {
  border-color: var(--theme-ink);
  box-shadow: 8px 11px 0 var(--theme-ink);
  transform: rotate(0) translateY(-4px);
}
.blog-post-card .blog-card-media {
  min-height: 128px;
  border: 1px solid var(--theme-ink);
  border-radius: 12px;
  background: #f6ecd9;
  overflow: hidden;
}
.blog-post-card .blog-card-body {
  padding: 0;
}
.blog-post-card h2 {
  margin-top: 0;
  font-family: "Archivo Black", "Noto Sans SC", system-ui, sans-serif;
  font-size: 20px;
  line-height: 1.15;
}
.paper-blog-prose {
  padding: clamp(22px, 3vw, 38px);
  border: 2px solid var(--memphis-border);
  border-radius: 4px;
  background: #fffdf8;
  box-shadow: var(--memphis-shadow);
}
.paper-blog-prose h2 {
  position: relative;
  padding-bottom: 9px;
  border-bottom: 1px solid var(--border);
}
.paper-blog-prose h2::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: -2px;
  width: 58px;
  height: 3px;
  border-radius: 2px;
  background: var(--accent-warm);
}
.paper-blog-prose h3 {
  padding-left: 10px;
  border-left: 3px solid var(--accent);
}
.paper-blog-toc,
.paper-detail.is-deep-reading-only .paper-blog-toc {
  border: 2px solid var(--memphis-border);
  border-radius: 4px;
  background: #fffdf8;
  box-shadow: 4px 4px 0 rgba(47, 47, 47, 0.14);
}
.paper-blog-toc.is-collapsed,
.paper-detail.is-deep-reading-only .paper-blog-toc.is-collapsed {
  box-shadow: 3px 3px 0 rgba(47, 47, 47, 0.12);
}
.paper-blog-tag {
  border-color: rgba(47, 47, 47, 0.36);
}
.paper-blog-tag-accent {
  border-color: var(--memphis-border);
  background: var(--accent-warm);
  color: var(--ink-primary);
}
.neighbor-card,
.paper-blog-neighbor,
.paper-blog-comments-empty {
  border-color: rgba(47, 47, 47, 0.34);
  background: #fffdf8;
  box-shadow: 2px 2px 0 rgba(47, 47, 47, 0.08);
}

/* ============ Yantao article layout match ============ */
.paper-detail.is-deep-reading-only {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 56px;
  background:
    radial-gradient(circle at 1px 1px, rgba(91, 74, 49, 0.12) 1px, transparent 0) 0 0 / 18px 18px,
    #fff9ee;
}
.paper-detail.is-deep-reading-only .paper-detail-topbar {
  width: min(1180px, calc(100vw - 64px));
  margin: 0 auto;
  padding: 18px 0 10px;
  border: 0;
  background: transparent;
}
.paper-detail.is-deep-reading-only .paper-detail-deep-reading-bar {
  border: 1px solid rgba(47, 47, 47, 0.22);
  border-radius: 3px;
  background: #fffdf8;
  box-shadow: 2px 2px 0 rgba(47, 47, 47, 0.08);
}
.paper-detail.is-deep-reading-only .paper-mode-deep-reading {
  --paper-blog-toc-width: 260px;
  width: min(1180px, calc(100vw - 64px));
  max-width: none;
  margin-left: 30px;
  margin-right: auto;
}
.paper-detail.is-deep-reading-only .paper-blog-section {
  gap: 28px;
  padding: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-meta {
  width: 880px;
  max-width: calc(100vw - 64px);
  min-height: 174px;
  display: grid;
  align-content: end;
  gap: 10px;
  margin: 0;
  padding: 34px 0 28px;
  border: 0;
  background:
    linear-gradient(90deg, rgba(229, 239, 247, 0.86), rgba(255, 249, 238, 0.08));
}
.paper-detail.is-deep-reading-only .paper-blog-meta .eyebrow {
  margin: 0;
  border-color: rgba(47, 47, 47, 0.32);
  background: #f7d358;
  color: #1b1b1b;
}
.paper-detail.is-deep-reading-only .paper-blog-meta h1.paper-blog-title {
  max-width: 760px;
  margin: 0;
  color: #1b1b1b;
  font-family: "Archivo Black", "Noto Sans SC", "PingFang SC", system-ui, sans-serif;
  font-size: clamp(31px, 3.2vw, 44px);
  line-height: 1.08;
  letter-spacing: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-meta-row {
  justify-content: flex-start;
  gap: 16px;
  color: #61584b;
}
.paper-detail.is-deep-reading-only .paper-blog-layout {
  width: min(1180px, calc(100vw - 64px));
  max-width: none;
  grid-template-columns: 880px 260px;
  gap: 40px;
  align-items: start;
}
.paper-detail.is-deep-reading-only .paper-blog-prose,
.paper-detail.is-deep-reading-only .article-main.paper-blog-prose {
  width: 880px;
  max-width: 880px;
  gap: 12px;
  padding: 44px 54px 50px;
  border: 2px solid #2f2f2f;
  border-radius: 0;
  background: #fffdf8;
  box-shadow: 5px 5px 0 rgba(47, 47, 47, 0.18);
  color: #1b1b1b;
  font-family: "DM Sans", "Noto Sans SC", "PingFang SC", system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.9;
}
.paper-detail.is-deep-reading-only .paper-blog-prose h1 {
  font-family: "Archivo Black", "Noto Sans SC", "PingFang SC", system-ui, sans-serif;
}
.paper-detail.is-deep-reading-only .paper-blog-prose h2 {
  margin: 34px 0 14px;
  padding-bottom: 10px;
  font-size: 24px;
}
.paper-detail.is-deep-reading-only .paper-blog-prose h3 {
  margin: 24px 0 10px;
  padding-left: 12px;
  border-left: 4px solid #f7d358;
  color: #1b1b1b;
  font-size: 18px;
}
.paper-detail.is-deep-reading-only .paper-blog-prose p,
.paper-detail.is-deep-reading-only .paper-blog-prose li {
  color: #2f2a23;
  font-size: 16px;
  line-height: 1.92;
}
.paper-detail.is-deep-reading-only .paper-blog-prose blockquote {
  margin: 14px 0;
  padding: 12px 16px;
  border-left: 4px solid #f7d358;
  background: #fff7dd;
  color: #3c3428;
}
.paper-detail.is-deep-reading-only .paper-blog-image {
  margin: 18px 0 22px;
  justify-items: stretch;
}
.paper-detail.is-deep-reading-only .paper-blog-image img {
  width: auto;
  max-width: 100%;
  max-height: none;
  border: 1px solid rgba(47, 47, 47, 0.34);
  border-radius: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-image figcaption {
  max-width: 100%;
  color: #695f50;
  font-size: 13px;
}
.paper-detail.is-deep-reading-only .paper-blog-code-block,
.paper-detail.is-deep-reading-only .paper-blog-prose pre {
  border: 2px solid #2f2f2f;
  border-radius: 0;
  box-shadow: 3px 3px 0 rgba(47, 47, 47, 0.14);
}
.paper-detail.is-deep-reading-only .paper-blog-aside {
  position: fixed;
  top: 96px;
  left: min(calc(100vw - 292px), calc(50vw + 330px));
  width: 260px;
  display: grid;
  grid-template-columns: 1fr;
  grid-auto-flow: row;
  grid-auto-columns: auto;
  gap: 18px;
  z-index: 8;
}
.paper-detail.is-deep-reading-only .paper-blog-toc {
  position: static;
  grid-column: 1;
  grid-row: auto;
  width: 260px;
  max-height: calc(100vh - 124px);
  padding: 18px 18px 20px;
  border: 2px solid #2f2f2f;
  border-radius: 0;
  background: #fffdf8;
  box-shadow: 4px 4px 0 rgba(47, 47, 47, 0.18);
  backdrop-filter: none;
}
.paper-detail.is-deep-reading-only .paper-blog-toc.is-collapsed {
  width: 260px;
  max-height: calc(100vh - 124px);
  padding: 18px 18px 20px;
  overflow: auto;
  background: #fffdf8;
  box-shadow: 4px 4px 0 rgba(47, 47, 47, 0.18);
}
.paper-detail.is-deep-reading-only .paper-blog-toc.is-collapsed .paper-blog-toc-list {
  display: grid;
}
.paper-detail.is-deep-reading-only .paper-blog-toc.is-collapsed .paper-blog-toc-toggle strong {
  display: block;
}
.paper-detail.is-deep-reading-only .paper-blog-info {
  grid-column: 1;
  grid-row: auto;
  width: 260px;
  padding: 18px;
  border: 2px solid #2f2f2f;
  border-radius: 0;
  background: #fffdf8;
  box-shadow: 4px 4px 0 rgba(47, 47, 47, 0.18);
}
.paper-detail.is-deep-reading-only .paper-blog-info h3 {
  margin: 0 0 14px;
  color: #1b1b1b;
  font-size: 16px;
  line-height: 1.25;
}
.paper-detail.is-deep-reading-only .paper-blog-info dl {
  display: grid;
  gap: 10px;
  margin: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-info div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  align-items: baseline;
  padding-top: 10px;
  border-top: 1px solid rgba(47, 47, 47, 0.16);
}
.paper-detail.is-deep-reading-only .paper-blog-info div:first-child {
  padding-top: 0;
  border-top: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-info dt {
  color: #6b6257;
  font-size: 12px;
  font-weight: 800;
}
.paper-detail.is-deep-reading-only .paper-blog-info dd {
  min-width: 0;
  margin: 0;
  color: #1b1b1b;
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-toggle {
  min-height: auto;
  padding: 0 0 12px;
  border-bottom: 1px solid rgba(47, 47, 47, 0.18);
  border-radius: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-toc strong {
  color: #1b1b1b;
  font-size: 16px;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-list {
  gap: 0;
  padding-top: 10px;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-link {
  grid-template-columns: 44px minmax(0, 1fr);
  min-height: 30px;
  padding: 6px 0;
  color: #4f473d;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-link span {
  color: #0f7b6c;
  font-size: 12px;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-link b {
  font-size: 13px;
  line-height: 1.35;
}
.paper-detail.is-deep-reading-only .paper-blog-toc-link.is-active,
.paper-detail.is-deep-reading-only .paper-blog-toc-link:hover,
.paper-detail.is-deep-reading-only .paper-blog-toc-link:focus-visible {
  color: #1e66c1;
}
.paper-detail.is-deep-reading-only .article-footer.paper-blog-footer {
  width: 880px;
  max-width: calc(100vw - 64px);
  margin-top: 48px;
  padding-top: 0;
  border-top: 0;
}
.paper-detail.is-deep-reading-only .paper-blog-tags {
  min-height: 42px;
  padding: 10px 12px;
  border: 2px solid #2f2f2f;
  background: #fffdf8;
  box-shadow: 3px 3px 0 rgba(47, 47, 47, 0.12);
  justify-content: flex-start;
}
.paper-detail.is-deep-reading-only .paper-blog-footer-label,
.paper-detail.is-deep-reading-only .paper-blog-neighbor-label {
  color: #6b6257;
  font-size: 12px;
  font-weight: 850;
}
.paper-detail.is-deep-reading-only .paper-blog-tag {
  border: 2px solid rgba(47, 47, 47, 0.72);
  border-radius: 0;
  background: #fff9ee;
  color: #1b1b1b;
}
.paper-detail.is-deep-reading-only .paper-blog-tag-accent {
  background: #ffce5c;
}
.paper-detail.is-deep-reading-only .paper-blog-neighbors {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.paper-detail.is-deep-reading-only .paper-blog-neighbor,
.paper-detail.is-deep-reading-only .paper-blog-comments-empty {
  border: 2px solid #2f2f2f;
  border-radius: 0;
  background: #fffdf8;
  box-shadow: 3px 3px 0 rgba(47, 47, 47, 0.12);
}
.paper-detail.is-deep-reading-only .paper-blog-neighbor {
  min-height: 86px;
  padding: 16px 18px;
}
.paper-detail.is-deep-reading-only .paper-blog-neighbor a {
  color: #1b1b1b;
}
.paper-detail.is-deep-reading-only .paper-blog-neighbor a:hover,
.paper-detail.is-deep-reading-only .paper-blog-neighbor a:focus-visible {
  color: #1e66c1;
}
.paper-detail.is-deep-reading-only .paper-blog-comments {
  margin-top: 20px;
  padding: 22px 0 0;
  border-top: 2px solid rgba(47, 47, 47, 0.22);
}
.paper-immersive-evidence {
  display: grid;
  grid-template-columns: minmax(260px, 360px) minmax(0, 1fr);
  gap: 22px;
  padding: 24px;
  background: var(--bg-surface);
  color: var(--ink-body);
}
.paper-immersive-evidence-main {
  display: grid;
  gap: 18px;
  min-width: 0;
}
.back-link { display: inline-flex; margin-bottom: 18px; }
.paper-evidence-summary {
  display: block;
  max-height: calc(100vh - 176px);
  overflow: auto;
  padding-right: 4px;
}
.paper-evidence-summary h1,
.paper-evidence-summary h2,
.paper-evidence-summary h3 {
  margin: 14px 0 8px;
  color: var(--ink-primary);
  font-size: 16px;
  line-height: 1.25;
}
.paper-evidence-summary h1:first-child,
.paper-evidence-summary h2:first-child,
.paper-evidence-summary h3:first-child { margin-top: 0; }
.paper-evidence-summary p {
  margin: 0;
  color: var(--ink-body);
  font-size: 14px;
  line-height: 1.72;
  overflow-wrap: anywhere;
}
.paper-evidence-summary p + p { margin-top: 8px; }
.tab-list { display: flex; flex-wrap: wrap; gap: 8px; margin: 24px 0 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
.tab-list button { border: 1px solid var(--border); border-radius: 6px; background: white; padding: 7px 10px; cursor: pointer; }
.tab-list button[aria-selected="true"] { background: var(--accent-light); border-color: var(--accent); color: var(--accent-hover); }
.tab-panel { display: none; }
.tab-panel.is-active { display: block; }
.paper-fact-sections {
  display: grid;
  gap: 14px;
}
.paper-fact-section {
  scroll-margin-top: 92px;
}
.paper-fact-section[hidden] { display: none; }
.paper-fact-section-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin: 0 0 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.paper-fact-section-head h2 {
  margin: 0;
  color: var(--ink-primary);
  font-size: 18px;
  line-height: 1.2;
}
.paper-fact-section-head > span {
  display: inline-grid;
  place-items: center;
  min-width: 32px;
  height: 28px;
  border: 1px solid rgba(15, 123, 108, 0.22);
  border-radius: 999px;
  color: var(--accent-hover);
  background: rgba(15, 123, 108, 0.08);
  font: 800 13px/1 var(--font-mono);
}
.tab-panel,
.tab-panel ul,
.paper-fact-section,
.paper-fact-section ul,
.fact-row,
.fact-row * {
  min-width: 0;
}
.tab-panel ul, .paper-fact-section ul, .paper-detail > ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.fact-row {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(255,255,255,0.86);
  padding: 14px;
  overflow: hidden;
}
.fact-row div { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.fact-row p {
  margin: 10px 0;
  max-width: 72ch;
  overflow-wrap: anywhere;
  word-break: normal;
}
.cluster-paper-list { display: grid; gap: 12px; margin-top: 18px; }
.cluster-paper-card .paper-card-body > p[data-lang] { -webkit-line-clamp: 2; color: var(--ink-secondary); }
.cluster-evidence {
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  display: grid;
  gap: 8px;
}
.cluster-evidence .fact-chip { justify-self: start; }
.cluster-evidence ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.cluster-evidence li {
  padding: 8px 10px;
  border-left: 3px solid rgba(124, 58, 237, 0.38);
  background: var(--bg-sunken);
}
.cluster-evidence p { margin: 0; }
blockquote {
  max-width: 100%;
  margin: 10px 0;
  padding: 10px 12px;
  border-left: 3px solid var(--accent);
  background: var(--bg-sunken);
  color: var(--ink-secondary);
  overflow-wrap: anywhere;
  word-break: normal;
}
code { font-family: var(--font-mono); color: var(--ink-secondary); overflow-wrap: anywhere; }
.confidence { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.confidence.high { color: #0f7b6c; }
.confidence.mid { color: #b45309; }
.confidence.low { color: #dc2626; }
.cluster-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.report-prose { max-width: 900px; border: 1px solid var(--border); border-radius: 6px; background: white; padding: 18px 22px; }
.report-prose p { margin: 9px 0; }
.report-prose .bullet { padding-left: 14px; border-left: 2px solid var(--border); }
.map-shell {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
  min-height: 620px;
  margin-bottom: 18px;
}
.map-sidebar, .map-canvas-wrap, .report-details {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}
.map-sidebar { padding: 16px; align-self: start; position: sticky; top: 78px; }
.map-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 12px 0 16px; }
.map-stats span { padding: 10px; border-radius: 6px; background: var(--bg-sunken); color: var(--ink-secondary); font-size: 12px; }
.map-stats strong { display: block; color: var(--ink-primary); font: 700 20px/1 var(--font-mono); font-variant-numeric: tabular-nums; }
.map-controls { display: flex; flex-wrap: wrap; gap: 7px; margin: 0 0 16px; }
.map-controls button {
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: white;
  padding: 6px 9px;
  cursor: pointer;
}
.map-controls button[aria-pressed="true"], .map-controls button:hover {
  border-color: var(--accent);
  background: var(--accent-light);
  color: var(--accent-hover);
}
.map-selection { border-top: 1px solid var(--border); padding-top: 12px; }
.map-selection p { margin: 6px 0 0; color: var(--ink-secondary); }
.map-selection a { display: inline-block; margin-top: 8px; font-weight: 700; }
.map-canvas-wrap { min-height: 620px; overflow: hidden; background: radial-gradient(circle at 50% 50%, rgba(15,123,108,0.08), transparent 32rem), var(--bg-surface); }
.research-map { display: block; width: 100%; height: 620px; }
.starmap-shell {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
  min-height: 720px;
}
.starmap-sidebar, .starmap-canvas-wrap {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #0b0d13;
  box-shadow: var(--shadow-sm);
}
.starmap-sidebar {
  padding: 16px;
  position: sticky;
  top: 78px;
  color: #d2d5db;
}
.starmap-sidebar .map-stats span,
.starmap-sidebar .map-selection,
.starmap-sidebar .map-controls button {
  background: rgba(255,255,255,0.04);
  border-color: rgba(212, 169, 87, 0.24);
  color: #d2d5db;
}
.starmap-canvas-wrap {
  min-height: 720px;
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 20%, rgba(104, 82, 185, 0.18), transparent 20rem),
    radial-gradient(circle at 75% 28%, rgba(212, 169, 87, 0.16), transparent 18rem),
    radial-gradient(circle at 50% 60%, rgba(71, 156, 166, 0.12), transparent 24rem),
    #07090f;
}
.starmap-canvas { display: block; width: 100%; height: 720px; }
.starmap-cluster {
  fill-opacity: 0.12;
  stroke-opacity: 0.34;
}
.starmap-edge { stroke: rgba(212, 169, 87, 0.18); stroke-width: 1; }
.starmap-edge[data-type="author"] { stroke: rgba(240, 240, 245, 0.18); }
.starmap-edge[data-type="method"] { stroke: rgba(91, 163, 179, 0.24); }
.starmap-edge[data-type="dataset"] { stroke: rgba(125, 124, 242, 0.22); }
.starmap-edge[data-type="citation"] { stroke: rgba(212, 169, 87, 0.26); }
.starmap-node circle { stroke: rgba(255,255,255,0.9); stroke-width: 1.5; }
.starmap-node.paper circle { fill: #d4a957; }
.starmap-node.author circle { fill: #f3f4f6; }
.starmap-node.method circle { fill: #5ba3b3; }
.starmap-node.dataset circle { fill: #7d7cf2; }
.starmap-label { fill: #edf0f4; font: 11px var(--font-body); pointer-events: none; }
.starmap-selection a { color: #f1cd7b; }
.starmap-selection img {
  width: 100%;
  max-width: 260px;
  max-height: 180px;
  aspect-ratio: 4 / 3;
  margin-top: 10px;
  border-radius: 6px;
  object-fit: cover;
}
.report-prose img,
.paper-summary-block img {
  width: auto;
  max-width: 100%;
  max-height: 520px;
  margin: 12px 0;
  border-radius: 6px;
}
.map-edge { stroke: rgba(55,53,47,0.18); stroke-width: 1; transition: opacity 180ms ease, stroke-width 180ms ease; }
.map-edge.is-muted { opacity: .08; }
.map-edge.is-active { stroke: var(--accent); stroke-width: 2; opacity: .85; }
.map-node { cursor: pointer; transition: opacity 180ms ease, transform 180ms ease; transform-box: fill-box; transform-origin: center; }
.map-node:hover, .map-node.is-active { transform: scale(1.08); }
.map-node.is-muted { opacity: .18; }
.map-node circle { stroke: white; stroke-width: 2; }
.map-node.topic circle { fill: var(--accent); }
.map-node.paper circle { fill: #58616a; }
.map-node.method circle { fill: var(--tag-method); }
.map-node.claim circle { fill: var(--tag-claim); }
.map-node.limitation circle { fill: var(--tag-limitation); }
.map-node.dataset circle { fill: var(--tag-dataset); }
.map-node.benchmark circle { fill: var(--tag-benchmark); }
.map-label { pointer-events: none; fill: var(--ink-primary); font: 11px var(--font-body); paint-order: stroke; stroke: white; stroke-width: 3px; stroke-linejoin: round; }
.report-details { padding: 12px 14px; }
.report-details summary { cursor: pointer; color: var(--accent); font-weight: 700; }
.report-details .report-prose { margin-top: 12px; max-width: none; border: 0; padding: 0; box-shadow: none; }
.gap-layout {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 16px;
  align-items: start;
  margin-bottom: 16px;
}
.gap-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
  margin-bottom: 18px;
}
.gap-coverage-panel {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
  padding: 16px;
}
.gap-coverage-panel > p { color: var(--ink-secondary); margin: 8px 0 14px; }
.gap-coverage-panel ul, .gap-paper-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.coverage-row {
  display: grid;
  grid-template-columns: minmax(120px, max-content) minmax(120px, 1fr) minmax(100px, max-content);
  gap: 10px;
  align-items: center;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}
.coverage-row:first-child { border-top: 0; }
.coverage-row > * { min-width: 0; }
.gap-lowest-panel .coverage-row {
  grid-template-columns: minmax(104px, max-content) minmax(88px, 1fr) minmax(86px, max-content);
}
.coverage-row div:first-child { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; }
.coverage-row strong { font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--ink-primary); }
.coverage-row p { margin: 0; color: var(--ink-secondary); font-size: 13px; overflow-wrap: anywhere; white-space: normal; }
.coverage-track {
  height: 9px;
  border-radius: 999px;
  background: var(--bg-sunken);
  overflow: hidden;
}
.coverage-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), #6aa99c);
}
.gap-paper-row {
  display: grid;
  gap: 5px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}
.gap-paper-row:first-child { border-top: 0; }
.gap-paper-row > a { color: var(--ink-primary); font-weight: 700; }
.gap-paper-row > span, .gap-paper-row small { color: var(--ink-secondary); }
.gap-paper-row small { font-size: 12px; }
.digest-layout {
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
  margin-bottom: 18px;
}
.digest-sidebar {
  position: sticky;
  top: 78px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
  padding: 16px;
}
.digest-sidebar h2 + ul { margin-top: 10px; }
.digest-sidebar ul, .digest-findings ul {
  list-style: none;
  margin: 0 0 18px;
  padding: 0;
  display: grid;
  gap: 9px;
}
.digest-sidebar li {
  display: grid;
  gap: 3px;
  padding: 9px 0;
  border-top: 1px solid var(--border);
}
.digest-sidebar li:first-child { border-top: 0; }
.digest-sidebar li span { color: var(--ink-secondary); font-size: 13px; }
.digest-main { display: grid; gap: 18px; }
.digest-paper-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.digest-paper, .digest-findings {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}
.digest-paper { padding: 14px; }
.digest-paper p { margin: 8px 0; }
.digest-paper span { color: var(--ink-secondary); font-size: 13px; }
.digest-findings { padding: 16px; }
.finding-row {
  display: grid;
  gap: 7px;
  padding: 12px 0;
  border-top: 1px solid var(--border);
}
.finding-row:first-child { border-top: 0; }
.finding-row div { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.finding-row strong { font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--accent); }
.finding-row p { margin: 0; }
.synthesis-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: start;
  margin-bottom: 18px;
}
.synthesis-main { display: grid; gap: 14px; }
.synthesis-band, .synthesis-aside, .synthesis-notes, .synthesis-targets {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}
.synthesis-band, .synthesis-aside, .synthesis-notes, .synthesis-targets { padding: 16px; }
.synthesis-band > p, .synthesis-aside small { color: var(--ink-secondary); }
.synthesis-band ul, .synthesis-notes ul, .synthesis-targets ul {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: grid;
  gap: 10px;
}
.synthesis-coverage-row {
  display: grid;
  grid-template-columns: 180px minmax(120px, 1fr) 150px;
  gap: 10px;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.synthesis-coverage-row:first-child { border-top: 0; padding-top: 0; }
.synthesis-coverage-row div:first-child, .synthesis-note div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.synthesis-coverage-row strong, .synthesis-note strong, .synthesis-risk strong {
  color: var(--ink-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.synthesis-coverage-row p { margin: 0; color: var(--ink-secondary); font-size: 13px; }
.synthesis-aside {
  position: sticky;
  top: 78px;
  display: grid;
  gap: 14px;
}
.synthesis-risk {
  display: grid;
  gap: 7px;
  padding: 12px;
  border-radius: 6px;
  background: var(--bg-sunken);
}
.synthesis-risk span { color: var(--ink-secondary); }
.synthesis-risk strong { font-size: 24px; line-height: 1; }
.synthesis-note {
  display: grid;
  gap: 8px;
  padding: 12px 0;
  border-top: 1px solid var(--border);
}
.synthesis-note:first-child { border-top: 0; }
.synthesis-note p { margin: 0; }
.synthesis-targets { margin: 0 0 18px; }
.synthesis-targets ul { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
.synthesis-targets li {
  display: grid;
  gap: 4px;
  padding: 10px;
  border-radius: 6px;
  background: var(--bg-sunken);
}
.synthesis-targets li span { color: var(--ink-primary); font-weight: 700; overflow-wrap: anywhere; }
.synthesis-targets li small { color: var(--ink-secondary); }
.narrative-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  align-items: start;
  margin-bottom: 18px;
}
.narrative-main { display: grid; gap: 16px; }
.narrative-panel, .narrative-aside {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
  padding: 16px;
}
.narrative-coverage-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.narrative-list, .narrative-findings, .narrative-actions {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: grid;
  gap: 10px;
}
.narrative-list li {
  padding: 11px 0;
  border-top: 1px solid var(--border);
}
.narrative-list li:first-child { border-top: 0; padding-top: 0; }
.narrative-findings {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.narrative-finding {
  display: grid;
  gap: 8px;
  min-width: 0;
  padding: 12px;
  border-radius: 6px;
  background: var(--bg-sunken);
}
.narrative-finding-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.narrative-finding-head strong, .narrative-action strong {
  color: var(--ink-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.narrative-finding p { margin: 0; }
.narrative-finding small, .narrative-action small {
  display: block;
  color: var(--ink-secondary);
}
.narrative-finding blockquote {
  margin: 0;
  font-size: 13px;
}
.narrative-finding code {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
.narrative-aside {
  position: sticky;
  top: 78px;
  display: grid;
  gap: 16px;
}
.caution-list li {
  border-left: 3px solid var(--tag-limitation);
  padding-left: 10px;
}
.narrative-action {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border-radius: 6px;
  background: var(--bg-sunken);
}
.narrative-action div {
  display: grid;
  place-items: center;
  align-self: start;
  min-height: 54px;
  border-radius: 6px;
  background: white;
  border: 1px solid var(--border);
}
.narrative-action div span {
  color: var(--ink-secondary);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .08em;
}
.narrative-action p { margin: 0; }
.narrative-action b { display: block; color: var(--ink-primary); margin-bottom: 3px; }
.empty-state { color: var(--ink-secondary); }
.site-footer { width: min(1240px, calc(100% - 40px)); margin: 0 auto; padding: 22px 0 36px; border-top: 1px solid var(--border); display: flex; gap: 16px; color: var(--ink-secondary); }
.reveal { opacity: 1; transform: none; }
@keyframes reveal { from { opacity: 1; transform: none; } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; scroll-behavior: auto !important; }
}
@media (max-width: 880px) {
  .topbar { position: static; align-items: flex-start; flex-direction: column; width: 100%; max-width: 100%; min-width: 0; padding: 12px 18px; overflow: hidden; }
  .topbar nav { width: 100%; max-width: 100%; min-width: 0; flex-wrap: wrap; overflow-x: visible; }
  .topbar-actions { width: 100%; justify-content: space-between; }
  .lang-toggle { justify-content: flex-end; }
  main, .site-footer { width: min(100% - 28px, 1240px); }
  .hero, .dashboard-grid { grid-template-columns: 1fr; }
  .map-shell { grid-template-columns: 1fr; min-height: auto; }
  .map-sidebar { position: static; }
  .map-canvas-wrap, .research-map { min-height: 460px; height: 460px; }
  .starmap-shell { grid-template-columns: 1fr; min-height: auto; }
  .starmap-sidebar { position: static; }
  .starmap-canvas-wrap, .starmap-canvas { min-height: 480px; height: 480px; }
  .gap-layout, .gap-columns, .digest-layout, .synthesis-layout, .narrative-layout, .narrative-coverage-grid { grid-template-columns: 1fr; }
  .digest-sidebar, .synthesis-aside, .narrative-aside { position: static; }
  .digest-paper-grid, .narrative-findings { grid-template-columns: 1fr; }
  .coverage-row, .synthesis-coverage-row { grid-template-columns: 1fr; }
  .metrics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .toolbar { grid-template-columns: 1fr; }
  .paper-card { grid-template-columns: 1fr; }
  .paper-list { width: 100%; }
  .paper-post-card.reveal,
  .paper-post-card.reveal:nth-child(2n) {
    grid-template-columns: 1fr;
    gap: 14px;
    min-height: 0;
    padding: 14px;
    transform: none;
  }
  .paper-post-card.reveal:hover,
  .paper-post-card.reveal:nth-child(2n):hover,
  .paper-post-card.reveal:nth-child(3n):hover {
    transform: translateY(-2px);
  }
  .paper-post-card .paper-card-media {
    width: min(100%, 280px);
    max-width: 280px;
    min-height: 0;
  }
  .blog-post-card.reveal,
  .blog-post-card.reveal:nth-child(2n) {
    grid-template-columns: 1fr;
    transform: none;
  }
  .blog-post-card.reveal:hover { transform: translateY(-2px); }
  .blog-index-stats, .blog-card-footer { align-items: flex-start; flex-direction: column; }
  .blog-card { grid-template-columns: 1fr; }
  .blog-card-cover { min-height: 150px; border-right: 0; border-bottom: 1px solid var(--border); }
  .paper-detail { width: 100%; margin-left: 0; transform: none; }
  .paper-detail-layout { grid-template-columns: 1fr; gap: 18px; }
  .paper-detail-aside { position: static; }
  .paper-detail-topbar { align-items: flex-start; flex-direction: column; }
  .paper-mode-deep-reading { width: 100%; }
  .paper-detail.is-deep-reading-only .paper-mode-deep-reading { width: 100%; margin-left: 0; }
  .paper-blog-aside { position: static; }
  .paper-blog-layout { grid-template-columns: 1fr; gap: 16px; }
  .paper-detail.is-deep-reading-only .paper-blog-layout,
  .paper-detail.is-deep-reading-only .paper-blog-layout:has(.paper-blog-toc.is-collapsed) {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .paper-detail.is-deep-reading-only .paper-blog-prose,
  .paper-blog-prose { width: 100%; max-width: 100%; }
  .paper-blog-toc {
    position: fixed;
    top: auto;
    bottom: 16px;
    left: auto;
    right: 16px;
    width: min(340px, calc(100vw - 32px));
    max-height: min(54vh, 420px);
    padding: 14px;
    background: rgba(248, 250, 247, 0.92);
    box-shadow: 0 20px 56px rgba(31, 41, 55, 0.2);
    backdrop-filter: blur(18px);
  }
  .paper-detail.is-deep-reading-only .paper-blog-toc {
    position: fixed;
    top: auto;
    bottom: 16px;
    left: auto;
    right: 16px;
    width: min(340px, calc(100vw - 32px));
    max-height: min(54vh, 420px);
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: rgba(248, 250, 247, 0.92);
    box-shadow: 0 20px 56px rgba(31, 41, 55, 0.2);
    backdrop-filter: blur(18px);
  }
  .paper-blog-toc.is-collapsed {
    right: 16px;
    width: 46px;
    padding: 8px;
    max-height: 48px;
    background: rgba(248, 250, 247, 0.94);
  }
  .paper-detail.is-deep-reading-only .paper-blog-toc.is-collapsed {
    right: 16px;
    width: 46px;
    padding: 8px;
    max-height: 48px;
    background: rgba(248, 250, 247, 0.94);
  }
  .paper-detail.is-deep-reading-only .paper-blog-toc-toggle { padding: 4px 6px; }
  .paper-blog-toc-list { grid-template-columns: 1fr; max-height: min(42vh, 330px); overflow: auto; }
  .paper-blog-toc-link,
  .paper-blog-toc-link.level-3 { grid-template-columns: 38px minmax(0, 1fr); padding-left: 0; }
  .paper-blog-info { display: none; }
  .paper-blog-neighbors { grid-template-columns: 1fr; }
  .paper-mode-workbench, .paper-immersive-evidence { grid-template-columns: 1fr; }
  .paper-workbench-sidebar, .paper-workbench-aside { position: static; padding-right: 0; border-right: 0; }
  .paper-workbench-aside .paper-summary-block { max-height: none; overflow: hidden; }
  .paper-immersive-stage { min-height: auto; padding: 20px 16px; background-size: 760px auto; }
  .paper-immersive-content { width: 100%; padding-top: 10px; }
  .paper-mode-immersive .paper-detail-title { font-size: 28px; }
  .paper-fact-stats,
  .paper-mode-immersive .paper-fact-stats { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 5px; }
  .paper-fact-stat { padding: 6px 4px; gap: 3px; }
  .paper-fact-stat span { font-size: 9px; }
  .paper-fact-stat strong { font-size: 13px; }
  .paper-layout-metrics,
  .paper-layout-compact,
  .paper-layout-status { grid-template-columns: 1fr 1fr; }
  .paper-evidence-graph-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .paper-evidence-fact-row {
    grid-template-columns: 1fr;
    grid-template-areas: "meta" "statement" "evidence";
    gap: 8px;
  }
  .paper-evidence-link,
  .paper-evidence-reference { grid-template-columns: 1fr; gap: 3px; }
  .paper-layout-code-card pre { max-height: 220px; }
  .paper-summary-block { margin-top: 4px; }
  h1 { font-size: 34px; }
}
"""


SITE_JS = """
(() => {
  const setupLanguage = () => {
    const root = document.documentElement;
    const toggle = document.querySelector('[data-lang-toggle-button]');
    const label = toggle ? toggle.querySelector('[data-lang-toggle-label]') : null;
    const apply = (lang) => {
      const normalized = lang === 'zh' ? 'zh' : 'en';
      root.dataset.lang = normalized;
      try { window.localStorage.setItem('airesearch.lang', normalized); } catch (_error) {}
      if (toggle) {
        toggle.setAttribute('aria-pressed', String(normalized === 'zh'));
        toggle.setAttribute('aria-label', normalized === 'zh' ? 'Switch to English' : '切换到中文');
        toggle.title = normalized === 'zh' ? 'Switch to English' : '切换到中文';
      }
      if (label) label.textContent = normalized === 'zh' ? 'EN' : '简';
    };
    const initial = (() => {
      try { return window.localStorage.getItem('airesearch.lang') || 'en'; } catch (_error) { return 'en'; }
    })();
    if (toggle) {
      toggle.addEventListener('click', () => apply(root.dataset.lang === 'zh' ? 'en' : 'zh'));
    }
    apply(initial);
  };

  const setupSearch = () => {
    const forms = document.querySelectorAll('[data-search-root]');
    forms.forEach((form) => {
      const root = form.dataset.searchRoot || '.';
      const input = form.querySelector('input[type="search"]');
      const scope = form.querySelector('[data-search-scope]');
      const results = form.querySelector('.search-results');
      if (!input || !results) return;
      let entries = [];
      fetch(`${root}/api/search-index.json`)
        .then((response) => response.ok ? response.json() : [])
        .then((payload) => { entries = Array.isArray(payload) ? payload : []; })
        .catch(() => { entries = []; });
      const fieldForScope = (value) => ({
        title: 'title_terms',
        author: 'author_terms',
        method: 'method_terms',
        dataset: 'dataset_terms',
        year: 'year_terms'
      }[value] || 'terms');
      const apply = () => {
        const query = input.value.trim().toLowerCase();
        if (!query) {
          results.innerHTML = '';
          return;
        }
        const field = fieldForScope(scope ? scope.value : 'all');
        const hits = entries.filter((entry) => String(entry[field] || entry.terms || '').includes(query)).slice(0, 8);
        results.innerHTML = hits.length ? hits.map((entry) => `
          <a class="search-hit" href="${root}/${entry.url}">
            <strong>${escapeHtml(entry.title || entry.id)}</strong>
            <small>${escapeHtml(entry.type || 'result')} · ${escapeHtml(entry.subtitle || '')}</small>
          </a>
        `).join('') : '<p class="empty-state">No matches found.</p>';
      };
      input.addEventListener('input', apply);
      if (scope) scope.addEventListener('change', apply);
    });
  };

  const setupTabs = () => {
    document.querySelectorAll('.tab-list').forEach((list) => {
      const buttons = Array.from(list.querySelectorAll('[data-tab]'));
      const scope = list.closest('[data-tab-scope]') || document;
      const panels = Array.from(scope.querySelectorAll('.tab-panel'));
      buttons.forEach((button) => {
        button.addEventListener('click', () => {
          buttons.forEach((item) => item.setAttribute('aria-selected', String(item === button)));
          panels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.panel === button.dataset.tab));
        });
      });
    });
  };

  const setupPaperFactPanels = () => {
    const apply = (mode, factType, shouldScroll) => {
      const buttons = Array.from(mode.querySelectorAll('[data-paper-fact-button]'));
      const sections = Array.from(mode.querySelectorAll('[data-fact-section]'));
      sections.forEach((section) => {
        section.hidden = section.dataset.factSection !== factType;
      });
      buttons.forEach((button) => {
        button.setAttribute('aria-pressed', String(button.dataset.paperFactButton === factType));
      });
      if (shouldScroll) {
        const target = sections.find((section) => section.dataset.factSection === factType);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };
    document.querySelectorAll('[data-paper-mode]').forEach((mode) => {
      const buttons = Array.from(mode.querySelectorAll('[data-paper-fact-button]'));
      const sections = Array.from(mode.querySelectorAll('[data-fact-section]'));
      if (!buttons.length || !sections.length) return;
      const initial = buttons.find((button) => button.getAttribute('aria-pressed') === 'true')?.dataset.paperFactButton || buttons[0].dataset.paperFactButton;
      apply(mode, initial, false);
    });
    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-paper-fact-button]');
      if (!button) return;
      const mode = button.closest('[data-paper-mode]');
      if (!mode) return;
      event.preventDefault();
      apply(mode, button.dataset.paperFactButton, true);
    });
  };

  const setupPaperDetailMode = () => {
    document.querySelectorAll('[data-paper-detail-view]').forEach((root) => {
      const modes = Array.from(root.querySelectorAll('[data-paper-mode]'));
      const buttons = Array.from(root.querySelectorAll('[data-paper-mode-button]'));
      if (!modes.length || !buttons.length) return;
      const storageKey = 'airesearch-paper-detail-mode';
      const available = new Set(modes.map((mode) => mode.dataset.paperMode));
      const modeFromHash = () => {
        const hash = window.location.hash.replace(/^#/, '');
        if (hash === 'deep-reading' || hash === 'paper-deep-reading') return 'deep-reading';
        if (available.has(hash)) return hash;
        return '';
      };
      const stored = (() => {
        try { return localStorage.getItem(storageKey); } catch (_error) { return ''; }
      })();
      const initial = modeFromHash() || (available.has(stored) ? stored : 'workbench');
      const apply = (modeName, options = {}) => {
        const selected = available.has(modeName) ? modeName : 'workbench';
        if (options.updateHash && selected === 'deep-reading' && window.location.hash !== '#deep-reading') {
          history.replaceState(null, '', '#deep-reading');
        }
        const deepReadingOnly = selected === 'deep-reading' && (window.location.hash === '#deep-reading' || window.location.hash === '#paper-deep-reading');
        root.classList.toggle('is-deep-reading-only', deepReadingOnly);
        modes.forEach((mode) => { mode.hidden = mode.dataset.paperMode !== selected; });
        buttons.forEach((button) => {
          const active = button.dataset.paperModeButton === selected;
          button.setAttribute('aria-pressed', String(active));
          button.setAttribute('aria-selected', String(active));
          button.tabIndex = active ? 0 : -1;
        });
        try { localStorage.setItem(storageKey, selected); } catch (_error) {}
      };
      buttons.forEach((button) => button.addEventListener('click', () => apply(button.dataset.paperModeButton, { updateHash: true })));
      buttons.forEach((button, index) => button.addEventListener('keydown', (event) => {
        let nextIndex = -1;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') nextIndex = (index + 1) % buttons.length;
        if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') nextIndex = (index - 1 + buttons.length) % buttons.length;
        if (event.key === 'Home') nextIndex = 0;
        if (event.key === 'End') nextIndex = buttons.length - 1;
        if (nextIndex < 0) return;
        event.preventDefault();
        const nextButton = buttons[nextIndex];
        apply(nextButton.dataset.paperModeButton, { updateHash: true });
        nextButton.focus();
      }));
      window.addEventListener('hashchange', () => {
        const next = modeFromHash();
        if (next) apply(next);
      });
      apply(initial);
    });
  };

  const setupPaperBlogToc = () => {
    const mobileQuery = window.matchMedia('(max-width: 880px)');
    document.querySelectorAll('[data-paper-blog-toc]').forEach((toc, index) => {
      const toggle = toc.querySelector('[data-paper-blog-toc-toggle]');
      const links = Array.from(toc.querySelectorAll('.paper-blog-toc-link'));
      const section = toc.closest('[data-paper-blog-section]') || document;
      const headings = Array.from(section.querySelectorAll('h1, h2, h3'));
      const headingById = new Map(
        links
          .map((link) => {
            const id = decodeURIComponent((link.getAttribute('href') || '').replace(/^#/, ''));
            return [id, headings.find((heading) => heading.id === id)];
          })
          .filter(([, heading]) => heading)
      );
      if (!toggle) return;
      const storageKey = `airesearch.paperBlogToc.${index}`;
      const setActive = (activeLink) => {
        links.forEach((link) => {
          const active = link === activeLink;
          link.classList.toggle('is-active', active);
          if (active) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        });
      };
      const setCollapsed = (collapsed, persist) => {
        toc.classList.toggle('is-collapsed', collapsed);
        toggle.setAttribute('aria-expanded', String(!collapsed));
        toggle.title = collapsed ? '展开目录' : '收起目录';
        if (persist && !mobileQuery.matches) {
          try { window.localStorage.setItem(storageKey, collapsed ? 'collapsed' : 'expanded'); } catch (_error) {}
        }
      };
      const initialCollapsed = (() => {
        if (mobileQuery.matches) return true;
        try { return window.localStorage.getItem(storageKey) === 'collapsed'; } catch (_error) { return false; }
      })();
      setCollapsed(initialCollapsed, false);
      toggle.addEventListener('click', () => setCollapsed(!toc.classList.contains('is-collapsed'), true));
      links.forEach((link) => {
        link.addEventListener('click', () => {
          setActive(link);
          if (mobileQuery.matches) setCollapsed(true, false);
        });
      });
      const initialHash = decodeURIComponent(window.location.hash.replace(/^#/, ''));
      const initialLink = links.find((link) => link.getAttribute('href') === `#${initialHash}`) || links[0];
      setActive(initialLink);
      if (typeof window.IntersectionObserver === 'function' && headingById.size) {
        const observer = new IntersectionObserver((entries) => {
          const visible = entries
            .filter((entry) => entry.isIntersecting)
            .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
          if (!visible.length) return;
          const activeHeading = visible[0].target;
          const activeLink = links.find((link) => link.getAttribute('href') === `#${activeHeading.id}`);
          if (activeLink) setActive(activeLink);
        }, { rootMargin: '-96px 0px -62% 0px', threshold: [0, 1] });
        headingById.forEach((heading) => observer.observe(heading));
      }
      if (typeof mobileQuery.addEventListener === 'function') {
        mobileQuery.addEventListener('change', (event) => {
          if (event.matches) {
            setCollapsed(true, false);
            return;
          }
          let collapsed = false;
          try { collapsed = window.localStorage.getItem(storageKey) === 'collapsed'; } catch (_error) {}
          setCollapsed(collapsed, false);
        });
      }
    });
  };

  const setupPaperBlogCode = () => {
    const copyText = async (value) => {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(value);
        return;
      }
      const textarea = document.createElement('textarea');
      textarea.value = value;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const copied = document.execCommand('copy');
      textarea.remove();
      if (!copied) throw new Error('copy failed');
    };
    document.querySelectorAll('[data-paper-blog-copy]').forEach((button) => {
      button.addEventListener('click', async () => {
        const block = button.closest('[data-paper-blog-code]');
        const code = block ? block.querySelector('pre code') : null;
        if (!code) return;
        const original = button.textContent || '复制';
        try {
          await copyText(code.textContent || '');
          button.textContent = '已复制';
        } catch (_error) {
          button.textContent = '复制失败';
        }
        window.setTimeout(() => { button.textContent = original; }, 1400);
      });
    });
  };

  const setupPaperPagination = () => {
    const list = document.querySelector('.paper-list');
    const input = document.getElementById('paper-filter');
    const year = document.getElementById('year-filter');
    const type = document.getElementById('type-filter');
    const author = document.getElementById('author-filter');
    const count = document.getElementById('paper-count');
    const prev = document.getElementById('prev-page');
    const next = document.getElementById('next-page');
    const label = document.getElementById('page-label');
    // 日期筛选/排序控件（可能不存在于旧页面，全部按可选处理）
    const sortOrder = document.getElementById('sort-order');
    const dateBasis = document.getElementById('date-basis');
    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const recent30 = document.getElementById('recent-30');
    if (!list || !input || !year || !type || !author || !count || !prev || !next || !label) return;
    let cards = Array.from(list.querySelectorAll('.paper-card'));
    const pageSize = Number(list.dataset.pageSize || 20);
    let page = 0;
    const apply = () => {
      const query = input.value.trim().toLowerCase();
      const selectedYear = year.value;
      const selectedType = type.value;
      const selectedAuthor = author.value;
      const fromValue = dateFrom ? dateFrom.value : '';
      const toValue = dateTo ? dateTo.value : '';
      const basis = dateBasis && dateBasis.value === 'published' ? 'published' : 'added';
      const cardDate = (card) => (basis === 'published'
        ? (card.dataset.published || card.dataset.added || '')
        : (card.dataset.added || card.dataset.published || ''));
      const visible = cards.filter((card) => {
        const text = card.textContent.toLowerCase();
        const yearMatches = selectedYear === 'all' || card.dataset.year === selectedYear;
        const typeMatches = selectedType === 'all' || text.includes(selectedType);
        const authorMatches = selectedAuthor === 'all' || (card.dataset.authors || '').includes(selectedAuthor);
        let dateMatches = true;
        if (fromValue || toValue) {
          const value = cardDate(card);
          dateMatches = Boolean(value) && (!fromValue || value >= fromValue) && (!toValue || value <= toValue);
        }
        return (!query || text.includes(query)) && yearMatches && typeMatches && authorMatches && dateMatches;
      });
      const maxPage = Math.max(0, Math.ceil(visible.length / pageSize) - 1);
      page = Math.min(page, maxPage);
      cards.forEach((card) => { card.hidden = true; });
      visible.slice(page * pageSize, (page + 1) * pageSize).forEach((card) => { card.hidden = false; });
      count.textContent = `${visible.length} paper${visible.length === 1 ? '' : 's'}`;
      label.textContent = `Page ${page + 1} / ${maxPage + 1}`;
      prev.disabled = page === 0;
      next.disabled = page === maxPage;
    };
    let allPapers = [];
    const renderCards = (papers) => {
      allPapers = papers.slice();
      const order = sortOrder ? sortOrder.value : 'added';
      const sorted = papers.slice().sort((a, b) => {
        if (order === 'added' || order === 'published') {
          const field = order === 'added' ? 'added_at' : 'published_date';
          const secondary = order === 'added' ? 'published_date' : 'added_at';
          const delta = String(b[field] || '').localeCompare(String(a[field] || ''));
          if (delta) return delta;
          const delta2 = String(b[secondary] || '').localeCompare(String(a[secondary] || ''));
          if (delta2) return delta2;
        } else if (order === 'title') {
          const titleDelta = String(a.title || '').localeCompare(String(b.title || ''));
          if (titleDelta) return titleDelta;
        }
        const yearDelta = Number(b.year || 0) - Number(a.year || 0);
        if (yearDelta) return yearDelta;
        return String(b.paper_key || '').localeCompare(String(a.paper_key || ''));
      });
      list.innerHTML = sorted.map((paper) => {
        const allAuthors = Array.isArray(paper.authors) ? paper.authors : [];
        const authors = allAuthors.length ? allAuthors.slice(0, 3).join(', ') : 'Unknown authors';
        const authorTerms = allAuthors.join(' ').toLowerCase();
        const factCounts = paper.fact_counts && typeof paper.fact_counts === 'object' ? paper.fact_counts : {};
        const badges = Object.entries(factCounts)
          .filter(([, value]) => Number(value) > 0)
          .map(([key, value]) => `<span class="fact-chip ${escapeHtml(key)}">${escapeHtml(key)} ${Number(value)}</span>`)
          .join('') || '<span class="fact-chip">no facts</span>';
        const title = escapeHtml(paper.title || paper.paper_key || 'Untitled paper');
        const detailPath = escapeHtml(paper.detail_path || `papers/${paper.slug || paper.paper_key}.html`);
        const yearValue = Number(paper.year || 0);
        const coverPath = paper.cover_path ? escapeHtml(paper.cover_path) : '';
        const cover = coverPath
          ? `<div class="paper-cover-wrap paper-card-media"><img class="paper-cover" src="../${coverPath}" alt="${title} cover" loading="lazy"></div>`
          : '<div class="paper-cover-wrap paper-card-media paper-cover-empty" aria-hidden="true"></div>';
        const summaryEn = escapeHtml(paper.tldr || 'No short summary available yet.');
        const summaryZh = escapeHtml(paper.tldr_zh || paper.tldr || '暂无短摘要。');
        // 日期标签（入库 / 发表）+ NEW 标记
        const addedDay = String(paper.added_at || '').slice(0, 10);
        const publishedDay = String(paper.published_date || '').slice(0, 10);
        const dateParts = [];
        if (addedDay) dateParts.push(`入库 ${addedDay}`);
        if (publishedDay) dateParts.push(`发表 ${publishedDay}`);
        const dateLine = dateParts.length ? `<p class="paper-dates">📅 ${escapeHtml(dateParts.join(' · '))}</p>` : '';
        const newBadge = paper.is_new ? '<span class="new-badge">NEW</span>' : '';
        return `
          <article class="paper-card paper-post-card reveal" data-year="${yearValue || ''}" data-added="${escapeHtml(addedDay)}" data-published="${escapeHtml(publishedDay)}" data-authors="${escapeHtml(authorTerms)}" data-fact-count="${Number(paper.fact_count || 0)}">
            ${cover}
            <div class="paper-card-body paper-card-content">
              <a class="paper-title" href="../${detailPath}">${title}</a>
              <p class="paper-meta">${newBadge}${escapeHtml(authors)} · ${escapeHtml(yearValue ? String(yearValue) : 'n.d.')} · ${escapeHtml(paper.paper_key || '')}</p>
              ${dateLine}
              <p data-lang="en">${summaryEn}</p>
              <p data-lang="zh">${summaryZh}</p>
              <div class="chip-row">${badges}</div>
            </div>
          </article>
        `;
      }).join('');
      cards = Array.from(list.querySelectorAll('.paper-card'));
      apply();
    };
    [input, year, type, author, dateBasis, dateFrom, dateTo].forEach((control) => {
      if (control) control.addEventListener('input', () => { page = 0; apply(); });
    });
    if (sortOrder) sortOrder.addEventListener('change', () => {
      page = 0;
      if (allPapers.length) renderCards(allPapers);
      else apply();
    });
    if (recent30) recent30.addEventListener('click', () => {
      const today = new Date();
      const past = new Date();
      past.setDate(past.getDate() - 30);
      if (dateBasis) dateBasis.value = 'added';
      if (dateFrom) dateFrom.value = past.toISOString().slice(0, 10);
      if (dateTo) dateTo.value = today.toISOString().slice(0, 10);
      page = 0;
      apply();
    });
    prev.addEventListener('click', () => { page = Math.max(0, page - 1); apply(); });
    next.addEventListener('click', () => { page += 1; apply(); });
    if (list.dataset.papersSource) {
      fetch(list.dataset.papersSource)
        .then((response) => response.ok ? response.json() : [])
        .then((payload) => renderCards(Array.isArray(payload) ? payload : []))
        .catch(() => {
          list.innerHTML = '<p class="empty-state">Papers could not be loaded.</p>';
          cards = [];
          apply();
        });
    } else {
      apply();
    }
  };

  const setupResearchMap = () => {
    const shell = document.querySelector('[data-research-map]');
    if (!shell) return;
    const svg = shell.querySelector('.research-map');
    const selection = shell.querySelector('.map-selection');
    const controls = Array.from(shell.querySelectorAll('[data-map-filter]'));
    if (!svg || !selection) return;

    fetch(shell.dataset.researchMap)
      .then((response) => response.ok ? response.json() : { nodes: [], edges: [] })
      .then((graph) => renderMap(svg, selection, controls, graph))
      .catch(() => {
        selection.innerHTML = '<strong>Map unavailable</strong><p>The graph data could not be loaded.</p>';
      });
  };

  const setupStarmap = () => {
    const shell = document.querySelector('[data-starmap-source]');
    if (!shell) return;
    const svg = shell.querySelector('.starmap-canvas');
    const selection = shell.querySelector('.starmap-selection');
    const controls = Array.from(shell.querySelectorAll('[data-starmap-filter]'));
    if (!svg || !selection) return;
    fetch(shell.dataset.starmapSource)
      .then((response) => response.ok ? response.json() : { clusters: [], nodes: [], edges: [] })
      .then((payload) => renderStarmap(svg, selection, controls, payload))
      .catch(() => {
        selection.innerHTML = '<strong>Starmap unavailable</strong><p>The graph data could not be loaded.</p>';
      });
  };

  const renderMap = (svg, selection, controls, graph) => {
    if (window.d3 && typeof window.d3.forceSimulation === 'function') {
      renderD3ForceMap(svg, selection, controls, graph);
      return;
    }
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const width = Math.max(svg.clientWidth || 900, 720);
    const height = Math.max(svg.clientHeight || 620, 420);
    const centerX = width / 2;
    const centerY = height / 2;
    const topicNodes = nodes.filter((node) => node.kind === 'topic');
    const paperNodes = nodes.filter((node) => node.kind === 'paper');

    topicNodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(topicNodes.length, 1) - Math.PI / 2;
      const radius = Math.min(width, height) * (0.18 + ((index % 3) * 0.045));
      node.x = centerX + Math.cos(angle) * radius;
      node.y = centerY + Math.sin(angle) * radius;
    });
    paperNodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(paperNodes.length, 1) - Math.PI / 2;
      const radius = Math.min(width, height) * (0.38 + ((index % 4) * 0.025));
      node.x = centerX + Math.cos(angle) * radius;
      node.y = centerY + Math.sin(angle) * radius;
    });

    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.innerHTML = '';
    const edgeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    const nodeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    svg.append(edgeLayer, nodeLayer);

    edges.forEach((edge) => {
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      if (!source || !target) return;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', source.x);
      line.setAttribute('y1', source.y);
      line.setAttribute('x2', target.x);
      line.setAttribute('y2', target.y);
      line.classList.add('map-edge');
      line.dataset.source = edge.source;
      line.dataset.target = edge.target;
      line.dataset.group = edge.group || '';
      edgeLayer.append(line);
    });

    nodes.forEach((node) => {
      const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      const radius = node.kind === 'topic'
        ? Math.min(22, 8 + Math.sqrt(Number(node.size || 1)) * 3)
        : Math.min(14, 5 + Math.sqrt(Number(node.size || 1)));
      group.classList.add('map-node', node.kind || 'node', node.group || 'mixed');
      group.dataset.id = node.id;
      group.dataset.group = node.group || '';
      group.setAttribute('transform', `translate(${node.x} ${node.y})`);
      circle.setAttribute('r', radius);
      label.classList.add('map-label');
      label.setAttribute('x', radius + 6);
      label.setAttribute('y', 4);
      label.textContent = truncate(node.label || node.id, node.kind === 'topic' ? 28 : 22);
      group.append(circle, label);
      group.addEventListener('click', () => selectNode(node));
      nodeLayer.append(group);
    });

    const applyFilter = (filter) => {
      controls.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.mapFilter === filter)));
      svg.querySelectorAll('.map-node').forEach((nodeEl) => {
        const visible = filter === 'all' || nodeEl.dataset.group === filter || nodeEl.classList.contains('paper');
        nodeEl.classList.toggle('is-muted', !visible);
      });
      svg.querySelectorAll('.map-edge').forEach((edgeEl) => {
        edgeEl.classList.toggle('is-muted', filter !== 'all' && edgeEl.dataset.group !== filter);
      });
    };

    const selectNode = (node) => {
      const connected = new Set([node.id]);
      edges.forEach((edge) => {
        if (edge.source === node.id) connected.add(edge.target);
        if (edge.target === node.id) connected.add(edge.source);
      });
      svg.querySelectorAll('.map-node').forEach((nodeEl) => {
        const active = nodeEl.dataset.id === node.id;
        const related = connected.has(nodeEl.dataset.id);
        nodeEl.classList.toggle('is-active', active);
        nodeEl.classList.toggle('is-muted', !related);
      });
      svg.querySelectorAll('.map-edge').forEach((edgeEl) => {
        const active = edgeEl.dataset.source === node.id || edgeEl.dataset.target === node.id;
        edgeEl.classList.toggle('is-active', active);
        edgeEl.classList.toggle('is-muted', !active);
      });
      selection.innerHTML = `
        <strong>${escapeHtml(node.label || node.id)}</strong>
        <p>${escapeHtml(node.subtitle || node.kind || 'node')}</p>
        ${node.url ? `<a href="${escapeHtml(node.url)}">Open paper</a>` : ''}
      `;
    };

    controls.forEach((button) => button.addEventListener('click', () => applyFilter(button.dataset.mapFilter || 'all')));
    applyFilter('all');
  };

  const renderD3ForceMap = (svg, selection, controls, graph) => {
    const d3 = window.d3;
    const nodes = (Array.isArray(graph.nodes) ? graph.nodes : []).map((node) => ({ ...node }));
    const edges = (Array.isArray(graph.edges) ? graph.edges : []).map((edge) => ({ ...edge }));
    const width = Math.max(svg.clientWidth || 900, 720);
    const height = Math.max(svg.clientHeight || 620, 420);
    const radiusFor = (node) => node.kind === 'topic'
      ? Math.min(22, 8 + Math.sqrt(Number(node.size || 1)) * 3)
      : Math.min(14, 5 + Math.sqrt(Number(node.size || 1)));

    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.innerHTML = '';

    const root = d3.select(svg);
    const edgeLayer = root.append('g').attr('class', 'map-edge-layer');
    const nodeLayer = root.append('g').attr('class', 'map-node-layer');
    const linkForce = d3.forceLink(edges)
      .id((node) => node.id)
      .distance((edge) => edge.group === 'paper' ? 70 : 105)
      .strength(0.55);
    const simulation = d3.forceSimulation(nodes)
      .force('link', linkForce)
      .force('charge', d3.forceManyBody().strength((node) => node.kind === 'topic' ? -240 : -70))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((node) => radiusFor(node) + 10))
      .force('x', d3.forceX(width / 2).strength(0.035))
      .force('y', d3.forceY(height / 2).strength(0.035));

    const links = edgeLayer.selectAll('line')
      .data(edges)
      .join('line')
      .attr('class', 'map-edge')
      .attr('data-group', (edge) => edge.group || '')
      .attr('data-source', (edge) => typeof edge.source === 'object' ? edge.source.id : edge.source)
      .attr('data-target', (edge) => typeof edge.target === 'object' ? edge.target.id : edge.target);

    const nodeGroups = nodeLayer.selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', (node) => `map-node ${node.kind || 'node'} ${node.group || 'mixed'}`)
      .attr('data-id', (node) => node.id)
      .attr('data-group', (node) => node.group || '')
      .call(d3.drag()
        .on('start', (event, node) => {
          if (!event.active) simulation.alphaTarget(0.18).restart();
          node.fx = node.x;
          node.fy = node.y;
        })
        .on('drag', (event, node) => {
          node.fx = event.x;
          node.fy = event.y;
        })
        .on('end', (event, node) => {
          if (!event.active) simulation.alphaTarget(0);
          node.fx = null;
          node.fy = null;
        }));

    nodeGroups.append('circle').attr('r', radiusFor);
    nodeGroups.append('text')
      .attr('class', 'map-label')
      .attr('x', (node) => radiusFor(node) + 6)
      .attr('y', 4)
      .text((node) => truncate(node.label || node.id, node.kind === 'topic' ? 28 : 22));

    const applyFilter = (filter) => {
      controls.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.mapFilter === filter)));
      svg.querySelectorAll('.map-node').forEach((nodeEl) => {
        const visible = filter === 'all' || nodeEl.dataset.group === filter || nodeEl.classList.contains('paper');
        nodeEl.classList.toggle('is-muted', !visible);
      });
      svg.querySelectorAll('.map-edge').forEach((edgeEl) => {
        edgeEl.classList.toggle('is-muted', filter !== 'all' && edgeEl.dataset.group !== filter);
      });
    };

    const selectNode = (node) => {
      const connected = new Set([node.id]);
      edges.forEach((edge) => {
        const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
        const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
        if (sourceId === node.id) connected.add(targetId);
        if (targetId === node.id) connected.add(sourceId);
      });
      svg.querySelectorAll('.map-node').forEach((nodeEl) => {
        const active = nodeEl.dataset.id === node.id;
        const related = connected.has(nodeEl.dataset.id);
        nodeEl.classList.toggle('is-active', active);
        nodeEl.classList.toggle('is-muted', !related);
      });
      svg.querySelectorAll('.map-edge').forEach((edgeEl) => {
        const active = edgeEl.dataset.source === node.id || edgeEl.dataset.target === node.id;
        edgeEl.classList.toggle('is-active', active);
        edgeEl.classList.toggle('is-muted', !active);
      });
      selection.innerHTML = `
        <strong>${escapeHtml(node.label || node.id)}</strong>
        <p>${escapeHtml(node.subtitle || node.kind || 'node')}</p>
        ${node.url ? `<a href="${escapeHtml(node.url)}">Open paper</a>` : ''}
      `;
    };

    nodeGroups.on('click', (event, node) => selectNode(node));
    simulation.on('tick', () => {
      nodes.forEach((node) => {
        node.x = Math.max(24, Math.min(width - 24, node.x));
        node.y = Math.max(24, Math.min(height - 24, node.y));
      });
      links
        .attr('x1', (edge) => edge.source.x)
        .attr('y1', (edge) => edge.source.y)
        .attr('x2', (edge) => edge.target.x)
        .attr('y2', (edge) => edge.target.y);
      nodeGroups.attr('transform', (node) => `translate(${node.x} ${node.y})`);
    });
    for (let i = 0; i < 90; i += 1) simulation.tick();
    simulation.alpha(0.25).restart();
    controls.forEach((button) => button.addEventListener('click', () => applyFilter(button.dataset.mapFilter || 'all')));
    applyFilter('all');
  };

  const renderStarmap = (svg, selection, controls, payload) => {
    if (!(window.d3 && typeof window.d3.forceSimulation === 'function')) return;
    const d3 = window.d3;
    const nodes = (Array.isArray(payload.nodes) ? payload.nodes : []).map((node) => ({ ...node }));
    const edges = (Array.isArray(payload.edges) ? payload.edges : []).map((edge) => ({ ...edge }));
    const clusters = Array.isArray(payload.clusters) ? payload.clusters : [];
    const width = Math.max(svg.clientWidth || 980, 720);
    const height = Math.max(svg.clientHeight || 720, 480);
    const centerX = width / 2;
    const centerY = height / 2;
    const clusterPositions = new Map();
    clusters.forEach((cluster, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(clusters.length, 1) - Math.PI / 2;
      const radius = Math.min(width, height) * 0.26;
      clusterPositions.set(cluster.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        color: cluster.color || '#d4a957',
        label: cluster.label || cluster.id,
      });
    });

    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.innerHTML = '';
    const root = d3.select(svg);
    const clusterLayer = root.append('g');
    const edgeLayer = root.append('g');
    const nodeLayer = root.append('g');

    clusterLayer.selectAll('circle')
      .data(clusters)
      .join('circle')
      .attr('class', 'starmap-cluster')
      .attr('cx', (cluster) => (clusterPositions.get(cluster.id) || {}).x || centerX)
      .attr('cy', (cluster) => (clusterPositions.get(cluster.id) || {}).y || centerY)
      .attr('r', (cluster) => 96 + Math.min(120, ((cluster.papers || []).length || 0) * 8))
      .attr('fill', (cluster) => cluster.color || '#d4a957')
      .attr('stroke', (cluster) => cluster.color || '#d4a957');

    clusterLayer.selectAll('text')
      .data(clusters)
      .join('text')
      .attr('class', 'starmap-label')
      .attr('x', (cluster) => ((clusterPositions.get(cluster.id) || {}).x || centerX) - 28)
      .attr('y', (cluster) => ((clusterPositions.get(cluster.id) || {}).y || centerY) - 72)
      .text((cluster) => truncate(cluster.label || cluster.id, 20));

    const radiusFor = (node) => node.kind === 'paper' ? Number(node.size || 8) : Math.min(9, Number(node.size || 5));
    nodes.forEach((node) => {
      const cluster = clusterPositions.get(node.cluster_id || node.group);
      if (cluster && node.kind === 'paper') {
        node.x = cluster.x + ((Math.random() - 0.5) * 80);
        node.y = cluster.y + ((Math.random() - 0.5) * 80);
      }
    });
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id((node) => node.id).distance((edge) => edge.type === 'citation' ? 100 : 70).strength(0.38))
      .force('charge', d3.forceManyBody().strength((node) => node.kind === 'paper' ? -80 : -28))
      .force('collision', d3.forceCollide().radius((node) => radiusFor(node) + 10))
      .force('x', d3.forceX((node) => ((clusterPositions.get(node.cluster_id || node.group) || {}).x || centerX)).strength((node) => node.kind === 'paper' ? 0.12 : 0.04))
      .force('y', d3.forceY((node) => ((clusterPositions.get(node.cluster_id || node.group) || {}).y || centerY)).strength((node) => node.kind === 'paper' ? 0.12 : 0.04));

    const links = edgeLayer.selectAll('line')
      .data(edges)
      .join('line')
      .attr('class', 'starmap-edge')
      .attr('data-type', (edge) => edge.type || '');

    const nodeGroups = nodeLayer.selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', (node) => `starmap-node ${node.kind || 'node'}`)
      .attr('data-id', (node) => node.id)
      .call(d3.drag()
        .on('start', (event, node) => {
          if (!event.active) simulation.alphaTarget(0.15).restart();
          node.fx = node.x;
          node.fy = node.y;
        })
        .on('drag', (event, node) => {
          node.fx = event.x;
          node.fy = event.y;
        })
        .on('end', (event, node) => {
          if (!event.active) simulation.alphaTarget(0);
          node.fx = null;
          node.fy = null;
        }));

    nodeGroups.append('circle').attr('r', radiusFor);
    nodeGroups.append('text')
      .attr('class', 'starmap-label')
      .attr('x', (node) => radiusFor(node) + 6)
      .attr('y', 4)
      .text((node) => truncate(node.label || node.id, node.kind === 'paper' ? 26 : 18));

    const selectNode = (node) => {
      const connected = new Set([node.id]);
      edges.forEach((edge) => {
        const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
        const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
        if (sourceId === node.id) connected.add(targetId);
        if (targetId === node.id) connected.add(sourceId);
      });
      svg.querySelectorAll('.starmap-node').forEach((element) => {
        const related = connected.has(element.dataset.id);
        element.style.opacity = related ? '1' : '0.14';
      });
      svg.querySelectorAll('.starmap-edge').forEach((element, index) => {
        const edge = edges[index];
        const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
        const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
        const active = sourceId === node.id || targetId === node.id;
        element.style.opacity = active ? '0.95' : '0.08';
        element.style.strokeWidth = active ? '2.1' : '1';
      });
      selection.innerHTML = `
        <strong>${escapeHtml(node.label || node.id)}</strong>
        <p>${escapeHtml(node.tldr || node.kind || 'node')}</p>
        ${node.cover_path ? `<img class="paper-cover" src="${escapeHtml(node.cover_path)}" alt="${escapeHtml(node.label || node.id)} cover">` : ''}
        ${node.url ? `<a href="${escapeHtml(node.url)}">Open paper</a>` : ''}
      `;
    };

    const applyFilter = (filter) => {
      controls.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.starmapFilter === filter)));
      svg.querySelectorAll('.starmap-edge').forEach((element, index) => {
        const edge = edges[index];
        const visible = filter === 'all' || edge.type === filter;
        element.style.display = visible ? '' : 'none';
      });
    };

    nodeGroups.on('click', (_event, node) => selectNode(node));
    simulation.on('tick', () => {
      nodes.forEach((node) => {
        node.x = Math.max(18, Math.min(width - 18, node.x));
        node.y = Math.max(18, Math.min(height - 18, node.y));
      });
      links
        .attr('x1', (edge) => edge.source.x)
        .attr('y1', (edge) => edge.source.y)
        .attr('x2', (edge) => edge.target.x)
        .attr('y2', (edge) => edge.target.y);
      nodeGroups.attr('transform', (node) => `translate(${node.x} ${node.y})`);
    });
    for (let i = 0; i < 80; i += 1) simulation.tick();
    simulation.alpha(0.28).restart();
    controls.forEach((button) => button.addEventListener('click', () => applyFilter(button.dataset.starmapFilter || 'all')));
    applyFilter('all');
  };

  const truncate = (value, max) => {
    const text = String(value || '');
    return text.length <= max ? text : `${text.slice(0, Math.max(0, max - 1)).trim()}...`;
  };

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));

  setupLanguage();
  setupSearch();
  setupTabs();
  setupPaperFactPanels();
  setupPaperDetailMode();
  setupPaperBlogToc();
  setupPaperBlogCode();
  setupPaperPagination();
  setupResearchMap();
  setupStarmap();
})();
"""


def render_report_site(bundle_dir: Path) -> str:
    payloads = _site_payloads(bundle_dir)
    papers = _digest_papers(payloads, bundle_dir)
    clusters = _cluster_items(payloads)
    stats = _stats_payload(payloads, papers, clusters)
    return _dashboard_page(payloads, papers, clusters, stats)


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def _read_static_asset(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _copy_dir_if_present(source: Path, target: Path) -> None:
    if not source.exists() or not source.is_dir():
        return
    if source.resolve() == target.resolve():
        return
    shutil.copytree(source, target, dirs_exist_ok=True)


def _relative_file_list(root: Path, directory: str) -> list[str]:
    base = root / directory
    if not base.exists() or not base.is_dir():
        return []
    return sorted(str(path.relative_to(root)) for path in base.rglob("*") if path.is_file())


def export_report_site(bundle_dir: Path, out_path: Path | None = None) -> ReportSite:
    target = out_path or (bundle_dir / "index.html")
    site_root = target.parent
    site_root.mkdir(parents=True, exist_ok=True)

    payloads = _site_payloads(bundle_dir)
    manifest = payloads["manifest"]
    papers = _digest_papers(payloads, bundle_dir)
    clusters = _cluster_items(payloads)
    stats = _stats_payload(payloads, papers, clusters)

    written: list[str] = []
    written.append(_write_text(target, _dashboard_page(payloads, papers, clusters, stats)))
    written.append(_write_text(site_root / "assets" / "site.css", SITE_CSS.strip() + "\n"))
    written.append(_write_text(site_root / "assets" / "site.js", SITE_JS.strip() + "\n"))
    written.append(_write_text(site_root / "assets" / "d3.v7.min.js", _read_static_asset(D3_ASSET_PATH)))
    written.append(_write_text(site_root / "assets" / "d3.LICENSE", _read_static_asset(D3_LICENSE_PATH)))
    _copy_dir_if_present(bundle_dir / "paper-assets", site_root / "paper-assets")
    written.append(_write_json(site_root / "api" / "stats.json", stats))

    paper_summaries = [_paper_summary(paper) for paper in papers]
    cluster_summaries = [_cluster_summary(cluster) for cluster in clusters]
    graph_payload = _research_graph_payload(payloads, papers)
    starmap_payload = _starmap_payload(payloads, papers, clusters)
    written.append(_write_json(site_root / "api" / "papers.json", paper_summaries))
    written.append(_write_json(site_root / "api" / "clusters.json", cluster_summaries))
    written.append(_write_json(site_root / "api" / "relations-graph.json", graph_payload))
    written.append(_write_json(site_root / "api" / "starmap.json", starmap_payload))
    written.append(_write_json(site_root / "api" / "search-index.json", _lightweight_search_entries(papers, clusters, stats)))
    written.append(_write_json(site_root / "search-index.json", build_search_index(bundle_dir)))
    written.append(_write_json(site_root / "provenance-index.json", build_provenance_index(bundle_dir)))
    written.append(_write_json(site_root / "navigation-index.json", build_navigation_index(bundle_dir)))

    written.append(_write_text(site_root / "papers" / "index.html", _papers_page(papers)))
    written.append(_write_text(site_root / "blogs" / "index.html", _blogs_page(papers)))
    blog_papers = [
        paper
        for paper in papers
        if isinstance(paper.get("blog"), dict) and paper["blog"].get("status") == "published"
    ]
    blog_navigation: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]] = {}
    for index, blog_paper in enumerate(blog_papers):
        paper_key = _compact_string(blog_paper.get("paper_key"))
        blog_navigation[paper_key] = (
            blog_papers[index - 1] if index > 0 else None,
            blog_papers[index + 1] if index + 1 < len(blog_papers) else None,
        )
    for paper in papers:
        detail = _paper_detail_payload(paper)
        previous, next_paper = blog_navigation.get(detail["paper_key"], (None, None))
        written.append(
            _write_text(
                site_root / "papers" / f"{detail['slug']}.html",
                _paper_detail_page(paper, previous=previous, next_paper=next_paper),
            )
        )
        written.append(_write_json(site_root / "api" / "papers" / f"{detail['slug']}.json", detail))

    written.append(_write_text(site_root / "clusters" / "index.html", _clusters_page(clusters)))
    for cluster in clusters[:300]:
        summary = _cluster_summary(cluster)
        written.append(_write_text(site_root / "clusters" / f"{summary['slug']}.html", _cluster_detail_page(cluster, papers)))

    written.append(_write_text(site_root / "map" / "index.html", _map_page(graph_payload)))
    written.append(_write_text(site_root / "starmap" / "index.html", _starmap_page(starmap_payload)))
    written.append(_write_text(site_root / "gaps" / "index.html", _gap_page(payloads.get("gap-analysis"))))
    written.append(_write_text(site_root / "digest" / "index.html", _digest_page(papers, clusters)))
    written.append(_write_text(site_root / "synthesis" / "index.html", _synthesis_page(payloads.get("synthesis"))))
    written.append(_write_text(site_root / "narrative" / "index.html", _narrative_page(payloads.get("narrative"))))

    source_files = [
        "manifest.json",
        "digest.json",
        "map.json",
        "gap-analysis.json",
        "synthesis.json",
        "narrative.json",
        "clusters.json",
        "paper-blogs.json",
        "digest.md",
        "map.md",
        "gap-analysis.md",
        "synthesis.md",
        "narrative.md",
        "clusters.md",
    ]
    publish_files = sorted(
        {
            str(Path(path).relative_to(site_root))
            for path in map(Path, written)
            if Path(path).is_relative_to(site_root)
        }
        | {relative for relative in source_files if (site_root / relative).exists()}
        | set(_relative_file_list(site_root, "paper-assets"))
    )
    site_manifest = {
        "generated_at": manifest.get("generated_at", "unknown"),
        "entrypoint": "index.html",
        "publish_files": sorted(publish_files + [SITE_MANIFEST_FILE]),
        "paper_count": len(papers),
        "cluster_count": len(clusters),
        "file_count": len(publish_files) + 1,
        "architecture": "static multi-page Academic Calm site with lightweight API shards",
    }
    _write_json(site_root / SITE_MANIFEST_FILE, site_manifest)

    return ReportSite(
        bundle_dir=bundle_dir,
        out_path=target,
        report_count=int(manifest.get("report_count", 0)),
        artifact_count=len(site_manifest["publish_files"]),
    )

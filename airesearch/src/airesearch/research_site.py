from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReportSite:
    bundle_dir: Path
    out_path: Path
    report_count: int
    artifact_count: int


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
        snippet = _snippet(markdown)
        search_text = _collapse_text(
            " ".join(
                [
                    name,
                    title,
                    _artifact_type(name),
                    markdown_path,
                    json_path,
                    markdown,
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

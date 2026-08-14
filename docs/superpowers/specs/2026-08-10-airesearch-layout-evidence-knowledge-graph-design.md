# AIResearch Layout Evidence Knowledge Graph Design

## Context

AIResearch already stores paper metadata, five research-fact types, claim provenance, native layout v2 blocks, and a SQLite knowledge graph. Public paper pages and the admin Layout Evidence Inspector can display formulas, tables, figures, OCR, and layout quality, but these records are still parallel datasets. A reader cannot currently answer which formula, table, or figure supports a specific method, dataset, benchmark, claim, or limitation.

The current corpus contains 209 papers. SQLite remains appropriate at this size, and the existing `kg_nodes`, `kg_edges`, and `kg_provenance` tables already provide versioned properties, extractor ownership, and uniqueness constraints. This feature therefore extends the existing graph instead of installing MinerU, introducing a graph database, or adding an LLM matching dependency.

## Goals

- Represent research facts and selected layout evidence as traceable graph nodes.
- Create conservative `supported_by` edges only when evidence can be matched deterministically.
- Make the relationships visible in both public paper detail pages and the admin evidence inspector.
- Keep extraction idempotent, bounded, HTML-safe, and independently removable by extractor name.
- Rebuild all 209 papers and include the graph in the normal report-generation workflow.

## Non-Goals

- No LLM-generated fact/evidence links.
- No vector search or embedding dependency.
- No Neo4j, Kuzu, or other new database.
- No speculative cross-paper semantic edges.
- No claim that every fact must have a layout evidence match.
- No replacement for raw fact provenance, layout artifacts, or the existing cross-paper research map.

## Chosen Approach

Use a dedicated deterministic extractor named `layout_evidence_graph`. It writes only records carrying that extractor name and clears only its own fact/evidence records when rebuilding a paper. Existing paper-card graph records remain untouched. The shared `paper:<paper_key>` node is reused with `insert or ignore`; the new extractor never updates its properties or deletes it.

Two alternatives were rejected:

- LLM matching would link more facts but could create plausible-looking unsupported edges, add provider cost, and make reruns nondeterministic.
- A dedicated graph database would add deployment, migration, backup, and query complexity without a demonstrated scale requirement.

## Graph Contract

### Node Keys

- Paper: reuse `paper:<paper_key>` without changing its current extractor ownership. If it is absent, insert a minimal anchor once and retain that anchor during cleanup so graph edges always satisfy foreign-key constraints.
- Research fact: `research_fact:<paper_key>:<fact_id>`.
- Layout evidence: `layout_evidence:<paper_key>:<run_id>:<block_id>`.

Layout node types are limited to:

- `layout_figure`
- `layout_table`
- `layout_equation`

Text-only blocks remain matching inputs but are not public evidence nodes in this iteration. This keeps the graph focused on the visual and mathematical evidence the frontend can display.

### Edge Types

- `paper -> has_research_fact -> research_fact`
- `paper -> has_layout_evidence -> layout_evidence`
- `research_fact -> supported_by -> layout_evidence`

Every node and edge stores `extractor_name = "layout_evidence_graph"`, `source_paper_key`, timestamps, and JSON properties. Properties include fact type, statement, page, block type, source reference, caption or formula preview, quality score, quality reasons, matching method, and matching score as applicable.

### Provenance

- Fact nodes and `has_research_fact` edges point to `research_facts:<fact_id>`.
- Evidence nodes and `has_layout_evidence` edges point to `paper_layout_blocks:<block_id>`.
- `supported_by` edges record provenance for both the research fact and the matched layout block through two `kg_provenance` rows.
- Provenance confidence equals `1.0` for direct source references and the deterministic match score for lexical matches.

## Evidence Selection

Only blocks from the latest completed or reused native layout run are considered. Eligible block types are image/figure/chart, table, and interline equation. A block is included when it has a usable asset, table structure, caption, or formula text and a layout quality score of at least `0.55`. Lower-quality blocks remain available through layout detail but do not enter the evidence graph.

Malformed metadata is treated as an empty object. Empty captions, empty formulas, missing assets, and unsupported block types are skipped without failing the paper.

## Fact Matching

Matching is deliberately strict and ordered.

### 1. Direct Reference

A fact is linked when its provenance source path identifies `paper_layout_blocks:<block_id>` for the same paper and latest run. The edge uses `match_method = "direct_layout_block"` and score `1.0`. Direct references may link review-quality evidence because the source identity is explicit.

### 2. Exact Normalized Containment

The fact evidence quote is normalized and compared with the block text, caption, table Markdown, and formula LaTeX. A quote with at least 24 normalized characters may match when one normalized value contains the other. The block must have quality score at least `0.72`.

### 3. Strict Token Coverage

For non-formula prose/table evidence, matching requires:

- at least four shared informative tokens;
- source-token coverage of at least `0.72`;
- Jaccard similarity of at least `0.30`;
- block quality score of at least `0.72`;
- a compatible fact/evidence type.

Compatibility rules:

- `dataset` and `benchmark`: table or figure;
- `method` and `claim`: figure, table, or equation;
- `limitation`: figure or table;
- equations never match `dataset`, `benchmark`, or `limitation` through lexical matching.

At most three evidence nodes are linked to one fact. Candidates sort by directness, match score, layout quality, page, and block id. Candidates below any threshold are not written as edges and are not exposed as suggestions.

## Extractor API And CLI

New module: `airesearch.layout_evidence_graph`.

Primary interfaces:

- `extract_layout_evidence_graph(db_path, paper_key=None, limit=None)`
- `load_paper_evidence_graph(db_path, paper_key, public=False)`
- `export_layout_evidence_graph(db_path, out_path)`

CLI commands:

- `extract-layout-evidence-graph [--paper-key KEY] [--limit N]`
- `export-layout-evidence-graph --out PATH`

The extraction result reports papers seen, fact nodes, evidence nodes, paper edges, support edges, provenance rows, linked facts, and unlinked facts. A paper with no completed layout run succeeds with zero evidence nodes and keeps its fact nodes, making missing coverage observable rather than exceptional.

## Workflow Integration

- `run-mvp-pipeline` runs graph extraction after fact extraction/audit and before report-bundle generation.
- A successful single-paper layout parse triggers a graph refresh for that paper.
- A successful fact extraction refreshes the graph for the affected papers.
- Rebuilding one paper clears only `layout_evidence_graph` rows owned by that paper.
- Production data is backed up before the first 209-paper graph rebuild.

## Public API

Each public paper JSON gains:

```json
{
  "evidence_graph": {
    "api_version": "evidence-graph-v1",
    "fact_count": 13,
    "linked_fact_count": 7,
    "evidence_count": 11,
    "relation_count": 14,
    "facts": [],
    "evidence": [],
    "relations": []
  }
}
```

Public payload limits:

- 24 facts, preserving all five fact types before filling remaining slots by confidence;
- 48 evidence nodes;
- three relations per fact and 72 relations total;
- 240 characters per statement/caption preview;
- no local absolute file paths, raw parser HTML, standalone database ids outside opaque graph keys, or admin artifact paths.

The static bundle remains usable when graph data is absent: it emits an empty `evidence-graph-v1` object instead of failing site generation.

## Public Paper UI

The existing layout evidence suite gains a `证据关系` view. It uses an unframed relationship list rather than a dense force graph:

- each row starts with fact type, localized fact statement, and fact confidence;
- connected evidence appears as compact formula/table/figure references with page, quality, and match label;
- selecting a relation scrolls to the existing formula, table, or visual evidence section when that target is present;
- unlinked facts are summarized separately as `尚无严格版面关联`, not hidden and not treated as errors;
- mobile layout stacks fact and evidence columns without page-level horizontal overflow.

All content is escaped before HTML generation. No `table_html`, caption HTML, or model output is inserted as trusted markup.

## Admin Inspector UI

The Layout Evidence Inspector gains a `事实关联` tab sourced from the authenticated layout detail response. It shows the complete per-paper graph without public caps, bounded to 200 rows for browser safety.

Admin-only fields include:

- deterministic node and edge keys;
- `match_method`;
- match score and layout quality score;
- provenance source table/key/field;
- unlinked fact count by fact type.

The tab remains read-only. Graph rebuilds use the existing job/action infrastructure rather than direct browser database writes.

## Error Handling And Idempotency

- JSON parsing failures fall back to empty values and increment skipped-block counters.
- Missing paper nodes are inserted as minimal anchors before edges are inserted. Existing paper nodes are never updated by this extractor.
- All graph records are namespaced by extractor name.
- A paper rebuild deletes that extractor's prior provenance, edges, research-fact nodes, and layout-evidence nodes in foreign-key-safe order, then writes a complete replacement in one transaction. It never deletes `paper:<paper_key>`.
- Batch extraction stops on database integrity errors and preserves the previous committed database state.
- Public export treats missing graph records as an empty graph.

## Testing

Unit tests cover:

- node/edge/provenance creation;
- idempotent reruns and isolated cleanup;
- direct block references;
- exact containment and strict token matching;
- rejection below quality/similarity thresholds;
- fact/evidence type compatibility;
- latest-run selection;
- public payload limits and path stripping;
- JSON and HTML escaping;
- empty/malformed metadata;
- CLI and MVP pipeline integration.

Cross-layer acceptance covers:

- one fixture paper with all fact/evidence types;
- real `colavla`, `world2vlm`, and `world-model-self-distillation` extraction;
- public JSON and HTML markers;
- admin inspector tab and response contract;
- full AIResearch tests, platform audit, Vue build, admin smoke, desktop/mobile public DOM checks, backup, deployment, and production HTTP verification.

## Success Criteria

- The extractor is deterministic and idempotent.
- No weak or incompatible `supported_by` edge is written.
- All 209 papers can be processed without an LLM call.
- Public and admin UIs expose the same underlying relationships at different detail levels.
- Existing fact provenance, layout evidence panels, paper-card graph, and cross-paper map continue to work.
- Documentation states that unlinked facts indicate insufficient strict evidence, not false facts.

# Stage 3H Research Clusters Design

## Goal

Add a deterministic cross-paper clustering report for AIResearch facts. The report groups similar facts across the current paper corpus so the user can see repeated themes, shared methods, common claims, and isolated one-off observations without calling an LLM or adding a network dependency.

## Scope

Stage 3H reads the existing Stage 3 digest inputs: `paper_cards`, `research_facts`, evidence provenance, and code links. It does not create new database tables and does not change existing facts.

The feature adds:

- `generate-research-clusters` CLI with Markdown and JSON output.
- A `research_clusters.py` report module.
- Bundle integration so `generate-report-bundle` includes `clusters.md` and `clusters.json`.
- Tests for deterministic clustering, export formats, CLI behavior, and bundle manifest counts.

## Non-Goals

- No embedding model, LLM, or external semantic service.
- No mutation of fact statements, names, confidence, evidence, or provenance.
- No interactive cluster review workflow.
- No graph database or vector database migration.

## Clustering Approach

Facts are clustered separately by `fact_type` to avoid mixing methods, datasets, benchmarks, claims, and limitations.

For each fact:

1. Combine `fact.name` and `fact.statement`.
2. Lowercase and extract alphanumeric tokens.
3. Drop a fixed stopword list and tokens shorter than three characters.
4. Build a token set.

Within each fact type, facts are sorted deterministically by confidence descending, paper title, paper key, fact name, and statement. The builder greedily assigns each fact to the existing cluster with the highest Jaccard similarity against the cluster token union. If the best score is at least `0.22`, the fact joins that cluster; otherwise it starts a new cluster.

Only clusters with at least two facts or at least two papers are listed as clusters. Remaining one-fact, one-paper groups are counted as singletons and summarized by fact type.

## Cluster Metadata

Each cluster has:

- `cluster_id`: deterministic string like `method:attention-transformer-architecture`.
- `fact_type`
- `label`: title-cased top token signature.
- `token_signature`: top tokens sorted by frequency descending then alphabetically.
- `paper_count`
- `fact_count`
- `average_confidence`
- `facts`: paper title, key, fact name, statement, confidence, evidence source path.

Cluster sorting is deterministic: fact type order, paper count descending, fact count descending, average confidence descending, then label.

## Output

Markdown structure:

- `# AIResearch Research Clusters`
- Snapshot counts: papers, facts, clusters, clustered facts, singletons.
- Cluster summary by fact type.
- Fact clusters with paper references and evidence paths.
- Singleton summary by fact type.

JSON structure mirrors the dataclasses and includes all facts in each emitted cluster plus singleton counts.

## Error Handling

The module uses `build_research_digest()`. If `paper_cards` is empty, the existing `DigestInputError` flows through and the CLI returns exit code `2`, matching the other Stage 3 reports.

## Testing

Tests use a synthetic SQLite fixture with two papers and overlapping facts. They verify:

- Similar facts of the same type cluster together.
- Different fact types do not cluster together even when tokens overlap.
- Singleton counts are reported.
- Markdown and JSON exports are stable.
- CLI prints cluster and singleton counts.
- Report bundle contains the new cluster artifacts and manifest counts.

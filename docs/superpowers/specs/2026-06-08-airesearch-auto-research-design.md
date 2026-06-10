# AIResearch Automatic Research Design

## Summary

AIResearch is the Niu Secretary research board for local-first automatic scientific research. It supports two entry points: scheduled research updates and manual paper submission. Both entry points feed one unified pipeline for source resolution, paper ingestion, metadata enrichment, parsing, RAG indexing, knowledge graph construction, and evidence-grounded reporting.

## User Need

The user wants an AI research secretary that can update every two days or weekly and can also accept a paper URL, arXiv ID, DOI, local PDF path, or paper title on demand. The system should build a local RAG knowledge base and knowledge graph, then produce research digests, paper cards, research maps, claim tracing, method comparisons, and gap analysis.

## Approved Baseline Stack

| Layer | Preferred Tool | Reason |
|-------|----------------|--------|
| Paper ingestion | paperpipe / papi | Supports arXiv, local PDF, LaTeX, equations, abstracts, local paper DB, RAG backend, and paper-grounded agent workflows. |
| Metadata and citation graph | OpenAlex | Scholarly graph API for works, authors, institutions, topics, and citations. |
| Recommendation and expansion | Semantic Scholar API | Seed-paper recommendation and similar-paper expansion. |
| Vector retrieval | Qdrant | Local vector database with payload metadata and hybrid retrieval support. |
| Knowledge graph | Neo4j | Mature GraphRAG ecosystem and Python integration. |
| KG construction | LlamaIndex PropertyGraph or LangChain LLMGraphTransformer | Extracts entities and relations from chunks with source provenance. |
| Query pattern | Microsoft GraphRAG style | Local search for specific facts; global search for topic-level themes and trends. |
| Local ledger | SQLite | Auditable local state for papers, chunks, jobs, candidates, claims, equations, and provenance. |

## Architecture

```text
manual paper input          scheduled research topic
URL / DOI / arXiv / PDF     every_2_days / weekly
        |                         |
        v                         v
              source resolver
                    |
                    v
              candidate ledger
                    |
                    v
             paperpipe/papi ingest
                    |
                    v
       OpenAlex + Semantic Scholar enrichment
                    |
                    v
       PDF / LaTeX / equation / chunk parsing
                    |
                    v
        SQLite + local file artifact storage
                    |
                    v
       Qdrant vectors + SQLite FTS/BM25
                    |
                    v
      Neo4j graph + extracted entity relations
                    |
                    v
       paper cards / digests / maps / GraphRAG
```

Manual and scheduled inputs differ only at the entry point. Manual papers enter ingestion immediately. Scheduled papers first pass through topic-based discovery, deduplication, scoring, and skip-reason tracking.

## Research Topic Model

Each automatic research topic includes:

- `topic_id`
- `name`
- `description`
- `keywords`
- `exclude_keywords`
- `seed_papers`
- `venues`
- `authors`
- `update_frequency`: `daily`, `every_2_days`, or `weekly`
- `last_run_at`

Scheduled runs create an auditable `research_run` with query parameters, source systems, candidates, selected papers, skipped papers, failure reasons, and report paths.

## Pipeline Components

### Source Resolver

Resolve manual inputs and scheduled candidates into canonical paper records. Deduplicate by DOI, arXiv ID, OpenAlex work ID, Semantic Scholar ID, normalized title, and PDF hash.

### Ingestion

Use paperpipe/papi as the preferred backend. Store original PDFs and source files under `airesearch/data/papers/`; store parsed outputs under `airesearch/data/parsed/`. Track status transitions from `candidate` through `graph_built` or `failed`.

### Indexing

Use SQLite FTS5/BM25 for exact lookup and Qdrant for semantic retrieval. Every chunk must carry `paper_id`, `chunk_id`, `title`, `section`, `page`, `source_path`, `text_hash`, and `created_at`.

### Knowledge Graph

Use OpenAlex for scholarly graph edges and Neo4j for the local graph. Extract Method, Dataset, Metric, Task, Claim, Equation, Topic, Author, Institution, and CodeArtifact nodes from chunks. Every extracted relation must preserve provenance: `paper_id`, `chunk_id`, `page`, `section`, `quote`, `extractor`, and `created_at`.

### Reports

Manual builds produce a paper card. Scheduled runs produce a digest. Cross-paper commands produce research maps, method comparisons, claim traces, and gap analysis. Reports must separate extracted facts, model summaries, and speculative hypotheses.

## Command Surface

```text
/research-topic add <topic>
/research-topic list
/research-run --topic <topic> --mode scheduled
/paper-add <url|doi|arxiv|pdf|title>
/paper-build <paper_id>
/paper-search <query>
/kg-search <query>
/claim-trace <claim>
/paper-compare <paper-a> <paper-b>
/research-digest --topic <topic> --since 7d
/research-map <topic>
/gap-analysis <topic>
```

## Data Model

SQLite tables:

- `papers`
- `paper_sources`
- `paper_chunks`
- `paper_equations`
- `paper_claims`
- `paper_citations`
- `research_topics`
- `research_runs`
- `research_candidates`
- `graph_entities`
- `graph_relations`
- `provenance`
- `jobs`

Neo4j nodes:

- `Paper`
- `Author`
- `Institution`
- `Topic`
- `Method`
- `Dataset`
- `Metric`
- `Task`
- `Claim`
- `Equation`
- `Chunk`
- `CodeArtifact`

Neo4j relations:

- `Paper -[:CITES]-> Paper`
- `Paper -[:WRITTEN_BY]-> Author`
- `Author -[:AFFILIATED_WITH]-> Institution`
- `Paper -[:HAS_TOPIC]-> Topic`
- `Paper -[:USES_METHOD]-> Method`
- `Paper -[:INTRODUCES_METHOD]-> Method`
- `Paper -[:EVALUATES_ON]-> Dataset`
- `Paper -[:REPORTS_METRIC]-> Metric`
- `Claim -[:SUPPORTED_BY]-> Chunk`
- `Equation -[:DEFINED_IN]-> Chunk`
- `CodeArtifact -[:IMPLEMENTS]-> Method`

## MVP Phases

1. Unified paper ledger and manual ingestion.
2. Scheduled OpenAlex and Semantic Scholar discovery.
3. Qdrant RAG indexing and evidence-grounded answers.
4. Neo4j citation graph and extracted research KG.
5. GraphRAG research assistant for maps, trends, and gaps.

## Safety Constraints

- Keep local PDFs, parsed text, SQLite databases, Qdrant collections, and Neo4j dumps local by default.
- Store API keys only in ignored `.env` files or environment variables.
- Cite evidence for factual claims.
- Mark unsupported statements as inference or unknown.
- Treat KG extraction as a reviewable draft until verified.
- Label generated hypotheses as hypotheses, not facts.

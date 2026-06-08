# Stage 2D.3 Code Links In Paper Cards And Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make extracted GitHub repositories visible in Paper Card exports and the knowledge graph.

**Architecture:** Keep `paper_code_links` as the extraction source of truth. Extend the deterministic paper-card extractor to read existing code-link rows, add repository nodes and edges during graph rebuild, and include the links in JSONL card export.

**Tech Stack:** Python, SQLite, pytest, existing AIResearch CLI and ledger helpers.

---

## File Map

- Modify: `airesearch/src/airesearch/knowledge_graph.py` - load code links, add KG nodes/edges, and export `code_links`.
- Modify: `airesearch/tests/test_knowledge_graph.py` - verify repository graph rows and card export payloads.
- Modify: `airesearch/PLAN.md` - record Stage 2D.3 completion.

## Task 1: Add Tests For Code Links In Cards And KG

**Files:**
- Modify: `airesearch/tests/test_knowledge_graph.py`

- [x] **Step 1: Add a test that extracts code links before paper cards**

Add imports:

```python
import json

from airesearch.code_links import extract_code_links
```

Add this test:

```python
def test_extract_paper_cards_adds_code_repository_graph(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)
    extract_code_links(db_path)

    result = extract_paper_cards(db_path)

    with connect(db_path) as conn:
        repo_node = conn.execute(
            "select * from kg_nodes where node_key = ?",
            ("code_repository:github_com:attention:transformer",),
        ).fetchone()
        repo_edge = conn.execute(
            """
            select * from kg_edges
            where source_key = ? and relation = ? and target_key = ?
            """,
            (
                "paper:1706_03762",
                "has_code_repository",
                "code_repository:github_com:attention:transformer",
            ),
        ).fetchone()
        provenance = conn.execute(
            """
            select count(*) as count from kg_provenance
            where source_table = ? and source_paper_key = ?
            """,
            ("paper_code_links", "1706_03762"),
        ).fetchone()["count"]

    assert result.nodes_written >= 1
    assert result.edges_written >= 1
    assert repo_node["node_type"] == "code_repository"
    assert repo_node["label"] == "attention/transformer"
    assert repo_edge["relation"] == "has_code_repository"
    assert provenance == 2
```

- [x] **Step 2: Add a test that exported paper cards include code links**

Add this test:

```python
def test_export_paper_cards_includes_code_links(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    out_path = tmp_path / "paper_cards.jsonl"
    setup_fixture_db(db_path)
    extract_code_links(db_path)
    extract_paper_cards(db_path)

    exported = export_paper_cards(db_path, out_path)
    payload = json.loads(out_path.read_text(encoding="utf-8").splitlines()[0])

    assert exported == 1
    assert payload["code_links"] == [
        {
            "host": "github.com",
            "owner": "attention",
            "repo": "transformer",
            "source_path": "source.tex",
            "source_type": "source_tex",
            "url": "https://github.com/attention/transformer",
        }
    ]
```

- [x] **Step 3: Run tests to verify they fail before implementation**

Run:

```bash
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/pytest tests/test_knowledge_graph.py -v
```

Expected: fail because code repository graph rows and `code_links` export are not implemented.

## Task 2: Implement Code Links In Graph Extraction And Export

**Files:**
- Modify: `airesearch/src/airesearch/knowledge_graph.py`

- [x] **Step 1: Add helpers**

Add:

```python
def code_repository_node_key(host: str, owner: str, repo: str) -> str:
    return f"code_repository:{normalize_key(host)}:{normalize_key(owner)}:{normalize_key(repo)}"


def load_code_links(conn, paper_key: str):
    return conn.execute(
        """
        select * from paper_code_links
        where paper_key = ?
        order by host, owner, repo, url
        """,
        (paper_key,),
    ).fetchall()
```

- [x] **Step 2: Load code links in `extract_one`**

After artifacts are loaded, add:

```python
    code_links = load_code_links(conn, paper_key)
```

- [x] **Step 3: Add code repository graph rows**

Before returning from `extract_one`, add:

```python
    for code_link in code_links:
        host = str(code_link["host"] or "").strip()
        owner = str(code_link["owner"] or "").strip()
        repo = str(code_link["repo"] or "").strip()
        url = str(code_link["url"] or "").strip()
        if not host or not owner or not repo or not url:
            continue
        node_key = code_repository_node_key(host, owner, repo)
        source_key = str(code_link["id"])
        upsert_node(
            conn,
            node_key=node_key,
            node_type="code_repository",
            label=f"{owner}/{repo}",
            properties={"url": url, "host": host, "owner": owner, "repo": repo},
            paper_key=paper_key,
            now=now,
        )
        upsert_edge(
            conn,
            source_key=paper_node,
            relation="has_code_repository",
            target_key=node_key,
            properties={"url": url, "host": host},
            paper_key=paper_key,
            now=now,
        )
        add_provenance(conn, entity_type="node", entity_key=node_key, source_table="paper_code_links", source_key=source_key, source_field="url", paper_key=paper_key, now=now)
        add_provenance(conn, entity_type="edge", entity_key=f"{paper_node}|has_code_repository|{node_key}", source_table="paper_code_links", source_key=source_key, source_field="url", paper_key=paper_key, now=now)
        nodes += 1
        edges += 1
        provenance += 2
```

- [x] **Step 4: Include code links in paper-card export**

In `export_paper_cards`, query code links for each row and add:

```python
                "code_links": [
                    {
                        "url": code_link["url"],
                        "host": code_link["host"],
                        "owner": code_link["owner"],
                        "repo": code_link["repo"],
                        "source_type": code_link["source_type"],
                        "source_path": code_link["source_path"],
                    }
                    for code_link in load_code_links(conn, row["paper_key"])
                ],
```

- [x] **Step 5: Run focused tests**

Run:

```bash
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/pytest tests/test_knowledge_graph.py tests/test_code_links.py tests/test_cli.py -v
```

Expected: pass.

## Task 3: Verify Real Database And Record Status

**Files:**
- Modify: `airesearch/PLAN.md`

- [x] **Step 1: Refresh real code links and paper cards**

Run:

```bash
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/python -m airesearch.cli extract-code-links
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/python -m airesearch.cli extract-paper-cards
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/python -m airesearch.cli export-paper-cards --out exports/paper-cards-stage-2d3.jsonl
```

Expected: real DB retains `code_links=9`; paper cards are regenerated; export exists with `code_links` arrays.

- [x] **Step 2: Update project plan**

In `PLAN.md`, mark Stage 2D.3 as completed and note that Paper Card export and KG include code repository links.

- [x] **Step 3: Run full tests**

Run:

```bash
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/pytest -v
```

Expected: all tests pass.

- [x] **Step 4: Commit implementation**

Run:

```bash
git -C /home/ubuntu/.openclaw/workspace/niu-secretary add airesearch/src/airesearch/knowledge_graph.py airesearch/tests/test_knowledge_graph.py airesearch/PLAN.md airesearch/docs/superpowers/plans/2026-06-08-stage-2d3-code-links-card-graph.md airesearch/exports/paper-cards-stage-2d3.jsonl
git -C /home/ubuntu/.openclaw/workspace/niu-secretary commit -m "feat: add code links to paper graph"
```

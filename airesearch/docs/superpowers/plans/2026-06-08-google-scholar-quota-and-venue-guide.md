# Google Scholar Quota And Venue Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in Google Scholar discovery provider through SerpAPI with SQLite cache and monthly quota protection, while keeping Paper Copilot as a documented venue guide only.

**Architecture:** Keep the existing Stage 2B provider interface unchanged. Add a small persistence helper for provider response cache and usage counters, then compose it inside `GoogleScholarProvider`. Wire `google_scholar` into CLI provider selection without adding it to the default provider set.

**Tech Stack:** Python 3.12, SQLite, stdlib `urllib`, `pytest`, existing `airesearch` package.

---

## File Map

| Path | Responsibility |
| --- | --- |
| `src/airesearch/schema.sql` | Add `provider_query_cache` and `provider_usage` tables plus indexes. |
| `src/airesearch/provider_cache.py` | New focused helper for cache keys, cache reads/writes, and monthly usage accounting. |
| `src/airesearch/providers.py` | Add `GoogleScholarProvider`, SerpAPI parsing helpers, and keep default providers unchanged. |
| `src/airesearch/cli.py` | Add `google_scholar` CLI choice, `--refresh-provider-cache`, and provider construction. |
| `src/airesearch/candidates.py` | Treat `google_scholar` as a conservative trusted discovery source. |
| `tests/test_provider_cache.py` | New tests for cache and monthly usage behavior. |
| `tests/test_providers.py` | Add SerpAPI Google Scholar provider parsing, missing key, cache hit, cache miss, and quota tests. |
| `tests/test_cli.py` | Add CLI provider selection tests for opt-in behavior. |
| `.env.example` | Already includes `SERPAPI_API_KEY`, `SERPAPI_MONTHLY_LIMIT`, and `SERPAPI_CACHE_TTL_DAYS`; verify it remains present. |

## Task 1: SQLite Cache And Usage Helpers

**Files:**
- Modify: `src/airesearch/schema.sql`
- Create: `src/airesearch/provider_cache.py`
- Test: `tests/test_provider_cache.py`

- [ ] **Step 1: Write failing schema/helper tests**

Create `tests/test_provider_cache.py`:

```python
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.provider_cache import (
    cache_key,
    get_cached_response,
    increment_usage,
    monthly_usage,
    put_cached_response,
    quota_available,
)


def test_provider_cache_round_trip(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    key = cache_key("google_scholar", "diffusion_models", '"diffusion model"', 10)

    assert get_cached_response(db_path, "google_scholar", key) is None

    put_cached_response(
        db_path,
        provider="google_scholar",
        cache_key_value=key,
        profile_name="diffusion_models",
        query='"diffusion model"',
        limit=10,
        response_json='{"organic_results": []}',
        ttl_days=30,
    )

    assert get_cached_response(db_path, "google_scholar", key) == '{"organic_results": []}'


def test_expired_provider_cache_misses(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    key = cache_key("google_scholar", "diffusion_models", "query", 5)

    put_cached_response(
        db_path,
        provider="google_scholar",
        cache_key_value=key,
        profile_name="diffusion_models",
        query="query",
        limit=5,
        response_json='{"organic_results": []}',
        ttl_days=-1,
    )

    assert get_cached_response(db_path, "google_scholar", key) is None


def test_provider_usage_counts_by_month(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    assert monthly_usage(db_path, "google_scholar", "2026-06") == 0
    assert quota_available(db_path, "google_scholar", "2026-06", 2)

    increment_usage(db_path, "google_scholar", "2026-06")
    increment_usage(db_path, "google_scholar", "2026-06")

    assert monthly_usage(db_path, "google_scholar", "2026-06") == 2
    assert not quota_available(db_path, "google_scholar", "2026-06", 2)


def test_provider_tables_created_by_init_db(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert "provider_query_cache" in tables
    assert "provider_usage" in tables
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_provider_cache.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'airesearch.provider_cache'`.

- [ ] **Step 3: Add cache and usage tables**

Append to `src/airesearch/schema.sql` before the final indexes section:

```sql
create table if not exists provider_query_cache (
    id integer primary key autoincrement,
    provider text not null,
    cache_key text not null,
    profile_name text not null,
    query text not null,
    limit_count integer not null,
    response_json text not null,
    created_at text not null,
    expires_at text not null,
    unique(provider, cache_key)
);

create table if not exists provider_usage (
    provider text not null,
    period text not null,
    request_count integer not null default 0,
    updated_at text not null,
    primary key(provider, period)
);
```

Append to the index section:

```sql
create index if not exists idx_provider_query_cache_provider_key on provider_query_cache(provider, cache_key);
create index if not exists idx_provider_query_cache_expires_at on provider_query_cache(expires_at);
create index if not exists idx_provider_usage_provider_period on provider_usage(provider, period);
```

- [ ] **Step 4: Implement provider cache helper**

Create `src/airesearch/provider_cache.py`:

```python
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import utc_now


def utc_datetime() -> datetime:
    return datetime.now(timezone.utc)


def cache_key(provider: str, profile_name: str, query: str, limit: int) -> str:
    normalized = "\n".join(
        [
            provider.strip().lower(),
            profile_name.strip().lower(),
            " ".join(query.split()).lower(),
            str(limit),
        ]
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached_response(db_path: Path, provider: str, cache_key_value: str) -> str | None:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        row = conn.execute(
            """
            select response_json from provider_query_cache
            where provider = ? and cache_key = ? and expires_at > ?
            """,
            (provider, cache_key_value, now),
        ).fetchone()
    if row is None:
        return None
    return str(row["response_json"])


def put_cached_response(
    db_path: Path,
    *,
    provider: str,
    cache_key_value: str,
    profile_name: str,
    query: str,
    limit: int,
    response_json: str,
    ttl_days: int,
) -> None:
    init_db(db_path)
    created_at = utc_now()
    expires_at = (utc_datetime() + timedelta(days=ttl_days)).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into provider_query_cache (
                provider, cache_key, profile_name, query, limit_count,
                response_json, created_at, expires_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(provider, cache_key) do update set
                profile_name = excluded.profile_name,
                query = excluded.query,
                limit_count = excluded.limit_count,
                response_json = excluded.response_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (
                provider,
                cache_key_value,
                profile_name,
                query,
                limit,
                response_json,
                created_at,
                expires_at,
            ),
        )
        conn.commit()


def monthly_usage(db_path: Path, provider: str, period: str) -> int:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "select request_count from provider_usage where provider = ? and period = ?",
            (provider, period),
        ).fetchone()
    if row is None:
        return 0
    return int(row["request_count"])


def quota_available(db_path: Path, provider: str, period: str, monthly_limit: int) -> bool:
    return monthly_usage(db_path, provider, period) < monthly_limit


def increment_usage(db_path: Path, provider: str, period: str) -> None:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into provider_usage (provider, period, request_count, updated_at)
            values (?, ?, 1, ?)
            on conflict(provider, period) do update set
                request_count = provider_usage.request_count + 1,
                updated_at = excluded.updated_at
            """,
            (provider, period, now),
        )
        conn.commit()
```

- [ ] **Step 5: Run cache tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_provider_cache.py -v
```

Expected: PASS, 4 tests.

- [ ] **Step 6: Commit Task 1**

```bash
git add airesearch/src/airesearch/schema.sql airesearch/src/airesearch/provider_cache.py airesearch/tests/test_provider_cache.py
git commit -m "feat: add provider cache and usage ledger"
```

## Task 2: Google Scholar SerpAPI Provider

**Files:**
- Modify: `src/airesearch/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Add failing provider tests**

Modify the import in `tests/test_providers.py`:

```python
from airesearch.providers import ArxivProvider, GoogleScholarProvider, OpenAlexProvider, SemanticScholarProvider
```

Append tests:

```python
from pathlib import Path

import pytest

from airesearch.db import init_db
from airesearch.provider_cache import increment_usage, put_cached_response, cache_key


def google_scholar_payload():
    return json.dumps(
        {
            "organic_results": [
                {
                    "title": "Diffusion Policy for Generalist Robot Foundation Models",
                    "link": "https://arxiv.org/abs/2601.00001",
                    "snippet": "We study diffusion policy for embodied AI and robot foundation models.",
                    "publication_info": {
                        "summary": "A. Scientist, B. Researcher - arXiv preprint arXiv:2601.00001, 2026"
                    },
                    "resources": [
                        {
                            "title": "arxiv.org",
                            "file_format": "PDF",
                            "link": "https://arxiv.org/pdf/2601.00001"
                        }
                    ],
                    "inline_links": {
                        "cited_by": {
                            "total": 42
                        }
                    }
                }
            ]
        }
    )


def test_google_scholar_provider_requires_api_key(tmp_path: Path):
    provider = GoogleScholarProvider(db_path=tmp_path / "db.sqlite3", api_key="")

    with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
        provider.search("diffusion_models", 1)


def test_google_scholar_provider_parses_serpapi_result(tmp_path: Path):
    db_path = tmp_path / "db.sqlite3"
    init_db(db_path)
    opener = RecordingOpener(google_scholar_payload())

    papers = GoogleScholarProvider(
        db_path=db_path,
        api_key="serp-key",
        opener=opener,
        monthly_limit=10,
        cache_ttl_days=30,
    ).search("diffusion_models", 1)

    assert papers[0].source == "google_scholar"
    assert papers[0].title == "Diffusion Policy for Generalist Robot Foundation Models"
    assert papers[0].url == "https://arxiv.org/abs/2601.00001"
    assert papers[0].published_date == "2026-01-01"
    assert papers[0].year == 2026
    assert papers[0].abstract == "We study diffusion policy for embodied AI and robot foundation models."
    assert papers[0].artifact_links == ["https://arxiv.org/pdf/2601.00001"]
    assert "A. Scientist" in papers[0].authors
    assert "arxiv" in papers[0].venue.lower()
    assert "api_key=serp-key" in opener.requests[0].full_url


def test_google_scholar_cache_hit_does_not_call_opener(tmp_path: Path):
    db_path = tmp_path / "db.sqlite3"
    init_db(db_path)
    query = '"diffusion model" OR "discrete diffusion" OR "diffusion policy" OR "flow matching" OR "rectified flow"'
    key = cache_key("google_scholar", "diffusion_models", query, 1)
    put_cached_response(
        db_path,
        provider="google_scholar",
        cache_key_value=key,
        profile_name="diffusion_models",
        query=query,
        limit=1,
        response_json=google_scholar_payload(),
        ttl_days=30,
    )
    opener = RecordingOpener('{"organic_results": []}')

    papers = GoogleScholarProvider(
        db_path=db_path,
        api_key="serp-key",
        opener=opener,
        monthly_limit=10,
    ).search("diffusion_models", 1)

    assert papers
    assert opener.requests == []


def test_google_scholar_quota_blocks_before_http(tmp_path: Path):
    db_path = tmp_path / "db.sqlite3"
    init_db(db_path)
    increment_usage(db_path, "google_scholar", "2026-06")
    opener = RecordingOpener(google_scholar_payload())

    provider = GoogleScholarProvider(
        db_path=db_path,
        api_key="serp-key",
        opener=opener,
        monthly_limit=1,
        current_period=lambda: "2026-06",
    )

    with pytest.raises(RuntimeError, match="monthly quota reached"):
        provider.search("diffusion_models", 1)

    assert opener.requests == []
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_providers.py -v
```

Expected: FAIL with `ImportError` for `GoogleScholarProvider`.

- [ ] **Step 3: Add imports and parsing helpers**

Modify the import block in `src/airesearch/providers.py`:

```python
import hashlib
from datetime import date
from pathlib import Path
```

Add:

```python
from airesearch.config import Settings
from airesearch.provider_cache import (
    cache_key,
    get_cached_response,
    increment_usage,
    put_cached_response,
    quota_available,
)
```

Add helper functions near the existing provider helpers:

```python
def current_period() -> str:
    return date.today().strftime("%Y-%m")


def int_from_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def stable_source_id(*parts: str) -> str:
    raw = "\n".join(part for part in parts if part)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def year_from_text(value: str) -> int | None:
    match = re.search(r"\b(20\d{2}|19\d{2})\b", value)
    if match:
        return int(match.group(1))
    return None


def split_scholar_publication_info(summary: str) -> tuple[list[str], str, int | None]:
    parts = [compact_text(part) for part in summary.split(" - ") if compact_text(part)]
    authors = [author.strip() for author in parts[0].split(",") if author.strip()] if parts else []
    venue = parts[1] if len(parts) > 1 else ""
    year = year_from_text(summary)
    return authors, venue, year
```

- [ ] **Step 4: Implement `GoogleScholarProvider`**

Add this class after `SemanticScholarProvider` in `src/airesearch/providers.py`:

```python
class GoogleScholarProvider:
    name = "google_scholar"

    def __init__(
        self,
        *,
        db_path: Path | None = None,
        opener: HttpOpener = default_opener,
        api_key: str | None = None,
        monthly_limit: int | None = None,
        cache_ttl_days: int | None = None,
        refresh_cache: bool = False,
        current_period: Callable[[], str] = current_period,
    ):
        settings = Settings.from_env()
        self.db_path = db_path or settings.sqlite_path
        self.opener = opener
        self.api_key = api_key if api_key is not None else os.environ.get("SERPAPI_API_KEY", "")
        self.monthly_limit = monthly_limit if monthly_limit is not None else int_from_env("SERPAPI_MONTHLY_LIMIT", 200)
        self.cache_ttl_days = cache_ttl_days if cache_ttl_days is not None else int_from_env("SERPAPI_CACHE_TTL_DAYS", 30)
        self.refresh_cache = refresh_cache
        self.current_period = current_period

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY is required for google_scholar provider")
        bounded_limit = max(1, min(limit, 20))
        query = profile_query(profile_name)
        key = cache_key(self.name, profile_name, query, bounded_limit)

        if not self.refresh_cache:
            cached = get_cached_response(self.db_path, self.name, key)
            if cached is not None:
                return self._parse_payload(json.loads(cached))

        period = self.current_period()
        if not quota_available(self.db_path, self.name, period, self.monthly_limit):
            raise RuntimeError(f"google_scholar monthly quota reached for {period}")

        params = {
            "engine": "google_scholar",
            "q": query,
            "num": str(bounded_limit),
            "api_key": self.api_key,
        }
        url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
        payload = fetch_json(url, opener=self.opener, headers={"User-Agent": "airesearch/0.1"})
        increment_usage(self.db_path, self.name, period)
        put_cached_response(
            self.db_path,
            provider=self.name,
            cache_key_value=key,
            profile_name=profile_name,
            query=query,
            limit=bounded_limit,
            response_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            ttl_days=self.cache_ttl_days,
        )
        return self._parse_payload(payload)

    def _parse_payload(self, payload: dict[str, Any]) -> list[CandidatePaper]:
        return [self._parse_result(item) for item in payload.get("organic_results", [])]

    def _parse_result(self, item: dict[str, Any]) -> CandidatePaper:
        publication_info = item.get("publication_info") or {}
        summary = compact_text(publication_info.get("summary"))
        authors, venue, year = split_scholar_publication_info(summary)
        resources = item.get("resources") or []
        artifact_links = [
            resource.get("link", "")
            for resource in resources
            if resource.get("link") and compact_text(resource.get("file_format")).upper() == "PDF"
        ]
        title = compact_text(item.get("title"))
        link = item.get("link") or ""
        return CandidatePaper(
            source=self.name,
            source_id=stable_source_id(title, link, summary),
            title=title,
            url=link,
            authors=authors,
            venue=venue,
            published_date=f"{year}-01-01" if year else "",
            year=year,
            abstract=compact_text(item.get("snippet")),
            artifact_links=artifact_links,
        )
```

- [ ] **Step 5: Run provider tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_provider_cache.py tests/test_providers.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add airesearch/src/airesearch/providers.py airesearch/tests/test_providers.py
git commit -m "feat: add google scholar provider"
```

## Task 3: CLI Opt-In Wiring And Conservative Scoring

**Files:**
- Modify: `src/airesearch/cli.py`
- Modify: `src/airesearch/candidates.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_candidates.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `tests/test_cli.py`:

```python
from airesearch.cli import build_discovery_providers


def test_google_scholar_is_not_default_provider():
    providers = build_discovery_providers(None)

    assert [provider.name for provider in providers] == ["openalex", "arxiv", "semantic_scholar"]


def test_google_scholar_provider_can_be_selected(tmp_path, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-key")
    providers = build_discovery_providers(["google_scholar"], db_path=tmp_path / "db.sqlite3")

    assert [provider.name for provider in providers] == ["google_scholar"]


def test_google_scholar_refresh_cache_flag_is_passed(tmp_path, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "serp-key")
    providers = build_discovery_providers(
        ["google_scholar"],
        db_path=tmp_path / "db.sqlite3",
        refresh_provider_cache=True,
    )

    assert providers[0].refresh_cache is True
```

- [ ] **Step 2: Add failing scoring test**

Append to `tests/test_candidates.py`:

```python
from airesearch.candidates import CandidatePaper, score_candidate
from airesearch.profiles import default_profiles


def test_google_scholar_gets_conservative_trusted_source_score():
    profile = next(profile for profile in default_profiles() if profile.name == "diffusion_models")
    candidate = CandidatePaper(
        source="google_scholar",
        source_id="abc",
        title="Diffusion Policy for Generalist Robot Foundation Models",
        url="https://arxiv.org/abs/2601.00001",
        venue="arXiv preprint",
        published_date="2026-01-01",
        year=2026,
        abstract="diffusion policy for robot foundation models",
    )

    score, reasons = score_candidate(profile, candidate)

    assert score > 0
    assert "venue:trusted_source=google_scholar" in reasons
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_cli.py tests/test_candidates.py -v
```

Expected: FAIL because `build_discovery_providers` does not accept `db_path`, CLI choices exclude `google_scholar`, and scoring does not trust `google_scholar`.

- [ ] **Step 4: Wire CLI provider choice**

Modify the provider import in `src/airesearch/cli.py`:

```python
from airesearch.providers import ArxivProvider, GoogleScholarProvider, OpenAlexProvider, SemanticScholarProvider
```

Modify provider choices in `build_parser()`:

```python
choices=["openalex", "arxiv", "semantic_scholar", "google_scholar"],
```

Add to `discover-candidates` parser:

```python
    discover.add_argument(
        "--refresh-provider-cache",
        action="store_true",
        help="Bypass provider response cache for cache-aware providers while still respecting quota limits.",
    )
```

Replace `build_discovery_providers` with:

```python
def build_discovery_providers(
    names: list[str] | None,
    *,
    db_path: Path | None = None,
    refresh_provider_cache: bool = False,
):
    provider_names = names or ["openalex", "arxiv", "semantic_scholar"]
    providers = []
    for name in provider_names:
        if name == "openalex":
            providers.append(OpenAlexProvider())
        elif name == "arxiv":
            providers.append(ArxivProvider())
        elif name == "semantic_scholar":
            providers.append(SemanticScholarProvider())
        elif name == "google_scholar":
            providers.append(
                GoogleScholarProvider(
                    db_path=db_path,
                    refresh_cache=refresh_provider_cache,
                )
            )
        else:
            raise ValueError(f"unknown discovery provider: {name}")
    return providers
```

Modify the discover command provider construction:

```python
        providers = build_discovery_providers(
            args.provider,
            db_path=args.db,
            refresh_provider_cache=args.refresh_provider_cache,
        )
```

- [ ] **Step 5: Add conservative scoring source**

Modify `venue_score` in `src/airesearch/candidates.py`:

```python
    if candidate.source.lower() in {"arxiv", "openreview", "semantic_scholar", "openalex", "google_scholar"}:
        reasons.append("venue:trusted_source=" + candidate.source)
        return 0.35
```

- [ ] **Step 6: Run CLI and scoring tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_cli.py tests/test_candidates.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full test suite**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest -v
```

Expected: PASS.

- [ ] **Step 8: Commit Task 3**

```bash
git add airesearch/src/airesearch/cli.py airesearch/src/airesearch/candidates.py airesearch/tests/test_cli.py airesearch/tests/test_candidates.py
git commit -m "feat: wire google scholar discovery opt in"
```

## Task 4: Documentation And Runtime Smoke Checks

**Files:**
- Modify: `PLAN.md`
- Modify: `.env.example`
- Test: runtime CLI checks only

- [ ] **Step 1: Verify `.env.example` contains SerpAPI settings**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
rg -n "^SERPAPI_(API_KEY|MONTHLY_LIMIT|CACHE_TTL_DAYS)=" .env.example
```

Expected:

```text
SERPAPI_API_KEY=
SERPAPI_MONTHLY_LIMIT=200
SERPAPI_CACHE_TTL_DAYS=30
```

If any line is missing, add it:

```text
SERPAPI_API_KEY=
SERPAPI_MONTHLY_LIMIT=200
SERPAPI_CACHE_TTL_DAYS=30
```

- [ ] **Step 2: Update project status plan**

In `PLAN.md`, add a completed or in-progress bullet under Stage 2B/Stage 2C status:

```markdown
- [x] Designed quota-safe Google Scholar provider through SerpAPI and Paper Copilot venue-guide policy.
- [x] Implemented opt-in Google Scholar provider with SQLite cache and monthly usage guard.
```

Keep Paper Copilot wording explicit:

```markdown
- Paper Copilot is treated as a human venue/source guide only; AIResearch does not automatically scrape Paper Copilot.
```

- [ ] **Step 3: Smoke test default providers do not include Google Scholar**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
python -m airesearch.cli discover-candidates --profile diffusion_models --limit 1
```

Expected output starts with:

```text
providers=openalex,arxiv,semantic_scholar
```

Network failures from default providers may appear as provider errors in restricted environments; the important check is that `google_scholar` is absent from the provider list.

- [ ] **Step 4: Smoke test Google Scholar opt-in without spending quota when cache exists**

First run the unit tests from Task 2 to validate cache behavior:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest tests/test_providers.py::test_google_scholar_cache_hit_does_not_call_opener -v
```

Expected: PASS.

Do not run a real SerpAPI request during this task unless the user explicitly approves spending one search.

- [ ] **Step 5: Run full test suite**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
pytest -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add airesearch/PLAN.md airesearch/.env.example
git commit -m "docs: document google scholar discovery policy"
```

## Self-Review

- Spec coverage: Google Scholar provider, explicit opt-in, cache TTL, monthly usage guard, missing key behavior, conservative scoring, CLI refresh option, tests, and Paper Copilot no-scrape policy are all covered.
- Placeholder scan: No unresolved implementation holes remain.
- Type consistency: `GoogleScholarProvider.search(profile_name, limit)` matches the existing `DiscoveryProvider` protocol; cache helpers consistently use `cache_key_value` when avoiding name collision with `cache_key()`.
- Scope: Paper Copilot venue-source config is documented as future work only. This plan does not implement `venue_sources` because the approved change only requires the policy and Google Scholar quota-safe provider.

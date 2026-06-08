# Google Scholar Quota Cache And Venue Guide Design

Date: 2026-06-08

## Goal

Extend Stage 2B candidate discovery with a quota-safe Google Scholar source while using Paper Copilot only as a human venue/source guide.

The system should discover more top-conference and high-citation papers without wasting the limited SerpAPI monthly quota or relying on automated scraping of sites that do not provide a stable, permitted API.

## Decisions

- Add Google Scholar through SerpAPI as an explicit provider named `google_scholar`.
- Do not include `google_scholar` in the default provider list.
- Cache Google Scholar responses in SQLite before parsing candidates.
- Track monthly SerpAPI usage and stop calls before the paid quota is exhausted.
- Do not implement a Paper Copilot scraping provider.
- Use Paper Copilot as a manual venue/source guide for identifying official conference sources.

## Google Scholar Provider

`GoogleScholarProvider` implements the existing Stage 2B provider interface:

```python
search(profile_name: str, limit: int) -> list[CandidatePaper]
```

The provider reads the query from the existing `profile_query(profile_name)` mapping and calls SerpAPI with:

- `engine=google_scholar`
- `q=<profile query>`
- `num=<bounded limit>`
- `api_key=<SERPAPI_API_KEY>`

The provider maps SerpAPI `organic_results` into `CandidatePaper`:

- `source`: `google_scholar`
- `source_id`: stable hash or SerpAPI result id/link when available
- `title`: result title
- `url`: result link
- `authors`: best-effort parse from publication info
- `venue`: best-effort parse from publication info
- `published_date` / `year`: best-effort year parse
- `abstract`: result snippet
- `artifact_links`: PDF/resources links when present

Google Scholar metadata is treated as discovery metadata, not final provenance. Later ingestion and enrichment should prefer arXiv, DOI, OpenAlex, Semantic Scholar, official proceedings, or paperpipe artifacts.

## Quota Protection

Google Scholar discovery is opt-in:

```bash
airesearch discover-candidates --profile diffusion_models --provider google_scholar
```

The default command remains unchanged and does not spend SerpAPI quota:

```bash
airesearch discover-candidates --profile diffusion_models
```

The provider uses two SQLite-backed safeguards.

### Provider Query Cache

Create `provider_query_cache`:

- `provider`
- `cache_key`
- `profile_name`
- `query`
- `limit`
- `response_json`
- `created_at`
- `expires_at`

The cache key is derived from provider, profile name, normalized query, and limit. If the cache entry exists and has not expired, discovery parses the cached response and does not call SerpAPI.

Default cache TTL:

```bash
SERPAPI_CACHE_TTL_DAYS=30
```

### Provider Usage

Create `provider_usage`:

- `provider`
- `period`, formatted as `YYYY-MM`
- `request_count`
- `updated_at`

Default monthly limit:

```bash
SERPAPI_MONTHLY_LIMIT=200
```

The default is below SerpAPI's 250 free monthly searches so there is a manual reserve. Cache hits do not increment usage. Cache misses increment usage only after a SerpAPI request is attempted.

When the monthly limit is reached, the provider raises a clear provider-level error. `run_discovery` already records provider errors without blocking other sources.

## CLI Behavior

Add provider selection:

```bash
airesearch discover-candidates --profile <profile> --provider google_scholar
```

Add optional cache refresh:

```bash
airesearch discover-candidates --profile <profile> --provider google_scholar --refresh-provider-cache
```

Refresh bypasses the cache but still respects the monthly limit.

If `SERPAPI_API_KEY` is missing, the provider returns a clear error and does not write a cache entry.

## Scoring

`google_scholar` can be recognized as a trusted discovery source, but conservatively. It should not receive more trust than OpenAlex or Semantic Scholar because Google Scholar results can include books, slides, course pages, and non-paper pages.

The existing candidate filters remain in force:

- require parseable date or year
- reject future dates
- require profile topic signal
- deduplicate by normalized title within a discovery run

## Paper Copilot Policy

Paper Copilot should not be implemented as an automatic provider.

Allowed use:

- manual reference for identifying top venues and current conference-year pages
- manual verification of official venue links
- source notes in local venue configuration
- manually curated import manifests created by a human

Disallowed use:

- automated scraping of Paper Copilot pages
- periodic crawling of Paper Copilot conference lists
- using Paper Copilot page data as the primary system database

Future work can add a `venue_sources` configuration seeded from human review:

```json
{
  "CVPR 2026": {
    "field": "Computer Vision",
    "official_url": "https://cvpr.thecvf.com/",
    "paper_source": "CVF OpenAccess or official accepted papers page",
    "reference_url": "https://papercopilot.com/",
    "status": "manual_verified"
  }
}
```

Official or authorized sources should become providers instead, such as CVF OpenAccess, OpenReview, ACL Anthology, arXiv, OpenAlex, and Semantic Scholar.

## Testing

Add focused tests for:

- CLI accepts `--provider google_scholar`.
- Default provider list does not include `google_scholar`.
- Missing `SERPAPI_API_KEY` produces a clear provider error.
- Cache hit avoids calling the HTTP opener.
- Cache miss calls SerpAPI and writes `provider_query_cache`.
- Monthly usage limit blocks a request before HTTP is called.
- Successful SerpAPI request increments `provider_usage`.
- SerpAPI Google Scholar JSON maps into `CandidatePaper`.
- Paper Copilot is documented as a guide only and has no automatic provider registration.

## Acceptance Criteria

- Users must explicitly opt into Google Scholar discovery.
- Repeating the same Google Scholar query within the TTL must not spend SerpAPI quota.
- Monthly usage must stop before the configured limit.
- Discovery runs must continue to support provider-level partial failure.
- No code automatically scrapes Paper Copilot.

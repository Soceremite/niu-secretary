import json
import urllib.error
from io import BytesIO
from pathlib import Path

import pytest

from airesearch.db import init_db
from airesearch.provider_cache import cache_key, increment_usage, put_cached_response
from airesearch.providers import (
    ArxivProvider,
    GoogleScholarProvider,
    OpenAlexProvider,
    SemanticScholarProvider,
    arxiv_id_from_input,
    arxiv_pdf_fallback_command,
    fetch_arxiv_website_metadata,
    parse_arxiv_search_html,
)


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RecordingOpener:
    def __init__(self, payload: str | bytes):
        self.payload = payload.encode("utf-8") if isinstance(payload, str) else payload
        self.requests = []

    def __call__(self, request, timeout=0):
        self.requests.append(request)
        return FakeResponse(self.payload)


class FailFirstThenPayloadOpener:
    """Fails the first call (simulating the rate-limited export API), then serves payload."""

    def __init__(self, payload: str):
        self.payload = payload.encode("utf-8")
        self.requests = []
        self.calls = 0

    def __call__(self, request, timeout=0):
        self.requests.append(request)
        self.calls += 1
        if self.calls == 1:
            raise urllib.error.URLError("HTTP Error 429: Rate exceeded")
        return FakeResponse(self.payload)


def test_openalex_provider_parses_work_result():
    opener = RecordingOpener(
        json.dumps(
            {
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "title": "World Foundation Models for Physical AI",
                        "publication_date": "2026-02-01",
                        "publication_year": 2026,
                        "doi": "https://doi.org/10.0000/example",
                        "authorships": [
                            {
                                "author": {"display_name": "Ada Researcher"},
                                "institutions": [{"display_name": "NVIDIA"}],
                            }
                        ],
                        "primary_location": {
                            "landing_page_url": "https://example.org/paper",
                            "source": {"display_name": "ICLR"},
                        },
                        "abstract_inverted_index": {
                            "world": [0],
                            "model": [1],
                            "physical": [2],
                            "AI": [3],
                        },
                    }
                ]
            }
        )
    )

    papers = OpenAlexProvider(opener=opener).search("world_models_physical_ai", 3)

    assert papers[0].source == "openalex"
    assert papers[0].source_id == "W123"
    assert papers[0].title == "World Foundation Models for Physical AI"
    assert papers[0].organizations == ["NVIDIA"]
    assert papers[0].venue == "ICLR"
    assert papers[0].published_date == "2026-02-01"
    assert papers[0].abstract == "world model physical AI"


def test_arxiv_provider_parses_atom_result():
    opener = RecordingOpener(
        """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>https://arxiv.org/abs/2601.00001v2</id>
            <title>Unified Multimodal Understanding and Generation</title>
            <summary>A unified vision-language model.</summary>
            <published>2026-01-10T00:00:00Z</published>
            <author><name>Jane Doe</name></author>
            <category term="cs.CV" />
          </entry>
        </feed>
        """
    )

    papers = ArxivProvider(opener=opener).search("unified_multimodal_understanding_generation", 2)

    assert papers[0].source == "arxiv"
    assert papers[0].source_id == "2601.00001"
    assert papers[0].url == "https://arxiv.org/abs/2601.00001"
    assert papers[0].authors == ["Jane Doe"]
    assert papers[0].published_date == "2026-01-10"
    assert papers[0].venue == "arXiv cs.CV"


ARXIV_SEARCH_PAGE_HTML = """
<li class="arxiv-result">
    <div class="is-marginless">
      <p class="list-title is-inline-block"><a href="https://arxiv.org/abs/2609.15903">arXiv:2609.15903</a></p>
      <div class="tags is-inline-block">
        <span class="tag is-small is-link tooltip is-tooltip-top" data-tooltip="Machine Learning">cs.LG</span>
      </div>
    </div>
    <p class="title is-5 mathjax">
        Discrete Beckmann Transport <span class="search-hit mathjax">Models</span> for One-Step <span class="search-hit mathjax">Language</span> <span class="search-hit mathjax">Modeling</span>
    </p>
    <p class="authors">
      <span class="has-text-black-bis has-text-weight-semibold">Authors:</span>
      <a href="/search/?searchtype=author&amp;query=Tang%2C+S">Sophia Tang</a>,
      <a href="/search/?searchtype=author&amp;query=Wang%2C+S">Shiyi Wang</a>
    </p>
    <p class="abstract mathjax">
      <span class="search-hit">Abstract</span>:
      <span class="abstract-short has-text-grey-dark mathjax">Discrete &hellip; <a class="is-size-7">&#9661; More</a></span>
      <span class="abstract-full has-text-grey-dark mathjax">Discrete <span class="search-hit mathjax">diffusion</span> and flow models are promising alternatives.</span>
    </p>
    <p class="is-size-7"><span class="has-text-black-bis has-text-weight-semibold">Submitted</span> 14 September, 2026; <span class="has-text-black-bis has-text-weight-semibold">originally announced</span> September 2026.</p>
</li>
<li class="arxiv-result">
    <div class="is-marginless">
      <p class="list-title is-inline-block"><a href="https://arxiv.org/abs/2508.02193v2">arXiv:2508.02193v2</a></p>
      <div class="tags is-inline-block">
        <span class="tag is-small is-link tooltip is-tooltip-top" data-tooltip="Computation and Language">cs.CL</span>
      </div>
    </div>
    <p class="title is-5 mathjax">Seed Diffusion: A Large-Scale Diffusion Language Model with High-Speed</p>
    <p class="authors">
      <span class="has-text-black-bis has-text-weight-semibold">Authors:</span>
      <a href="/search/?searchtype=author&amp;query=Yang%2C+Z">Zed Yang</a>
    </p>
    <p class="abstract mathjax">
      <span class="search-hit">Abstract</span>:
      <span class="abstract-short has-text-grey-dark mathjax">We introduce Seed Diffusion &hellip; <a class="is-size-7">&#9661; More</a></span>
      <span class="abstract-full has-text-grey-dark mathjax">We introduce Seed Diffusion, a full-size diffusion language model.</span>
    </p>
    <p class="is-size-7"><span class="has-text-black-bis has-text-weight-semibold">Submitted</span> 4 August, 2025; <span class="has-text-black-bis has-text-weight-semibold">originally announced</span> August 2025.</p>
</li>
"""


def test_arxiv_provider_falls_back_to_site_when_export_api_rate_limited():
    opener = FailFirstThenPayloadOpener(ARXIV_SEARCH_PAGE_HTML)

    papers = ArxivProvider(opener=opener).search("language_foundation_models", 5)

    assert len(opener.requests) == 2
    assert "export.arxiv.org" in opener.requests[0].full_url
    assert "arxiv.org/search" in opener.requests[1].full_url
    assert "searchtype=all" in opener.requests[1].full_url
    assert papers[0].source == "arxiv"
    assert papers[0].source_id == "2609.15903"
    assert papers[0].title == "Discrete Beckmann Transport Models for One-Step Language Modeling"
    assert papers[0].authors == ["Sophia Tang", "Shiyi Wang"]
    assert papers[0].published_date == "2026-09-14"
    assert papers[0].venue == "arXiv cs.LG"
    assert papers[0].abstract == "Discrete diffusion and flow models are promising alternatives."
    assert papers[0].artifact_links == ["https://arxiv.org/pdf/2609.15903"]
    assert papers[1].source_id == "2508.02193"
    assert papers[1].published_date == "2025-08-04"
    assert papers[1].venue == "arXiv cs.CL"


def test_parse_arxiv_search_html_returns_empty_when_no_results():
    assert parse_arxiv_search_html("<html><body><p>Sorry, your query returned no results</p></body></html>") == []


ARXIV_ABS_PAGE_HTML = """
<html><head>
<meta name="citation_title" content="DA-DLM: Explicitly Modeling Token Dependencies in Diffusion Language Models" />
<meta name="citation_author" content="Ji, Pengyu" />
<meta name="citation_author" content="Zhang, Zichen" />
<meta name="citation_date" content="2026/09/14" />
<meta name="citation_pdf_url" content="https://arxiv.org/pdf/2609.15070" />
</head><body>
<blockquote class="abstract mathjax">
  <span class="descriptor">Abstract:</span>Diffusion Language Models generate text by denoising.
</blockquote>
</body></html>
"""


def test_arxiv_id_from_input_variants():
    assert arxiv_id_from_input("2609.15070") == "2609.15070"
    assert arxiv_id_from_input("arXiv:2609.15070v2") == "2609.15070"
    assert arxiv_id_from_input("https://arxiv.org/abs/2609.15070") == "2609.15070"
    assert arxiv_id_from_input("https://arxiv.org/pdf/2609.15070v1") == "2609.15070"
    assert arxiv_id_from_input("Attention Is All You Need") == ""
    assert arxiv_id_from_input("https://github.com/a/b/blob/main/paper.pdf") == ""


def test_fetch_arxiv_website_metadata_reads_abs_page():
    opener = RecordingOpener(ARXIV_ABS_PAGE_HTML)

    meta = fetch_arxiv_website_metadata("2609.15070", opener=opener)

    assert meta["title"] == "DA-DLM: Explicitly Modeling Token Dependencies in Diffusion Language Models"
    assert meta["authors"] == ["Ji, Pengyu", "Zhang, Zichen"]
    assert meta["published_date"] == "2026-09-14"
    assert meta["year"] == 2026
    assert meta["abstract"] == "Diffusion Language Models generate text by denoising."
    assert meta["pdf_url"] == "https://arxiv.org/pdf/2609.15070"
    assert "arxiv.org/abs/2609.15070" in opener.requests[0].full_url


def test_arxiv_pdf_fallback_command_builds_papi_pdf_command():
    opener = RecordingOpener(ARXIV_ABS_PAGE_HTML)

    command = arxiv_pdf_fallback_command("papi", "https://arxiv.org/abs/2609.15070", opener=opener)

    assert command is not None
    assert command[:5] == ["papi", "add", "--pdf", "https://arxiv.org/pdf/2609.15070", "--title"]
    assert command[5] == "DA-DLM: Explicitly Modeling Token Dependencies in Diffusion Language Models"
    assert "Ji, Pengyu; Zhang, Zichen" in command
    assert "--year" in command and "2026" in command
    assert "--url" in command and "https://arxiv.org/abs/2609.15070" in command


def test_arxiv_pdf_fallback_command_ignores_non_arxiv_input():
    assert arxiv_pdf_fallback_command("papi", "https://example.org/paper.pdf") is None
    assert arxiv_pdf_fallback_command("papi", "Attention Is All You Need") is None


def test_semantic_scholar_provider_parses_search_result_and_api_key_header():
    opener = RecordingOpener(
        json.dumps(
            {
                "data": [
                    {
                        "paperId": "abc123",
                        "title": "Diffusion Policy for Robot Foundation Models",
                        "url": "https://www.semanticscholar.org/paper/abc123",
                        "abstract": "diffusion policy for robotics",
                        "venue": "CoRL",
                        "year": 2025,
                        "publicationDate": "2025-09-15",
                        "authors": [{"name": "Alex Scientist"}],
                        "externalIds": {"ArXiv": "2509.00001"},
                    }
                ]
            }
        )
    )

    papers = SemanticScholarProvider(api_key="secret-key", opener=opener).search("diffusion_models", 1)

    assert papers[0].source == "semantic_scholar"
    assert papers[0].source_id == "abc123"
    assert papers[0].artifact_links == ["https://arxiv.org/abs/2509.00001"]
    assert opener.requests[0].headers["X-api-key"] == "secret-key"

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


def test_google_scholar_provider_caps_serpapi_num_at_50(tmp_path: Path):
    db_path = tmp_path / "db.sqlite3"
    init_db(db_path)
    opener = RecordingOpener(google_scholar_payload())

    GoogleScholarProvider(
        db_path=db_path,
        api_key="serp-key",
        opener=opener,
        monthly_limit=10,
        cache_ttl_days=30,
    ).search("diffusion_models", 100)

    assert "num=50" in opener.requests[0].full_url


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


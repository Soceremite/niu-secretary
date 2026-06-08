import json
from io import BytesIO
from pathlib import Path

import pytest

from airesearch.db import init_db
from airesearch.provider_cache import cache_key, increment_usage, put_cached_response
from airesearch.providers import ArxivProvider, GoogleScholarProvider, OpenAlexProvider, SemanticScholarProvider


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


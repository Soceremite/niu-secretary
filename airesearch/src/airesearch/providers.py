from __future__ import annotations

import json
import os
import re
import hashlib
from datetime import date
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from typing import Any

from airesearch.candidates import CandidatePaper
from airesearch.config import Settings
from airesearch.provider_cache import (
    cache_key,
    get_cached_response,
    increment_usage,
    put_cached_response,
    quota_available,
)
from airesearch.profiles import default_profiles


HttpOpener = Callable[[urllib.request.Request, float], Any]

PROFILE_QUERY = {
    "multimodal_foundation_models": (
        '"multimodal foundation model" OR "large multimodal model" OR '
        '"vision language model" OR "vision-language model" OR MLLM OR VLM OR omni-modal'
    ),
    "unified_multimodal_understanding_generation": (
        '"unified multimodal understanding and generation" OR '
        '"unified vision-language" OR "image understanding and generation" OR '
        '"autoregressive visual generation"'
    ),
    "world_models_physical_ai": (
        '"world foundation model" OR "physical AI" OR "video world model" OR '
        '"interactive world model" OR "generative world model" OR "neural world model"'
    ),
    "diffusion_models": (
        '"diffusion model" OR "discrete diffusion" OR "diffusion policy" OR '
        '"flow matching" OR "rectified flow"'
    ),
    "embodied_ai_vla_robotics": (
        '"embodied AI" OR "vision-language-action" OR VLA OR '
        '"robot foundation model" OR "generalist robot policy"'
    ),
}


def profile_query(profile_name: str) -> str:
    if profile_name in PROFILE_QUERY:
        return PROFILE_QUERY[profile_name]
    for profile in default_profiles():
        if profile.name == profile_name:
            return " OR ".join(f'"{keyword}"' for keyword in profile.keywords)
    raise ValueError(f"unknown research profile: {profile_name}")


def default_opener(request: urllib.request.Request, timeout: float = 30.0) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_json(
    url: str,
    *,
    opener: HttpOpener = default_opener,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=dict(headers or {}))
    with opener(request, timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(
    url: str,
    *,
    opener: HttpOpener = default_opener,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30.0,
) -> str:
    request = urllib.request.Request(url, headers=dict(headers or {}))
    with opener(request, timeout) as response:
        return response.read().decode("utf-8")


def compact_text(value: str | None) -> str:
    return " ".join((value or "").split())


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



def is_non_paper_location(url: str, venue: str) -> bool:
    combined = f"{url} {venue}".lower()
    blocked = [
        "zenodo.org",
        "doi.org/10.5281/zenodo",
        "github.com",
    ]
    return any(term in combined for term in blocked)


def openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned.append((int(position), word))
    positioned.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned)


def openalex_work_id(raw_id: str) -> str:
    return raw_id.rstrip("/").split("/")[-1] if raw_id else ""


def arxiv_id_from_url(raw_url: str) -> str:
    raw_id = raw_url.rstrip("/").split("/")[-1]
    return re.sub(r"v\d+$", "", raw_id)


def year_from_date(value: str) -> int | None:
    if len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


class OpenAlexProvider:
    name = "openalex"

    def __init__(self, *, opener: HttpOpener = default_opener, mailto: str | None = None):
        self.opener = opener
        self.mailto = mailto or os.environ.get("OPENALEX_MAILTO", "")

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        query = profile_query(profile_name)
        params = {
            "search": query,
            "filter": f"from_publication_date:2024-01-01,to_publication_date:{date.today().isoformat()}",
            "per-page": str(max(1, min(limit, 200))),
            "sort": "publication_date:desc",
        }
        if self.mailto:
            params["mailto"] = self.mailto
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        payload = fetch_json(url, opener=self.opener, headers={"User-Agent": "airesearch/0.1"})
        papers = [self._parse_work(item) for item in payload.get("results", [])]
        return [paper for paper in papers if not is_non_paper_location(paper.url, paper.venue)]

    def _parse_work(self, item: dict[str, Any]) -> CandidatePaper:
        authors = []
        organizations = []
        for authorship in item.get("authorships") or []:
            author_name = ((authorship.get("author") or {}).get("display_name") or "").strip()
            if author_name:
                authors.append(author_name)
            for institution in authorship.get("institutions") or []:
                org_name = (institution.get("display_name") or "").strip()
                if org_name and org_name not in organizations:
                    organizations.append(org_name)

        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        url = location.get("landing_page_url") or location.get("pdf_url") or item.get("doi") or item.get("id") or ""
        return CandidatePaper(
            source=self.name,
            source_id=openalex_work_id(item.get("id") or ""),
            title=compact_text(item.get("title") or item.get("display_name")),
            url=url,
            authors=authors,
            organizations=organizations,
            venue=compact_text(source.get("display_name")),
            published_date=item.get("publication_date") or "",
            year=item.get("publication_year"),
            abstract=openalex_abstract(item.get("abstract_inverted_index")),
        )


class ArxivProvider:
    name = "arxiv"

    def __init__(self, *, opener: HttpOpener = default_opener):
        self.opener = opener

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        query = profile_query(profile_name)
        params = {
            "search_query": "all:(" + query + ")",
            "start": "0",
            "max_results": str(max(1, min(limit, 100))),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        xml_text = fetch_text(url, opener=self.opener, headers={"User-Agent": "airesearch/0.1"})
        return self._parse_feed(xml_text)

    def _parse_feed(self, xml_text: str) -> list[CandidatePaper]:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_text)
        papers: list[CandidatePaper] = []
        for entry in root.findall("atom:entry", ns):
            raw_id = compact_text(entry.findtext("atom:id", default="", namespaces=ns))
            arxiv_id = arxiv_id_from_url(raw_id)
            published = compact_text(entry.findtext("atom:published", default="", namespaces=ns))[:10]
            authors = [
                compact_text(author.findtext("atom:name", default="", namespaces=ns))
                for author in entry.findall("atom:author", ns)
            ]
            categories = [
                category.attrib.get("term", "")
                for category in entry.findall("atom:category", ns)
                if category.attrib.get("term")
            ]
            papers.append(
                CandidatePaper(
                    source=self.name,
                    source_id=arxiv_id,
                    title=compact_text(entry.findtext("atom:title", default="", namespaces=ns)),
                    url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else raw_id,
                    authors=[author for author in authors if author],
                    venue="arXiv " + ", ".join(categories) if categories else "arXiv",
                    published_date=published,
                    year=year_from_date(published),
                    abstract=compact_text(entry.findtext("atom:summary", default="", namespaces=ns)),
                    artifact_links=[f"https://arxiv.org/pdf/{arxiv_id}"] if arxiv_id else [],
                )
            )
        return papers


class SemanticScholarProvider:
    name = "semantic_scholar"

    def __init__(
        self,
        *,
        opener: HttpOpener = default_opener,
        api_key: str | None = None,
    ):
        self.opener = opener
        self.api_key = api_key if api_key is not None else os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        query = profile_query(profile_name)
        params = {
            "query": query,
            "limit": str(max(1, min(limit, 100))),
            "fields": "paperId,title,url,abstract,venue,year,publicationDate,authors,externalIds",
        }
        headers = {"User-Agent": "airesearch/0.1"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
        payload = fetch_json(url, opener=self.opener, headers=headers)
        return [self._parse_paper(item) for item in payload.get("data", [])]

    def _parse_paper(self, item: dict[str, Any]) -> CandidatePaper:
        external_ids = item.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv") or external_ids.get("Arxiv")
        artifact_links = [f"https://arxiv.org/abs/{arxiv_id}"] if arxiv_id else []
        return CandidatePaper(
            source=self.name,
            source_id=item.get("paperId") or arxiv_id or item.get("url") or "",
            title=compact_text(item.get("title")),
            url=item.get("url") or (artifact_links[0] if artifact_links else ""),
            authors=[compact_text(author.get("name")) for author in item.get("authors", []) if author.get("name")],
            venue=compact_text(item.get("venue")),
            published_date=item.get("publicationDate") or "",
            year=item.get("year"),
            abstract=compact_text(item.get("abstract")),
            artifact_links=artifact_links,
        )


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


def default_discovery_providers() -> list[OpenAlexProvider | ArxivProvider | SemanticScholarProvider]:
    return [OpenAlexProvider(), ArxivProvider(), SemanticScholarProvider()]

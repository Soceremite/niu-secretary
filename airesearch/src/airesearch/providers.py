from __future__ import annotations

import json
import os
import re
import hashlib
from datetime import date
from html import unescape as html_unescape
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

ARXIV_SEARCH_URL = "https://arxiv.org/search/"
ARXIV_ABS_URL = "https://arxiv.org/abs/"
ARXIV_PDF_URL = "https://arxiv.org/pdf/"
ARXIV_USER_AGENT = "NiuSecretary-AIResearch/1.0 (+https://github.com/Soceremite/niu-secretary)"

PROFILE_QUERY = {
    "language_foundation_models": (
        '"language foundation model" OR "large language model" OR LLM OR '
        '"diffusion language model" OR "latent language model" OR '
        '"continuous token generation" OR "embedded language flows" OR '
        '"non-autoregressive language model" OR "text diffusion model" OR '
        '"flow matching language model"'
    ),
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


_MONTH_NUMBERS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _strip_markup(fragment: str) -> str:
    return compact_text(html_unescape(re.sub(r"<[^>]+>", "", fragment)))


def _arxiv_website_date(block: str) -> str:
    match = re.search(
        r"Submitted</span>\s*([0-9]{1,2})\s+([A-Za-z]+),?\s+([0-9]{4})", block
    )
    if not match:
        return ""
    day, month_name, year = match.groups()
    month = _MONTH_NUMBERS.get(month_name.lower())
    if not month:
        return ""
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def _arxiv_website_abstract(block: str) -> str:
    for marker in ('<span class="abstract-full', '<span class="abstract-short'):
        index = block.find(marker)
        if index == -1:
            continue
        tail = block[index:]
        paragraph_end = tail.find("</p>")
        if paragraph_end != -1:
            tail = tail[:paragraph_end]
        open_end = tail.find(">")
        if open_end == -1:
            continue
        content = tail[open_end + 1 :]
        wrapper_close = content.rfind("</span>")
        if wrapper_close != -1:
            content = content[:wrapper_close]
        content = re.sub(r'<a class="is-size-7".*?</a>', " ", content, flags=re.S)
        text = _strip_markup(content)
        if text:
            return text
    return ""


def parse_arxiv_search_html(markup: str) -> list[dict[str, Any]]:
    """Parse an arxiv.org/search results page into neutral row dicts.

    Used when the export API is rate-limited or unreachable; the public search
    page stays available and carries the same metadata (id, title, authors,
    abstract, submission date, categories).
    """
    rows: list[dict[str, Any]] = []
    for block in markup.split('<li class="arxiv-result">')[1:]:
        block = block.split("</li>", 1)[0]
        id_match = re.search(r"arxiv\.org/abs/([^\"'#?]+)", block)
        arxiv_id = arxiv_id_from_url(id_match.group(1)) if id_match else ""
        title_match = re.search(r'<p class="title is-5 mathjax">(.*?)</p>', block, flags=re.S)
        title = _strip_markup(title_match.group(1)) if title_match else ""
        if not title or not arxiv_id:
            continue
        authors_match = re.search(r'<p class="authors">(.*?)</p>', block, flags=re.S)
        authors: list[str] = []
        if authors_match:
            authors = [
                compact_text(html_unescape(name))
                for name in re.findall(r"<a [^>]*>([^<]+)</a>", authors_match.group(1))
            ]
        categories = [
            compact_text(html_unescape(term))
            for term in re.findall(r'<span class="tag[^"]*"[^>]*>([^<]+)</span>', block)
        ]
        rows.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": [author for author in authors if author],
                "abstract": _arxiv_website_abstract(block),
                "published_date": _arxiv_website_date(block),
                "categories": [category for category in categories if category],
            }
        )
    return rows


def search_arxiv_website(
    query: str,
    limit: int = 10,
    *,
    opener: HttpOpener = default_opener,
) -> list[CandidatePaper]:
    """Search arXiv via the public arxiv.org search page — the fallback path.

    The export API (export.arxiv.org) applies aggressive rate limiting; this
    keeps discovery and the admin single-paper search working when it trips.
    """
    size = next((page for page in (25, 50, 100, 200) if page >= min(limit, 200)), 200)
    params = {"searchtype": "all", "query": query, "start": "0", "size": str(size)}
    url = ARXIV_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    markup = fetch_text(url, opener=opener, headers={"User-Agent": ARXIV_USER_AGENT}, timeout=45.0)
    papers: list[CandidatePaper] = []
    for row in parse_arxiv_search_html(markup)[:limit]:
        arxiv_id = row["arxiv_id"]
        categories = row["categories"]
        papers.append(
            CandidatePaper(
                source="arxiv",
                source_id=arxiv_id,
                title=row["title"],
                url=f"https://arxiv.org/abs/{arxiv_id}",
                authors=row["authors"],
                venue="arXiv " + ", ".join(categories) if categories else "arXiv",
                published_date=row["published_date"],
                year=year_from_date(row["published_date"]),
                abstract=row["abstract"],
                artifact_links=[f"https://arxiv.org/pdf/{arxiv_id}"],
            )
        )
    return papers


_ARXIV_BARE_ID = re.compile(r"^(?:arxiv:)?\s*(\d{4}\.\d{4,5})(?:v\d+)?$", re.IGNORECASE)
_ARXIV_OLD_ID = re.compile(r"^(?:arxiv:)?\s*([a-z\-]+(?:\.[A-Za-z]{2})?/\d{7})(?:v\d+)?$", re.IGNORECASE)
_ARXIV_URL_ID = re.compile(r"arxiv\.org/(?:abs|pdf)/([A-Za-z0-9.\-/]+)", re.IGNORECASE)


def arxiv_id_from_input(value: str) -> str:
    """Extract an arXiv id from a bare id, 'arXiv:ID', or an abs/pdf URL; '' when not an arXiv reference."""
    text = (value or "").strip()
    if not text:
        return ""
    match = _ARXIV_URL_ID.search(text)
    if match:
        return arxiv_id_from_url(match.group(1))
    match = _ARXIV_BARE_ID.match(text) or _ARXIV_OLD_ID.match(text)
    if match:
        return match.group(1)
    return ""


def _meta_content(markup: str, name: str) -> str:
    match = re.search(rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"', markup)
    return compact_text(html_unescape(match.group(1))) if match else ""


def fetch_arxiv_website_metadata(arxiv_id: str, *, opener: HttpOpener = default_opener) -> dict[str, Any]:
    """Read title/authors/date/abstract from the public abs page — no export API involved."""
    resolved = arxiv_id_from_input(arxiv_id) or arxiv_id
    abs_url = ARXIV_ABS_URL + resolved
    markup = fetch_text(abs_url, opener=opener, headers={"User-Agent": ARXIV_USER_AGENT}, timeout=45.0)
    title = _meta_content(markup, "citation_title")
    if not title:
        heading = re.search(r'<h1 class="title mathjax">(.*?)</h1>', markup, flags=re.S)
        if heading:
            title = _strip_markup(re.sub(r'<span class="descriptor">.*?</span>', "", heading.group(1), flags=re.S))
    authors = [
        compact_text(html_unescape(author))
        for author in re.findall(r'<meta name="citation_author" content="([^"]*)"', markup)
    ]
    raw_date = _meta_content(markup, "citation_date")
    published_date = raw_date.replace("/", "-") if re.fullmatch(r"\d{4}/\d{2}/\d{2}", raw_date) else ""
    abstract = ""
    blockquote = re.search(r'<blockquote class="abstract mathjax">(.*?)</blockquote>', markup, flags=re.S)
    if blockquote:
        abstract = re.sub(r"^Abstract:\s*", "", _strip_markup(blockquote.group(1)))
    return {
        "arxiv_id": resolved,
        "title": title,
        "authors": [author for author in authors if author],
        "abstract": abstract,
        "published_date": published_date,
        "year": year_from_date(published_date),
        "pdf_url": _meta_content(markup, "citation_pdf_url") or (ARXIV_PDF_URL + resolved),
        "abs_url": abs_url,
    }


def arxiv_pdf_fallback_command(
    papi_executable: str,
    value: str,
    *,
    opener: HttpOpener = default_opener,
) -> list[str] | None:
    """Build a `papi add --pdf ...` command for an arXiv reference, bypassing the export API.

    The export API rate-limits aggressively (HTTP 429 "Rate exceeded"), which blocks
    both `papi add <id>` and `papi add <abs-url>`. The PDF and the metadata both come
    from arxiv.org itself, which stays reachable.
    """
    arxiv_id = arxiv_id_from_input(value)
    if not arxiv_id:
        return None
    try:
        meta = fetch_arxiv_website_metadata(arxiv_id, opener=opener)
    except Exception:
        return None
    if not meta["title"]:
        return None
    command = [papi_executable, "add", "--pdf", meta["pdf_url"], "--title", meta["title"]]
    if meta["authors"]:
        command += ["--authors", "; ".join(meta["authors"])]
    if meta["abstract"]:
        command += ["--abstract", meta["abstract"]]
    if meta["year"]:
        command += ["--year", str(meta["year"])]
    command += ["--url", meta["abs_url"]]
    return command


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
        try:
            xml_text = fetch_text(
                url,
                opener=self.opener,
                headers={"User-Agent": ARXIV_USER_AGENT},
                timeout=20.0,
            )
            return self._parse_feed(xml_text)
        except Exception:
            # export API is rate-limited or unreachable — use the public search page
            return search_arxiv_website(query, limit, opener=self.opener)

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
        bounded_limit = max(1, min(limit, 50))
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

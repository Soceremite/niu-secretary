"""URL normalization pipeline for batch ingest.

Resolves URLs that ``papi add`` cannot handle — NeurIPS proceedings,
CVPR openaccess, preprints.org, figshare, and other non-arxiv DOIs —
into arxiv IDs or paper titles that ``papi add`` can ingest.

Design
    * categorize_url     – classify a raw input into a known pattern
    * normalize_url_raw  – main entry: try to resolve to {arxiv_id, title, url}
    * Individual resolvers are pure functions that return str | None.
    * HTTP calls use the configured opener (swappable for testing).
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request
import html
from dataclasses import dataclass, field
from collections.abc import Callable

HttpOpener = Callable[[urllib.request.Request, float], str]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class NormalizeCategory:
    ARXIV = "arxiv"
    DOI = "doi"
    PROCEEDINGS = "proceedings"      # NeurIPS-style hash pages
    CVPR_OPENACCESS = "cvpr_openaccess"
    PREPRINTS = "preprints"          # preprints.org
    FIGSHARE = "figshare"
    TITLE = "title"                  # raw title string
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizeResult:
    normalized: str | None           # papi-compatible input (arxiv ID, URL, or title)
    category: str                    # NormalizeCategory
    method: str                      # e.g. "proceedings_title_arxiv_lookup"
    messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_ARXIV_ABS = re.compile(r"arxiv\.org/abs/([\w.\-]+)")
_ARXIV_PDF = re.compile(r"arxiv\.org/pdf/([\w.\-]+)")
_ARXIV_BARE_ID = re.compile(r"^(\d{4}\.\d{4,5})(?:v\d+)?$")
_DOI_PREFIX = re.compile(r"doi\.org/(10\.[^/]+/[^?\s]+)")

_PROCEEDINGS_HASH = re.compile(
    r"proceedings\.neurips\.cc/paper_files/paper/\d+/hash/([0-9a-f]+)(?:-Abstract-Conference)?"
)

_CVPR_OPENACCESS = re.compile(
    r"openaccess\.thecvf\.com/content/CVPR\w*/html/[^/]+_paper\.html"
)

_PREPRINTS_DOT_ORG = re.compile(r"doi\.org/10\.20944/preprints(\d+)")

_FIGSHARE = re.compile(r"(?:doi\.org/10\.6084/m9\.)?figshare\.(\d+)")


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------


def categorize_url(raw: str) -> str:
    """Return a NormalizeCategory constant for *raw*."""
    if _ARXIV_ABS.search(raw) or _ARXIV_PDF.search(raw) or _ARXIV_BARE_ID.match(raw.strip()):
        return NormalizeCategory.ARXIV
    if _PROCEEDINGS_HASH.search(raw):
        return NormalizeCategory.PROCEEDINGS
    if _CVPR_OPENACCESS.search(raw):
        return NormalizeCategory.CVPR_OPENACCESS
    if _PREPRINTS_DOT_ORG.search(raw):
        return NormalizeCategory.PREPRINTS
    if _FIGSHARE.search(raw):
        return NormalizeCategory.FIGSHARE
    if _DOI_PREFIX.search(raw):
        return NormalizeCategory.DOI
    # Heuristic: if it looks like a sentence, treat as title
    if " " in raw.strip() and not raw.strip().startswith(("http://", "https://")):
        return NormalizeCategory.TITLE
    return NormalizeCategory.UNKNOWN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_title(raw: str) -> str:
    """Collapse whitespace and strip."""
    return " ".join(raw.split()).strip()


def _extract_html_title(html_text: str) -> str | None:
    """Extract <title> or <meta name=\"citation_title\"> from HTML.

    Tries, in order:
      1. <meta name="citation_title">
      2. <meta name="DC.Title">
      3. <meta property="og:title">
      4. <title> tag
      5. <h1> tag
    """
    # 1. citation_title (most precise)
    m = re.search(
        r'<meta\s+name=["\']citation_title["\']\s+content=["\']([^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    )
    if m:
        return html.unescape(m.group(1))
    # 2. DC.Title
    m = re.search(
        r'<meta\s+name=["\']DC\.Title["\']\s+content=["\']([^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    )
    if m:
        return html.unescape(m.group(1))
    # 3. og:title
    m = re.search(
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        html_text,
        re.IGNORECASE,
    )
    if m:
        return html.unescape(m.group(1))
    # 4. <title>
    m = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    if m:
        raw_title = _clean_title(m.group(1))
        # Strip common suffixes
        raw_title = re.sub(r"\s*[|–—-]\s*(CVF Open Access|IEEE Xplore|OpenReview|arXiv|NeurIPS|Proceedings).*$", "", raw_title, flags=re.IGNORECASE)
        return html.unescape(raw_title)
    # 5. <h1> (last resort)
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.IGNORECASE | re.DOTALL)
    if m:
        return html.unescape(_clean_title(m.group(1)))
    return None


def _fetch_page(url: str, opener: HttpOpener, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )})
    try:
        return opener(req, timeout)
    except (OSError, ValueError, ssl.SSLError) as exc:
        raise _FetchError(str(exc)) from exc


class _FetchError(Exception):
    """Raised when a page fetch fails for any reason."""


def _fetch_json(url: str, opener: HttpOpener, timeout: float = 15.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )})
    try:
        body = opener(req, timeout)
    except (OSError, ValueError, ssl.SSLError) as exc:
        raise _FetchError(str(exc)) from exc
    return json.loads(body)


# ---------------------------------------------------------------------------
# Individual resolvers
# ---------------------------------------------------------------------------


def resolve_proceedings_to_title(
    url: str, *, opener: HttpOpener
) -> str | None:
    """Extract paper title from a NeurIPS proceedings page."""
    try:
        html_text = _fetch_page(url, opener)
    except _FetchError:
        return None
    return _extract_html_title(html_text)


def resolve_cvpr_to_title(
    url: str, *, opener: HttpOpener
) -> str | None:
    """Extract paper title from a CVPR openaccess page."""
    try:
        html_text = _fetch_page(url, opener)
    except _FetchError:
        return None
    return _extract_html_title(html_text)


def resolve_preprints_to_title(
    doi_url: str, *, opener: HttpOpener
) -> str | None:
    """Resolve a preprints.org DOI to paper title.

    preprints.org often blocks automated requests (403).
    Try OpenAlex as a fallback since preprints.org DOIs may be indexed there.
    """
    # Try direct page fetch first
    try:
        html_text = _fetch_page(doi_url, opener)
    except _FetchError:
        html_text = None
    if html_text:
        title = _extract_html_title(html_text)
        if title:
            return title
    # Fallback: try OpenAlex
    doi_match = _DOI_PREFIX.search(doi_url)
    if doi_match:
        work = resolve_doi_via_openalex(doi_match.group(1), opener=opener)
        if work and work.get("title"):
            return work.get("title")
    return None


def resolve_figshare_to_title(
    url: str, *, opener: HttpOpener
) -> str | None:
    """Resolve a figshare DOI to paper title.

    figshare often blocks automated requests (403).
    Try the figshare API first, then fall back to OpenAlex.
    """
    # Try figshare API
    figshare_match = _FIGSHARE.search(url)
    if figshare_match:
        article_id = figshare_match.group(1)
        api_url = f"https://api.figshare.com/v2/articles/{article_id}"
        try:
            data = _fetch_json(api_url, opener, timeout=15.0)
            if data.get("title"):
                return data["title"]
        except (_FetchError, json.JSONDecodeError, KeyError):
            pass
    # Fallback: try page scrape
    try:
        html_text = _fetch_page(url, opener)
    except _FetchError:
        html_text = None
    if html_text:
        title = _extract_html_title(html_text)
        if title:
            return title
    # Fallback: try OpenAlex
    doi_match = _DOI_PREFIX.search(url)
    if doi_match:
        work = resolve_doi_via_openalex(doi_match.group(1), opener=opener)
        if work and work.get("title"):
            return work.get("title")
    return None


def resolve_doi_via_openalex(
    doi: str, *, opener: HttpOpener
) -> dict | None:
    """Look up a DOI via the OpenAlex API; return work dict or None."""
    encoded = urllib.parse.quote(doi, safe="")
    api_url = f"https://api.openalex.org/works/doi:{encoded}"
    try:
        return _fetch_json(api_url, opener, timeout=20.0)
    except Exception:
        return None


def search_arxiv_by_title(
    title: str, *, opener: HttpOpener
) -> str | None:
    """Search arXiv API for *title*; return best-match arxiv ID or None."""
    import xml.etree.ElementTree as ET

    query = " AND ".join(f'ti:"{word}"' for word in title.split() if len(word) > 2)
    if not query:
        return None
    params = {
        "search_query": query,
        "start": "0",
        "max_results": "3",
        "sortBy": "relevance",
    }
    api_url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    try:
        xml_text = _fetch_page(api_url, opener, timeout=25.0)
    except Exception:
        return None

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    entries = root.findall("atom:entry", ns)
    if not entries:
        return None

    # Pick the first (best-match) entry
    raw_id = " ".join(
        (entries[0].findtext("atom:id", default="", namespaces=ns) or "").split()
    )
    m = re.search(r"arxiv\.org/abs/([\w.\-]+)", raw_id)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Main normalizer
# ---------------------------------------------------------------------------


def normalize_url_raw(
    raw: str,
    *,
    opener: HttpOpener | None = None,
) -> NormalizeResult:
    """Try to resolve *raw* into a papi-compatible input string.

    Returns a NormalizeResult; if *normalized* is None the input could not be resolved.
    """
    _opener: HttpOpener = opener or (  # type: ignore[assignment]
        lambda req, t: urllib.request.urlopen(req, timeout=t).read().decode("utf-8", errors="replace")
    )

    category = categorize_url(raw)

    # --- arXiv: already papi-compatible, pass through ---
    if category == NormalizeCategory.ARXIV:
        m = _ARXIV_ABS.search(raw) or _ARXIV_PDF.search(raw) or _ARXIV_BARE_ID.match(raw.strip())
        assert m is not None
        return NormalizeResult(
            normalized=m.group(1),
            category=category,
            method="arxiv_id_extracted",
        )

    # --- Title: already papi-compatible, pass through ---
    if category == NormalizeCategory.TITLE:
        return NormalizeResult(
            normalized=raw.strip(),
            category=category,
            method="title_passthrough",
        )

    # --- NeurIPS proceedings → extract title → search arXiv ---
    if category == NormalizeCategory.PROCEEDINGS:
        title = resolve_proceedings_to_title(raw, opener=_opener)
        if title:
            arxiv_id = search_arxiv_by_title(title, opener=_opener)
            if arxiv_id:
                return NormalizeResult(
                    normalized=arxiv_id,
                    category=category,
                    method="proceedings_title_arxiv_lookup",
                    messages=[f"title={title}"],
                )
            return NormalizeResult(
                normalized=title,
                category=category,
                method="proceedings_title_no_arxiv",
                messages=[f"title={title} (no arxiv match)"],
            )
        return NormalizeResult(
            normalized=None,
            category=category,
            method="proceedings_failed",
            messages=["could not extract title from proceedings page"],
        )

    # --- CVPR openaccess → extract title → search arXiv ---
    if category == NormalizeCategory.CVPR_OPENACCESS:
        title = resolve_cvpr_to_title(raw, opener=_opener)
        if title:
            arxiv_id = search_arxiv_by_title(title, opener=_opener)
            if arxiv_id:
                return NormalizeResult(
                    normalized=arxiv_id,
                    category=category,
                    method="cvpr_title_arxiv_lookup",
                    messages=[f"title={title}"],
                )
            return NormalizeResult(
                normalized=title,
                category=category,
                method="cvpr_title_no_arxiv",
                messages=[f"title={title} (no arxiv match)"],
            )
        return NormalizeResult(
            normalized=None,
            category=category,
            method="cvpr_failed",
            messages=["could not extract title from CVPR page"],
        )

    # --- preprints.org DOI → extract title → search arXiv ---
    if category == NormalizeCategory.PREPRINTS:
        title = resolve_preprints_to_title(raw, opener=_opener)
        if title:
            # Check if the title itself contains an arXiv reference
            arxiv_id = search_arxiv_by_title(title, opener=_opener)
            if arxiv_id:
                return NormalizeResult(
                    normalized=arxiv_id,
                    category=category,
                    method="preprints_title_arxiv_lookup",
                    messages=[f"title={title}"],
                )
            return NormalizeResult(
                normalized=title,
                category=category,
                method="preprints_title_no_arxiv",
                messages=[f"title={title} (no arxiv match)"],
            )
        return NormalizeResult(
            normalized=None,
            category=category,
            method="preprints_failed",
            messages=["could not extract title from preprints page"],
        )

    # --- figshare DOI → extract title from page ---
    if category == NormalizeCategory.FIGSHARE:
        title = resolve_figshare_to_title(raw, opener=_opener)
        if title:
            return NormalizeResult(
                normalized=title,
                category=category,
                method="figshare_title_extracted",
                messages=[f"title={title}"],
            )
        return NormalizeResult(
            normalized=None,
            category=category,
            method="figshare_failed",
            messages=["could not extract title from figshare page"],
        )

    # --- Generic DOI → OpenAlex lookup for arxiv ID ---
    if category == NormalizeCategory.DOI:
        doi_match = _DOI_PREFIX.search(raw)
        if doi_match:
            doi = doi_match.group(1)
            work = resolve_doi_via_openalex(doi, opener=_opener)
            if work and work.get("title"):
                title = work.get("title", "")
                # Check if there's a locations entry with an arxiv landing page
                primary_location = work.get("primary_location") or {}
                landing_page = primary_location.get("landing_page_url", "")
                pdf_url = primary_location.get("pdf_url", "")
                arxiv_match = _ARXIV_ABS.search(landing_page or "") or _ARXIV_ABS.search(pdf_url or "")
                if arxiv_match:
                    return NormalizeResult(
                        normalized=arxiv_match.group(1),
                        category=category,
                        method="doi_openalex_arxiv_location",
                        messages=[f"title={title}"],
                    )
                # No arxiv location — search by title
                arxiv_id = search_arxiv_by_title(title, opener=_opener)
                if arxiv_id:
                    return NormalizeResult(
                        normalized=arxiv_id,
                        category=category,
                        method="doi_openalex_title_arxiv_lookup",
                        messages=[f"title={title}"],
                    )
                # Title found but no arxiv — return title for papi
                return NormalizeResult(
                    normalized=title,
                    category=category,
                    method="doi_openalex_title_no_arxiv",
                    messages=[f"title={title} (no arxiv match)"],
                )
        return NormalizeResult(
            normalized=None,
            category=category,
            method="doi_failed",
            messages=["could not resolve DOI via OpenAlex"],
        )

    # --- Unknown ---
    return NormalizeResult(
        normalized=None,
        category=category,
        method="unknown",
        messages=["input pattern not recognized"],
    )


def normalize_manifest(
    raw_inputs: list[str],
    *,
    opener: HttpOpener | None = None,
) -> dict[str, NormalizeResult]:
    """Normalize a list of raw inputs, returning a dict keyed by raw input.

    Already-papi-compatible inputs (arxiv IDs/URLs, titles) pass through
    with their original values.  Problematic URLs are resolved.
    """
    return {raw: normalize_url_raw(raw, opener=opener) for raw in raw_inputs}

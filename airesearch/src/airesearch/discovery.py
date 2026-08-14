from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from airesearch.candidates import CandidatePaper, score_candidate, upsert_candidate
from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import utc_now
from airesearch.profiles import load_profile


class DiscoveryProvider(Protocol):
    name: str

    def search(self, profile_name: str, limit: int) -> list[CandidatePaper]:
        """Return candidate papers for a profile without mutating local state."""


def normalized_title(value: str) -> str:
    return " ".join(value.lower().split())


@dataclass(frozen=True)
class DiscoveryResult:
    total_seen: int
    stored_count: int
    skipped_count: int
    errors: list[str]


def run_discovery(
    *,
    db_path: Path,
    profile_name: str,
    providers: list[DiscoveryProvider],
    limit: int = 50,
    concurrency: int | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> DiscoveryResult:
    init_db(db_path)
    profile = load_profile(db_path, profile_name)
    started_at = utc_now()
    provider_names = [provider.name for provider in providers]
    total_seen = 0
    stored_count = 0
    skipped_count = 0
    errors: list[str] = []
    seen_titles: set[str] = set()

    max_workers = max(1, min(concurrency or len(providers) or 1, len(providers) or 1))

    def search_provider(provider: DiscoveryProvider) -> tuple[DiscoveryProvider, list[CandidatePaper] | None, str | None]:
        try:
            return provider, provider.search(profile_name, limit), None
        except Exception as exc:  # provider failures are audited without stopping other sources
            return provider, None, str(exc)

    provider_results: list[tuple[DiscoveryProvider, list[CandidatePaper] | None, str | None]] = []
    if max_workers == 1:
        provider_results = [search_provider(provider) for provider in providers]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(search_provider, provider) for provider in providers]
            for future in as_completed(futures):
                provider_results.append(future.result())

    provider_results.sort(key=lambda item: provider_names.index(item[0].name) if item[0].name in provider_names else 9999)
    for provider, candidates, error in provider_results:
        if error is not None:
            errors.append(f"{provider.name}: {error}")
            if progress_callback is not None:
                progress_callback(f"discover {profile_name}/{provider.name}")
            continue
        if candidates is None:
            continue
        for candidate in candidates[:limit]:
            total_seen += 1
            title_key = normalized_title(candidate.title)
            if title_key and title_key in seen_titles:
                skipped_count += 1
                continue
            if title_key:
                seen_titles.add(title_key)
            score, reasons = score_candidate(profile, candidate)
            if score <= 0:
                skipped_count += 1
                continue
            upsert_candidate(
                db_path,
                profile_name=profile_name,
                candidate=candidate,
                score=score,
                reasons=reasons,
            )
            stored_count += 1
        if progress_callback is not None:
            progress_callback(f"discover {profile_name}/{provider.name}")

    if errors and stored_count == 0:
        status = "failed"
    elif errors:
        status = "partial_success"
    else:
        status = "success"
    error = "\n".join(errors)
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into discovery_runs (
                profile_name, provider_names_json, total_seen, stored_count,
                skipped_count, started_at, finished_at, status, error
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_name,
                json.dumps(provider_names, ensure_ascii=False),
                total_seen,
                stored_count,
                skipped_count,
                started_at,
                utc_now(),
                status,
                error,
            ),
        )
        conn.commit()

    return DiscoveryResult(
        total_seen=total_seen,
        stored_count=stored_count,
        skipped_count=skipped_count,
        errors=errors,
    )

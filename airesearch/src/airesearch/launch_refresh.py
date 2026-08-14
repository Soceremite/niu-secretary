from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from airesearch.batch import BatchResult, run_batch_ingest
from airesearch.canonical_candidates import (
    CanonicalMaterializationResult,
    CandidateReviewResult,
    export_candidate_review,
    export_approved_candidates,
    list_approved_candidates,
    materialize_candidate_papers,
    select_top_canonical_candidates,
)
from airesearch.db import init_db
from airesearch.discovery import DiscoveryProvider, DiscoveryResult, run_discovery
from airesearch.mvp_pipeline import MvpPipelineResult, run_mvp_pipeline
from airesearch.paperpipe_sync import SyncResult, sync_paperpipe, utc_now
from airesearch.profiles import default_profiles, seed_profiles
from airesearch.static_publish import StaticPublishResult, publish_static_site

MVP_PROGRESS_STEPS = 13


@dataclass(frozen=True)
class ProfileDiscoverySummary:
    profile_name: str
    total_seen: int
    stored_count: int
    skipped_count: int
    errors: list[str]


@dataclass(frozen=True)
class LaunchRefreshResult:
    db_path: Path
    paper_db_path: Path
    profiles_seeded: int
    profile_names: list[str]
    provider_names: list[str]
    discovery: list[ProfileDiscoverySummary]
    canonical: CanonicalMaterializationResult
    selected_count: int
    approved_count: int
    approved_manifest_path: Path
    candidate_review: CandidateReviewResult
    batch: BatchResult | None
    sync: SyncResult
    mvp: MvpPipelineResult
    publish: StaticPublishResult
    run_manifest_path: Path
    run_history_path: Path | None = None
    concise_log_path: Path | None = None
    steps: list[str] = field(default_factory=list)


def _path_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_path_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _path_value(item) for key, item in value.items()}
    return value


def _result_payload(result: LaunchRefreshResult) -> dict[str, Any]:
    payload = asdict(result)
    return _path_value(payload)


def _run_history_stem(generated_at: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in generated_at).strip("-")


def write_launch_refresh_manifest(
    result: LaunchRefreshResult,
    *,
    generated_at: str | None = None,
    path: Path | None = None,
) -> None:
    target_path = path or result.run_manifest_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _result_payload(result)
    payload["generated_at"] = generated_at or utc_now()
    target_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_launch_refresh_log(result: LaunchRefreshResult, *, generated_at: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    discovered = sum(item.stored_count for item in result.discovery)
    discovery_errors = sum(len(item.errors) for item in result.discovery)
    batch_failed = result.batch.failed if result.batch is not None else 0
    lines = [
        f"generated_at={generated_at}",
        f"profiles={len(result.profile_names)}",
        f"providers={','.join(result.provider_names)}",
        f"discovered={discovered}",
        f"discovery_errors={discovery_errors}",
        f"canonical={result.canonical.canonical_count}",
        f"selected={result.selected_count}",
        f"approved={result.approved_count}",
        f"candidate_review={result.candidate_review.json_path}",
        f"candidate_review_already_in_database={result.candidate_review.already_in_database_count}",
        f"candidate_review_below_min_score={result.candidate_review.below_min_score_count}",
        f"candidate_review_not_in_top_limit={result.candidate_review.not_in_top_limit_count}",
        f"batch_failed={batch_failed}",
        f"papers={result.mvp.papers_seen}",
        f"facts={result.mvp.facts_written}",
        f"fact_failures={result.mvp.fact_failures}",
        f"site={result.publish.entrypoint}",
        f"publish_diff={result.publish.diff_path}",
        f"run_manifest={result.run_manifest_path}",
        f"run_history={result.run_history_path}",
        "steps=" + ",".join(result.steps),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_launch_refresh(
    *,
    db_path: Path,
    paper_db_path: Path,
    providers: list[DiscoveryProvider],
    profile_names: list[str] | None = None,
    limit_per_profile: int = 50,
    select_limit: int = 10,
    min_score: float | None = 0.6,
    approved_manifest_path: Path = Path("manifests/approved-launch-refresh-current.txt"),
    papi_executable: str = "papi",
    out_dir: Path = Path("exports/mvp-current"),
    site_dir: Path = Path("exports/site-current"),
    run_manifest_path: Path = Path("exports/launch-refresh-current.json"),
    candidate_review_json_path: Path | None = None,
    candidate_review_markdown_path: Path | None = None,
    fact_provider: str = "openai-compatible",
    fixture_path: Path | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str = "AIRESEARCH_FACT_API_KEY",
    concurrency: int = 5,
    refresh_facts: bool = False,
    fact_error_policy: str = "strict",
    semantic: bool = False,
    semantic_threshold: float = 0.82,
    history_dir: Path | None = Path("exports/run-history"),
    log_dir: Path | None = Path("logs"),
    progress_callback: Callable[[str], None] | None = None,
) -> LaunchRefreshResult:
    if not providers:
        raise ValueError("at least one discovery provider is required")
    if limit_per_profile <= 0:
        raise ValueError("limit_per_profile must be greater than zero")
    if select_limit <= 0:
        raise ValueError("select_limit must be greater than zero")

    steps: list[str] = []

    def mark(step: str) -> None:
        steps.append(step)
        if progress_callback is not None:
            progress_callback(step)

    init_db(db_path)
    mark("init-db")

    profiles_seeded = seed_profiles(db_path)
    mark("seed-profiles")

    names = profile_names or [profile.name for profile in default_profiles()]
    provider_names = [provider.name for provider in providers]
    discovery_summaries: list[ProfileDiscoverySummary] = []
    for profile_name in names:
        discovery_result: DiscoveryResult = run_discovery(
            db_path=db_path,
            profile_name=profile_name,
            providers=providers,
            limit=limit_per_profile,
            concurrency=concurrency,
            progress_callback=progress_callback,
        )
        discovery_summaries.append(
            ProfileDiscoverySummary(
                profile_name=profile_name,
                total_seen=discovery_result.total_seen,
                stored_count=discovery_result.stored_count,
                skipped_count=discovery_result.skipped_count,
                errors=discovery_result.errors,
            )
        )
    steps.append("discover-candidates")

    canonical = materialize_candidate_papers(db_path)
    mark("dedupe-candidates")

    selected_count = select_top_canonical_candidates(db_path, select_limit, min_score)
    mark("select-canonical-candidates")

    approved_count = export_approved_candidates(db_path, approved_manifest_path)
    mark("export-approved-candidates")

    candidate_review = export_candidate_review(
        db_path,
        candidate_review_json_path or out_dir / "candidate-review.json",
        markdown_path=candidate_review_markdown_path or out_dir / "candidate-review.md",
        min_score=min_score,
        limit=select_limit,
    )
    mark("export-candidate-review")

    batch: BatchResult | None = None
    if approved_count:
        batch = run_batch_ingest(
            db_path=db_path,
            paper_db_path=paper_db_path,
            manifest_path=approved_manifest_path,
            papi_executable=papi_executable,
            normalize_urls=True,
            concurrency=min(4, max(1, concurrency)),
        )
        mark("batch-ingest")
    else:
        mark("skip-batch-ingest")

    sync = sync_paperpipe(db_path=db_path, paper_db_path=paper_db_path)
    mark("sync-paperpipe")

    mvp = run_mvp_pipeline(
        db_path=db_path,
        paper_db_path=paper_db_path,
        out_dir=out_dir,
        fact_provider=fact_provider,
        fixture_path=fixture_path,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
        concurrency=concurrency,
        refresh_facts=refresh_facts,
        fact_error_policy=fact_error_policy,
        semantic=semantic,
        semantic_threshold=semantic_threshold,
        progress_callback=progress_callback,
    )
    steps.append("run-mvp-pipeline")

    publish = publish_static_site(out_dir / "bundle", site_dir)
    mark("publish-static-site")

    generated_at = utc_now()
    history_stem = _run_history_stem(generated_at)
    run_history_path = history_dir / f"launch-refresh-{history_stem}.json" if history_dir is not None else None
    concise_log_path = log_dir / f"launch-refresh-{history_stem}.log" if log_dir is not None else None

    result = LaunchRefreshResult(
        db_path=db_path,
        paper_db_path=paper_db_path,
        profiles_seeded=profiles_seeded,
        profile_names=names,
        provider_names=provider_names,
        discovery=discovery_summaries,
        canonical=canonical,
        selected_count=selected_count,
        approved_count=len(list_approved_candidates(db_path)),
        approved_manifest_path=approved_manifest_path,
        candidate_review=candidate_review,
        batch=batch,
        sync=sync,
        mvp=mvp,
        publish=publish,
        run_manifest_path=run_manifest_path,
        run_history_path=run_history_path,
        concise_log_path=concise_log_path,
        steps=steps,
    )
    write_launch_refresh_manifest(result, generated_at=generated_at)
    if run_history_path is not None:
        write_launch_refresh_manifest(result, generated_at=generated_at, path=run_history_path)
    if concise_log_path is not None:
        write_launch_refresh_log(result, generated_at=generated_at, path=concise_log_path)
    return result

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from airesearch.batch import run_batch_ingest
from airesearch.candidates import export_candidates, list_candidates
from airesearch.canonical_candidates import (
    export_canonical_candidates,
    list_canonical_candidates,
    materialize_candidate_papers,
)
from airesearch.config import Settings
from airesearch.db import connect, init_db
from airesearch.discovery import run_discovery
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.profiles import seed_profiles
from airesearch.providers import ArxivProvider, GoogleScholarProvider, OpenAlexProvider, SemanticScholarProvider


def build_parser() -> argparse.ArgumentParser:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(prog="airesearch")
    parser.add_argument("--db", type=Path, default=settings.sqlite_path)
    parser.add_argument("--paper-db", type=Path, default=settings.paper_db_path)
    parser.add_argument("--papi", default=settings.papi_executable)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")
    subparsers.add_parser("sync-paperpipe")
    batch = subparsers.add_parser("batch-ingest")
    batch.add_argument("manifest", type=Path)
    subparsers.add_parser("status")
    subparsers.add_parser("seed-profiles")
    discover = subparsers.add_parser("discover-candidates")
    discover.add_argument("--profile", required=True)
    discover.add_argument("--limit", type=int, default=50)
    discover.add_argument(
        "--provider",
        action="append",
        choices=["openalex", "arxiv", "semantic_scholar", "google_scholar"],
        help="Discovery provider to use. Repeat for multiple providers. Defaults to all.",
    )
    discover.add_argument(
        "--refresh-provider-cache",
        action="store_true",
        help="Bypass provider response cache for cache-aware providers while still respecting quota limits.",
    )
    listing = subparsers.add_parser("list-candidates")
    listing.add_argument("--profile", required=True)
    listing.add_argument("--limit", type=int, default=20)
    export = subparsers.add_parser("export-candidates")
    export.add_argument("--profile", required=True)
    export.add_argument("--limit", type=int, default=100)
    export.add_argument("--out", type=Path, required=True)
    subparsers.add_parser("dedupe-candidates")
    canonical_listing = subparsers.add_parser("list-canonical-candidates")
    canonical_listing.add_argument("--limit", type=int, default=20)
    canonical_export = subparsers.add_parser("export-canonical-candidates")
    canonical_export.add_argument("--limit", type=int, default=100)
    canonical_export.add_argument("--out", type=Path, required=True)
    return parser


def count_table(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0
    try:
        with connect(db_path) as conn:
            row = conn.execute(f"select count(*) as count from {table}").fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row["count"])


def latest_value(db_path: Path, sql: str) -> str:
    if not db_path.exists():
        return "none"
    with connect(db_path) as conn:
        row = conn.execute(sql).fetchone()
    if row is None:
        return "none"
    return str(row[0])


def print_status(db_path: Path) -> None:
    print(f"db: {db_path}")
    print(f"papers: {count_table(db_path, 'papers')}")
    print(f"artifacts: {count_table(db_path, 'paper_artifacts')}")
    print(f"profiles: {count_table(db_path, 'research_profiles')}")
    print(f"candidates: {count_table(db_path, 'research_candidates')}")
    print(f"canonical_candidates: {count_table(db_path, 'candidate_papers')}")
    print(
        "latest_sync: "
        + latest_value(
            db_path,
            "select finished_at from sync_events order by id desc limit 1",
        )
    )
    print(
        "latest_ingest_run: "
        + latest_value(
            db_path,
            "select status || ' ' || coalesce(finished_at, started_at) from ingest_runs order by id desc limit 1",
        )
    )


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-db":
        init_db(args.db)
        print(f"initialized: {args.db}")
        return 0

    if args.command == "sync-paperpipe":
        result = sync_paperpipe(db_path=args.db, paper_db_path=args.paper_db)
        print(f"papers_seen={result.papers_seen} artifacts_seen={result.artifacts_seen}")
        return 0

    if args.command == "batch-ingest":
        result = run_batch_ingest(
            db_path=args.db,
            paper_db_path=args.paper_db,
            manifest_path=args.manifest,
            papi_executable=args.papi,
        )
        print(
            "total={total} success={success} failed={failed} "
            "duplicate={duplicate} skipped={skipped}".format(
                total=result.total,
                success=result.success,
                failed=result.failed,
                duplicate=result.duplicate,
                skipped=result.skipped,
            )
        )
        return 0 if result.failed == 0 else 2

    if args.command == "status":
        print_status(args.db)
        return 0

    if args.command == "seed-profiles":
        init_db(args.db)
        count = seed_profiles(args.db)
        print(f"profiles_seeded={count}")
        return 0

    if args.command == "discover-candidates":
        init_db(args.db)
        providers = build_discovery_providers(
            args.provider,
            db_path=args.db,
            refresh_provider_cache=args.refresh_provider_cache,
        )
        result = run_discovery(
            db_path=args.db,
            profile_name=args.profile,
            providers=providers,
            limit=args.limit,
        )
        print(
            "providers={providers} total_seen={total_seen} stored={stored} skipped={skipped} errors={errors}".format(
                providers=",".join(provider.name for provider in providers),
                total_seen=result.total_seen,
                stored=result.stored_count,
                skipped=result.skipped_count,
                errors=len(result.errors),
            )
        )
        for error in result.errors:
            print(f"provider_error: {error}")
        return 0 if result.stored_count > 0 or not result.errors else 2

    if args.command == "list-candidates":
        rows = list_candidates(args.db, args.profile, args.limit)
        for row in rows:
            print(
                f"{row['score']:.4f} | {row['published_date']} | "
                f"{row['source']} | {row['title']} | {row['url']}"
            )
        return 0

    if args.command == "export-candidates":
        count = export_candidates(args.db, args.profile, args.limit, args.out)
        print(f"candidates_exported={count} out={args.out}")
        return 0

    if args.command == "dedupe-candidates":
        result = materialize_candidate_papers(args.db)
        print(
            "candidates_seen={seen} canonical={canonical} links={links} skipped={skipped}".format(
                seen=result.candidates_seen,
                canonical=result.canonical_count,
                links=result.links_count,
                skipped=result.skipped_count,
            )
        )
        return 0

    if args.command == "list-canonical-candidates":
        rows = list_canonical_candidates(args.db, args.limit)
        for row in rows:
            print(
                f"{row['best_score']:.4f} | {row['published_date']} | "
                f"{row['sources_json']} | {row['profiles_json']} | {row['title']} | {row['url']}"
            )
        return 0

    if args.command == "export-canonical-candidates":
        count = export_canonical_candidates(args.db, args.limit, args.out)
        print(f"canonical_candidates_exported={count} out={args.out}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

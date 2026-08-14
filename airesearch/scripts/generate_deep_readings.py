#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from airesearch import blog_batch


def _paper_keys(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise blog_batch.BlogBatchError(f"unable to read paper list: {path}") from exc
    result: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("#", 1)[0].strip()
        if key and key not in seen:
            result.append(key)
            seen.add(key)
    if not result:
        raise blog_batch.BlogBatchError("paper list is empty")
    return result


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _print_result(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _add_common_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--paper-list", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight, compare, and generate evidence-grounded paper deep readings."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Validate evidence gates for selected papers.")
    _add_common_selection_arguments(preflight)

    backup = subparsers.add_parser("backup", help="Back up selected blog rows and asset manifests.")
    _add_common_selection_arguments(backup)

    ab = subparsers.add_parser("ab", help="Run both model arms on the first two selected papers.")
    _add_common_selection_arguments(ab)
    ab.add_argument("--target-chars", type=int, default=5000)

    batch = subparsers.add_parser("batch", help="Generate or resume selected papers with one arm.")
    _add_common_selection_arguments(batch)
    batch.add_argument("--model-arm", required=True, choices=("deepseek", "luna"))
    batch.add_argument("--target-chars", type=int, default=5000)
    batch.add_argument("--concurrency", type=_positive_int, default=1)

    restore = subparsers.add_parser("restore", help="Restore selected blog state from a backup.")
    restore.add_argument("--db", required=True, type=Path)
    restore.add_argument("--backup-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "restore":
            result = blog_batch.restore_blog_state(args.db, args.backup_dir)
            _print_result(result)
            return 0

        paper_keys = _paper_keys(args.paper_list)
        args.out.mkdir(parents=True, exist_ok=True)
        if args.command == "preflight":
            rows = blog_batch.preflight_papers(args.db, paper_keys)
            result = {
                "status": "completed" if all(row["ready"] for row in rows) else "partial",
                "paper_count": len(rows),
                "ready_count": sum(bool(row["ready"]) for row in rows),
                "papers": rows,
            }
            _write_json(args.out / "preflight.json", result)
            _print_result(result)
            return 0 if result["status"] == "completed" else 2
        if args.command == "backup":
            result = blog_batch.backup_blog_state(args.db, paper_keys, args.out)
            _print_result(result)
            return 0
        if args.command == "ab":
            if len(paper_keys) < 2:
                raise blog_batch.BlogBatchError("A/B requires at least two papers")
            blog_batch.validate_backup_manifest(args.db, args.out, paper_keys)
            result = blog_batch.run_ab(
                args.db,
                paper_keys[:2],
                args.out,
                target_chars=args.target_chars,
            )
            _print_result(result)
            return 0 if result["status"] == "completed" else 2
        if args.command == "batch":
            runtime_arm = blog_batch.model_arm_from_env(args.model_arm)
            blog_batch.validate_winner_file(
                args.db,
                args.out,
                paper_keys,
                args.model_arm,
                runtime_arm=runtime_arm,
            )
            result = blog_batch.run_batch(
                args.db,
                paper_keys,
                args.out,
                runtime_arm,
                target_chars=args.target_chars,
                concurrency=args.concurrency,
            )
            _print_result(result)
            return 0 if result["status"] == "completed" else 2
    except blog_batch.BlogBatchError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from airesearch.db import connect
from airesearch import paper_blog
from airesearch.provider_config import api_root, responses_url


SCORING_VERSION = "deep-reading-ab-v1"
REQUIRED_FACT_TYPES = {"benchmark", "claim", "dataset", "limitation", "method"}
MIN_VALID_FACT_COVERAGE = 0.5
BLOG_TABLES = (
    "paper_blog_posts",
    "paper_blog_versions",
    "paper_blog_generation_cache",
)


class BlogBatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlogModelArm:
    name: str
    model: str
    api_style: str
    base_url: str
    api_key_env: str
    proxy_url: str = ""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _first_env(env: Mapping[str, str], names: Sequence[str]) -> tuple[str, str]:
    for name in names:
        value = str(env.get(name, "") or "").strip()
        if value:
            return value, name
    return "", ""


def _require_env_value(
    env: Mapping[str, str],
    names: Sequence[str],
    *,
    missing_name: str,
) -> tuple[str, str]:
    value, source_name = _first_env(env, names)
    if not value:
        raise BlogBatchError(f"missing required environment variable: {missing_name}")
    return value, source_name


def model_arm_from_env(name: str, env: Mapping[str, str] | None = None) -> BlogModelArm:
    values = os.environ if env is None else env
    normalized = str(name or "").strip().lower()
    if normalized == "deepseek":
        model, _model_env = _first_env(
            values,
            ("AIRESEARCH_DEEPSEEK_BLOG_MODEL", "AIRESEARCH_BLOG_MODEL"),
        )
        model = model or paper_blog.DEFAULT_BLOG_MODEL
        base_url, _base_env = _require_env_value(
            values,
            (
                "OPENCODE_GO_BASE_URL",
                "AIRESEARCH_DEEPSEEK_BLOG_BASE_URL",
                "AIRESEARCH_BLOG_BASE_URL",
                "NIU_ASSISTANT_API_BASE",
            ),
            missing_name="NIU_ASSISTANT_API_BASE",
        )
        _key, key_env = _require_env_value(
            values,
            (
                "OPENCODE_GO_API_KEY",
                "AIRESEARCH_DEEPSEEK_BLOG_API_KEY",
                "AIRESEARCH_BLOG_API_KEY",
                "NIU_ASSISTANT_API_KEY",
            ),
            missing_name="NIU_ASSISTANT_API_KEY",
        )
        proxy_url, _proxy_env = _first_env(
            values,
            ("OPENCODE_GO_PROXY", "AIRESEARCH_DEEPSEEK_BLOG_PROXY", "AIRESEARCH_BLOG_PROXY"),
        )
        return BlogModelArm(
            name="deepseek",
            model=model,
            api_style="chat_completions",
            base_url=api_root(base_url),
            api_key_env=key_env,
            proxy_url=proxy_url,
        )
    if normalized == "luna":
        model, _model_env = _require_env_value(
            values,
            ("AIRESEARCH_LUNA_BLOG_MODEL", "AIRESEARCH_FORMULA_OCR_MODEL"),
            missing_name="AIRESEARCH_FORMULA_OCR_MODEL",
        )
        base_url, _base_env = _require_env_value(
            values,
            (
                "OPENCODE_GO_BASE_URL",
                "AIRESEARCH_LUNA_BLOG_BASE_URL",
                "AIRESEARCH_LUNA_BLOG_API_BASE",
                "AIRESEARCH_FORMULA_OCR_API_BASE",
            ),
            missing_name="AIRESEARCH_FORMULA_OCR_API_BASE",
        )
        _key, key_env = _require_env_value(
            values,
            (
                "OPENCODE_GO_API_KEY",
                "AIRESEARCH_LUNA_BLOG_API_KEY",
                "AIRESEARCH_FORMULA_OCR_API_KEY",
            ),
            missing_name="AIRESEARCH_FORMULA_OCR_API_KEY",
        )
        proxy_url, _proxy_env = _first_env(
            values,
            ("OPENCODE_GO_PROXY", "AIRESEARCH_LUNA_BLOG_PROXY", "AIRESEARCH_FORMULA_OCR_PROXY"),
        )
        return BlogModelArm(
            name="luna",
            model=model,
            api_style="responses",
            base_url=responses_url(base_url),
            api_key_env=key_env,
            proxy_url=proxy_url,
        )
    raise BlogBatchError(f"unknown blog model arm: {normalized or '<empty>'}")


def _configured_secret_values(
    env: Mapping[str, str],
    arms: Iterable[BlogModelArm] = (),
) -> list[str]:
    names = {arm.api_key_env for arm in arms}
    names.update(
        name
        for name in env
        if re.search(r"(?:API_?KEY|TOKEN|SECRET|PASSWORD)$", str(name), re.I)
    )
    return sorted(
        {
            str(env.get(name, "") or "")
            for name in names
            if len(str(env.get(name, "") or "")) >= 4
        },
        key=len,
        reverse=True,
    )


def _sanitize_text(value: Any, secrets: Iterable[str]) -> str:
    text = str(value or "")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(
        r"https?://[^\s/]+(?:/[^\s?#]*)?(?:\?[^\s#]*)?(?:#[^\s]*)?",
        lambda match: _safe_endpoint_origin(match.group(0)),
        text,
        flags=re.I,
    )
    return text


def _safe_endpoint_origin(value: str) -> str:
    try:
        parsed = urlsplit(str(value or ""))
        port = f":{parsed.port}" if parsed.port is not None else ""
    except ValueError:
        return "configured-endpoint"
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "configured-endpoint"
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def _require_existing_db(db_path: Path) -> Path:
    candidate = Path(db_path)
    if not candidate.exists() or not candidate.is_file():
        raise BlogBatchError(f"database file does not exist: {candidate}")
    return candidate.resolve()


def provider_for_arm(
    arm: BlogModelArm,
    env: Mapping[str, str] | None = None,
) -> paper_blog.OpenAICompatibleBlogProvider:
    values = os.environ if env is None else env
    api_key = str(values.get(arm.api_key_env, "") or "").strip()
    if not api_key:
        raise BlogBatchError(f"missing required environment variable: {arm.api_key_env}")
    secrets = [api_key]
    try:
        if arm.api_style == "responses":
            transport_class = getattr(paper_blog, "OpenAIResponsesBlogTransport", None)
            if transport_class is None:
                raise BlogBatchError("paper_blog.OpenAIResponsesBlogTransport is unavailable")
            transport = transport_class(proxy_url=arm.proxy_url)
        elif arm.api_style == "chat_completions":
            transport = paper_blog.OpenAICompatibleBlogTransport()
        else:
            raise BlogBatchError(f"unsupported blog API style: {arm.api_style}")
        return paper_blog.OpenAICompatibleBlogProvider(
            model=arm.model,
            api_key=api_key,
            base_url=arm.base_url,
            transport=transport,
        )
    except Exception as exc:
        detail = _sanitize_text(exc, secrets)
        if isinstance(exc, BlogBatchError):
            raise BlogBatchError(detail) from exc
        raise BlogBatchError(f"failed to construct provider for {arm.name}: {detail}") from exc


def _unique_paper_keys(paper_keys: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw_key in paper_keys:
        key = str(raw_key or "").strip()
        if key and key not in seen:
            result.append(key)
            seen.add(key)
    return result


def _paper_row(db_path: Path, paper_key: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "select paper_key, paper_dir from papers where paper_key = ?",
            (paper_key,),
        ).fetchone()
    return dict(row) if row is not None else None


def _registered_source_paths(db_path: Path, paper_key: str, paper_dir: Path) -> set[Path]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select path as registered_path from paper_artifacts where paper_key = ?
            union all
            select asset_path as registered_path from paper_layout_blocks where paper_key = ?
            """,
            (paper_key, paper_key),
        ).fetchall()
    registered: set[Path] = set()
    for row in rows:
        value = str(row["registered_path"] or "").strip()
        if not value:
            continue
        path = Path(value)
        registered.add((path if path.is_absolute() else paper_dir / path).resolve())
    return registered


def _selected_image_is_local(
    db_path: Path,
    paper_key: str,
    image: Mapping[str, Any],
    paper_dir: Path,
) -> bool:
    if _image_path_error(str(image.get("asset_path") or ""), paper_dir):
        return False
    source_value = str(image.get("source_path") or "").strip()
    if not source_value:
        return True
    source_path = Path(source_value)
    source_resolved = (
        source_path if source_path.is_absolute() else paper_dir / source_path
    ).resolve()
    if not source_resolved.is_file():
        return False
    try:
        source_resolved.relative_to(paper_dir.resolve())
        return True
    except ValueError:
        return source_resolved in _registered_source_paths(db_path, paper_key, paper_dir)


def preflight_papers(db_path: Path, paper_keys: Iterable[str]) -> list[dict[str, Any]]:
    db_path = Path(db_path)
    rows: list[dict[str, Any]] = []
    for paper_key in _unique_paper_keys(paper_keys):
        result: dict[str, Any] = {
            "paper_key": paper_key,
            "source_hash": "",
            "fact_types": [],
            "fact_count": 0,
            "equation_count": 0,
            "image_count": 0,
            "structured_table_chars": 0,
            "ready": False,
            "errors": [],
        }
        paper = _paper_row(db_path, paper_key)
        if paper is None:
            result["errors"].append("paper_missing")
            rows.append(result)
            continue
        try:
            pack = paper_blog.build_blog_evidence_pack(db_path, paper_key)
        except Exception as exc:
            result["errors"].append(f"evidence_pack_failed:{type(exc).__name__}")
            rows.append(result)
            continue

        fact_types = sorted(
            {
                str(fact.get("fact_type") or "").strip()
                for fact in pack.facts
                if str(fact.get("fact_type") or "").strip()
            }
        )
        result.update(
            {
                "source_hash": pack.source_hash,
                "fact_types": fact_types,
                "fact_count": len(pack.facts),
                "equation_count": len(pack.equations),
                "structured_table_chars": len(
                    str(pack.artifact_texts.get("layout_structured_tables") or "")
                ),
            }
        )
        if not any(str(pack.artifact_texts.get(kind) or "").strip() for kind in ("summary", "tldr")):
            result["errors"].append("summary_or_tldr_missing")
        missing_fact_types = sorted(REQUIRED_FACT_TYPES - set(fact_types))
        if missing_fact_types:
            result["errors"].append("fact_types_missing:" + ",".join(missing_fact_types))

        with connect(db_path) as conn:
            completed_layout = conn.execute(
                """
                select 1 from paper_layout_runs
                where paper_key = ? and status = 'completed'
                order by id desc limit 1
                """,
                (paper_key,),
            ).fetchone()
        if completed_layout is None:
            result["errors"].append("completed_layout_missing")

        try:
            selected_images = paper_blog.select_blog_images(db_path, paper_key, max_images=paper_blog.MAX_IMAGES)
        except Exception:
            selected_images = []
        paper_dir = Path(str(paper.get("paper_dir") or ""))
        local_images = [
            image
            for image in selected_images
            if _selected_image_is_local(db_path, paper_key, image, paper_dir)
        ]
        result["image_count"] = len(local_images)
        if not local_images:
            result["errors"].append("selected_local_image_missing")

        result["ready"] = not result["errors"]
        rows.append(result)
    return rows


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_bytes(path, _json_bytes(value))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_id_for_manifest(manifest: Mapping[str, Any]) -> str:
    identity = {key: value for key, value in manifest.items() if key != "backup_id"}
    return _sha256_bytes(_json_bytes(identity))


def _selected_rows(conn: Any, table: str, paper_keys: Sequence[str]) -> list[dict[str, Any]]:
    if not paper_keys:
        return []
    placeholders = ",".join("?" for _key in paper_keys)
    order_by = "paper_key" if table == "paper_blog_posts" else "paper_key, id"
    rows = conn.execute(
        f"select * from {table} where paper_key in ({placeholders}) order by {order_by}",
        tuple(paper_keys),
    ).fetchall()
    return [dict(row) for row in rows]


def _asset_manifest(conn: Any, paper_keys: Sequence[str]) -> list[dict[str, Any]]:
    if not paper_keys:
        return []
    placeholders = ",".join("?" for _key in paper_keys)
    paper_rows = conn.execute(
        f"select paper_key, paper_dir from papers where paper_key in ({placeholders}) order by paper_key",
        tuple(paper_keys),
    ).fetchall()
    manifest: list[dict[str, Any]] = []
    for row in paper_rows:
        paper_dir = Path(str(row["paper_dir"] or "")).resolve()
        asset_root = paper_dir / "blog-assets"
        files: list[dict[str, Any]] = []
        if asset_root.is_dir():
            for path in sorted(asset_root.rglob("*")):
                if path.is_symlink() or not path.is_file():
                    continue
                resolved = path.resolve()
                try:
                    relative = resolved.relative_to(asset_root.resolve())
                except ValueError:
                    continue
                files.append(
                    {
                        "path": relative.as_posix(),
                        "sha256": _sha256_file(resolved),
                        "size_bytes": resolved.stat().st_size,
                    }
                )
        manifest.append(
            {
                "paper_key": str(row["paper_key"]),
                "paper_dir": str(paper_dir),
                "asset_root": str(asset_root),
                "files": files,
            }
        )
    return manifest


def backup_blog_state(
    db_path: Path,
    paper_keys: Iterable[str],
    out_dir: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    db_path = _require_existing_db(Path(db_path))
    out_dir = Path(out_dir)
    keys = _unique_paper_keys(paper_keys)
    paper_blog.ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        conn.execute("begin")
        try:
            table_rows = {table: _selected_rows(conn, table, keys) for table in BLOG_TABLES}
            assets = _asset_manifest(conn, keys)
            if keys:
                placeholders = ",".join("?" for _key in keys)
                current_rows = conn.execute(
                    f"select paper_key, current_version_id from paper_blog_posts "
                    f"where paper_key in ({placeholders}) order by paper_key",
                    tuple(keys),
                ).fetchall()
            else:
                current_rows = []
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    current_lookup = {
        str(row["paper_key"]): row["current_version_id"]
        for row in current_rows
        if str(row["paper_key"]) in set(keys)
    }
    current_by_key = {key: current_lookup.get(key) for key in keys}
    payloads: dict[str, bytes] = {
        f"{table}.json": _json_bytes(table_rows[table]) for table in BLOG_TABLES
    }
    payloads["assets.json"] = _json_bytes(assets)

    values = os.environ if env is None else env
    secrets = _configured_secret_values(values)
    for filename, content in payloads.items():
        serialized = content.decode("utf-8")
        if any(secret in serialized for secret in secrets):
            raise BlogBatchError(f"refusing to write secret-bearing backup payload: {filename}")

    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in payloads.items():
        _atomic_write_bytes(out_dir / filename, content)
    manifest = {
        "format_version": 1,
        "database_path": str(db_path),
        "created_at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "paper_keys": keys,
        "current_version_ids": current_by_key,
        "row_counts": {table: len(table_rows[table]) for table in BLOG_TABLES},
        "files": {
            filename: {"sha256": _sha256_bytes(content), "size_bytes": len(content)}
            for filename, content in sorted(payloads.items())
        },
    }
    manifest["backup_id"] = _backup_id_for_manifest(manifest)
    manifest_content = _json_bytes(manifest)
    if any(secret in manifest_content.decode("utf-8") for secret in secrets):
        raise BlogBatchError("refusing to write secret-bearing backup manifest")
    _atomic_write_bytes(out_dir / "manifest.json", manifest_content)
    return manifest


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BlogBatchError(f"invalid backup file: {path.name}") from exc


def _verify_backup_files(backup_dir: Path, manifest: Mapping[str, Any]) -> None:
    file_entries = manifest.get("files")
    if not isinstance(file_entries, dict):
        raise BlogBatchError("backup manifest is missing file hashes")
    for filename, metadata in file_entries.items():
        path = backup_dir / str(filename)
        if not path.is_file() or not isinstance(metadata, dict):
            raise BlogBatchError(f"backup file missing: {filename}")
        if _sha256_file(path) != str(metadata.get("sha256") or ""):
            raise BlogBatchError(f"backup file hash mismatch: {filename}")


def validate_backup_manifest(
    db_path: Path,
    backup_dir: Path,
    paper_keys: Iterable[str] | None = None,
) -> dict[str, Any]:
    resolved_db = _require_existing_db(Path(db_path))
    backup_dir = Path(backup_dir)
    manifest = _load_json(backup_dir / "manifest.json")
    if not isinstance(manifest, dict):
        raise BlogBatchError("backup manifest must be a JSON object")
    bound_path = Path(str(manifest.get("database_path") or ""))
    if not bound_path.is_absolute() or bound_path.resolve() != resolved_db:
        raise BlogBatchError("backup manifest database path does not match requested database")
    manifest_keys = _unique_paper_keys(manifest.get("paper_keys", []))
    if paper_keys is not None and manifest_keys != _unique_paper_keys(paper_keys):
        raise BlogBatchError("backup manifest paper selection does not match requested papers")
    _verify_backup_files(backup_dir, manifest)
    backup_id = str(manifest.get("backup_id") or "")
    if len(backup_id) != 64 or backup_id != _backup_id_for_manifest(manifest):
        raise BlogBatchError("backup manifest backup_id is missing or invalid")
    return manifest


def validate_winner_file(
    db_path: Path,
    out_dir: Path,
    paper_keys: Iterable[str],
    requested_arm: str,
    *,
    prompt_version: str = paper_blog.BLOG_PROMPT_VERSION,
    runtime_arm: BlogModelArm | None = None,
) -> dict[str, Any]:
    resolved_db = _require_existing_db(Path(db_path))
    out_dir = Path(out_dir)
    selected_keys = _unique_paper_keys(paper_keys)
    manifest = validate_backup_manifest(resolved_db, out_dir, selected_keys)
    winner = _load_json(out_dir / "winner.json")
    report = _load_json(out_dir / "ab-report.json")
    if not isinstance(winner, dict) or not isinstance(report, dict):
        raise BlogBatchError("winner and A/B report must be JSON objects")
    arm_name = str(winner.get("model_arm") or "")
    if arm_name not in {"deepseek", "luna"} or arm_name != str(requested_arm or ""):
        raise BlogBatchError("requested model arm does not match the A/B winner")
    if (
        str(winner.get("database_path") or "") != str(resolved_db)
        or str(report.get("database_path") or "") != str(resolved_db)
    ):
        raise BlogBatchError("winner data does not match requested database")
    if (
        winner.get("backup_id") != manifest.get("backup_id")
        or report.get("backup_id") != manifest.get("backup_id")
        or winner.get("paper_keys") != selected_keys
        or report.get("paper_keys") != selected_keys
        or winner.get("prompt_version") != prompt_version
        or report.get("prompt_version") != prompt_version
        or winner.get("scoring_version") != SCORING_VERSION
        or report.get("scoring_version") != SCORING_VERSION
        or report.get("status") != "completed"
        or report.get("winner") != arm_name
    ):
        raise BlogBatchError("winner data is incomplete or stale")
    sample_keys = _unique_paper_keys(winner.get("sample_papers", []))
    if (
        not sample_keys
        or not set(sample_keys).issubset(set(selected_keys))
        or report.get("sample_papers") != sample_keys
    ):
        raise BlogBatchError("winner sample papers do not match requested batch")
    source_hashes = winner.get("sample_source_hashes")
    if (
        not isinstance(source_hashes, dict)
        or report.get("sample_source_hashes") != source_hashes
        or set(source_hashes) != set(sample_keys)
    ):
        raise BlogBatchError("winner sample source hashes are incomplete")
    for paper_key in sample_keys:
        try:
            current_hash = _current_source_hash(resolved_db, paper_key)
        except Exception as exc:
            raise BlogBatchError(f"unable to rebuild winner evidence for {paper_key}") from exc
        if current_hash != str(source_hashes.get(paper_key) or ""):
            raise BlogBatchError("winner sample evidence has changed since A/B")
    public_arms = {
        str(item.get("name") or ""): item
        for item in report.get("arms", [])
        if isinstance(item, dict)
    }
    winning_public_arm = public_arms.get(arm_name)
    if (
        not isinstance(winning_public_arm, dict)
        or not str(winner.get("model") or "")
        or winner.get("model") != winning_public_arm.get("model")
        or winner.get("api_style") != winning_public_arm.get("api_style")
    ):
        raise BlogBatchError("winner runtime configuration does not match the A/B report")
    if runtime_arm is not None and (
        runtime_arm.name != arm_name
        or runtime_arm.model != winner.get("model")
        or runtime_arm.api_style != winner.get("api_style")
    ):
        raise BlogBatchError("runtime model configuration does not match the A/B winner")
    return winner


def _insert_rows(conn: Any, table: str, rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        columns = list(row)
        if not columns:
            continue
        column_sql = ", ".join(columns)
        placeholders = ", ".join("?" for _column in columns)
        conn.execute(
            f"insert into {table} ({column_sql}) values ({placeholders})",
            tuple(row[column] for column in columns),
        )


def _backup_identity(out_dir: Path) -> str:
    path = out_dir / "manifest.json"
    if not path.is_file():
        return ""
    value = _load_json(path)
    return str(value.get("backup_id") or "") if isinstance(value, dict) else ""


def _snapshot_assets(db_path: Path, paper_keys: Sequence[str]) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        conn.execute("begin")
        try:
            snapshot = _asset_manifest(conn, paper_keys)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    return snapshot


def _load_or_create_asset_tracking(
    db_path: Path,
    paper_keys: Sequence[str],
    out_dir: Path,
) -> dict[str, Any]:
    path = out_dir / "created-assets.json"
    backup_id = _backup_identity(out_dir)
    tracking: dict[str, Any] = {}
    if path.is_file():
        value = _load_json(path)
        if isinstance(value, dict):
            tracking = value
    same_run = bool(
        tracking
        and str(tracking.get("database_path") or "") == str(db_path.resolve())
        and str(tracking.get("backup_id") or "") == backup_id
    )
    if not same_run:
        tracking = {
            "format_version": 1,
            "database_path": str(db_path.resolve()),
            "backup_id": backup_id,
            "paper_keys": [],
            "baseline": [],
            "created": [],
            "ownership": "unverified_snapshot_diff",
            "updated_at": _utc_now(),
        }
    tracked_keys = _unique_paper_keys(tracking.get("paper_keys", []))
    new_keys = [key for key in paper_keys if key not in set(tracked_keys)]
    if new_keys:
        tracking["baseline"] = [
            *[item for item in tracking.get("baseline", []) if isinstance(item, dict)],
            *_snapshot_assets(db_path, new_keys),
        ]
        tracked_keys.extend(new_keys)
    tracking["paper_keys"] = tracked_keys
    tracking["updated_at"] = _utc_now()
    _atomic_write_json(path, tracking)
    return tracking


def _refresh_created_assets(
    db_path: Path,
    tracking: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    keys = _unique_paper_keys(tracking.get("paper_keys", []))
    current = _snapshot_assets(db_path, keys)
    baseline_paths = {
        (str(record.get("paper_key") or ""), str(item.get("path") or ""))
        for record in tracking.get("baseline", [])
        if isinstance(record, dict)
        for item in record.get("files", [])
        if isinstance(item, dict)
    }
    tracking["created"] = [
        {
            "paper_key": str(record.get("paper_key") or ""),
            "path": str(item.get("path") or ""),
            "sha256": str(item.get("sha256") or ""),
            "size_bytes": int(item.get("size_bytes") or 0),
        }
        for record in current
        if isinstance(record, dict)
        for item in record.get("files", [])
        if isinstance(item, dict)
        and (str(record.get("paper_key") or ""), str(item.get("path") or ""))
        not in baseline_paths
    ]
    tracking["updated_at"] = _utc_now()
    _atomic_write_json(out_dir / "created-assets.json", tracking)
    return tracking


def restore_blog_state(db_path: Path, backup_dir: Path) -> dict[str, Any]:
    db_path = _require_existing_db(Path(db_path))
    backup_dir = Path(backup_dir)
    manifest = validate_backup_manifest(db_path, backup_dir)
    keys = _unique_paper_keys(manifest.get("paper_keys", []))
    rows_by_table = {
        table: _load_json(backup_dir / f"{table}.json") for table in BLOG_TABLES
    }
    assets = _load_json(backup_dir / "assets.json")
    if not all(isinstance(rows, list) for rows in rows_by_table.values()) or not isinstance(assets, list):
        raise BlogBatchError("backup payload has an invalid shape")
    created_records: list[Mapping[str, Any]] = []
    created_path = backup_dir / "created-assets.json"
    if created_path.is_file():
        tracking = _load_json(created_path)
        if (
            isinstance(tracking, dict)
            and str(tracking.get("database_path") or "") == str(db_path)
            and str(tracking.get("backup_id") or "") == str(manifest.get("backup_id") or "")
        ):
            tracked_keys = set(_unique_paper_keys(tracking.get("paper_keys", [])))
            if tracked_keys.issubset(set(keys)):
                created_records = [
                    item for item in tracking.get("created", []) if isinstance(item, dict)
                ]
    paper_blog.ensure_blog_schema(db_path)
    with connect(db_path) as conn:
        try:
            conn.execute("begin")
            if keys:
                placeholders = ",".join("?" for _key in keys)
                for table in ("paper_blog_posts", "paper_blog_generation_cache", "paper_blog_versions"):
                    conn.execute(
                        f"delete from {table} where paper_key in ({placeholders})",
                        tuple(keys),
                    )
            _insert_rows(conn, "paper_blog_versions", rows_by_table["paper_blog_versions"])
            _insert_rows(conn, "paper_blog_posts", rows_by_table["paper_blog_posts"])
            _insert_rows(
                conn,
                "paper_blog_generation_cache",
                rows_by_table["paper_blog_generation_cache"],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    baseline_paths = {
        (str(record.get("paper_key") or ""), str(item.get("path") or ""))
        for record in assets
        if isinstance(record, dict)
        for item in record.get("files", [])
        if isinstance(item, dict)
    }
    current_assets = _snapshot_assets(db_path, keys)
    retained_unowned_assets = [
        {
            "paper_key": str(record.get("paper_key") or ""),
            "path": str(item.get("path") or ""),
            "sha256": str(item.get("sha256") or ""),
        }
        for record in current_assets
        if isinstance(record, dict)
        for item in record.get("files", [])
        if isinstance(item, dict)
        and (str(record.get("paper_key") or ""), str(item.get("path") or ""))
        not in baseline_paths
    ]
    return {
        "status": "restored",
        "paper_keys": keys,
        "row_counts": {table: len(rows_by_table[table]) for table in BLOG_TABLES},
        "asset_restore_policy": "retain_all_without_explicit_generator_ownership",
        "deleted_asset_count": 0,
        "retained_unowned_assets": retained_unowned_assets,
        "informational_created_asset_count": len(created_records),
    }


def _parse_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _mask_markdown_math(markdown: str) -> str:
    prose = re.sub(r"\$\$.*?\$\$", " ", markdown, flags=re.S)
    prose = re.sub(r"\\\[.*?\\\]", " ", prose, flags=re.S)
    prose = re.sub(r"\\\(.*?\\\)", " ", prose, flags=re.S)
    prose = re.sub(r"(?<!\\)\$(?!\$).*?(?<!\\)\$", " ", prose, flags=re.S)
    return prose


def _absolute_path_present(markdown: str) -> bool:
    prose = _mask_markdown_math(markdown)
    return bool(
        re.search(
            r"(?:file://|(?<![\w.])/(?:home|tmp|var|opt|root|srv|mnt)/|[A-Za-z]:\\)",
            prose,
            re.I,
        )
    )


def _placeholder_present(markdown: str) -> bool:
    prose = _mask_markdown_math(markdown)
    explicit_template = re.search(
        r"(?:\bTODO\b|\bTBD\b|\bTBC\b|\bPLACEHOLDER\b|\{\{[^{}]+\}\}|此处插入)",
        prose,
        re.I,
    )
    standalone_chinese_placeholder = re.search(
        r"(?m)^\s*(?:[-*+]\s*)?(?:待补充|待完善)(?:\s*[:：].*)?\s*$",
        prose,
    )
    return bool(explicit_template or standalone_chinese_placeholder)


def _visible_markdown_source(markdown: str) -> str:
    return paper_blog._mask_markdown_code(markdown)


def _visible_h2_heading_count(markdown: str) -> int:
    visible_markdown = _visible_markdown_source(markdown)
    return len(re.findall(r"(?m)^##(?!#)[ \t]+\S", visible_markdown))


def _unescaped_model_control_token_present(markdown: str) -> bool:
    visible_markdown = _visible_markdown_source(markdown)
    return any(
        not paper_blog._is_markdown_escaped(visible_markdown, match.start())
        for match in paper_blog.MODEL_CONTROL_TOKEN_RE.finditer(visible_markdown)
    )


def _normalized_asset_path(value: Any) -> str:
    return paper_blog._normalize_declared_asset_path(value)


def _markdown_image_paths(markdown: str) -> set[str]:
    return {path for path in paper_blog._embedded_image_paths(markdown) if path}


def _image_path_error(asset_path: str, paper_dir: Path) -> str:
    value = str(asset_path or "").strip()
    if not value:
        return "empty"
    if value.startswith(("http://", "https://", "//", "file://")):
        return "external"
    relative = Path(value)
    if relative.is_absolute():
        return "absolute"
    try:
        resolved = (paper_dir / relative).resolve()
        resolved.relative_to(paper_dir.resolve())
    except (OSError, ValueError):
        return "outside_paper_dir"
    return "" if resolved.is_file() else "missing"


def _outline_references(outline: Mapping[str, Any]) -> tuple[set[int], set[str]]:
    fact_ids: set[int] = set()
    image_ids: set[str] = set()
    for section in outline.get("sections", []):
        if not isinstance(section, dict):
            continue
        for fact_id in section.get("fact_ids", []):
            try:
                fact_ids.add(int(fact_id))
            except (TypeError, ValueError):
                continue
        image_ids.update(str(value) for value in section.get("image_ids", []) if str(value))
    return fact_ids, image_ids


def _numeric_tokens(value: str) -> set[str]:
    return {
        token.rstrip("%")
        for token in re.findall(r"(?<![\w])[-+]?\d+(?:\.\d+)?%?", value or "")
        if token.rstrip("%")
    }


def _prose_without_math(markdown: str) -> str:
    text = re.sub(r"\$\$.*?\$\$", " ", markdown, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!?\[[^\]]*\]\([^)]*\)", " ", text)
    return text


def _paragraph_repeat_ratio(markdown: str) -> float:
    paragraphs = [
        re.sub(r"\s+", "", paragraph).lower()
        for paragraph in re.split(r"\n\s*\n", markdown)
        if len(re.sub(r"\s+", "", paragraph)) >= 40 and not paragraph.lstrip().startswith("#")
    ]
    if not paragraphs:
        return 0.0
    return max(0.0, (len(paragraphs) - len(set(paragraphs))) / len(paragraphs))


def _version_row(db_path: Path, paper_key: str, version_id: int) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "select * from paper_blog_versions where id = ? and paper_key = ?",
            (int(version_id), paper_key),
        ).fetchone()
    return dict(row) if row is not None else None


def _score_version(
    *,
    markdown: str,
    outline: Mapping[str, Any],
    image_refs: Sequence[Mapping[str, Any]],
    generation_meta: Mapping[str, Any],
    pack: Any,
    duration_seconds: float,
    hard_gate_errors: Sequence[str],
) -> dict[str, Any]:
    valid_fact_ids = {int(fact["fact_id"]) for fact in pack.facts}
    referenced_fact_ids, referenced_image_ids = _outline_references(outline)
    cited_valid = referenced_fact_ids & valid_fact_ids
    fact_coverage = len(cited_valid) / max(1, len(valid_fact_ids))

    evidence_text = " ".join(
        [
            *(
                " ".join(
                    str(fact.get(key) or "")
                    for key in ("statement", "evidence_quote", "metadata")
                )
                for fact in pack.facts
            ),
            *(str(value) for value in pack.artifact_texts.values()),
        ]
    )
    evidence_numbers = _numeric_tokens(evidence_text)
    prose_numbers = _numeric_tokens(_prose_without_math(markdown))
    grounded_numbers = prose_numbers & evidence_numbers
    numeric_grounding = len(grounded_numbers) / len(prose_numbers) if prose_numbers else 1.0
    grounding = 20.0 * fact_coverage + 15.0 * numeric_grounding

    display_math = paper_blog.display_math_block_count(markdown)
    formula_ratio = min(1.0, display_math / 2.0) if pack.equations else 1.0
    table_chars = len(str(pack.artifact_texts.get("layout_structured_tables") or ""))
    table_used = bool(
        re.search(r"(?im)^\s*\|.+\|\s*$", markdown)
        or re.search(r"(?:表格|实验表|Table\s*\d+)", markdown, re.I)
    )
    table_ratio = 1.0 if not table_chars else float(table_used)
    known_image_ids = {str(image.get("image_id") or "") for image in image_refs}
    markdown_image_paths = _markdown_image_paths(markdown)
    referenced_paths = {
        _normalized_asset_path(image.get("asset_path"))
        for image in image_refs
        if str(image.get("image_id") or "") in referenced_image_ids
        or _normalized_asset_path(image.get("asset_path")) in markdown_image_paths
    }
    image_ratio = len(referenced_paths) / max(1, len(image_refs)) if image_refs else 1.0
    fact_type_by_id = {int(fact["fact_id"]): str(fact.get("fact_type") or "") for fact in pack.facts}
    covered_types = {fact_type_by_id[fact_id] for fact_id in cited_valid}
    method_benchmark_ratio = len({"method", "benchmark"} & covered_types) / 2.0
    technical_evidence = (
        8.0 * formula_ratio
        + 6.0 * table_ratio
        + 4.0 * image_ratio
        + 7.0 * method_benchmark_ratio
    )

    required_sections = {key for key, _title in paper_blog.DEFAULT_SECTIONS}
    actual_sections = {
        str(section.get("section_key") or "")
        for section in outline.get("sections", [])
        if isinstance(section, dict)
    }
    section_ratio = len(required_sections & actual_sections) / max(1, len(required_sections))
    section_coverage = 15.0 * section_ratio

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", markdown))
    latin_chars = len(re.findall(r"[A-Za-z]", markdown))
    chinese_ratio = chinese_chars / max(1, chinese_chars + latin_chars)
    repeat_ratio = _paragraph_repeat_ratio(markdown)
    raw_html_count = len(re.findall(r"</?[A-Za-z][^>]*>", markdown))
    replacement_count = markdown.count("\ufffd")
    chinese_quality = 15.0 * min(1.0, chinese_ratio / 0.45)
    chinese_quality -= min(6.0, repeat_ratio * 15.0)
    chinese_quality -= min(3.0, raw_html_count * 0.5)
    chinese_quality -= min(6.0, replacement_count * 2.0)
    chinese_quality = max(0.0, chinese_quality)

    expected_calls = len(required_sections) + 1
    try:
        llm_calls = int(generation_meta.get("llm_calls", expected_calls) or 0)
    except (TypeError, ValueError):
        llm_calls = expected_calls
    generation_retry_count = max(0, llm_calls - expected_calls)
    call_score = max(0.0, 5.0 - min(5.0, float(generation_retry_count)))
    duration = max(0.0, float(duration_seconds or 0.0))
    latency_score = 5.0 if duration <= 120 else max(0.0, 5.0 * (600.0 - duration) / 480.0)
    reliability = call_score + latency_score

    components = {
        "grounding": round(grounding, 2),
        "technical_evidence": round(technical_evidence, 2),
        "section_coverage": round(section_coverage, 2),
        "chinese_quality": round(chinese_quality, 2),
        "reliability": round(reliability, 2),
    }
    eligible = not hard_gate_errors
    score = round(sum(components.values()), 2) if eligible else 0.0
    return {
        "eligible": eligible,
        "hard_gate_errors": list(hard_gate_errors),
        "score": score,
        "components": components,
        "metrics": {
            "fact_count": len(valid_fact_ids),
            "cited_fact_count": len(cited_valid),
            "fact_coverage_ratio": round(fact_coverage, 4),
            "prose_numeric_count": len(prose_numbers),
            "grounded_numeric_count": len(grounded_numbers),
            "numeric_grounding_ratio": round(numeric_grounding, 4),
            "equation_evidence_count": len(pack.equations),
            "display_math_count": display_math,
            "structured_table_chars": table_chars,
            "table_evidence_used": table_used,
            "image_ref_count": len(known_image_ids),
            "used_image_count": len(referenced_paths),
            "required_section_count": len(required_sections),
            "section_count": len(actual_sections & required_sections),
            "visible_section_heading_count": _visible_h2_heading_count(markdown),
            "embedded_image_count": len(markdown_image_paths),
            "chinese_ratio": round(chinese_ratio, 4),
            "repeated_paragraph_ratio": round(repeat_ratio, 4),
            "raw_html_count": raw_html_count,
            "replacement_character_count": replacement_count,
            "duration_seconds": round(duration, 3),
            "llm_calls": llm_calls,
            "generation_retry_count": generation_retry_count,
            "generation_retry_basis": "max(0,llm_calls-(required_sections+1))",
        },
        "scoring_version": SCORING_VERSION,
        "formulas": {
            "grounding": "20*valid_fact_coverage + 15*grounded_prose_numeric_ratio",
            "technical_evidence": "8*formula_use + 6*table_use + 4*image_use + 7*method_benchmark_coverage",
            "section_coverage": "15*required_section_coverage",
            "chinese_quality": "15*min(1,chinese_ratio/0.45) - repetition - raw_html - replacement_penalties",
            "reliability": "5*generation_call_efficiency + 5*latency_efficiency_without_content_omission_credit",
        },
    }


def audit_blog_version(
    db_path: Path,
    paper_key: str,
    version_id: int,
    duration_seconds: float,
) -> dict[str, Any]:
    row = _version_row(Path(db_path), paper_key, int(version_id))
    if row is None:
        return {
            "eligible": False,
            "hard_gate_errors": ["version_missing"],
            "score": 0.0,
            "components": {
                "grounding": 0.0,
                "technical_evidence": 0.0,
                "section_coverage": 0.0,
                "chinese_quality": 0.0,
                "reliability": 0.0,
            },
            "metrics": {},
            "scoring_version": SCORING_VERSION,
            "formulas": {},
        }
    pack = paper_blog.build_blog_evidence_pack(Path(db_path), paper_key)
    markdown = str(row.get("markdown") or "")
    outline = _parse_object(row.get("outline_json"))
    image_refs = [item for item in _parse_array(row.get("image_refs_json")) if isinstance(item, dict)]
    generation_meta = _parse_object(row.get("generation_meta_json"))
    errors: list[str] = []

    required_sections = {key for key, _title in paper_blog.DEFAULT_SECTIONS}
    section_values = outline.get("sections", [])
    section_keys = {
        str(section.get("section_key") or "")
        for section in section_values
        if isinstance(section, dict)
    }
    missing_sections = sorted(required_sections - section_keys)
    if missing_sections:
        errors.append("missing_sections:" + ",".join(missing_sections))
    if _visible_h2_heading_count(markdown) < len(required_sections):
        errors.append("visible_section_headings_missing")
    if paper_blog.chinese_char_count(markdown) < paper_blog.MIN_BLOG_CHARS:
        errors.append("text_too_short")
    if "\ufffd" in markdown:
        errors.append("replacement_character")
    if _placeholder_present(markdown):
        errors.append("unresolved_placeholder")
    if _absolute_path_present(markdown):
        errors.append("raw_absolute_path")
    if _unescaped_model_control_token_present(markdown):
        errors.append("unescaped_model_control_token")

    valid_fact_ids = {int(fact["fact_id"]) for fact in pack.facts}
    referenced_fact_ids, referenced_image_ids = _outline_references(outline)
    invalid_fact_ids = sorted(referenced_fact_ids - valid_fact_ids)
    if invalid_fact_ids:
        errors.append("invalid_fact_references:" + ",".join(str(value) for value in invalid_fact_ids))
    valid_fact_coverage = len(referenced_fact_ids & valid_fact_ids) / max(1, len(valid_fact_ids))
    if valid_fact_ids and valid_fact_coverage < MIN_VALID_FACT_COVERAGE:
        errors.append("insufficient_fact_coverage")
    for section in section_values if isinstance(section_values, list) else []:
        if not isinstance(section, dict):
            continue
        for raw_fact_id in section.get("fact_ids", []):
            try:
                int(raw_fact_id)
            except (TypeError, ValueError):
                errors.append(f"invalid_fact_reference_format:{str(raw_fact_id)[:80]}")
    known_image_ids = {str(image.get("image_id") or "") for image in image_refs}
    invalid_image_ids = sorted(referenced_image_ids - known_image_ids)
    if invalid_image_ids:
        errors.append("invalid_image_references:" + ",".join(invalid_image_ids))

    paper = _paper_row(Path(db_path), paper_key) or {}
    paper_dir = Path(str(paper.get("paper_dir") or ""))
    for image in image_refs:
        asset_path = _normalized_asset_path(image.get("asset_path"))
        path_error = _image_path_error(asset_path, paper_dir)
        if path_error:
            errors.append(f"invalid_local_image:{path_error}:{asset_path[:120]}")
    declared_paths = {
        _normalized_asset_path(image.get("asset_path")) for image in image_refs
    }
    usable_evidence_paths = {
        asset_path
        for image in pack.image_candidates
        if isinstance(image, dict)
        and (asset_path := _normalized_asset_path(image.get("asset_path")))
        and not _image_path_error(asset_path, paper_dir)
    }
    markdown_paths = _markdown_image_paths(markdown)
    if (image_refs or usable_evidence_paths) and not markdown_paths:
        errors.append("embedded_image_missing")
    for path in sorted(markdown_paths - declared_paths):
        errors.append(f"undeclared_local_image:{path[:120]}")
    for path in sorted(markdown_paths):
        path_error = _image_path_error(path, paper_dir)
        if path_error:
            errors.append(f"invalid_local_image:{path_error}:{path[:120]}")
    publishable_equation_count = len(paper_blog._publishable_blog_equations(pack.equations))
    required_equation_blocks = min(2, publishable_equation_count)
    if paper_blog.display_math_block_count(markdown) < required_equation_blocks:
        errors.append("insufficient_display_math")

    return _score_version(
        markdown=markdown,
        outline=outline,
        image_refs=image_refs,
        generation_meta=generation_meta,
        pack=pack,
        duration_seconds=duration_seconds,
        hard_gate_errors=list(dict.fromkeys(errors)),
    )


def _result_audit(result: Mapping[str, Any]) -> Mapping[str, Any]:
    audit = result.get("audit")
    return audit if isinstance(audit, dict) else {}


def _ab_summaries(report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    sample_papers = _unique_paper_keys(report.get("sample_papers", []))
    grouped: dict[str, dict[str, Mapping[str, Any]]] = {}
    all_results: dict[str, list[Mapping[str, Any]]] = {}
    for result in report.get("results", []):
        if not isinstance(result, dict):
            continue
        arm_name = str(result.get("model_arm") or "")
        paper_key = str(result.get("paper_key") or "")
        if not arm_name or not paper_key:
            continue
        all_results.setdefault(arm_name, []).append(result)
        grouped.setdefault(arm_name, {})[paper_key] = result
    summaries: dict[str, dict[str, Any]] = {}
    for arm_name, by_paper in grouped.items():
        selected = [by_paper[key] for key in sample_papers if key in by_paper]
        eligible = len(selected) == len(sample_papers) and all(
            str(item.get("status") or "") == "completed"
            and bool(_result_audit(item).get("eligible"))
            for item in selected
        )
        scores = [float(_result_audit(item).get("score") or 0.0) for item in selected]
        generation_retry_count = sum(
            int(
                (_result_audit(item).get("metrics") or {}).get("generation_retry_count")
                or 0
            )
            for item in selected
        )
        latencies = [float(item.get("duration_seconds") or 0.0) for item in selected]
        summaries[arm_name] = {
            "eligible": eligible,
            "paper_count": len(selected),
            "mean_score": round(statistics.fmean(scores), 3) if scores else 0.0,
            "generation_retry_count": generation_retry_count,
            "median_latency_seconds": round(statistics.median(latencies), 3) if latencies else 0.0,
        }
    return summaries


def select_ab_winner(report: Mapping[str, Any]) -> str:
    summaries = _ab_summaries(report)
    candidates = [(name, values) for name, values in summaries.items() if values["eligible"]]
    if not candidates:
        raise BlogBatchError("no model arm passed all A/B hard gates")
    if len(candidates) == 1:
        return candidates[0][0]
    candidates.sort(key=lambda item: item[0])
    best_score = max(float(values["mean_score"]) for _name, values in candidates)
    score_winners = [
        item for item in candidates if best_score - float(item[1]["mean_score"]) <= 3.0
    ]
    if len(score_winners) == 1:
        return score_winners[0][0]
    return min(
        score_winners,
        key=lambda item: (
            int(item[1]["generation_retry_count"]),
            float(item[1]["median_latency_seconds"]),
            item[0],
        ),
    )[0]


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _matching_completed_event(
    rows: Sequence[Mapping[str, Any]],
    *,
    paper_key: str,
    source_hash: str,
    arm: BlogModelArm,
    prompt_version: str,
) -> dict[str, Any] | None:
    for row in reversed(rows):
        if (
            row.get("event") == "paper"
            and row.get("paper_key") == paper_key
            and row.get("model_arm") == arm.name
            and row.get("model") == arm.model
            and row.get("source_hash") == source_hash
            and row.get("prompt_version") == prompt_version
            and row.get("status") == "completed"
        ):
            return dict(row)
    return None


def _matching_version_exists(db_path: Path, event: Mapping[str, Any], arm: BlogModelArm) -> bool:
    try:
        version_id = int(event.get("version_id"))
    except (TypeError, ValueError):
        return False
    row = _version_row(db_path, str(event.get("paper_key") or ""), version_id)
    return bool(
        row
        and row.get("model") == arm.model
        and row.get("source_hash") == event.get("source_hash")
        and row.get("prompt_version") == event.get("prompt_version")
        and row.get("status") in {"published", "superseded"}
    )


def _current_version_id(db_path: Path, paper_key: str) -> int | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "select current_version_id from paper_blog_posts where paper_key = ?",
            (paper_key,),
        ).fetchone()
    if row is None or row["current_version_id"] is None:
        return None
    return int(row["current_version_id"])


def _restore_previous_current(
    db_path: Path,
    paper_key: str,
    previous_version_id: int | None,
    failed_version_id: int | None,
) -> None:
    failed_versions = (
        {paper_key: int(failed_version_id)} if failed_version_id is not None else None
    )
    _set_current_versions_atomically(
        db_path,
        {paper_key: previous_version_id},
        failed_version_ids=failed_versions,
    )


def _restore_original_currents(
    db_path: Path,
    original_current_ids: Mapping[str, int | None],
) -> None:
    _set_current_versions_atomically(db_path, original_current_ids)


def _set_current_versions_atomically(
    db_path: Path,
    version_ids: Mapping[str, int | None],
    *,
    failed_version_ids: Mapping[str, int] | None = None,
) -> None:
    paper_blog.ensure_blog_schema(db_path)
    now = _utc_now()
    with connect(db_path) as conn:
        try:
            conn.execute("begin immediate")
            versions: dict[str, Mapping[str, Any]] = {}
            for paper_key, version_id in version_ids.items():
                if version_id is None:
                    continue
                row = conn.execute(
                    "select * from paper_blog_versions where id = ? and paper_key = ?",
                    (int(version_id), paper_key),
                ).fetchone()
                if row is None:
                    raise BlogBatchError(
                        f"cannot set missing blog version {version_id} for paper {paper_key}"
                    )
                versions[paper_key] = dict(row)
            for paper_key in version_ids:
                conn.execute(
                    "update paper_blog_versions set status = 'superseded' "
                    "where paper_key = ? and status = 'published'",
                    (paper_key,),
                )
            for paper_key, version_id in (failed_version_ids or {}).items():
                conn.execute(
                    "update paper_blog_versions set status = 'failed' "
                    "where id = ? and paper_key = ?",
                    (int(version_id), paper_key),
                )
            for paper_key, version_id in version_ids.items():
                if version_id is None:
                    conn.execute("delete from paper_blog_posts where paper_key = ?", (paper_key,))
                    continue
                version = versions[paper_key]
                conn.execute(
                    "update paper_blog_versions set status = 'published' where id = ?",
                    (int(version_id),),
                )
                conn.execute(
                    """
                    insert into paper_blog_posts (
                        paper_key, current_version_id, title, slug, status, target_audience,
                        language, word_count, markdown, html, outline_json, image_refs_json,
                        model, prompt_version, source_hash, created_at, updated_at
                    ) values (?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(paper_key) do update set
                        current_version_id = excluded.current_version_id,
                        title = excluded.title,
                        slug = excluded.slug,
                        status = 'published',
                        target_audience = excluded.target_audience,
                        language = excluded.language,
                        word_count = excluded.word_count,
                        markdown = excluded.markdown,
                        html = excluded.html,
                        outline_json = excluded.outline_json,
                        image_refs_json = excluded.image_refs_json,
                        model = excluded.model,
                        prompt_version = excluded.prompt_version,
                        source_hash = excluded.source_hash,
                        updated_at = excluded.updated_at
                    """,
                    (
                        paper_key,
                        int(version_id),
                        version["title"],
                        paper_blog.slugify(paper_key),
                        paper_blog.BLOG_TARGET_AUDIENCE,
                        paper_blog.BLOG_LANGUAGE,
                        version["word_count"],
                        version["markdown"],
                        version["html"],
                        version["outline_json"],
                        version["image_refs_json"],
                        version["model"],
                        version["prompt_version"],
                        version["source_hash"],
                        now,
                        now,
                    ),
                )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise


def _mark_version_failed(db_path: Path, paper_key: str, version_id: int | None) -> None:
    if version_id is None:
        return
    with connect(db_path) as conn:
        conn.execute(
            "update paper_blog_versions set status = 'failed' where id = ? and paper_key = ?",
            (int(version_id), paper_key),
        )
        conn.commit()


def _load_or_persist_original_currents(
    db_path: Path,
    paper_keys: Sequence[str],
    out_dir: Path,
) -> dict[str, int | None]:
    path = out_dir / "original-current.json"
    backup_id = _backup_identity(out_dir)
    if path.is_file():
        value = _load_json(path)
        if not isinstance(value, dict):
            raise BlogBatchError("original current pointer file is invalid")
        if (
            str(value.get("database_path") or "") != str(db_path.resolve())
            or _unique_paper_keys(value.get("paper_keys", [])) != list(paper_keys)
            or str(value.get("backup_id") or "") != backup_id
        ):
            raise BlogBatchError("original current pointer file does not match this A/B run")
        raw_ids = value.get("current_version_ids")
        if not isinstance(raw_ids, dict) or set(raw_ids) != set(paper_keys):
            raise BlogBatchError("original current pointer file is incomplete")
        return {
            key: int(raw_ids[key]) if raw_ids[key] is not None else None for key in paper_keys
        }
    with connect(db_path) as conn:
        conn.execute("begin")
        try:
            current = {
                key: (
                    int(row["current_version_id"])
                    if (
                        row := conn.execute(
                            "select current_version_id from paper_blog_posts where paper_key = ?",
                            (key,),
                        ).fetchone()
                    )
                    is not None
                    and row["current_version_id"] is not None
                    else None
                )
                for key in paper_keys
            }
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    _atomic_write_json(
        path,
        {
            "format_version": 1,
            "database_path": str(db_path.resolve()),
            "backup_id": backup_id,
            "paper_keys": list(paper_keys),
            "current_version_ids": current,
            "created_at": _utc_now(),
        },
    )
    return current


def _current_source_hash(db_path: Path, paper_key: str) -> str:
    return str(paper_blog.build_blog_evidence_pack(db_path, paper_key).source_hash)


def _paper_event(
    *,
    paper_key: str,
    arm: BlogModelArm,
    source_hash: str,
    prompt_version: str,
    status: str,
    duration_seconds: float,
    version: Any | None = None,
    audit: Mapping[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "event": "paper",
        "paper_key": paper_key,
        "model_arm": arm.name,
        "model": arm.model,
        "source_hash": source_hash,
        "prompt_version": prompt_version,
        "status": status,
        "version_id": getattr(version, "version_id", None),
        "version_number": getattr(version, "version_number", None),
        "word_count": getattr(version, "word_count", 0),
        "duration_seconds": round(max(0.0, duration_seconds), 3),
        "audit": dict(audit or {}),
        "error": error,
        "created_at": _utc_now(),
    }


def _arm_public_dict(arm: BlogModelArm) -> dict[str, Any]:
    endpoint_origin = _safe_endpoint_origin(arm.base_url)
    return {
        "name": arm.name,
        "model": arm.model,
        "api_style": arm.api_style,
        "api_key_env": arm.api_key_env,
        "endpoint_origin": endpoint_origin,
        "endpoint_class": urlsplit(endpoint_origin).hostname or "configured-endpoint",
        "proxy_enabled": bool(str(arm.proxy_url or "").strip()),
    }


def _default_generate() -> Callable[..., Any]:
    return paper_blog.generate_and_publish_blog


def _default_audit() -> Callable[[Path, str, int, float], dict[str, Any]]:
    return audit_blog_version


def run_ab(
    db_path: Path,
    paper_keys: Iterable[str],
    out_dir: Path,
    *,
    target_chars: int = 5000,
    env: Mapping[str, str] | None = None,
    arms: Sequence[BlogModelArm] | None = None,
    providers: Mapping[str, Any] | None = None,
    generate_func: Callable[..., Any] | None = None,
    audit_func: Callable[[Path, str, int, float], dict[str, Any]] | None = None,
    prompt_version: str = paper_blog.BLOG_PROMPT_VERSION,
) -> dict[str, Any]:
    db_path = _require_existing_db(Path(db_path))
    out_dir = Path(out_dir)
    keys = _unique_paper_keys(paper_keys)
    if not keys:
        raise BlogBatchError("A/B requires at least one sample paper")
    manifest = validate_backup_manifest(db_path, out_dir)
    manifest_keys = _unique_paper_keys(manifest.get("paper_keys", []))
    if not set(keys).issubset(set(manifest_keys)):
        raise BlogBatchError("A/B sample papers are not covered by the selected-paper backup")
    values = os.environ if env is None else env
    resolved_arms = list(arms or [model_arm_from_env("deepseek", values), model_arm_from_env("luna", values)])
    if len({arm.name for arm in resolved_arms}) != len(resolved_arms):
        raise BlogBatchError("A/B model arm names must be unique")
    preflight = preflight_papers(db_path, keys)
    not_ready = [row["paper_key"] for row in preflight if not row["ready"]]
    if not_ready:
        raise BlogBatchError("A/B preflight failed for: " + ", ".join(not_ready))
    source_by_key = {row["paper_key"]: row["source_hash"] for row in preflight}
    original_current_ids = _load_or_persist_original_currents(db_path, keys, out_dir)
    asset_tracking = _load_or_create_asset_tracking(db_path, keys, out_dir)
    log_path = out_dir / "ab.jsonl"
    history = _read_jsonl(log_path)
    secrets = _configured_secret_values(values, resolved_arms)
    provider_map = dict(providers or {})
    generate = generate_func or _default_generate()
    audit_version = audit_func or _default_audit()
    results: list[dict[str, Any]] = []
    promotion_complete = False
    try:
        _restore_original_currents(db_path, original_current_ids)
        for paper_key in keys:
            source_hash = source_by_key[paper_key]
            for arm in resolved_arms:
                completed = _matching_completed_event(
                    history,
                    paper_key=paper_key,
                    source_hash=source_hash,
                    arm=arm,
                    prompt_version=prompt_version,
                )
                if completed is not None:
                    try:
                        matching_version = _matching_version_exists(db_path, completed, arm)
                        if matching_version:
                            fresh_audit = audit_version(
                                db_path,
                                paper_key,
                                int(completed["version_id"]),
                                float(completed.get("duration_seconds") or 0.0),
                            )
                            if (
                                fresh_audit.get("eligible")
                                and _current_source_hash(db_path, paper_key) == source_hash
                            ):
                                resumed = {**completed, "audit": fresh_audit, "resumed": True}
                                results.append(resumed)
                                continue
                    except Exception as exc:
                        row = _paper_event(
                            paper_key=paper_key,
                            arm=arm,
                            source_hash=source_hash,
                            prompt_version=prompt_version,
                            status="failed",
                            duration_seconds=0.0,
                            error="resume audit failed: " + _sanitize_text(exc, secrets)[:760],
                        )
                        _append_jsonl(log_path, row)
                        history.append(row)
                        results.append(row)
                        continue

                generated: Any | None = None
                started = time.monotonic()
                try:
                    if _current_source_hash(db_path, paper_key) != source_hash:
                        raise BlogBatchError("source hash changed before A/B generation")
                    provider = provider_map.get(arm.name)
                    if provider is None:
                        provider = provider_for_arm(arm, values)
                        provider_map[arm.name] = provider
                    generated = generate(
                        db_path,
                        paper_key,
                        provider=provider,
                        model=arm.model,
                        target_chars=target_chars,
                        force=False,
                        prompt_version=prompt_version,
                    )
                    duration = time.monotonic() - started
                    if _current_source_hash(db_path, paper_key) != source_hash:
                        raise BlogBatchError("source hash changed during A/B generation")
                    audit = audit_version(db_path, paper_key, generated.version_id, duration)
                    status = "completed" if audit.get("eligible") else "failed"
                    if status != "completed":
                        _mark_version_failed(db_path, paper_key, generated.version_id)
                    row = _paper_event(
                        paper_key=paper_key,
                        arm=arm,
                        source_hash=source_hash,
                        prompt_version=prompt_version,
                        status=status,
                        duration_seconds=duration,
                        version=generated,
                        audit=audit,
                        error="" if status == "completed" else "audit hard gates failed",
                    )
                except Exception as exc:
                    duration = time.monotonic() - started
                    if generated is not None:
                        _mark_version_failed(db_path, paper_key, generated.version_id)
                    row = _paper_event(
                        paper_key=paper_key,
                        arm=arm,
                        source_hash=source_hash,
                        prompt_version=prompt_version,
                        status="failed",
                        duration_seconds=duration,
                        version=generated,
                        error=_sanitize_text(exc, secrets)[:800],
                    )
                finally:
                    asset_tracking = _refresh_created_assets(db_path, asset_tracking, out_dir)
                    _restore_original_currents(db_path, original_current_ids)
                _append_jsonl(log_path, row)
                history.append(row)
                results.append(row)

        report: dict[str, Any] = {
            "status": "partial",
            "database_path": str(db_path),
            "backup_id": manifest["backup_id"],
            "paper_keys": manifest_keys,
            "prompt_version": prompt_version,
            "scoring_version": SCORING_VERSION,
            "sample_papers": keys,
            "sample_source_hashes": source_by_key,
            "arms": [_arm_public_dict(arm) for arm in resolved_arms],
            "results": results,
            "arm_summaries": {},
            "winner": None,
            "created_at": _utc_now(),
        }
        report["arm_summaries"] = _ab_summaries(report)
        try:
            winner_name = select_ab_winner(report)
        except BlogBatchError:
            winner_name = ""

        winning_version_ids: dict[str, int | None] = {}
        if winner_name:
            for paper_key in keys:
                winning_rows = [
                    row
                    for row in results
                    if row.get("paper_key") == paper_key
                    and row.get("model_arm") == winner_name
                    and row.get("status") == "completed"
                ]
                if not winning_rows:
                    winner_name = ""
                    break
                version_id = int(winning_rows[-1]["version_id"])
                try:
                    fresh_audit = audit_version(db_path, paper_key, version_id, 0.0)
                    source_unchanged = (
                        _current_source_hash(db_path, paper_key) == source_by_key[paper_key]
                    )
                except Exception as exc:
                    winning_rows[-1]["status"] = "failed"
                    winning_rows[-1]["audit"] = {}
                    winning_rows[-1]["error"] = (
                        "winner audit failed: " + _sanitize_text(exc, secrets)[:760]
                    )
                    _append_jsonl(log_path, winning_rows[-1])
                    winner_name = ""
                    break
                if not fresh_audit.get("eligible") or not source_unchanged:
                    winning_rows[-1]["status"] = "failed"
                    winning_rows[-1]["audit"] = fresh_audit
                    winning_rows[-1]["error"] = "winner evidence revalidation failed"
                    _append_jsonl(log_path, winning_rows[-1])
                    winner_name = ""
                    break
                winning_version_ids[paper_key] = version_id

        report["arm_summaries"] = _ab_summaries(report)
        if winner_name:
            report["winner"] = winner_name
            report["status"] = "completed"
            winning_arm = next(arm for arm in resolved_arms if arm.name == winner_name)
            winner_payload = {
                "database_path": str(db_path),
                "backup_id": manifest["backup_id"],
                "paper_keys": manifest_keys,
                "prompt_version": prompt_version,
                "sample_papers": keys,
                "sample_source_hashes": source_by_key,
                "model_arm": winner_name,
                "model": winning_arm.model,
                "api_style": winning_arm.api_style,
                "scoring_version": SCORING_VERSION,
                "selected_at": _utc_now(),
            }
            _atomic_write_json(out_dir / "ab-report.json", report)
            _atomic_write_json(out_dir / "winner.json", winner_payload)
            _set_current_versions_atomically(db_path, winning_version_ids)
            promotion_complete = True
        else:
            (out_dir / "winner.json").unlink(missing_ok=True)
            _atomic_write_json(out_dir / "ab-report.json", report)
        return report
    except BaseException:
        (out_dir / "winner.json").unlink(missing_ok=True)
        (out_dir / "ab-report.json").unlink(missing_ok=True)
        raise
    finally:
        if not promotion_complete:
            try:
                asset_tracking = _refresh_created_assets(db_path, asset_tracking, out_dir)
            finally:
                _restore_original_currents(db_path, original_current_ids)


def _current_matching_version(
    db_path: Path,
    paper_key: str,
    *,
    arm: BlogModelArm,
    source_hash: str,
    prompt_version: str,
) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            select v.* from paper_blog_posts p
            join paper_blog_versions v on v.id = p.current_version_id
            where p.paper_key = ? and p.status = 'published'
              and v.status = 'published'
              and v.model = ? and v.source_hash = ? and v.prompt_version = ?
            """,
            (paper_key, arm.model, source_hash, prompt_version),
        ).fetchone()
    return dict(row) if row is not None else None


@dataclass(frozen=True)
class _BatchPaperOutcome:
    row: dict[str, Any]
    source_hash: str
    append_to_log: bool
    generated: bool = False


def _run_batch_paper(
    db_path: Path,
    paper_key: str,
    preflight_row: Mapping[str, Any],
    *,
    arm: BlogModelArm,
    history: Sequence[Mapping[str, Any]],
    secrets: Sequence[str],
    provider_getter: Callable[[], Any],
    generate: Callable[..., Any],
    audit_version: Callable[[Path, str, int, float], dict[str, Any]],
    target_chars: int,
    prompt_version: str,
) -> _BatchPaperOutcome:
    source_hash = str(preflight_row.get("source_hash") or "")
    if not preflight_row.get("ready"):
        row = _paper_event(
            paper_key=paper_key,
            arm=arm,
            source_hash=source_hash,
            prompt_version=prompt_version,
            status="failed",
            duration_seconds=0.0,
            error="preflight failed: " + ",".join(preflight_row.get("errors", [])),
        )
        return _BatchPaperOutcome(row, source_hash, True)

    completed = _matching_completed_event(
        history,
        paper_key=paper_key,
        source_hash=source_hash,
        arm=arm,
        prompt_version=prompt_version,
    )
    resume_source_changed = False
    if completed is not None:
        try:
            matching_version = _matching_version_exists(db_path, completed, arm)
            if matching_version:
                fresh_audit = audit_version(
                    db_path,
                    paper_key,
                    int(completed["version_id"]),
                    float(completed.get("duration_seconds") or 0.0),
                )
                fresh_source_hash = _current_source_hash(db_path, paper_key)
                if fresh_audit.get("eligible") and fresh_source_hash == source_hash:
                    if _current_version_id(db_path, paper_key) != int(completed["version_id"]):
                        paper_blog.rollback_blog_post(
                            db_path, paper_key, int(completed["version_id"])
                        )
                    return _BatchPaperOutcome(
                        {**completed, "audit": fresh_audit, "resumed": True},
                        source_hash,
                        False,
                    )
                if fresh_source_hash != source_hash:
                    source_hash = fresh_source_hash
                    resume_source_changed = True
        except Exception as exc:
            row = _paper_event(
                paper_key=paper_key,
                arm=arm,
                source_hash=source_hash,
                prompt_version=prompt_version,
                status="failed",
                duration_seconds=0.0,
                error="resume audit failed: " + _sanitize_text(exc, secrets)[:760],
            )
            return _BatchPaperOutcome(row, source_hash, True)

    existing = (
        None
        if resume_source_changed
        else _current_matching_version(
            db_path,
            paper_key,
            arm=arm,
            source_hash=source_hash,
            prompt_version=prompt_version,
        )
    )
    if existing is not None:
        try:
            audit = audit_version(db_path, paper_key, int(existing["id"]), 0.0)
        except Exception as exc:
            row = _paper_event(
                paper_key=paper_key,
                arm=arm,
                source_hash=source_hash,
                prompt_version=prompt_version,
                status="failed",
                duration_seconds=0.0,
                error="existing version audit failed: " + _sanitize_text(exc, secrets)[:740],
            )
            return _BatchPaperOutcome(row, source_hash, True)
        if audit.get("eligible"):

            class ExistingVersion:
                version_id = int(existing["id"])
                version_number = int(existing["version_number"])
                word_count = int(existing["word_count"])

            row = _paper_event(
                paper_key=paper_key,
                arm=arm,
                source_hash=source_hash,
                prompt_version=prompt_version,
                status="completed",
                duration_seconds=0.0,
                version=ExistingVersion(),
                audit=audit,
            )
            row["existing"] = True
            return _BatchPaperOutcome(row, source_hash, True)

    previous_version_id = _current_version_id(db_path, paper_key)
    generated_version: Any | None = None
    started = time.monotonic()
    try:
        if _current_source_hash(db_path, paper_key) != source_hash:
            raise BlogBatchError("source hash changed before batch generation")
        generated_version = generate(
            db_path,
            paper_key,
            provider=provider_getter(),
            model=arm.model,
            target_chars=target_chars,
            force=False,
            prompt_version=prompt_version,
        )
        duration = time.monotonic() - started
        if _current_source_hash(db_path, paper_key) != source_hash:
            raise BlogBatchError("source hash changed during batch generation")
        audit = audit_version(db_path, paper_key, generated_version.version_id, duration)
        status = "completed" if audit.get("eligible") else "failed"
        row = _paper_event(
            paper_key=paper_key,
            arm=arm,
            source_hash=source_hash,
            prompt_version=prompt_version,
            status=status,
            duration_seconds=duration,
            version=generated_version,
            audit=audit,
            error="" if status == "completed" else "audit hard gates failed",
        )
        if status != "completed":
            _restore_previous_current(
                db_path,
                paper_key,
                previous_version_id,
                generated_version.version_id,
            )
    except Exception as exc:
        duration = time.monotonic() - started
        if generated_version is not None:
            _restore_previous_current(
                db_path,
                paper_key,
                previous_version_id,
                generated_version.version_id,
            )
        row = _paper_event(
            paper_key=paper_key,
            arm=arm,
            source_hash=source_hash,
            prompt_version=prompt_version,
            status="failed",
            duration_seconds=duration,
            error=_sanitize_text(exc, secrets)[:800],
        )
    return _BatchPaperOutcome(row, source_hash, True, generated=True)


def run_batch(
    db_path: Path,
    paper_keys: Iterable[str],
    out_dir: Path,
    model_arm: BlogModelArm | str,
    *,
    target_chars: int = 5000,
    env: Mapping[str, str] | None = None,
    provider: Any | None = None,
    generate_func: Callable[..., Any] | None = None,
    audit_func: Callable[[Path, str, int, float], dict[str, Any]] | None = None,
    prompt_version: str = paper_blog.BLOG_PROMPT_VERSION,
    concurrency: int = 1,
) -> dict[str, Any]:
    db_path = _require_existing_db(Path(db_path))
    out_dir = Path(out_dir)
    keys = _unique_paper_keys(paper_keys)
    values = os.environ if env is None else env
    arm = model_arm_from_env(model_arm, values) if isinstance(model_arm, str) else model_arm
    validate_winner_file(
        db_path,
        out_dir,
        keys,
        arm.name,
        prompt_version=prompt_version,
        runtime_arm=arm,
    )
    try:
        requested_concurrency = int(concurrency)
    except (TypeError, ValueError) as exc:
        raise BlogBatchError("concurrency must be a positive integer") from exc
    if requested_concurrency < 1:
        raise BlogBatchError("concurrency must be a positive integer")
    worker_count = min(requested_concurrency, max(1, len(keys)))
    if provider is not None and worker_count > 1:
        raise BlogBatchError("explicit provider is not thread-isolated; use concurrency=1")
    log_path = out_dir / "batch.jsonl"
    history = _read_jsonl(log_path)
    secrets = _configured_secret_values(values, [arm])
    generate = generate_func or _default_generate()
    audit_version = audit_func or _default_audit()
    preflight = preflight_papers(db_path, keys)
    preflight_by_key = {row["paper_key"]: row for row in preflight}
    asset_tracking = _load_or_create_asset_tracking(db_path, keys, out_dir)
    provider_local = threading.local()

    def thread_provider() -> Any:
        if provider is not None:
            return provider
        value = getattr(provider_local, "value", None)
        if value is None:
            value = provider_for_arm(arm, values)
            provider_local.value = value
        return value

    outcomes: list[_BatchPaperOutcome | None] = [None] * len(keys)
    executor = ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="deep-reading",
    )
    pending: dict[Any, int] = {}
    next_index = 0

    def submit_until_full() -> None:
        nonlocal next_index
        while len(pending) < worker_count and next_index < len(keys):
            index = next_index
            paper_key = keys[index]
            future = executor.submit(
                _run_batch_paper,
                db_path,
                paper_key,
                preflight_by_key[paper_key],
                arm=arm,
                history=history,
                secrets=secrets,
                provider_getter=thread_provider,
                generate=generate,
                audit_version=audit_version,
                target_chars=target_chars,
                prompt_version=prompt_version,
            )
            pending[future] = index
            next_index += 1

    def record_future(future: Any, index: int) -> None:
        paper_key = keys[index]
        try:
            outcome = future.result()
        except Exception as exc:
            source_hash = str(preflight_by_key[paper_key].get("source_hash") or "")
            row = _paper_event(
                paper_key=paper_key,
                arm=arm,
                source_hash=source_hash,
                prompt_version=prompt_version,
                status="failed",
                duration_seconds=0.0,
                error="batch worker failed: " + _sanitize_text(exc, secrets)[:760],
            )
            outcome = _BatchPaperOutcome(row, source_hash, True)
        outcomes[index] = outcome
        if outcome.source_hash != preflight_by_key[paper_key].get("source_hash"):
            preflight_by_key[paper_key] = {
                **preflight_by_key[paper_key],
                "source_hash": outcome.source_hash,
            }
        if outcome.append_to_log:
            _append_jsonl(log_path, outcome.row)

    submit_until_full()
    try:
        while pending:
            done, _not_done = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                record_future(future, index)
            submit_until_full()
    except BaseException:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)
        for future, index in list(pending.items()):
            if not future.cancelled() and outcomes[index] is None:
                record_future(future, index)
        if any(outcome.generated for outcome in outcomes if outcome is not None):
            try:
                _refresh_created_assets(db_path, asset_tracking, out_dir)
            except Exception:
                pass
        raise
    else:
        executor.shutdown(wait=True)

    if any(outcome.generated for outcome in outcomes if outcome is not None):
        asset_tracking = _refresh_created_assets(db_path, asset_tracking, out_dir)
    results = [outcome.row for outcome in outcomes if outcome is not None]

    final_papers: list[dict[str, Any]] = []
    for paper_key in keys:
        source_hash = str(preflight_by_key[paper_key].get("source_hash") or "")
        current = _current_matching_version(
            db_path,
            paper_key,
            arm=arm,
            source_hash=source_hash,
            prompt_version=prompt_version,
        )
        eligible = False
        version_id: int | None = None
        if current is not None:
            version_id = int(current["id"])
            try:
                eligible = bool(
                    audit_version(db_path, paper_key, version_id, 0.0).get("eligible")
                )
            except Exception as exc:
                row = _paper_event(
                    paper_key=paper_key,
                    arm=arm,
                    source_hash=source_hash,
                    prompt_version=prompt_version,
                    status="failed",
                    duration_seconds=0.0,
                    error="final audit failed: " + _sanitize_text(exc, secrets)[:760],
                )
                _append_jsonl(log_path, row)
                results.append(row)
        final_papers.append(
            {
                "paper_key": paper_key,
                "source_hash": source_hash,
                "version_id": version_id,
                "valid_current_version": eligible,
            }
        )
    failed_keys = [item["paper_key"] for item in final_papers if not item["valid_current_version"]]
    summary = {
        "status": "completed" if not failed_keys else "partial",
        "model_arm": _arm_public_dict(arm),
        "prompt_version": prompt_version,
        "concurrency": worker_count,
        "requested_count": len(keys),
        "completed_count": len(keys) - len(failed_keys),
        "failed_count": len(failed_keys),
        "failed_paper_keys": failed_keys,
        "papers": final_papers,
        "events": results,
        "created_at": _utc_now(),
    }
    _atomic_write_json(out_dir / "batch-summary.json", summary)
    return summary


__all__ = [
    "BlogBatchError",
    "BlogModelArm",
    "SCORING_VERSION",
    "audit_blog_version",
    "backup_blog_state",
    "model_arm_from_env",
    "preflight_papers",
    "provider_for_arm",
    "restore_blog_state",
    "run_ab",
    "run_batch",
    "select_ab_winner",
    "validate_backup_manifest",
    "validate_winner_file",
]

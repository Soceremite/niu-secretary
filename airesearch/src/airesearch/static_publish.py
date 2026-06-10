from __future__ import annotations

import json
import shutil
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


@dataclass(frozen=True)
class StaticPublishResult:
    source_dir: Path
    out_dir: Path
    entrypoint: Path
    manifest_path: Path
    diff_path: Path
    file_count: int


@dataclass(frozen=True)
class StaticHostConfigResult:
    site_dir: Path
    config_path: Path
    manifest_path: Path
    base_path: str
    deploy_root: Path


@dataclass(frozen=True)
class StaticDeployScriptsResult:
    site_dir: Path
    out_dir: Path
    deploy_script_path: Path
    rollback_script_path: Path
    manifest_path: Path
    deploy_root: Path
    snapshot_root: Path


def _resolve(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_source_dir(source_dir: Path) -> None:
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"source site directory does not exist: {source_dir}")
    if not (source_dir / "index.html").exists():
        raise ValueError(f"source site directory is missing index.html: {source_dir}")
    if not (source_dir / "manifest.json").exists():
        raise ValueError(f"source site directory is missing manifest.json: {source_dir}")


def _relative_files(directory: Path) -> list[str]:
    return sorted(str(path.relative_to(directory)) for path in directory.rglob("*") if path.is_file())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _content_hashes(directory: Path) -> dict[str, str]:
    if not directory.exists() or not directory.is_dir():
        return {}
    ignored = {"publish.json", "publish-diff.json"}
    hashes: dict[str, str] = {}
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        relative = str(path.relative_to(directory))
        if relative in ignored:
            continue
        hashes[relative] = _sha256(path)
    return hashes


def _publish_diff(previous: dict[str, str], current: dict[str, str]) -> dict[str, object]:
    previous_files = set(previous)
    current_files = set(current)
    shared = previous_files & current_files
    changed = sorted(path for path in shared if previous[path] != current[path])
    unchanged = sorted(path for path in shared if previous[path] == current[path])
    added = sorted(current_files - previous_files)
    removed = sorted(previous_files - current_files)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "previous_file_count": len(previous),
        "current_file_count": len(current),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "unchanged_count": len(unchanged),
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }


def publish_static_site(source_dir: Path, out_dir: Path, *, clean: bool = True) -> StaticPublishResult:
    _validate_source_dir(source_dir)
    resolved_source = _resolve(source_dir)
    resolved_out = _resolve(out_dir)
    if resolved_source == resolved_out:
        raise ValueError("source site directory and publish directory must be different")
    if _is_relative_to(resolved_out, resolved_source):
        raise ValueError("publish directory cannot be inside the source site directory")

    previous_hashes = _content_hashes(out_dir)
    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, out_dir, dirs_exist_ok=True)

    files_before_manifest = _relative_files(out_dir)
    current_hashes = _content_hashes(out_dir)
    manifest_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_dir": str(source_dir),
        "out_dir": str(out_dir),
        "entrypoint": str(out_dir / "index.html"),
        "file_count": len(files_before_manifest) + 2,
        "files": sorted(files_before_manifest + ["publish.json", "publish-diff.json"]),
    }
    manifest_path = out_dir / "publish.json"
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    diff_path = out_dir / "publish-diff.json"
    diff_path.write_text(
        json.dumps(_publish_diff(previous_hashes, current_hashes), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return StaticPublishResult(
        source_dir=source_dir,
        out_dir=out_dir,
        entrypoint=out_dir / "index.html",
        manifest_path=manifest_path,
        diff_path=diff_path,
        file_count=manifest_payload["file_count"],
    )


def _normalize_base_path(base_path: str) -> str:
    normalized = "/" + base_path.strip("/") + "/"
    if normalized == "//":
        raise ValueError("base_path must not be empty")
    return normalized


def _nginx_config_text(*, base_path: str, deploy_root: Path) -> str:
    normalized_base = _normalize_base_path(base_path)
    no_slash = normalized_base.rstrip("/")
    resolved_deploy_root = _resolve(deploy_root)
    return f"""# Install this inside the existing niu-secretary nginx server block.
location = {no_slash} {{
    return 301 {normalized_base};
}}

location {normalized_base} {{
    alias {resolved_deploy_root}/;
    index index.html;
    try_files $uri $uri/ {normalized_base}index.html;
}}
"""


def write_static_host_config(
    site_dir: Path,
    out_dir: Path,
    *,
    base_path: str = "/niu-secretary/airesearch/",
    deploy_root: Path = Path("/var/www/html/niu-secretary/airesearch"),
) -> StaticHostConfigResult:
    _validate_source_dir(site_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    normalized_base = _normalize_base_path(base_path)
    config_path = out_dir / "airesearch.nginx.conf"
    config_path.write_text(
        _nginx_config_text(base_path=normalized_base, deploy_root=deploy_root),
        encoding="utf-8",
    )
    manifest_path = out_dir / "static-host.json"
    manifest_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "site_dir": str(site_dir),
        "resolved_site_dir": str(_resolve(site_dir)),
        "config_path": str(config_path),
        "base_path": normalized_base,
        "deploy_root": str(_resolve(deploy_root)),
        "deploy_command": f"sudo rsync -av --delete {_resolve(site_dir)}/ {_resolve(deploy_root)}/",
        "install_hint": "Copy the published site into deploy_root, then include airesearch.nginx.conf inside the existing niu-secretary nginx server block and reload nginx.",
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return StaticHostConfigResult(
        site_dir=site_dir,
        config_path=config_path,
        manifest_path=manifest_path,
        base_path=normalized_base,
        deploy_root=deploy_root,
    )


def _shell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _static_deploy_script_text(*, site_dir: Path, deploy_root: Path, snapshot_root: Path) -> str:
    site = _shell_single_quote(str(_resolve(site_dir)))
    deploy = _shell_single_quote(str(_resolve(deploy_root)))
    snapshots = _shell_single_quote(str(_resolve(snapshot_root)))
    return f'''#!/usr/bin/env bash
set -euo pipefail

SITE_DIR={site}
DEPLOY_ROOT={deploy}
SNAPSHOT_ROOT={snapshots}
STAMP="${{1:-$(date -u +%Y%m%dT%H%M%SZ)}}"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$STAMP"

if [[ ! -f "$SITE_DIR/index.html" || ! -f "$SITE_DIR/manifest.json" ]]; then
  echo "site_dir_missing_required_files=$SITE_DIR" >&2
  exit 2
fi

mkdir -p "$SNAPSHOT_ROOT"
if [[ -d "$DEPLOY_ROOT" ]]; then
  mkdir -p "$SNAPSHOT_DIR"
  rsync -a --delete "$DEPLOY_ROOT"/ "$SNAPSHOT_DIR"/
else
  mkdir -p "$SNAPSHOT_DIR"
fi

mkdir -p "$DEPLOY_ROOT"
rsync -a --delete "$SITE_DIR"/ "$DEPLOY_ROOT"/
cat > "$DEPLOY_ROOT/deploy-manifest.json" <<EOF
{{"snapshot":"$SNAPSHOT_DIR","site_dir":"$SITE_DIR","deploy_root":"$DEPLOY_ROOT","deployed_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}}
EOF

echo "static_site_deployed deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"
'''


def _static_rollback_script_text(*, deploy_root: Path, snapshot_root: Path) -> str:
    deploy = _shell_single_quote(str(_resolve(deploy_root)))
    snapshots = _shell_single_quote(str(_resolve(snapshot_root)))
    return f'''#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT={deploy}
SNAPSHOT_ROOT={snapshots}
SNAPSHOT="${{1:-latest}}"

if [[ "$SNAPSHOT" == "latest" ]]; then
  SNAPSHOT_DIR="$(find "$SNAPSHOT_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
else
  SNAPSHOT_DIR="$SNAPSHOT_ROOT/$SNAPSHOT"
fi

if [[ -z "${{SNAPSHOT_DIR:-}}" || ! -d "$SNAPSHOT_DIR" ]]; then
  echo "snapshot_not_found=$SNAPSHOT" >&2
  exit 2
fi

mkdir -p "$DEPLOY_ROOT"
rsync -a --delete "$SNAPSHOT_DIR"/ "$DEPLOY_ROOT"/
cat > "$DEPLOY_ROOT/rollback-manifest.json" <<EOF
{{"snapshot":"$SNAPSHOT_DIR","deploy_root":"$DEPLOY_ROOT","rolled_back_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}}
EOF

echo "static_site_rolled_back deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"
'''


def write_static_deploy_scripts(
    site_dir: Path,
    out_dir: Path,
    *,
    deploy_root: Path = Path("/var/www/html/niu-secretary/airesearch"),
    snapshot_root: Path | None = None,
) -> StaticDeployScriptsResult:
    _validate_source_dir(site_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_deploy = _resolve(deploy_root)
    resolved_snapshots = _resolve(snapshot_root) if snapshot_root is not None else resolved_deploy.parent / ".airesearch-deploy-snapshots"
    deploy_script_path = out_dir / "deploy-airesearch.sh"
    rollback_script_path = out_dir / "rollback-airesearch.sh"
    manifest_path = out_dir / "static-deploy-scripts.json"

    deploy_script_path.write_text(
        _static_deploy_script_text(site_dir=site_dir, deploy_root=deploy_root, snapshot_root=resolved_snapshots),
        encoding="utf-8",
    )
    rollback_script_path.write_text(
        _static_rollback_script_text(deploy_root=deploy_root, snapshot_root=resolved_snapshots),
        encoding="utf-8",
    )
    deploy_script_path.chmod(0o755)
    rollback_script_path.chmod(0o755)

    manifest_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "site_dir": str(site_dir),
        "resolved_site_dir": str(_resolve(site_dir)),
        "deploy_root": str(resolved_deploy),
        "snapshot_root": str(resolved_snapshots),
        "deploy_script": str(deploy_script_path),
        "rollback_script": str(rollback_script_path),
        "deploy_command": f"sudo {deploy_script_path}",
        "rollback_command": f"sudo {rollback_script_path} latest",
        "rollback_hint": "Run rollback-airesearch.sh latest to restore the newest pre-deploy snapshot, or pass a snapshot directory name.",
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return StaticDeployScriptsResult(
        site_dir=site_dir,
        out_dir=out_dir,
        deploy_script_path=deploy_script_path,
        rollback_script_path=rollback_script_path,
        manifest_path=manifest_path,
        deploy_root=deploy_root,
        snapshot_root=resolved_snapshots,
    )


def serve_report_site(directory: Path, host: str, port: int) -> None:
    _validate_source_dir(directory)
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()

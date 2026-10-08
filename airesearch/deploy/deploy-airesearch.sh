#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SITE_DIR="${SITE_DIR:-$PROJECT_ROOT/airesearch/exports/site-current}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/var/www/html/niu-secretary/airesearch}"
SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/var/www/html/niu-secretary/.airesearch-deploy-snapshots}"
STAMP="${1:-$(date -u +%Y%m%dT%H%M%S%NZ)}"
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
rsync -a --delete --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r "$SITE_DIR"/ "$DEPLOY_ROOT"/
cat > "$DEPLOY_ROOT/deploy-manifest.json" <<EOF
{"snapshot":"$SNAPSHOT_DIR","site_dir":"$SITE_DIR","deploy_root":"$DEPLOY_ROOT","deployed_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

VERIFY_URL="${AIRESEARCH_VERIFY_URL:-http://127.0.0.1/niu-secretary/airesearch/papers/index.html}"
if [[ -n "$VERIFY_URL" ]]; then
  VERIFY_BODY="$(curl --fail --silent --show-error --max-time 15 "$VERIFY_URL")"
  if [[ "$VERIFY_BODY" != *'<h1>Papers</h1>'* ]]; then
    echo "public_papers_verification_failed url=$VERIFY_URL" >&2
    exit 3
  fi
fi

# Retain only the newest N pre-deploy snapshots (default 1) so disk usage stays bounded.
SNAPSHOT_KEEP="${SNAPSHOT_KEEP:-1}"
if [[ "$SNAPSHOT_KEEP" =~ ^[0-9]+$ ]] && (( SNAPSHOT_KEEP >= 1 )); then
  mapfile -t _prune_snaps < <(find "$SNAPSHOT_ROOT" -mindepth 1 -maxdepth 1 -type d | sort)
  _prune_count=$(( ${#_prune_snaps[@]} - SNAPSHOT_KEEP ))
  for (( _i=0; _i<_prune_count; _i++ )); do
    rm -rf -- "${_prune_snaps[_i]}" || echo "snapshot_prune_failed=${_prune_snaps[_i]}" >&2
  done
fi

echo "static_site_deployed deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"

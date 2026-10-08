#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
WEB_DIST="${WEB_DIST:-$PROJECT_ROOT/web/dist}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/var/www/html/niu-secretary}"
SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/var/www/html/.niu-secretary-vue-snapshots}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$STAMP"

if [[ ! -f "$WEB_DIST/index.html" ]]; then
  echo "web_dist_missing path=$WEB_DIST/index.html" >&2
  exit 1
fi

mkdir -p "$DEPLOY_ROOT" "$SNAPSHOT_DIR"

for path in index.html assets; do
  if [[ -e "$DEPLOY_ROOT/$path" ]]; then
    cp -a "$DEPLOY_ROOT/$path" "$SNAPSHOT_DIR/"
  fi
done

# Keep legacy module directories on disk, but make the Vite entry and hashed
# assets match this build exactly. Stale chunks can break dynamic imports.
rsync -av "$WEB_DIST/index.html" "$DEPLOY_ROOT/index.html"
mkdir -p "$DEPLOY_ROOT/assets"
rsync -av --delete "$WEB_DIST/assets"/ "$DEPLOY_ROOT/assets"/

cat > "$DEPLOY_ROOT/vue-deploy-manifest.json" <<EOF
{"snapshot":"$SNAPSHOT_DIR","web_dist":"$WEB_DIST","deploy_root":"$DEPLOY_ROOT","deployed_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

# Retain only the newest N pre-deploy snapshots (default 1) so disk usage stays bounded.
SNAPSHOT_KEEP="${SNAPSHOT_KEEP:-1}"
if [[ "$SNAPSHOT_KEEP" =~ ^[0-9]+$ ]] && (( SNAPSHOT_KEEP >= 1 )); then
  mapfile -t _prune_snaps < <(find "$SNAPSHOT_ROOT" -mindepth 1 -maxdepth 1 -type d | sort)
  _prune_count=$(( ${#_prune_snaps[@]} - SNAPSHOT_KEEP ))
  for (( _i=0; _i<_prune_count; _i++ )); do
    rm -rf -- "${_prune_snaps[_i]}" || echo "snapshot_prune_failed=${_prune_snaps[_i]}" >&2
  done
fi

echo "vue_web_deployed deploy_root=$DEPLOY_ROOT snapshot=$SNAPSHOT_DIR"

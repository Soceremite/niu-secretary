#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT=/home/ubuntu/vibe_proj/niu-secretary
DB="$ROOT/airesearch/data/airesearch.sqlite3"
RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260812-40"
PYTHONPATH="$ROOT/airesearch/src"
PYTHON="$ROOT/airesearch/.venv/bin/python"

set -a
source "$ROOT/airesearch/.env"
set +a
: "${OPENCODE_GO_BASE_URL:?OPENCODE_GO_BASE_URL is required in airesearch/.env}"
: "${OPENCODE_GO_API_KEY:?OPENCODE_GO_API_KEY is required in airesearch/.env}"
: "${AIRESEARCH_FACT_MODEL:?AIRESEARCH_FACT_MODEL is required in airesearch/.env}"
export AIRESEARCH_FACT_API_KEY="$OPENCODE_GO_API_KEY"
export AIRESEARCH_FACT_BASE_URL="${OPENCODE_GO_BASE_URL%/}/responses"
export AIRESEARCH_FACT_PROXY="${OPENCODE_GO_PROXY:-}"
export AIRESEARCH_DEEPSEEK_BLOG_BASE_URL="$OPENCODE_GO_BASE_URL"
export AIRESEARCH_DEEPSEEK_BLOG_API_KEY="$OPENCODE_GO_API_KEY"
export AIRESEARCH_LUNA_BLOG_BASE_URL="${OPENCODE_GO_BASE_URL%/}/responses"
export AIRESEARCH_LUNA_BLOG_API_KEY="$OPENCODE_GO_API_KEY"
export AIRESEARCH_LUNA_BLOG_PROXY="${OPENCODE_GO_PROXY:-}"

FACT_RETRY_LIST="$RUN_DIR/fact-retry-missing-type.txt"
FACT_RETRY_MAP="$RUN_DIR/fact-retry-required-types.txt"
PYTHONPATH="$PYTHONPATH" "$PYTHON" - "$DB" "$RUN_DIR/papers.txt" \
  "$FACT_RETRY_LIST" "$FACT_RETRY_MAP" <<'PY'
import sqlite3
import sys
from pathlib import Path

db_path, list_path, retry_list_path, retry_map_path = map(Path, sys.argv[1:])
keys = [
    line.split("#", 1)[0].strip()
    for line in list_path.read_text(encoding="utf-8").splitlines()
    if line.split("#", 1)[0].strip()
]
required = {"benchmark", "claim", "dataset", "limitation", "method"}
missing = {}
with sqlite3.connect(db_path) as conn:
    for key in keys:
        present = {
            str(row[0])
            for row in conn.execute(
                "select distinct fact_type from research_facts where paper_key = ?", (key,)
            )
        }
        if required - present:
            missing[key] = sorted(required - present)
retry_list_path.write_text(
    "".join(f"{key}\n" for key in missing), encoding="utf-8"
)
retry_map_path.write_text(
    "".join(f"{key}={','.join(types)}\n" for key, types in missing.items()),
    encoding="utf-8",
)
print(f"fact_refresh_required={len(missing)}")
PY

if [[ -s "$FACT_RETRY_LIST" ]]; then
  for attempt in 1 2 3; do
    if PYTHONPATH="$PYTHONPATH" "$PYTHON" -m airesearch.cli --db "$DB" \
      extract-research-facts --provider openai-compatible \
      --paper-list "$FACT_RETRY_LIST" \
      --required-fact-types-file "$FACT_RETRY_MAP" \
      --model "$AIRESEARCH_FACT_MODEL" --base-url "$AIRESEARCH_FACT_BASE_URL" \
      --api-key-env AIRESEARCH_FACT_API_KEY --refresh-cache \
      --max-input-chars 24000 --concurrency 4 --fact-error-policy strict \
      > "$RUN_DIR/fact-retry-required-types.json"; then
      break
    fi
    if [[ "$attempt" == 3 ]]; then
      echo "fact retry failed after $attempt attempts" >&2
      exit 2
    fi
    echo "fact retry attempt $attempt failed; retrying" >&2
    sleep 5
  done
else
  printf '{"paper_count":0,"status":"skipped","reason":"fact coverage complete"}\n' \
    > "$RUN_DIR/fact-retry-required-types.json"
fi

PYTHONPATH="$PYTHONPATH" "$PYTHON" - "$DB" "$RUN_DIR/papers.txt" <<'PY'
import sqlite3, sys
from pathlib import Path
db_path, list_path = Path(sys.argv[1]), Path(sys.argv[2])
required = {"benchmark", "claim", "dataset", "limitation", "method"}
keys = [line.strip() for line in list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
with sqlite3.connect(db_path) as conn:
    missing = {}
    for key in keys:
        types = {row[0] for row in conn.execute("select distinct fact_type from research_facts where paper_key=?", (key,))}
        if required - types:
            missing[key] = sorted(required - types)
if missing:
    raise SystemExit(f"strict fact coverage failed: {missing}")
print(f"strict_fact_coverage=ok papers={len(keys)}")
PY

if [[ -f "$RUN_DIR/manifest.json" ]]; then
  PYTHONPATH="$PYTHONPATH" "$PYTHON" - "$DB" "$RUN_DIR" "$RUN_DIR/papers.txt" <<'PY'
import sys
from pathlib import Path

from airesearch.blog_batch import validate_backup_manifest

db_path, run_dir, list_path = map(Path, sys.argv[1:])
keys = [
    line.split("#", 1)[0].strip()
    for line in list_path.read_text(encoding="utf-8").splitlines()
    if line.split("#", 1)[0].strip()
]
manifest = validate_backup_manifest(db_path, run_dir, keys)
print(f"backup=reused backup_id={manifest['backup_id']}")
PY
else
  PYTHONPATH="$PYTHONPATH" "$PYTHON" "$ROOT/airesearch/scripts/generate_deep_readings.py" \
    backup --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR"
fi

if PYTHONPATH="$PYTHONPATH" "$PYTHON" - "$DB" "$RUN_DIR/preflight.json" \
  "$RUN_DIR/papers.txt" <<'PY'
import json
import sys
from pathlib import Path

from airesearch.paper_blog import build_blog_evidence_pack

db_path, report_path, list_path = map(Path, sys.argv[1:])
if not report_path.is_file():
    raise SystemExit(1)
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
keys = [
    line.split("#", 1)[0].strip()
    for line in list_path.read_text(encoding="utf-8").splitlines()
    if line.split("#", 1)[0].strip()
]
report_keys = [
    str(row.get("paper_key") or "")
    for row in report.get("papers", [])
    if isinstance(row, dict)
]
report_hashes = {
    str(row.get("paper_key") or ""): str(row.get("source_hash") or "")
    for row in report.get("papers", [])
    if isinstance(row, dict)
}
valid = (
    report.get("status") == "completed"
    and report.get("paper_count") == len(keys)
    and report.get("ready_count") == len(keys)
    and report_keys == keys
    and all(
        report_hashes.get(key) == build_blog_evidence_pack(db_path, key).source_hash
        for key in keys
    )
)
raise SystemExit(0 if valid else 1)
PY
then
  echo "preflight=reused papers=40"
else
  PYTHONPATH="$PYTHONPATH" "$PYTHON" "$ROOT/airesearch/scripts/generate_deep_readings.py" \
    preflight --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR"
fi

PYTHONPATH="$PYTHONPATH" "$PYTHON" - "$DB" "$RUN_DIR" "$RUN_DIR/papers.txt" <<'PY'
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

db_path, run_dir, list_path = map(Path, sys.argv[1:])
pointer = run_dir / "original-current.json"
if not pointer.is_file():
    raise SystemExit(0)
keys = [
    line.split("#", 1)[0].strip()
    for line in list_path.read_text(encoding="utf-8").splitlines()
    if line.split("#", 1)[0].strip()
]
sample_keys = keys[:2]
try:
    value = json.loads(pointer.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    value = None
manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
valid = (
    isinstance(value, dict)
    and str(value.get("database_path") or "") == str(db_path.resolve())
    and value.get("paper_keys") == sample_keys
    and set(value.get("current_version_ids") or {}) == set(sample_keys)
    and str(value.get("backup_id") or "") == str(manifest.get("backup_id") or "")
)
if not valid:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = run_dir / "stale-run-artifacts" / stamp
    archive.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pointer), str(archive / pointer.name))
    print(f"original_current=archived path={archive / pointer.name}")
PY

PYTHONPATH="$PYTHONPATH" "$PYTHON" "$ROOT/airesearch/scripts/generate_deep_readings.py" \
  ab --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR" --target-chars 5000

MODEL_ARM="$(jq -r .model_arm "$RUN_DIR/winner.json")"
case "$MODEL_ARM" in
  deepseek|luna) ;;
  *) echo "invalid winner model arm: $MODEL_ARM" >&2; exit 2 ;;
esac

PYTHONPATH="$PYTHONPATH" "$PYTHON" "$ROOT/airesearch/scripts/generate_deep_readings.py" \
  batch --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR" \
  --model-arm "$MODEL_ARM" --target-chars 5000 --concurrency 4

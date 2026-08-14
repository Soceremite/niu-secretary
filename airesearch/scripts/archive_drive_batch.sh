#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  airesearch/scripts/archive_drive_batch.sh status
  airesearch/scripts/archive_drive_batch.sh plan
  airesearch/scripts/archive_drive_batch.sh upload
  airesearch/scripts/archive_drive_batch.sh verify
  airesearch/scripts/archive_drive_batch.sh upload-verify

Environment overrides:
  AIRESEARCH_ARCHIVE_REMOTE   default: gdrive:niu-secretary/airesearch/v1
  AIRESEARCH_RCLONE           default: rclone
  AIRESEARCH_ARCHIVE_STAGING  default: <repo>/airesearch/data/archive-staging
  CHUNK_SIZE                  default: 20
  CONCURRENCY                 default: 2
  LIMIT                       optional max paper count for this run

This script never runs archive evict and never deletes local paper files.
EOF
}

MODE="${1:-}"
if [[ -z "$MODE" || "$MODE" == "-h" || "$MODE" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
AIRESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$AIRESEARCH_DIR/.." && pwd)"
LOG_DIR="$AIRESEARCH_DIR/data/archive-logs"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$LOG_DIR"

export AIRESEARCH_ARCHIVE_REMOTE="${AIRESEARCH_ARCHIVE_REMOTE:-gdrive:niu-secretary/airesearch/v1}"
export AIRESEARCH_RCLONE="${AIRESEARCH_RCLONE:-rclone}"
export AIRESEARCH_ARCHIVE_STAGING="${AIRESEARCH_ARCHIVE_STAGING:-$AIRESEARCH_DIR/data/archive-staging}"
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

CHUNK_SIZE="${CHUNK_SIZE:-20}"
CONCURRENCY="${CONCURRENCY:-2}"
LIMIT="${LIMIT:-}"

cd "$AIRESEARCH_DIR"

PYTHON="$AIRESEARCH_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "error=missing_python_venv path=$PYTHON" >&2
  exit 2
fi

if [[ -z "$AIRESEARCH_ARCHIVE_REMOTE" ]]; then
  echo "error=archive_remote_not_configured" >&2
  exit 2
fi

if ! command -v "$AIRESEARCH_RCLONE" >/dev/null 2>&1; then
  echo "error=rclone_not_found executable=$AIRESEARCH_RCLONE" >&2
  exit 2
fi

if ! [[ "$CHUNK_SIZE" =~ ^[0-9]+$ ]] || (( CHUNK_SIZE < 1 )); then
  echo "error=invalid_chunk_size value=$CHUNK_SIZE" >&2
  exit 2
fi

if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]] || (( CONCURRENCY < 1 )); then
  echo "error=invalid_concurrency value=$CONCURRENCY" >&2
  exit 2
fi

if [[ -n "$LIMIT" ]] && { ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || (( LIMIT < 1 )); }; then
  echo "error=invalid_limit value=$LIMIT" >&2
  exit 2
fi

run_archive() {
  "$PYTHON" -m airesearch.cli archive "$@"
}

print_db_status() {
  "$PYTHON" - <<'PY'
from pathlib import Path
import sqlite3

db = Path("data/airesearch.sqlite3")
if not db.exists():
    print("records=0")
    raise SystemExit

with sqlite3.connect(db) as conn:
    rows = conn.execute(
        "select status, count(*) from paper_archives group by status order by status"
    ).fetchall()
    total = sum(count for _, count in rows)
    for status, count in rows:
        print(f"{status}={count}")
    print(f"records={total}")
PY
}

write_plan_keys() {
  local plan_log="$1"
  local keys_file="$2"

  run_archive plan | tee "$plan_log" >/dev/null
  awk '/^paper_key=/ && / status=eligible / { sub(/^paper_key=/,"",$1); print $1 }' \
    "$plan_log" > "$keys_file"

  if [[ -n "$LIMIT" ]]; then
    local limited="$keys_file.limit"
    head -n "$LIMIT" "$keys_file" > "$limited"
    mv "$limited" "$keys_file"
  fi
}

filter_upload_keys() {
  local input_file="$1"
  local output_file="$2"

  "$PYTHON" - "$input_file" "$output_file" <<'PY'
from pathlib import Path
import sqlite3
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
keys = [line.strip() for line in source.read_text().splitlines() if line.strip()]

skip_statuses = {"verified", "evicted", "available"}
skip = set()
db = Path("data/airesearch.sqlite3")
if db.exists() and keys:
    placeholders = ",".join("?" for _ in keys)
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            f"select paper_key, status from paper_archives where paper_key in ({placeholders})",
            keys,
        ).fetchall()
    skip = {paper_key for paper_key, status in rows if status in skip_statuses}

selected = [key for key in keys if key not in skip]
target.write_text("\n".join(selected) + ("\n" if selected else ""))
PY
}

write_verify_keys() {
  local output_file="$1"

  "$PYTHON" - "$output_file" <<'PY'
from pathlib import Path
import os
import sqlite3
import sys

target = Path(sys.argv[1])
db = Path("data/airesearch.sqlite3")
if not db.exists():
    target.write_text("")
    raise SystemExit

with sqlite3.connect(db) as conn:
    rows = conn.execute(
        """
        select paper_key
        from paper_archives
        where status in ('uploaded', 'available')
        order by paper_key
        """
    ).fetchall()

keys = [row[0] for row in rows]
limit = os.environ.get("LIMIT", "")
if limit:
    keys = keys[: int(limit)]
target.write_text("\n".join(keys) + ("\n" if keys else ""))
PY
}

run_chunked() {
  local action="$1"
  local keys_file="$2"
  local log_file="$3"
  local total
  total="$(wc -l < "$keys_file" | tr -d ' ')"

  echo "action=$action keys=$keys_file total=$total concurrency=$CONCURRENCY chunk_size=$CHUNK_SIZE log=$log_file"
  if (( total == 0 )); then
    echo "action=$action status=no_keys" | tee -a "$log_file"
    return 0
  fi

  local chunk=0
  while mapfile -t -n "$CHUNK_SIZE" batch && ((${#batch[@]})); do
    chunk=$((chunk + 1))
    printf '%s_chunk=%03d size=%d started=%s\n' \
      "$action" "$chunk" "${#batch[@]}" "$(date -Is)" | tee -a "$log_file"

    local args=()
    local key
    for key in "${batch[@]}"; do
      [[ -n "$key" ]] && args+=(--paper-key "$key")
    done

    run_archive "$action" --concurrency "$CONCURRENCY" "${args[@]}" 2>&1 | tee -a "$log_file"

    printf '%s_chunk=%03d completed=%s\n' \
      "$action" "$chunk" "$(date -Is)" | tee -a "$log_file"
  done < "$keys_file"

  printf '%s_completed=%s total=%d\n' "$action" "$(date -Is)" "$total" | tee -a "$log_file"
}

case "$MODE" in
  status)
    echo "remote=$AIRESEARCH_ARCHIVE_REMOTE"
    print_db_status
    ;;
  plan)
    PLAN_LOG="$LOG_DIR/archive-plan-$TS.log"
    KEYS_FILE="$LOG_DIR/archive-plan-keys-$TS.txt"
    write_plan_keys "$PLAN_LOG" "$KEYS_FILE"
    echo "plan_log=$PLAN_LOG"
    echo "keys_file=$KEYS_FILE"
    echo "eligible_keys=$(wc -l < "$KEYS_FILE" | tr -d ' ')"
    ;;
  upload)
    PLAN_LOG="$LOG_DIR/archive-upload-plan-$TS.log"
    ALL_KEYS="$LOG_DIR/archive-upload-all-keys-$TS.txt"
    KEYS_FILE="$LOG_DIR/archive-upload-keys-$TS.txt"
    UPLOAD_LOG="$LOG_DIR/archive-upload-$TS.log"
    write_plan_keys "$PLAN_LOG" "$ALL_KEYS"
    filter_upload_keys "$ALL_KEYS" "$KEYS_FILE"
    echo "plan_log=$PLAN_LOG"
    run_chunked upload "$KEYS_FILE" "$UPLOAD_LOG"
    ;;
  verify)
    KEYS_FILE="$LOG_DIR/archive-verify-keys-$TS.txt"
    VERIFY_LOG="$LOG_DIR/archive-verify-$TS.log"
    write_verify_keys "$KEYS_FILE"
    run_chunked verify "$KEYS_FILE" "$VERIFY_LOG"
    ;;
  upload-verify)
    "$SCRIPT_PATH" upload
    "$SCRIPT_PATH" verify
    ;;
  *)
    usage
    exit 2
    ;;
esac

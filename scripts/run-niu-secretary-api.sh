#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT=/home/ubuntu/vibe_proj/niu-secretary
ENV_FILE="$ROOT/airesearch/.env"

test -r "$ENV_FILE" || {
  echo "missing AIResearch environment file: $ENV_FILE" >&2
  exit 78
}

# systemd loads administrator authentication from /etc/niu-secretary-api.env.
# Keep those values authoritative even if the project AI environment contains
# an accidental same-named variable.
_niu_admin_user_set="${NIU_SECRETARY_ADMIN_USER+x}"
_niu_admin_user="${NIU_SECRETARY_ADMIN_USER-}"
_niu_admin_password_set="${NIU_SECRETARY_ADMIN_PASSWORD+x}"
_niu_admin_password="${NIU_SECRETARY_ADMIN_PASSWORD-}"
_niu_admin_password_sha256_set="${NIU_SECRETARY_ADMIN_PASSWORD_SHA256+x}"
_niu_admin_password_sha256="${NIU_SECRETARY_ADMIN_PASSWORD_SHA256-}"
_niu_admin_session_secret_set="${NIU_SECRETARY_ADMIN_SESSION_SECRET+x}"
_niu_admin_session_secret="${NIU_SECRETARY_ADMIN_SESSION_SECRET-}"

# systemd loads administrator authentication from /etc/niu-secretary-api.env.
# Keep those values authoritative even if the project AI environment contains
# an accidental same-named variable.
# Unified gateway key also comes from config/.env (loaded after airesearch/.env
# so it wins); both are needed by niu_core.llm_client.
set -a
source "$ROOT/config/.env"
source "$ENV_FILE"
set +a
if [[ "$_niu_admin_user_set" == x ]]; then
  export NIU_SECRETARY_ADMIN_USER="$_niu_admin_user"
else
  unset NIU_SECRETARY_ADMIN_USER
fi
if [[ "$_niu_admin_password_set" == x ]]; then
  export NIU_SECRETARY_ADMIN_PASSWORD="$_niu_admin_password"
else
  unset NIU_SECRETARY_ADMIN_PASSWORD
fi
if [[ "$_niu_admin_password_sha256_set" == x ]]; then
  export NIU_SECRETARY_ADMIN_PASSWORD_SHA256="$_niu_admin_password_sha256"
else
  unset NIU_SECRETARY_ADMIN_PASSWORD_SHA256
fi
if [[ "$_niu_admin_session_secret_set" == x ]]; then
  export NIU_SECRETARY_ADMIN_SESSION_SECRET="$_niu_admin_session_secret"
else
  unset NIU_SECRETARY_ADMIN_SESSION_SECRET
fi

: "${OPENCODE_GO_BASE_URL:?OPENCODE_GO_BASE_URL is required in $ENV_FILE}"
: "${OPENCODE_GO_API_KEY:?OPENCODE_GO_API_KEY is required in $ENV_FILE}"

exec /usr/bin/python3 "$ROOT/server/niu_secretary_api.py"

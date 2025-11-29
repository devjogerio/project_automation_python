#!/usr/bin/env bash
set -euo pipefail

echo "Helper to set GH Actions secrets using gh CLI. Requires gh to be authenticated."

usage() {
  cat <<'USAGE'
Usage:
  # Set private key secret from file
  ./scripts/set_github_secrets.sh set-ssh-key path/to/private_key

  # Set string secrets
  ./scripts/set_github_secrets.sh set secret_name secret_value

Examples:
  ./scripts/set_github_secrets.sh set-ssh-key deploy_key_rsa
  ./scripts/set_github_secrets.sh set SSH_USER deploy
  ./scripts/set_github_secrets.sh set SSH_HOST example.com
  ./scripts/set_github_secrets.sh set SSH_PATH /var/www/static/openapi
  ./scripts/set_github_secrets.sh set DEPLOY_DOCS_SERVER true
USAGE
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

cmd=$1
shift

case "$cmd" in
  set-ssh-key)
    file=${1:-}
    if [ ! -f "$file" ]; then
      echo "File not found: $file" >&2
      exit 2
    fi
    gh secret set SSH_PRIVATE_KEY --body "$(cat "$file")"
    echo "Set SSH_PRIVATE_KEY secret."
    ;;
  set)
    name=${1:-}
    value=${2:-}
    if [ -z "$name" ] || [ -z "$value" ]; then
      usage
      exit 1
    fi
    gh secret set "$name" --body "$value"
    echo "Set secret $name"
    ;;
  *)
    usage
    exit 1
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail

# Test script to simulate or perform an rsync deploy of docs/
# Usage:
#  - Local simulation (copy to local dir):
#      DEST=./_deploy_sim ./scripts/test_deploy_rsync.sh
#  - Remote real deploy (requires SSH key already available or in agent):
#      SSH_USER=deploy SSH_HOST=host.example.com SSH_PATH=/var/www/docs ./scripts/test_deploy_rsync.sh

DEST=${DEST:-}
SSH_USER=${SSH_USER:-}
SSH_HOST=${SSH_HOST:-}
SSH_PATH=${SSH_PATH:-}

if [ -n "$DEST" ]; then
  echo "Simulating deploy to local path: $DEST"
  mkdir -p "$DEST"
  rsync -av --delete docs/ "$DEST/"
  echo "Files copied to $DEST (simulation)"
  exit 0
fi

if [ -n "$SSH_USER" ] && [ -n "$SSH_HOST" ] && [ -n "$SSH_PATH" ]; then
  echo "Attempting real deployment to ${SSH_USER}@${SSH_HOST}:${SSH_PATH}"
  rsync -avz --delete docs/ "${SSH_USER}@${SSH_HOST}:${SSH_PATH}"
  echo "Remote deploy finished."
  exit 0
fi

echo "No DEST or SSH_* variables provided. Nothing to do."
echo "Examples:"
echo "  DEST=./_deploy_sim ./scripts/test_deploy_rsync.sh"
echo "  SSH_USER=deploy SSH_HOST=1.2.3.4 SSH_PATH=/var/www/docs ./scripts/test_deploy_rsync.sh"
exit 2

#!/usr/bin/env bash
# DOMAIN-01 D-01f: guard against the DELETED Render backend host reappearing.
# The service `content-backend-flmx.onrender.com` was removed; any reference to it
# is a dead link. Use content-jumpstart.com (or an env-driven base) instead.
set -uo pipefail

DEAD_HOST='content-backend-flmx'

# Scope: runtime code, config and scripts. Docs (*.md) are excluded — stale-doc
# cleanup is the separate, lower-priority DOMAIN-01 D-01g item. This guard itself
# names the pattern, so it is excluded too.
if git grep -nI "$DEAD_HOST" -- . \
    ':(exclude)*.md' \
    ':(exclude)scripts/check-no-dead-host.sh'; then
  echo ""
  echo "ERROR: reference to the DELETED Render host 'content-backend-flmx.onrender.com' found (DOMAIN-01)."
  echo "       That service no longer exists. Use https://content-jumpstart.com or an env-driven base URL."
  exit 1
fi
exit 0

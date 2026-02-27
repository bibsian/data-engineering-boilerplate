#!/usr/bin/env bash
# .wt/hooks/on-delete.sh
# Called by 'wt delete' before the namespace and git worktree are removed.
# Env vars: WT_NAME  WT_BRANCH  WT_NAMESPACE  WT_PATH  WT_REPO_ROOT
set -euo pipefail

# shellcheck source=../.wt/config.sh
source "$WT_REPO_ROOT/.wt/config.sh"

echo "==> Uninstalling Helm release: $WT_NAME..."
if helm status "$WT_NAME" --namespace "$WT_NAMESPACE" &>/dev/null; then
  helm uninstall "$WT_NAME" --namespace "$WT_NAMESPACE" >&2
else
  echo "  Release $WT_NAME not found in $WT_NAMESPACE — skipping." >&2
fi

if [[ -n "${TEMPLATE_DB:-}" ]]; then
  echo "==> Dropping database: $WT_NAME..."
  kubectl exec -n "$INFRA_NAMESPACE" "$PG_POD" -- \
    psql -U "$PG_USER" -c "DROP DATABASE IF EXISTS \"${WT_NAME}\";" >&2
fi

echo "==> Cleanup complete for $WT_NAME"

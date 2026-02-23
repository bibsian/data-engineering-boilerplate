#!/usr/bin/env bash
# .wt/hooks/on-status.sh
# Called by 'wt list'.
#   --header  : print tab-separated column headers to stdout
#   (no args) : print tab-separated status values for WT_NAMESPACE
# Env vars: WT_NAME  WT_BRANCH  WT_NAMESPACE  WT_PATH  WT_REPO_ROOT
set -euo pipefail

# shellcheck source=../.wt/config.sh
source "$WT_REPO_ROOT/.wt/config.sh"

if [[ "${1:-}" == "--header" ]]; then
  header="NAME\tSTATUS"
  for svc in "${INFRA_SERVICES[@]+"${INFRA_SERVICES[@]}"}"; do
    header+="\t$(printf '%s' "$svc" | tr '[:lower:]' '[:upper:]')"
  done
  header+="\tSENSORS"
  printf '%b\n' "$header"
  exit 0
fi

# NAME
row="$WT_NAME"

# STATUS (namespace phase)
ns_status="$(kubectl get namespace "$WT_NAMESPACE" \
  --no-headers -o custom-columns=S:.status.phase 2>/dev/null || printf 'Missing')"
row+="\t${ns_status}"

# Per-service pod status
for svc in "${INFRA_SERVICES[@]+"${INFRA_SERVICES[@]}"}"; do
  pod_line="$(kubectl get pods \
    -n "$INFRA_NAMESPACE" -l "app=${svc}" \
    --no-headers 2>/dev/null | head -1 || true)"
  if [[ -z "$pod_line" ]]; then
    svc_status="Missing"
  elif printf '%s' "$pod_line" | grep -q "Running"; then
    svc_status="Running"
  else
    svc_status="NotReady"
  fi
  row+="\t${svc_status}"
done

# SENSORS (Running/Total pods with label type=sensor)
total="$(kubectl get pods -n "$WT_NAMESPACE" -l type=sensor \
  --no-headers 2>/dev/null | wc -l | tr -d ' ' || printf '0')"
running="$(kubectl get pods -n "$WT_NAMESPACE" -l type=sensor \
  --no-headers 2>/dev/null | grep -c "Running" || printf '0')"
row+="\t${running}/${total}"

printf '%b\n' "$row"

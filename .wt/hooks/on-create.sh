#!/usr/bin/env bash
# .wt/hooks/on-create.sh
# Called by 'wt create' after the git worktree and k8s namespace are created.
# Env vars: WT_NAME  WT_BRANCH  WT_NAMESPACE  WT_PATH  WT_REPO_ROOT
set -euo pipefail

# shellcheck source=../.wt/config.sh
source "$WT_REPO_ROOT/.wt/config.sh"

echo "==> Building and importing Docker images..."
for entry in "${SERVICES[@]+"${SERVICES[@]}"}"; do
  image_name="${entry%%:*}"
  dockerfile="${entry#*:}"
  tag="${image_name}:${WT_NAME}"
  echo "  Building $tag from $dockerfile..." >&2
  docker build -t "$tag" -f "$WT_REPO_ROOT/$dockerfile" "$WT_REPO_ROOT" >&2
  echo "  Importing $tag into k3d cluster $CLUSTER_NAME..." >&2
  k3d image import "$tag" -c "$CLUSTER_NAME" >&2
done

if [[ -n "${TEMPLATE_DB:-}" ]]; then
  echo "==> Cloning database: $TEMPLATE_DB → $WT_NAME..."
  kubectl exec -n "$INFRA_NAMESPACE" "$PG_POD" -- \
    createdb -U "$PG_USER" "$WT_NAME" >&2
  kubectl exec -n "$INFRA_NAMESPACE" "$PG_POD" -- \
    pg_dump -U "$PG_USER" --no-owner --no-acl "$TEMPLATE_DB" \
  | kubectl exec -i -n "$INFRA_NAMESPACE" "$PG_POD" -- \
    psql -U "$PG_USER" -d "$WT_NAME" -q >&2
fi

echo "==> Installing Helm chart: $HELM_CHART..."
helm install "$WT_NAME" "$WT_REPO_ROOT/$HELM_CHART" \
  --namespace "$WT_NAMESPACE" \
  --set "worktreeName=$WT_NAME" \
  --set "branch=$WT_BRANCH" \
  --set "dbName=$WT_NAME" \
  --set "infraNamespace=$INFRA_NAMESPACE" >&2

echo "==> Waiting for deployments to be ready (timeout: 5m)..."
kubectl wait --for=condition=available \
  --timeout=300s \
  deployment --all \
  -n "$WT_NAMESPACE" >&2 || {
  echo "Warning: some deployments did not become ready within 5 minutes." >&2
  kubectl get pods -n "$WT_NAMESPACE" >&2
}

echo "==> Worktree $WT_NAME is ready in namespace $WT_NAMESPACE"

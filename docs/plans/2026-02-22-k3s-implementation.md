# k3s Worktree Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `scripts/wt` with k3d/k8s namespace isolation and hook support, then convert the docker-compose project to k8s infra manifests + a per-worktree Helm chart.

**Architecture:** Single-file bash extension (`scripts/wt`) gated on `.wt/` existence for backwards compatibility; generic config-driven hooks read `.wt/config.sh`; static `k8s/infra/` manifests for shared infra; `charts/worktree/` Helm chart for per-worktree sensor deployments.

**Tech Stack:** bash, kubectl, k3d, helm, docker, git, Kubernetes YAML, Helm templates

---

## Task 1: Add `wt_sanitize` helper + test

**Files:**
- Modify: `scripts/wt` (add helper function near top, before `wt_create`)
- Create: `scripts/test_wt_sanitize.sh`

**Step 1: Create the test script**

```bash
#!/usr/bin/env bash
# scripts/test_wt_sanitize.sh — unit tests for wt_sanitize
set -euo pipefail

# Extract just the wt_sanitize function from scripts/wt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

wt_sanitize() {
  local branch="$1"
  printf '%s' "$branch" \
    | tr '[:upper:]' '[:lower:]' \
    | tr '/_ ' '-' \
    | tr -cd 'a-z0-9-' \
    | sed 's/--\+/-/g' \
    | sed 's/^-\+//;s/-\+$//'
}

pass=0; fail=0
assert_eq() {
  local got="$1" expected="$2" desc="$3"
  if [[ "$got" == "$expected" ]]; then
    echo "PASS: $desc"; (( pass++ )) || true
  else
    echo "FAIL: $desc — expected '$expected', got '$got'" >&2; (( fail++ )) || true
  fi
}

assert_eq "$(wt_sanitize 'earl/FIB-123')"            "earl-fib-123"       "slash + uppercase"
assert_eq "$(wt_sanitize 'my_feature')"              "my-feature"         "underscore"
assert_eq "$(wt_sanitize 'UPPER-CASE')"              "upper-case"         "uppercase only"
assert_eq "$(wt_sanitize 'a--b')"                    "a-b"                "collapse dashes"
assert_eq "$(wt_sanitize '-leading-trailing-')"      "leading-trailing"   "strip leading/trailing dashes"
assert_eq "$(wt_sanitize 'team/PROJ-999/my-thing')"  "team-proj-999-my-thing" "multiple slashes"
assert_eq "$(wt_sanitize 'simple')"                  "simple"             "passthrough"

echo ""
echo "Results: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]
```

**Step 2: Run it to verify it passes** (the logic is self-contained in the test)

```bash
bash scripts/test_wt_sanitize.sh
```

Expected: `7 passed, 0 failed`

**Step 3: Add `wt_sanitize` to `scripts/wt`**

Insert after line 14 (after the `WORKTREES_DIR` assignment), before the `usage()` function:

```bash
# Sanitize a git branch name for use as a k8s name segment.
# earl/FIB-123 → earl-fib-123
wt_sanitize() {
  local branch="$1"
  printf '%s' "$branch" \
    | tr '[:upper:]' '[:lower:]' \
    | tr '/_ ' '-' \
    | tr -cd 'a-z0-9-' \
    | sed 's/--\+/-/g' \
    | sed 's/^-\+//;s/-\+$//'
}
```

Also update the `usage()` heredoc to add the `init` line:

```
  init                     Scaffold .wt/ config and hooks for this project
```

And add `init)   wt_init ;;` to the `case` dispatch at the bottom.

**Step 4: Commit**

```bash
git add scripts/wt scripts/test_wt_sanitize.sh
git commit -m "feat: add wt_sanitize helper and test script"
```

---

## Task 2: Add `wt_init` command

**Files:**
- Modify: `scripts/wt` (add `wt_init` function)

**Step 1: Add `wt_init` function** to `scripts/wt`, before the `cmd` dispatch at the bottom. This function writes the hook files using single-quoted heredocs (so `$VARS` appear literally in the written files):

```bash
wt_init() {
  local wt_dir="$REPO_ROOT/.wt"
  if [[ -d "$wt_dir" ]]; then
    echo "Error: .wt/ already exists at $wt_dir" >&2
    echo "  Delete it first or edit the files directly." >&2
    exit 1
  fi
  mkdir -p "$wt_dir/hooks"
  echo "Initializing .wt/ in $REPO_ROOT" >&2

  # ── config.sh ────────────────────────────────────────────────────────────
  cat > "$wt_dir/config.sh" <<'CONFIG_EOF'
#!/usr/bin/env bash
# .wt/config.sh — per-project wt configuration
# Edit this file. All variables have sensible defaults.

# k3d cluster name
CLUSTER_NAME="dev-cluster"

# Prefix for k8s namespace names (result: <prefix>-<sanitized-branch>)
NAMESPACE_PREFIX="wt"

# Namespace where shared infra services run
INFRA_NAMESPACE="infra"

# Services to build and import into k3d.
# Format: "image-name:path/to/Dockerfile"  (path relative to repo root)
SERVICES=()

# Postgres StatefulSet pod name in INFRA_NAMESPACE (for DB cloning)
PG_POD="postgres-0"
PG_USER="postgres"

# Template database to clone for each worktree (leave empty to skip DB clone)
TEMPLATE_DB=""

# Helm chart path relative to repo root
HELM_CHART="charts/worktree"

# Infra service names shown in 'wt list' (used as -l app=<name> label selectors)
INFRA_SERVICES=()
CONFIG_EOF

  # ── on-create.sh ─────────────────────────────────────────────────────────
  cat > "$wt_dir/hooks/on-create.sh" <<'ON_CREATE_EOF'
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
ON_CREATE_EOF

  # ── on-delete.sh ─────────────────────────────────────────────────────────
  cat > "$wt_dir/hooks/on-delete.sh" <<'ON_DELETE_EOF'
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
ON_DELETE_EOF

  # ── on-status.sh ─────────────────────────────────────────────────────────
  cat > "$wt_dir/hooks/on-status.sh" <<'ON_STATUS_EOF'
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
ON_STATUS_EOF

  chmod +x "$wt_dir/hooks/on-create.sh" \
           "$wt_dir/hooks/on-delete.sh" \
           "$wt_dir/hooks/on-status.sh"

  echo "Created:"
  echo "  $wt_dir/config.sh"
  echo "  $wt_dir/hooks/on-create.sh"
  echo "  $wt_dir/hooks/on-delete.sh"
  echo "  $wt_dir/hooks/on-status.sh"
  echo ""
  echo "Next: edit $wt_dir/config.sh for your project, then run 'wt create <branch>'"
}
```

**Step 2: Smoke-test `wt init` in a temp dir**

```bash
tmpdir="$(mktemp -d)"
git -C "$tmpdir" init -q
git -C "$tmpdir" commit --allow-empty -m "init"
# Override REPO_ROOT for the test
REPO_ROOT="$tmpdir" bash scripts/wt init
ls "$tmpdir/.wt/hooks/"
rm -rf "$tmpdir"
```

Expected: `on-create.sh  on-delete.sh  on-status.sh`

**Step 3: Commit**

```bash
git add scripts/wt
git commit -m "feat: add wt init command — scaffolds .wt/ config and hooks"
```

---

## Task 3: Extend `wt_create` with k8s namespace + hook execution

**Files:**
- Modify: `scripts/wt` — `wt_create` function

**Step 1: Replace `wt_create` with the extended version**

Find the existing `wt_create` function (lines 37–88). Replace the body so the k8s/hook block is inserted between the git worktree creation and the `--go` block:

```bash
wt_create() {
  local go_flag=0 branch="" arg

  for arg in "$@"; do
    if [[ "$arg" == "--go" ]]; then
      go_flag=1
    elif [[ -z "$branch" ]]; then
      branch="$arg"
    else
      echo "wt create: unexpected argument: $arg" >&2; exit 1
    fi
  done

  if [[ -z "$branch" ]]; then
    echo "Usage: wt create <branch> [--go]" >&2; exit 1
  fi

  local dest="$WORKTREES_DIR/$branch"
  if [[ -d "$dest" ]]; then
    echo "Error: worktree already exists at $dest" >&2; exit 1
  fi

  mkdir -p "$(dirname "$dest")"

  if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
    git -C "$REPO_ROOT" worktree add "$dest" "$branch" >&2
  elif git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$branch" 2>/dev/null; then
    git -C "$REPO_ROOT" worktree add "$dest" -b "$branch" "origin/$branch" >&2
  else
    git -C "$REPO_ROOT" worktree add -b "$branch" "$dest" >&2
  fi

  # ── k8s/hook integration ────────────────────────────────────────────────
  local wt_config="$REPO_ROOT/.wt/config.sh"
  if [[ -f "$wt_config" ]]; then
    local wt_name wt_namespace
    wt_name="$(wt_sanitize "$branch")"

    # Source config to pick up NAMESPACE_PREFIX (and other vars for the hook)
    # shellcheck source=.wt/config.sh
    source "$wt_config"
    local ns_prefix="${NAMESPACE_PREFIX:-wt}"
    wt_namespace="${ns_prefix}-${wt_name}"

    echo "Creating k8s namespace: $wt_namespace" >&2
    kubectl create namespace "$wt_namespace" \
      --dry-run=client -o yaml | kubectl apply -f - >&2

    local on_create="$REPO_ROOT/.wt/hooks/on-create.sh"
    if [[ -f "$on_create" ]]; then
      export WT_NAME="$wt_name"
      export WT_BRANCH="$branch"
      export WT_NAMESPACE="$wt_namespace"
      export WT_PATH="$dest"
      export WT_REPO_ROOT="$REPO_ROOT"
      echo "Running on-create hook..." >&2
      if ! bash "$on_create"; then
        echo "Error: on-create hook failed — aborting." >&2
        exit 1
      fi
    fi
  fi
  # ────────────────────────────────────────────────────────────────────────

  if [[ "$go_flag" == 1 ]]; then
    if ! command -v claude &>/dev/null; then
      echo "wt create: --go requires 'claude' on PATH (not found)" >&2
      echo "Worktree created at: $dest" >&2
      exit 1
    fi
    printf 'EVAL:cd %s && claude\n' "$(printf '%q' "$dest")"
  else
    echo "Created worktree: $dest"
    echo "  Branch: $branch"
    echo "  Run: wt switch $branch"
  fi
}
```

**Step 2: Verify no regressions — create a plain worktree (no .wt/)**

```bash
wt create test-no-k8s
```

Expected: normal git worktree creation, no kubectl calls.

**Step 3: Commit**

```bash
git add scripts/wt
git commit -m "feat: wt create — add k8s namespace creation and on-create hook"
```

---

## Task 4: Extend `wt_list` with formatted table

**Files:**
- Modify: `scripts/wt` — replace `wt_list` function

**Step 1: Replace `wt_list`**

```bash
wt_list() {
  local on_status="$REPO_ROOT/.wt/hooks/on-status.sh"

  # Fall back to plain git output when no hook is present
  if [[ ! -f "$on_status" ]]; then
    git -C "$REPO_ROOT" worktree list
    return 0
  fi

  # Source config for NAMESPACE_PREFIX
  local wt_config="$REPO_ROOT/.wt/config.sh"
  [[ -f "$wt_config" ]] && source "$wt_config"
  local ns_prefix="${NAMESPACE_PREFIX:-wt}"

  # Get header row from hook
  local header
  header="$(bash "$on_status" --header)"

  # Parse 'git worktree list --porcelain' into parallel arrays
  local -a wt_paths=() wt_branches=()
  local _path="" _branch=""

  while IFS= read -r line; do
    case "$line" in
      worktree\ *) _path="${line#worktree }" ;;
      branch\ *)   _branch="${line#branch refs/heads/}" ;;
      "")
        if [[ -n "$_path" ]]; then
          wt_paths+=("$_path")
          wt_branches+=("${_branch:-HEAD}")
          _path="" _branch=""
        fi
        ;;
    esac
  done < <(git -C "$REPO_ROOT" worktree list --porcelain; printf '\n')

  # Build and print table
  {
    printf '%s\n' "$header"
    local i
    for i in "${!wt_paths[@]}"; do
      local wt_name ns
      wt_name="$(wt_sanitize "${wt_branches[$i]}")"
      ns="${ns_prefix}-${wt_name}"
      (
        export WT_NAME="$wt_name"
        export WT_BRANCH="${wt_branches[$i]}"
        export WT_NAMESPACE="$ns"
        export WT_PATH="${wt_paths[$i]}"
        export WT_REPO_ROOT="$REPO_ROOT"
        bash "$on_status"
      )
    done
  } | column -t -s $'\t'
}
```

**Step 2: Verify fallback still works (no .wt/)**

```bash
wt list
```

Expected: standard `git worktree list` output.

**Step 3: Commit**

```bash
git add scripts/wt
git commit -m "feat: wt list — formatted table via on-status.sh hook"
```

---

## Task 5: Extend `wt_delete` with hook + namespace cleanup

**Files:**
- Modify: `scripts/wt` — update `wt_delete` function

**Step 1: Insert k8s/hook block into `wt_delete`**

Insert after the "current directory" safety check and before `git worktree remove`:

```bash
  # ── k8s/hook integration ────────────────────────────────────────────────
  local wt_config="$REPO_ROOT/.wt/config.sh"
  if [[ -f "$wt_config" ]]; then
    local wt_name wt_namespace
    wt_name="$(wt_sanitize "$branch")"
    # shellcheck source=.wt/config.sh
    source "$wt_config"
    local ns_prefix="${NAMESPACE_PREFIX:-wt}"
    wt_namespace="${ns_prefix}-${wt_name}"

    local on_delete="$REPO_ROOT/.wt/hooks/on-delete.sh"
    if [[ -f "$on_delete" ]]; then
      export WT_NAME="$wt_name"
      export WT_BRANCH="$branch"
      export WT_NAMESPACE="$wt_namespace"
      export WT_PATH="$dest"
      export WT_REPO_ROOT="$REPO_ROOT"
      echo "Running on-delete hook..." >&2
      if ! bash "$on_delete"; then
        echo "Error: on-delete hook failed — aborting." >&2
        exit 1
      fi
    fi

    echo "Deleting k8s namespace: $wt_namespace" >&2
    kubectl delete namespace "$wt_namespace" --ignore-not-found >&2
  fi
  # ────────────────────────────────────────────────────────────────────────
```

**Step 2: Verify no regressions**

```bash
wt list   # should still work
```

**Step 3: Commit**

```bash
git add scripts/wt
git commit -m "feat: wt delete — run on-delete hook and remove k8s namespace"
```

---

## Task 6: `k8s/infra/namespace.yaml`

**Files:**
- Create: `k8s/infra/namespace.yaml`

**Step 1: Create the file**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: infra
```

**Step 2: Validate**

```bash
kubectl apply --dry-run=client -f k8s/infra/namespace.yaml
```

Expected: `namespace/infra configured (dry run)`

**Step 3: Commit**

```bash
git add k8s/infra/namespace.yaml
git commit -m "feat: add k8s infra namespace manifest"
```

---

## Task 7: Zookeeper manifests

**Files:**
- Create: `k8s/infra/zookeeper-deployment.yaml`
- Create: `k8s/infra/zookeeper-service.yaml`

**Step 1: Create `k8s/infra/zookeeper-deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zookeeper
  namespace: infra
spec:
  replicas: 1
  selector:
    matchLabels:
      app: zookeeper
  template:
    metadata:
      labels:
        app: zookeeper
    spec:
      containers:
        - name: zookeeper
          image: confluentinc/cp-zookeeper:7.4.4
          ports:
            - containerPort: 2181
          env:
            - name: ZOOKEEPER_CLIENT_PORT
              value: "2181"
            - name: ZOOKEEPER_TICK_TIME
              value: "2000"
```

**Step 2: Create `k8s/infra/zookeeper-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: zookeeper
  namespace: infra
spec:
  selector:
    app: zookeeper
  ports:
    - port: 2181
      targetPort: 2181
```

**Step 3: Validate**

```bash
kubectl apply --dry-run=client -f k8s/infra/zookeeper-deployment.yaml
kubectl apply --dry-run=client -f k8s/infra/zookeeper-service.yaml
```

Expected: both print `(dry run)` without error.

**Step 4: Commit**

```bash
git add k8s/infra/zookeeper-deployment.yaml k8s/infra/zookeeper-service.yaml
git commit -m "feat: add zookeeper k8s manifests"
```

---

## Task 8: Kafka deployment + service

**Files:**
- Create: `k8s/infra/kafka-deployment.yaml`
- Create: `k8s/infra/kafka-service.yaml`

**Step 1: Create `k8s/infra/kafka-deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka
  namespace: infra
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      containers:
        - name: kafka
          image: confluentinc/cp-kafka:7.4.4
          ports:
            - containerPort: 9092
          env:
            - name: KAFKA_BROKER_ID
              value: "1"
            - name: KAFKA_ZOOKEEPER_CONNECT
              value: "zookeeper.infra.svc.cluster.local:2181"
            - name: KAFKA_ADVERTISED_LISTENERS
              value: "PLAINTEXT://kafka.infra.svc.cluster.local:9092"
            - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
              value: "PLAINTEXT:PLAINTEXT"
            - name: KAFKA_INTER_BROKER_LISTENER_NAME
              value: "PLAINTEXT"
            - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
              value: "1"
          readinessProbe:
            exec:
              command:
                - kafka-topics
                - --bootstrap-server
                - localhost:9092
                - --list
            initialDelaySeconds: 15
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 5
```

**Step 2: Create `k8s/infra/kafka-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kafka
  namespace: infra
spec:
  selector:
    app: kafka
  ports:
    - port: 9092
      targetPort: 9092
```

**Step 3: Validate**

```bash
kubectl apply --dry-run=client -f k8s/infra/kafka-deployment.yaml
kubectl apply --dry-run=client -f k8s/infra/kafka-service.yaml
```

**Step 4: Commit**

```bash
git add k8s/infra/kafka-deployment.yaml k8s/infra/kafka-service.yaml
git commit -m "feat: add kafka k8s manifests"
```

---

## Task 9: Kafka init Job

**Files:**
- Create: `k8s/infra/kafka-init-job.yaml`

**Step 1: Create the file**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kafka-init
  namespace: infra
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: kafka-init
          image: confluentinc/cp-kafka:7.4.4
          command: ["/bin/sh", "-c"]
          args:
            - |
              until kafka-topics --bootstrap-server kafka.infra.svc.cluster.local:9092 --list > /dev/null 2>&1; do
                echo "Waiting for Kafka..."
                sleep 2
              done
              kafka-topics --bootstrap-server kafka.infra.svc.cluster.local:9092 --create --if-not-exists --topic earthquake-raw-dev --partitions 1 --replication-factor 1
              kafka-topics --bootstrap-server kafka.infra.svc.cluster.local:9092 --create --if-not-exists --topic earthquake-raw-prod --partitions 1 --replication-factor 1
              kafka-topics --bootstrap-server kafka.infra.svc.cluster.local:9092 --create --if-not-exists --topic tectonic-stress-raw-dev --partitions 1 --replication-factor 1
              kafka-topics --bootstrap-server kafka.infra.svc.cluster.local:9092 --create --if-not-exists --topic tectonic-stress-raw-prod --partitions 1 --replication-factor 1
              echo "All topics created."
```

**Step 2: Validate**

```bash
kubectl apply --dry-run=client -f k8s/infra/kafka-init-job.yaml
```

**Step 3: Commit**

```bash
git add k8s/infra/kafka-init-job.yaml
git commit -m "feat: add kafka-init job manifest"
```

---

## Task 10: MinIO manifests

**Files:**
- Create: `k8s/infra/minio-pvc.yaml`
- Create: `k8s/infra/minio-deployment.yaml`
- Create: `k8s/infra/minio-service.yaml`

**Step 1: Create `k8s/infra/minio-pvc.yaml`**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-data
  namespace: infra
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

**Step 2: Create `k8s/infra/minio-deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: infra
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: minio/minio:latest
          args: ["server", "/data", "--console-address", ":9001"]
          ports:
            - name: api
              containerPort: 9000
            - name: console
              containerPort: 9001
          env:
            - name: MINIO_ROOT_USER
              value: minioadmin
            - name: MINIO_ROOT_PASSWORD
              value: minioadmin
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-data
```

**Step 3: Create `k8s/infra/minio-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: infra
spec:
  selector:
    app: minio
  ports:
    - name: api
      port: 9000
      targetPort: 9000
    - name: console
      port: 9001
      targetPort: 9001
```

**Step 4: Validate**

```bash
kubectl apply --dry-run=client -f k8s/infra/minio-pvc.yaml
kubectl apply --dry-run=client -f k8s/infra/minio-deployment.yaml
kubectl apply --dry-run=client -f k8s/infra/minio-service.yaml
```

**Step 5: Commit**

```bash
git add k8s/infra/minio-pvc.yaml k8s/infra/minio-deployment.yaml k8s/infra/minio-service.yaml
git commit -m "feat: add minio k8s manifests"
```

---

## Task 11: Warehouse ConfigMap + PVC + StatefulSet + Service

**Files:**
- Create: `k8s/infra/warehouse-configmap.yaml`
- Create: `k8s/infra/warehouse-pvc.yaml`
- Create: `k8s/infra/warehouse-statefulset.yaml`
- Create: `k8s/infra/warehouse-service.yaml`

**Step 1: Create `k8s/infra/warehouse-configmap.yaml`**

Embed schema files verbatim. The `config.sh` init script runs in the Postgres entrypoint and references `/opt/program/tables.sql` (mounted via `subPath`).

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: warehouse-init
  namespace: infra
data:
  tables.sql: |
    SET TIME ZONE 'UTC';

    CREATE TABLE earthquake_activity (
        id BIGSERIAL PRIMARY KEY NOT NULL,
        raw JSONB NOT NULL,
        dt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE sensor_tectonic_stress (
        id BIGSERIAL PRIMARY KEY NOT NULL,
        raw JSONB NOT NULL,
        dt TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE earthquake_activity_with_stress (
        id BIGSERIAL PRIMARY KEY NOT NULL,
        raw JSONB NOT NULL,
        dt TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        average_tectonic_stress_magnitude FLOAT,
        dt_ingested_prev_catostrophic TIMESTAMP WITH TIME ZONE,
        dt_recorded_prev_catastrophic TIMESTAMP
    );
  config.sh: |
    #!/bin/bash
    createdb -U postgres earthquakes_dev &&
    psql -U postgres -d earthquakes_prod -f /opt/program/tables.sql &&
        psql -U postgres -d earthquakes_dev -f /opt/program/tables.sql
```

**Step 2: Create `k8s/infra/warehouse-pvc.yaml`**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: warehouse-data
  namespace: infra
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

**Step 3: Create `k8s/infra/warehouse-statefulset.yaml`**

Two `subPath` mounts from the same configmap place `tables.sql` at `/opt/program/tables.sql` (referenced by `config.sh`) and `config.sh` at `/docker-entrypoint-initdb.d/config.sh` (executed by Postgres on first start).

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: warehouse
  namespace: infra
spec:
  serviceName: warehouse
  replicas: 1
  selector:
    matchLabels:
      app: warehouse
  template:
    metadata:
      labels:
        app: warehouse
    spec:
      containers:
        - name: postgres
          image: postgres
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: earthquakes_prod
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: warehouse-credentials
                  key: POSTGRES_PASSWORD
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres"]
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 5
            failureThreshold: 5
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
            - name: init-scripts
              mountPath: /opt/program/tables.sql
              subPath: tables.sql
            - name: init-scripts
              mountPath: /docker-entrypoint-initdb.d/config.sh
              subPath: config.sh
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: warehouse-data
        - name: init-scripts
          configMap:
            name: warehouse-init
            defaultMode: 0755
```

**Step 4: Create `k8s/infra/warehouse-service.yaml`**

Headless service (required for StatefulSet DNS). `warehouse.infra.svc.cluster.local` resolves to the pod IP.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: warehouse
  namespace: infra
spec:
  clusterIP: None
  selector:
    app: warehouse
  ports:
    - port: 5432
      targetPort: 5432
```

**Step 5: Validate all four files**

```bash
kubectl apply --dry-run=client -f k8s/infra/warehouse-configmap.yaml
kubectl apply --dry-run=client -f k8s/infra/warehouse-pvc.yaml
kubectl apply --dry-run=client -f k8s/infra/warehouse-statefulset.yaml
kubectl apply --dry-run=client -f k8s/infra/warehouse-service.yaml
```

Expected: all four print `(dry run)` without error.

**Step 6: Validate the entire infra directory applies cleanly**

```bash
kubectl apply --dry-run=client -f k8s/infra/
```

Expected: 13 resources, all `(dry run)`.

**Step 7: Commit**

```bash
git add k8s/infra/
git commit -m "feat: add warehouse k8s manifests (StatefulSet + ConfigMap + PVC + Service)"
```

---

## Task 12: Helm chart skeleton + sensor deployment template

**Files:**
- Create: `charts/worktree/Chart.yaml`
- Create: `charts/worktree/values.yaml`
- Create: `charts/worktree/templates/sensor-deployment.yaml`

**Step 1: Create `charts/worktree/Chart.yaml`**

```yaml
apiVersion: v2
name: worktree
description: Per-worktree data pipeline services
version: 0.1.0
```

**Step 2: Create `charts/worktree/values.yaml`**

```yaml
worktreeName: ""
branch: ""
infraNamespace: "infra"
dbName: ""

sensors:
  - name: sensor-earthquake
    command: ["python3", "-u", "/opt/program/main.py"]
  - name: sensor-tectonic-stress
    command: ["python3", "-u", "/opt/program/main.py"]
```

**Step 3: Create `charts/worktree/templates/sensor-deployment.yaml`**

The `{{- range }}` loop generates one Deployment per sensor. The `type: sensor` label is used by `on-status.sh` to count running sensors.

```yaml
{{- range .Values.sensors }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .name }}
  namespace: {{ $.Release.Namespace }}
  labels:
    app: {{ .name }}
    type: sensor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{ .name }}
  template:
    metadata:
      labels:
        app: {{ .name }}
        type: sensor
    spec:
      containers:
        - name: {{ .name }}
          image: "{{ .name }}:{{ $.Values.worktreeName }}"
          command: {{ toJson .command }}
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: "kafka.{{ $.Values.infraNamespace }}.svc.cluster.local:9092"
            - name: MINIO_ENDPOINT
              value: "minio.{{ $.Values.infraNamespace }}.svc.cluster.local:9000"
            - name: DATABASE_HOST
              value: "warehouse.{{ $.Values.infraNamespace }}.svc.cluster.local"
            - name: DATABASE_NAME
              value: {{ $.Values.dbName | quote }}
{{- end }}
```

**Step 4: Validate with helm lint**

```bash
helm lint charts/worktree
```

Expected: `1 chart(s) linted, 0 chart(s) failed`

**Step 5: Verify template renders correctly**

```bash
helm template test-wt charts/worktree \
  --set worktreeName=my-feature \
  --set dbName=my-feature \
  --namespace wt-my-feature
```

Expected: two Deployment manifests, each with image `sensor-earthquake:my-feature` / `sensor-tectonic-stress:my-feature` and the correct env vars.

**Step 6: Commit**

```bash
git add charts/worktree/Chart.yaml charts/worktree/values.yaml charts/worktree/templates/sensor-deployment.yaml
git commit -m "feat: add Helm chart skeleton and sensor deployment template"
```

---

## Task 13: Pipeline tests Job template

**Files:**
- Create: `charts/worktree/templates/pipeline-tests-job.yaml`

**Step 1: Create the file**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pipeline-tests
  namespace: {{ .Release.Namespace }}
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: pipeline-tests
          image: "pipeline-tests:{{ .Values.worktreeName }}"
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: "kafka.{{ .Values.infraNamespace }}.svc.cluster.local:9092"
            - name: MINIO_ENDPOINT
              value: "minio.{{ .Values.infraNamespace }}.svc.cluster.local:9000"
            - name: DATABASE_HOST
              value: "warehouse.{{ .Values.infraNamespace }}.svc.cluster.local"
            - name: DATABASE_NAME
              value: {{ .Values.dbName | quote }}
```

**Step 2: Re-run helm lint and template**

```bash
helm lint charts/worktree
helm template test-wt charts/worktree \
  --set worktreeName=my-feature \
  --set dbName=my-feature \
  --namespace wt-my-feature
```

Expected: lint passes; template output includes 2 Deployments + 1 Job.

**Step 3: Commit**

```bash
git add charts/worktree/templates/pipeline-tests-job.yaml
git commit -m "feat: add pipeline-tests Job template to Helm chart"
```

---

## Task 14: Project `.wt/config.sh` via `wt init`

**Files:**
- Create: `.wt/config.sh` (via `wt init`, then overwrite)
- Create: `.wt/hooks/on-create.sh`, `on-delete.sh`, `on-status.sh` (via `wt init`)

**Step 1: Scaffold with `wt init`**

```bash
bash scripts/wt init
```

Expected output:
```
Initializing .wt/ in <repo-root>
Created:
  <repo-root>/.wt/config.sh
  <repo-root>/.wt/hooks/on-create.sh
  <repo-root>/.wt/hooks/on-delete.sh
  <repo-root>/.wt/hooks/on-status.sh
```

**Step 2: Replace `.wt/config.sh` with project-specific values**

Overwrite the generated `config.sh` with:

```bash
#!/usr/bin/env bash
# .wt/config.sh — data-engineering-boilerplate project configuration

CLUSTER_NAME="dev-cluster"
NAMESPACE_PREFIX="wt"
INFRA_NAMESPACE="infra"

SERVICES=(
  "sensor-earthquake:./service/sensor_earthquake/Dockerfile"
  "sensor-tectonic-stress:./service/sensor_tectonic_stress/Dockerfile"
  "pipeline-tests:./service/pipeline_tests/Dockerfile"
)

PG_POD="warehouse-0"
PG_USER="postgres"
TEMPLATE_DB="earthquakes_prod"

HELM_CHART="charts/worktree"

INFRA_SERVICES=("kafka" "minio" "warehouse")
```

**Step 3: Verify hooks are executable**

```bash
ls -la .wt/hooks/
```

Expected: all three hooks have `x` permission.

**Step 4: Verify on-status.sh --header works (uses INFRA_SERVICES)**

```bash
WT_REPO_ROOT="$(pwd)" bash .wt/hooks/on-status.sh --header
```

Expected: `NAME	STATUS	KAFKA	MINIO	WAREHOUSE	SENSORS`

**Step 5: Commit**

```bash
git add .wt/
git commit -m "feat: add project .wt/ config and default hooks"
```

---

## Deployment Reference (not a task — for documentation)

```bash
# One-time infra setup (run once per cluster)
kubectl create namespace infra
kubectl create secret generic warehouse-credentials \
  --namespace=infra \
  --from-literal=POSTGRES_PASSWORD=<your-password>
kubectl apply -f k8s/infra/

# Checking infra spinup
kubectl get pods -n infra

# Checking logs of pods with crashes
kubectl logs -n infra kafka-785d4d8dfc-mx5ft
kubectl logs -n infra warehouse-0

# Redeploying After yaml edits example:
kubectl delete deployment kafka -n infra # Delete first
kubectl delete job kafka-init -n infra
kubectl apply -f k8s/infra/kafka-deployment.yaml
kubectl rollout restart deployment kafka -n infra

#Scaling down cluster
kubectl scale deployment kafka -n infra --replicas=0
sleep 20
kubectl scale deployment kafka -n infra --replicas=1

# Deleting Statefulset and PersistentVolumeClaim & redeploying
kubectl delete statefulset warehouse -n infra
kubectl delete pvc warehouse-0 -n infra
kubectl apply -f k8s/infra/warehouse-deployment.yaml

# Verify new Pod environemnt
kubectl describe pod -n infra -l app=kafka | grep -A 30 "Environment"

# Per-worktree workflow
wt create my-feature --go   # builds images, clones DB, deploys chart
wt list                     # formatted status table
wt delete my-feature        # helm uninstall + drop DB + namespace + worktree
```

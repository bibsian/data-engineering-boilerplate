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

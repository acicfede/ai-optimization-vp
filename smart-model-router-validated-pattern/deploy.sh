#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="smart-model-router"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v oc >/dev/null 2>&1 || {
  echo "ERROR: oc CLI not found." >&2
  exit 1
}

oc whoami >/dev/null

echo "Preparing namespace: ${NAMESPACE}"
oc apply -f "${SCRIPT_DIR}/manifests/namespace.yaml"

if ! oc -n "${NAMESPACE}" get secret smart-router-maas-credentials >/dev/null 2>&1; then
  echo "ERROR: Secret smart-router-maas-credentials is missing in namespace ${NAMESPACE}." >&2
  echo "Create it securely before deploying. Never commit credentials to Git." >&2
  exit 1
fi

echo "Applying Smart Model Router manifests..."
oc apply -k "${SCRIPT_DIR}/manifests"

echo "Waiting for deployment rollout..."
oc -n "${NAMESPACE}" rollout status deployment/smart-model-router --timeout=180s

echo "Route:"
oc -n "${NAMESPACE}" get route smart-model-router

echo "Deployment completed."

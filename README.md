# AI Optimization

Kubernetes/OpenShift configuration examples for GPU workload management, LLM
serving, model routing and observability. The repository is designed to be
reviewed and adapted to a target environment; it does not install OpenShift,
OpenShift AI, Kueue, llm-d, the GPU Operator, or other platform operators.

> **Status:** example repository. It is not an official Red Hat Validated
> Pattern and does not imply certification or production readiness.

## Repository structure

| Path | Purpose | Deployment boundary |
|---|---|---|
| `gpuaas/` | Namespaces, ResourceFlavors, Kueue queues/cohort/priority classes and OpenShift AI HardwareProfiles | Render/apply after checking Kueue and OpenShift AI CRDs and cluster-specific quotas |
| `gpuaas/monitoring/` | User-workload monitoring enablement, RoleBinding and Kueue ServiceMonitor | Separate, explicit review required; includes a cluster-wide monitoring ConfigMap |
| `llm-d/` | Example `LLMInferenceService` resources | Examples only; customize model, gateway, queue, storage, service account and resources |
| `observability/` | Grafana dashboard ConfigMaps, ServiceMonitors and GPU Operator alerts | Customize namespaces, selectors, metric availability and monitoring permissions |
| `smart-model-router-validated-pattern/` | Smart Model Router application, Kustomize manifests and deployment helper | Standalone application; create its credential Secret securely before deployment |
| `docs/` | Architecture boundaries and Validated Patterns alignment notes | Reference documentation |
| `scripts/` | Local validation script | Safe checks only; does not apply resources |

## Prerequisites

- A working OpenShift cluster and compatible `oc`/`kubectl` CLI.
- The relevant operators and APIs installed for the selected component, such as
  OpenShift AI, Kueue, llm-d, Prometheus Operator and NVIDIA GPU Operator.
- Python 3 and PyYAML for syntax checks; `kubectl` with `kubectl kustomize` for
  rendering checks.
- Appropriate cluster permissions for the resources you choose to deploy.

## Validate before deployment

From the repository root:

```bash
./scripts/validate-repo.sh
```

The script parses all YAML and JSON files and renders every directory containing
`kustomization.yaml`. It does **not** validate resources against live cluster
CRDs, test endpoint connectivity, prove scheduling capacity, or deploy anything.
A GitHub Actions workflow runs the same checks on pushes to `main` and pull
requests.

To render an individual component for review:

```bash
kubectl kustomize gpuaas/
kubectl kustomize gpuaas/monitoring/
kubectl kustomize observability/
kubectl kustomize smart-model-router-validated-pattern/manifests/
```

Review the rendered output before applying it. Do not apply every directory at
once: some resources are cluster-scoped or have environment-specific effects.

## Deployment guidance

1. Start with one component and review its README and prerequisites.
2. Confirm all referenced namespaces, CRDs, ResourceFlavors, queues, models,
   gateways, secrets and service accounts exist or are included intentionally.
3. Render and inspect the manifests; use server-side dry-run against the target
   cluster where permissions and APIs are available.
4. Deploy through the target environment's approved GitOps workflow or explicit
   `oc apply -k` command, after review.
5. Verify the resulting resources, rollout, scheduling and metrics/inference.

The Smart Model Router helper `smart-model-router-validated-pattern/deploy.sh`
performs cluster changes. Read it before running it and ensure the required
`smart-router-maas-credentials` Secret already exists in the `smart-model-router`
namespace. Never commit real credentials.

## Security

- Do not commit credentials, tokens, private keys, kubeconfigs or live Secret
  manifests. `secret-example.yaml` is a placeholder and is intentionally not
  referenced by the application Kustomization.
- Review Route exposure and application-level authentication/authorization
  before exposing the Smart Model Router beyond a trusted environment.
- Prefer trusted TLS certificates over disabling certificate verification.
- Review cluster-scoped monitoring changes separately from workload manifests.

## Red Hat Validated Patterns

This repository borrows GitOps/MLOps design principles but is not the official
Red Hat OpenShift AI Validated Pattern. See
[`docs/validated-pattern-alignment.md`](docs/validated-pattern-alignment.md)
for the current architecture boundaries and known assumptions.

## License

Add the license appropriate for the project before publishing.

# Validated Patterns alignment notes

## Intent

This repository is an AI Optimization example repository built from OpenShift
and OpenShift AI resources. It is inspired by GitOps and MLOps practices; it is
not an official Red Hat Validated Pattern and this repository alone does not
claim certification or support status.

## Architecture boundaries

- `gpuaas/`: Kueue queues, cohorts, ResourceFlavors, HardwareProfiles and
  related namespaces. These resources depend on Kueue and OpenShift AI APIs
  already installed on the target cluster.
- `gpuaas/monitoring/`: optional monitoring setup. It is intentionally rendered
  and applied separately because `enableMonitoring.yaml` modifies the
  cluster-wide OpenShift user-workload monitoring configuration.
- `llm-d/`: illustrative LLMInferenceService examples. They depend on the
  installed llm-d/OpenShift AI API and environment-specific gateway, model,
  storage, queue and service-account configuration.
- `observability/`: dashboard ConfigMaps, ServiceMonitors and a PrometheusRule.
  The metrics endpoints, namespaces, labels and metric names must be verified
  against the target environment.
- `smart-model-router-validated-pattern/`: a standalone application example
  with its own Kustomize root and deployment script. Its MaaS credentials Secret
  must be created out-of-band and is not included in the Kustomization.

## GitOps operating model

1. Review and customize environment-specific values in a branch.
2. Render every Kustomization and run the repository validation script.
3. Review the generated manifests and verify that the required CRDs and
   operators exist on the target cluster.
4. Connect the intended directory to Argo CD only after defining the desired
   sync order and ownership boundaries. Do not combine every directory into a
   single root Kustomization by default: some resources are cluster-scoped,
   some are environment-specific, and monitoring setup has cluster-wide impact.
5. Verify rollout, scheduling, metrics scraping and inference after deployment.

## Known environment-specific assumptions

- Namespaces such as `agent`, `team-inference`, `team-training`,
  `redhat-ods-applications`, and `nvidia-gpu-operator` must exist or be created
  as documented for the target environment.
- GPU labels, resource quotas, Kueue API versions, HardwareProfile API versions,
  LLMInferenceService schemas and model identifiers depend on installed versions
  and cluster configuration.
- The Kueue ServiceMonitor currently uses `insecureSkipVerify: true`. Review
  the endpoint certificate and configure trusted CA verification where possible
  before production use.
- The Smart Model Router example Route has TLS edge termination, but this does
  not itself implement user authentication or authorization. Restrict exposure
  according to the intended use case before production deployment.

## Official references

- Red Hat Validated Patterns: <https://validatedpatterns.io/>
- OpenShift GitOps documentation: <https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/>
- OpenShift AI documentation: <https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/>

Review the official documentation for the versions deployed in the target
cluster; the repository does not pin or install those platform components.

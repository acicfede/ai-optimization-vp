# Observability

This directory provides reusable observability components for AI workloads on OpenShift.

## Components

- `dashboards/`: Grafana vLLM dashboard and dashboard provisioning configuration.
- `servicemonitor-agent-qwen3-32b-vllm-metrics.yaml`: example ServiceMonitor for vLLM metrics.
- `servicemonitor-ai-ops-llama-metrics.yaml`: example ServiceMonitor for Llama metrics.
- `servicemonitor-nvidia-gpu-operator-nvidia-dcgm-exporter.yaml`: optional NVIDIA DCGM Exporter monitoring.
- `prometheusrule-nvidia-gpu-operator-nvidia-gpu-operator-metrics.yaml`: optional NVIDIA GPU Operator alerting rules.

## Prerequisites

- OpenShift monitoring configured to scrape user workload metrics.
- Grafana and Prometheus-compatible metrics query access.
- vLLM metrics enabled for workloads using the vLLM dashboard.
- NVIDIA GPU Operator and DCGM Exporter for GPU-specific monitoring.

## Customization

Review namespaces, label selectors, endpoint ports, and metric availability before deploying the ServiceMonitors.

The dashboard uses a Prometheus datasource variable and a `model_name` variable. Ensure the target metrics expose the labels and metric names used by its queries.

Configure datasource endpoints and authentication separately for each environment. Do not commit tokens, passwords, cluster certificates, or environment-specific endpoints.

## Validation

Render the manifests locally:

```bash
oc kustomize observability/
```

Rendering validates the Kustomize structure; it does not validate runtime connectivity or apply resources to the cluster.

## Deployment

Integrate these resources with the target cluster's existing monitoring stack. Do not deploy duplicate Prometheus or Thanos components when OpenShift already provides them.

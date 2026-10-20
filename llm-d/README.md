# llm-d — Model Serving

This directory contains example `LLMInferenceService` manifests for model serving on OpenShift AI using the llm-d architecture.

## Prerequisites

- OpenShift Container Platform and OpenShift AI are installed and configured.
- The `LLMInferenceService` API is available.
- The required gateway, model storage, image pull secrets, service accounts, and scheduling resources are configured in the target environment.
- GPU resources are available for the selected model.

## Examples

- `examples/llminferenceservice-qwen3-32b.yaml`
- `examples/llminferenceservice-gpt-oss-20b.yaml`

These manifests are starting points, not universal deployment configurations. Adapt the model URI, resource requests, vLLM arguments, gateway, queue, and service account to the target environment.

## Hardware Profiles and Scheduling

The example manifests reference existing OpenShift AI Hardware Profiles through metadata annotations.

| Model | Hardware Profile | CPU | Memory | GPUs | Kueue LocalQueue | PriorityClass |
|---|---|---|---|---|---|---|
| GPT-OSS-20B | `gpu` | 8 | 16Gi | 1–2 | `default` | None |
| Qwen3-32B | `highpriority` | 1–32 | 2–128Gi | 1–4 | `team-inference` | `inference-priority` |

The values above describe the configured Hardware Profiles in the target environment; they are not guarantees of available capacity or successful scheduling.

The examples use these annotations:

- `opendatahub.io/hardware-profile-name`
- `opendatahub.io/hardware-profile-namespace`

The referenced profiles are assumed to exist in the `redhat-ods-applications` namespace. The annotations identify the intended profile but do not, by themselves, guarantee that the serving controller applies all profile settings. Verify the behavior supported by the installed OpenShift AI version.

Scheduling also depends on GPU availability, Kueue configuration, queue quotas, and cluster policies. The Qwen3-32B example additionally references the `team-inference` queue.

## Validation

Review each manifest and validate it against the installed CRD before deployment. Do not apply the examples without confirming that all referenced resources exist.

The repository does not include model weights, credentials, or cluster-generated status fields.

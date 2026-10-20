# Smart Model Router

A configurable model router for OpenShift that selects an AI model based on
request complexity and calls models through an OpenAI-compatible MaaS endpoint.

## Features

- Python HTTP application with a web interface.
- Simple and complex request routing.
- Configurable MaaS endpoint and model identifiers.
- Optional Llama-based classification with heuristic fallback.
- OpenShift Deployment, Service and Route.
- Kustomize-based manifest rendering.

## Prerequisites

- OpenShift CLI (`oc`) compatible with the target cluster.
- Access to an OpenShift cluster and permission to create the required resources.
- An OpenAI-compatible MaaS endpoint.
- A valid MaaS API key.
- Model identifiers supported by the configured MaaS endpoint.
- A reachable classifier endpoint if classifier-based routing is required.

## Configuration

Edit `manifests/router-config.env` before deployment.

| Variable | Purpose |
|---|---|
| `MAAS_URL` | Base URL of the MaaS endpoint |
| `MAAS_TLS_VERIFY` | Whether to verify the MaaS TLS certificate |
| `SIMPLE_MODEL` | Model identifier for simple requests |
| `COMPLEX_MODEL` | Model identifier for complex requests |
| `LLAMA_BASE_URL` | Classifier endpoint |
| `LLAMA_MODEL` | Classifier model identifier |
| `LLAMA_TIMEOUT` | Classifier timeout in seconds |
| `REQUEST_TIMEOUT` | MaaS request timeout in seconds |

Use model identifiers that are available to your MaaS subscription.
The example values are placeholders and may need to be changed.

## Credentials

Create the `smart-router-maas-credentials` Secret in the target namespace.
Do not commit API keys or real credentials to Git.

Example command (enter the actual key locally; do not place it in source control):

    oc create secret generic smart-router-maas-credentials \
      --namespace smart-model-router \
      --from-literal=MAAS_API_KEY='<your-key>'

## Render and validate manifests

    oc kustomize manifests > /tmp/smart-model-router-rendered.yaml
    oc apply --dry-run=client -f /tmp/smart-model-router-rendered.yaml

These commands render and validate the manifests without applying them to the cluster.

## Deployment

The `deploy.sh` script applies the Kustomize resources and waits for the Deployment rollout.
Review the script and configuration before executing it against a cluster.

    ./deploy.sh

The target namespace must contain the required Secret before the application can use MaaS.

## Verification

    oc -n smart-model-router rollout status deployment/smart-model-router
    oc -n smart-model-router get pods,service,route
    oc -n smart-model-router logs deployment/smart-model-router

Check the `/health` endpoint through the generated Route.

## Security notes

- Never commit API keys, tokens, or kubeconfig files.
- Keep TLS verification enabled where the MaaS certificate chain is trusted.
- If a private CA is used, configure the container to trust that CA instead of disabling verification.
- Review namespace and route settings for your environment before deployment.

## Known limitations

- Model identifiers must be available and authorized through the configured MaaS endpoint.
- Upstream rate limits, capacity constraints, or subscription policies can cause requests to fail.
- A successful manifest dry-run does not guarantee successful application startup or model inference.
- This repository is a community implementation and is not, by itself, evidence of official Red Hat Validated Patterns certification.

## License

Add the license appropriate for your project before publishing.

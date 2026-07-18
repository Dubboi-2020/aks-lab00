# AKS LLM Agent — Cost-Optimized Learning Project

A minimal agentic service deployed on Azure Kubernetes Service (AKS), talking to a
**free-tier LLM (Groq)**. Built as an interview-prep / learning exercise focused on
keeping real Azure spend as close to $0 as possible.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ AKS Cluster (Free tier control plane, 1 x B2s node)  │
│                                                       │
│   ┌───────────────────────────────┐                  │
│   │ Pod: llm-agent (Flask)        │                  │
│   │  - /chat endpoint             │                  │
│   │  - simple ReAct-style loop    │                  │
│   │  - 1 tool: calculator         │                  │
│   └──────────────┬────────────────┘                  │
│                  │ HTTPS (outbound only)              │
└──────────────────┼──────────────────────────────────┘
                    ▼
          Groq API (OpenAI-compatible, free tier)
          model: llama-3.1-8b-instant
```

No LoadBalancer, no ACR, no monitoring add-ons — every piece that costs money
beyond compute has been deliberately removed or swapped for a free alternative.

## Cost breakdown (approximate, East US, July 2026 pricing — verify current rates)

| Item | Choice | Cost |
|---|---|---|
| AKS control plane | Free tier | $0 |
| Node | 1x Standard_B2s (or Spot) | ~$0.04/hr on-demand, ~$0.01/hr spot |
| Disk | Default OS disk (Standard SSD, 30GB) | ~$0.02/hr |
| Load Balancer | None (ClusterIP only) | $0 |
| Container registry | Docker Hub free tier | $0 |
| LLM inference | Groq free tier | $0 |
| **Total if left running** | | **~$0.06/hr (~$1.50/day)** |
| **Total if stopped when idle** | `az aks stop` between sessions | **~$0.02/hr for disk only** |

Always run `infra/cleanup.sh` or `az aks stop` when you're done for the day.

## Prerequisites

- Azure subscription (free trial credit works fine)
- Azure CLI (`az`) logged in
- `kubectl`
- Docker
- A free [Groq API key](https://console.groq.com)
- A Docker Hub account (free)

## Steps

### 1. Create the cluster (cheap config)

```bash
export DOCKERHUB_USER=<your-dockerhub-username>
bash infra/aks-create.sh
```

This provisions a resource group, a 1-node Free-tier AKS cluster on a burstable
B2s VM using kubenet networking — see `infra/aks-create.sh` for the exact flags
and comments on what each one saves you.

### 2. Build and push the agent image

```bash
cd agent
docker build -t $DOCKERHUB_USER/llm-agent:v1 .
docker login
docker push $DOCKERHUB_USER/llm-agent:v1
cd ..
```

### 3. Get cluster credentials

```bash
az aks get-credentials --resource-group aks-learning-rg --name aks-learning-cluster
kubectl get nodes
```

### 4. Create the Groq API key secret

```bash
kubectl create secret generic llm-secret --from-literal=GROQ_API_KEY=<your-groq-key>
```

### 5. Deploy

```bash
# edit k8s/deployment.yaml to point image: at your dockerhub user/tag first
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods -w
```

### 6. Talk to your agent

```bash
kubectl port-forward svc/llm-agent-svc 8080:80
```

In another terminal:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 42 times 17, and explain what an AKS node pool is in one sentence?"}'
```

You should see a JSON response, and — if the model decides it needs the
calculator tool — a `tool_calls` trace in the response showing the agent
reasoning step.

### 7. Clean up (important for cost control)

```bash
bash infra/cleanup.sh
```

or, if you want to keep the cluster around for tomorrow without paying for
compute:

```bash
az aks stop --resource-group aks-learning-rg --name aks-learning-cluster
# next day:
az aks start --resource-group aks-learning-rg --name aks-learning-cluster
```

## What this demonstrates for an interview

- AKS cluster provisioning with deliberate cost controls (not just "az aks create")
- Containerizing a Python service and running it on K8s (Deployment, Service, Secret)
- Basic agent pattern: LLM + tool-calling loop, not just a passthrough chatbot
- Awareness of the cost surface area of a managed K8s service (control plane tier,
  node SKU/spot, networking plugin, LB, registry, add-ons)
- Clean teardown discipline

## Notes / things to call out live in an interview

- In production you'd use a proper secrets store (Azure Key Vault + CSI driver)
  instead of a raw K8s Secret.
- You'd add a HorizontalPodAutoscaler and resource requests/limits sized from
  real load testing, not guesses.
- You'd put a real Ingress/API Gateway in front instead of port-forwarding.
- Spot nodes can be evicted — fine for a demo, not for anything stateful or
  interview-day-critical without a fallback node pool.

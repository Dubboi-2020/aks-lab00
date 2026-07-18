# AKS LLM Agent — Learning Project

This project will be a base infrastrustrue for future agentic and LLMs. It builds a minimal agentic service deployed on Azure Kubernetes Service (AKS), talking to a
**free-tier LLM (Groq)**

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

Always run `infra/cleanup.sh` or `az aks stop` when done for the day.

## Prerequisites

- Azure subscription (free trial)
- Azure CLI (`az`) 
- `kubectl`
- Docker
- [Groq API key](https://console.groq.com)
- A Docker Hub account

## Steps

### 1. Create the cluster (cheap config)

```bash
export DOCKERHUB_USER=<your-dockerhub-username>
bash infra/aks-create.sh
```

This provisions a resource group, a 1-node Free-tier AKS cluster using kubenet networking
see `infra/aks-create.sh` for flags


### 2. Build and push the agent image

```bash
cd agent
docker build --platform linux/amd64 -t $DOCKERHUB_USER/llm-agent:v1 .
docker login
docker push $DOCKERHUB_USER/llm-agent:v1
cd ..
```

### 3. Get cluster credentials

```bash
az aks get-credentials --resource-group aks-lab00-rg  --name  aks-lab00-cluster
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

### 6. Create a path to communicae with agent

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

### 7. Clean up!! (important for cost control)

```bash
bash infra/cleanup.sh
```

or, if you want to keep the cluster around for tomorrow without paying for
compute:

```bash
az aks stop --resource-group aks-lab00-rg  --name aks-lab00-rg 
# next day:
az aks start --resource-group aks-lab00-rg  --name  aks-lab00-cluster
```

## What this lab demonstrates 

- AKS cluster provisioning with deliberate cost controls 
- Containerizing a Python service and running it on K8s (Deployment, Service, Secret)
- Basic agent pattern: LLM + tool-calling loop
- Clean teardown discipline




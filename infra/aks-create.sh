#!/usr/bin/env bash
# Creates the cheapest reasonable AKS cluster for learning/demo purposes.
# Review each flag below - they're chosen specifically to minimize cost.
set -euo pipefail

RG=aks-lab00-rg
CLUSTER=aks-lab00-cluster
LOCATION=southcentralus        # pick a region close to you; prices vary by region
NODE_SIZE=Standard_D2s_v3   # cheapest burstable VM with enough RAM for a small pod

echo "==> Creating resource group"
az group create --name "$RG" --location "$LOCATION"

echo "==> Creating AKS cluster (this takes ~5-10 min)"
az aks create \
  --resource-group "$RG" \
  --name "$CLUSTER" \
  --tier free \
  --node-count 1 \
  --node-vm-size "$NODE_SIZE" \
  --network-plugin kubenet \
  --disable-file-driver \
  --disable-snapshot-controller \
  --generate-ssh-keys \
  --no-wait

# Flags explained:
#   --tier free              -> control plane has no SLA but is free (vs Standard/Premium tier billing)
#   --node-count 1           -> single node is enough for a demo, avoids paying for redundancy you don't need
#   --node-vm-size B2s       -> cheapest burstable-CPU VM that comfortably runs a small Flask pod
#   --network-plugin kubenet -> uses fewer IPs / simpler routing than Azure CNI, no extra cost for CNI overlay
#   --disable-*-driver       -> skip storage CSI drivers you don't need for a stateless demo
#
# NOT included on purpose (all of these cost money and aren't needed for a labbing):
#   - Container Insights / monitoring add-on
#   - Azure Defender for Containers
#   - Multiple node pools / cluster autoscaler
#   - A LoadBalancer service (we use ClusterIP + port-forward instead)
#
# OPTIONAL further savings: add a Spot node pool instead of the default pool.
# Example (run after the cluster exists, then delete the default pool):
#
#   az aks nodepool add \
#     --resource-group "$RG" --cluster-name "$CLUSTER" \
#     --name spotpool --priority Spot --eviction-policy Delete \
#     --spot-max-price -1 --node-count 1 --node-vm-size "$NODE_SIZE" \
#     --no-wait
#
# Spot can save 80-90% but nodes can be evicted with short notice -- fine for
# learning, risky if you want a guaranteed-up demo on interview day.

echo "==> Cluster creation started in background. Check status with:"
echo "    az aks show --resource-group $RG --name $CLUSTER --query provisioningState"

#!/usr/bin/env bash
# Tears down everything so you don't get billed while you're not using it.
set -euo pipefail

RG=aks-learning-rg

read -p "This will DELETE the entire resource group '$RG' and everything in it. Continue? (y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

az group delete --name "$RG" --yes --no-wait
echo "Deletion started (running in background). Check with:"
echo "    az group show --name $RG"

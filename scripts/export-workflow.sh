#!/bin/sh
# export-workflow.sh "<name>" [more names...]: copy workflows you saved in
# ComfyUI (its workflows list) into workflows/ here, to commit them.
# Needs kubectl access to pve2 (KUBECONFIG, default ~/.kube/pve2.yaml).
set -eu
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/pve2.yaml}"
cd "$(dirname "$0")/../workflows"
pod=$(kubectl -n comfyui get pods -l app.kubernetes.io/name=comfyui -o name | head -1)
[ -n "$pod" ] || { echo "ComfyUI is not running (scripts/llm.sh off?)" >&2; exit 1; }
for name in "$@"; do
  kubectl -n comfyui exec "$pod" -- cat "/data/user/default/workflows/$name.json" > "$name.json.tmp"
  mv "$name.json.tmp" "$name.json"
  echo "exported workflows/$name.json"
done

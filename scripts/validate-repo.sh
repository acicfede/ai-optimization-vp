#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required (kubectl kustomize is used for rendering)." >&2
  exit 1
fi

python3 - <<'PY'
import json
from pathlib import Path
import sys
import yaml

root = Path.cwd()
errors = []
for pattern in ("*.yaml", "*.yml"):
    for path in sorted(root.rglob(pattern)):
        try:
            with path.open(encoding="utf-8") as stream:
                list(yaml.safe_load_all(stream))
        except Exception as exc:
            errors.append(f"YAML: {path.relative_to(root)}: {exc}")
for path in sorted(root.rglob("*.json")):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON: {path.relative_to(root)}: {exc}")
if errors:
    print("Syntax validation failed:", file=sys.stderr)
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print("YAML and JSON syntax validation passed.")
PY

mapfile -t kustomizations < <(find . -name kustomization.yaml -type f -not -path './.git/*' | sort)
if [[ ${#kustomizations[@]} -eq 0 ]]; then
  echo "ERROR: no kustomization.yaml files found." >&2
  exit 1
fi

for file in "${kustomizations[@]}"; do
  dir="$(dirname "$file")"
  echo "Rendering $dir"
  kubectl kustomize "$dir" >/dev/null
done

echo "All ${#kustomizations[@]} Kustomization directories rendered successfully."

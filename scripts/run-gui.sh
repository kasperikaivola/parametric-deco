#!/usr/bin/env bash
# Open the desktop CAD editor with the project virtualenv.
# Usage, from any directory: ./scripts/run-gui.sh [config.json]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
gui="$root/.venv/bin/parametric-deco-gui"
if [[ ! -x "$gui" ]]; then
  echo "Desktop editor is not installed. From the repository root, run: ./scripts/setup-env.sh" >&2
  exit 1
fi
cd "$root"
exec "$gui" "$@"

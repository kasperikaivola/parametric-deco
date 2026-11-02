#!/usr/bin/env bash
# Create .venv, install requirements.lock, and install the pinned desktop extra.
# Usage, from any directory: ./scripts/setup-env.sh
# Override the interpreter with PYTHON=/path/to/python3.12 ./scripts/setup-env.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
venv_python="$root/.venv/bin/python"

python_supported() {
  "$1" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)'
}

if [[ ! -x "$venv_python" ]]; then
  launcher=""
  if [[ -n "${PYTHON:-}" ]]; then
    if python_supported "$PYTHON"; then
      launcher="$PYTHON"
    else
      echo "Python at '$PYTHON' is not 3.11, 3.12, or 3.13." >&2
      exit 1
    fi
  else
    # Prefer 3.12: that is the interpreter recorded with the locked CAD stack.
    for candidate in python3.12 python3.13 python3.11 python3 python; do
      if command -v "$candidate" >/dev/null 2>&1 && python_supported "$candidate"; then
        launcher="$candidate"
        break
      fi
    done
  fi
  if [[ -z "$launcher" ]]; then
    echo "Python 3.11, 3.12, or 3.13 was not found. Install one, or set PYTHON." >&2
    exit 1
  fi
  echo "Creating .venv with $launcher"
  "$launcher" -m venv "$root/.venv"
fi

if ! python_supported "$venv_python"; then
  echo ".venv exists but its Python is outside 3.11-3.13. Remove .venv and run this script again." >&2
  exit 1
fi

gui_pin="$(sed -n 's/^gui = \["\(PySide6==[^"]*\)"\].*/\1/p' pyproject.toml)"
if [[ -z "$gui_pin" ]]; then
  echo "Could not read the gui extra pin from pyproject.toml." >&2
  exit 1
fi

echo "Installing pinned dependencies from requirements.lock"
"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install --upgrade -r "$root/requirements.lock"
echo "Installing parametric-deco without re-resolving locked dependencies"
"$venv_python" -m pip install --upgrade --no-deps -e "$root"
echo "Installing desktop extra $gui_pin"
"$venv_python" -m pip install --upgrade "$gui_pin"
echo "Environment ready: $venv_python"
echo "Open the editor with: ./scripts/run-gui.sh"

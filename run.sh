#!/usr/bin/env bash
# macOS / Linux launcher
set -euo pipefail
cd "$(dirname "$0")"

for candidate in ".venv/bin/python" "env/bin/python" "venv/bin/python"; do
  if [ -x "$candidate" ]; then
    exec "$candidate" -m streamlit run app.py
  fi
done

exec python3 -m streamlit run app.py

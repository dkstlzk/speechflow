#!/usr/bin/env bash
set -euo pipefail

# Remove local Python cache artifacts while protecting git metadata and virtualenvs.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

find . \
  \( -path "./.git" -o -path "./.git/*" \
     -o -path "./.sf-env" -o -path "./.sf-env/*" \
     -o -path "./.venv" -o -path "./.venv/*" \
     -o -path "./venv" -o -path "./venv/*" \
     -o -path "./env" -o -path "./env/*" \) -prune -o \
  -type d -name "__pycache__" -print -exec rm -rf {} +

find . \
  \( -path "./.git" -o -path "./.git/*" \
     -o -path "./.sf-env" -o -path "./.sf-env/*" \
     -o -path "./.venv" -o -path "./.venv/*" \
     -o -path "./venv" -o -path "./venv/*" \
     -o -path "./env" -o -path "./env/*" \) -prune -o \
  -type f \( -name "*.pyc" -o -name "*.pyo" \) -print -exec rm -f {} +

echo "Python cache cleanup complete"

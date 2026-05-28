#!/usr/bin/env bash
# Run all local code quality checks in one shot.
# Usage:  ./scripts/lint.sh
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${BOLD}▶ $*${NC}"; }
ok()   { echo -e "${GREEN}✔ $*${NC}"; }

FAILED=()

step "ruff — lint"
if ruff check app/ tests/; then ok "ruff: clean"; else FAILED+=("ruff"); fi

step "ruff — format check"
if ruff format --check app/ tests/; then ok "ruff-format: clean"; else FAILED+=("ruff-format"); fi

step "mypy — type check"
if mypy app/ --ignore-missing-imports; then ok "mypy: clean"; else FAILED+=("mypy"); fi

step "pytest — test suite"
if pytest tests/ -x -q; then ok "pytest: all passed"; else FAILED+=("pytest"); fi

echo ""
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}All checks passed.${NC}"
else
  echo -e "${RED}${BOLD}Failed: ${FAILED[*]}${NC}"
  exit 1
fi

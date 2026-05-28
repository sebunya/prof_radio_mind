#!/usr/bin/env bash
# Run the full RMIAS security scan suite locally.
# Usage:  ./scripts/sast.sh [--fix]
#
# Requires:
#   semgrep  — pip install semgrep   OR  brew install semgrep
#   snyk     — npm install -g snyk   OR  brew install snyk
#   sentry-cli (optional, for release commands)
set -euo pipefail

FIX=false
for arg in "$@"; do
  [[ "$arg" == "--fix" ]] && FIX=true
done

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${BOLD}▶ $*${NC}"; }
ok()   { echo -e "${GREEN}✔ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
fail() { echo -e "${RED}✖ $*${NC}"; }

FAILED=()

# ── 1. Semgrep SAST ───────────────────────────────────────────────────────
step "Semgrep SAST (p/security-audit + p/secrets + custom rules)"
if command -v semgrep &>/dev/null; then
  if semgrep \
       --config "p/security-audit" \
       --config "p/secrets" \
       --config "p/python" \
       --config ".semgrep/rules.yml" \
       --error \
       --quiet \
       app/; then
    ok "Semgrep: no findings"
  else
    fail "Semgrep: findings detected (see output above)"
    FAILED+=("semgrep")
  fi
else
  warn "semgrep not installed — skipping (pip install semgrep)"
fi

# ── 2. Snyk dependency scan ───────────────────────────────────────────────
step "Snyk — Python dependency vulnerabilities"
if command -v snyk &>/dev/null; then
  if snyk test --severity-threshold=high; then
    ok "Snyk: no high/critical vulnerabilities"
  else
    fail "Snyk: vulnerabilities found (see output above)"
    FAILED+=("snyk")
  fi
else
  warn "snyk not installed — skipping (npm install -g snyk  OR  brew install snyk)"
fi

# ── 3. Ruff (fast linter — catches some security patterns too) ────────────
step "Ruff lint"
if ruff check app/ tests/; then
  ok "Ruff: clean"
else
  fail "Ruff: issues found"
  FAILED+=("ruff")
fi

# ── 4. Bandit (optional lightweight Python security linter) ───────────────
step "Bandit (Python security linter)"
if command -v bandit &>/dev/null; then
  if bandit -r app/ -ll -q; then
    ok "Bandit: clean"
  else
    warn "Bandit: findings (medium/high severity shown above)"
    # Advisory only — not added to FAILED
  fi
else
  warn "bandit not installed — skipping (pip install bandit)"
fi

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}All security checks passed.${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}Failed checks: ${FAILED[*]}${NC}"
  echo "Fix the findings above, then re-run ./scripts/sast.sh"
  exit 1
fi

#!/usr/bin/env bash
# validate.sh — Pre-commit and post-setup validation.
# Checks for unfilled template placeholders, lint errors, and type errors.
# Exit code 0 = all clear. Non-zero = issues found.

set -euo pipefail

ERRORS=0
WARNINGS=0

echo "==> Validating project..."

# ── 1. Check for unfilled template placeholders ─────────────────────────────
echo ""
echo "--> Checking for template placeholders..."

PLACEHOLDER_PATTERNS=('\[PROJECT_NAME\]' '\[BUILD_COMMAND\]' '\[DOMAIN\]' '\[PLACEHOLDER\]' 'TODO: fill')

for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
  matches=$(grep -r "$pattern" . \
    --include="*.ts" \
    --include="*.js" \
    --include="*.json" \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    -l 2>/dev/null || true)

  if [ -n "$matches" ]; then
    echo "  WARNING: Placeholder '$pattern' found in:"
    echo "$matches" | sed 's/^/    /'
    WARNINGS=$((WARNINGS + 1))
  fi
done

# Check markdown separately (placeholders expected in template docs)
md_placeholders=$(grep -r '\[PROJECT_NAME\]' . \
  --include="*.md" \
  --exclude-dir=node_modules \
  --exclude="README.md" \
  --exclude="CLAUDE.md" \
  --exclude="*_TEMPLATE*" \
  -l 2>/dev/null || true)

if [ -n "$md_placeholders" ]; then
  echo "  WARNING: Unfilled [PROJECT_NAME] in non-template markdown:"
  echo "$md_placeholders" | sed 's/^/    /'
  WARNINGS=$((WARNINGS + 1))
fi

if [ $WARNINGS -eq 0 ]; then
  echo "  ✓ No unfilled placeholders"
fi

# ── 2. Check for leftover debug statements ──────────────────────────────────
echo ""
echo "--> Checking for debug artifacts..."

debug_matches=$(grep -r 'console\.log\|debugger;' src/ \
  --include="*.ts" \
  --include="*.js" \
  -l 2>/dev/null || true)

if [ -n "$debug_matches" ]; then
  echo "  WARNING: console.log/debugger found in:"
  echo "$debug_matches" | sed 's/^/    /'
  WARNINGS=$((WARNINGS + 1))
else
  echo "  ✓ No debug artifacts"
fi

# ── 3. Check for hardcoded secrets patterns ─────────────────────────────────
echo ""
echo "--> Checking for hardcoded secrets..."

secret_patterns=('password\s*=\s*"[^"]' "api_key\s*=\s*'" 'secret\s*=\s*"[^{]')

for pattern in "${secret_patterns[@]}"; do
  secret_matches=$(grep -ri "$pattern" src/ \
    --include="*.ts" \
    --include="*.js" \
    --include="*.json" \
    -l 2>/dev/null || true)

  if [ -n "$secret_matches" ]; then
    echo "  ERROR: Possible hardcoded secret ($pattern) in:"
    echo "$secret_matches" | sed 's/^/    /'
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $ERRORS -eq 0 ]; then
  echo "  ✓ No hardcoded secrets detected"
fi

# ── 4. Lint ──────────────────────────────────────────────────────────────────
echo ""
echo "--> Running linter..."

if npm run lint --silent 2>/dev/null; then
  echo "  ✓ Lint passed"
else
  echo "  ERROR: Lint failed"
  ERRORS=$((ERRORS + 1))
fi

# ── 5. Type check ────────────────────────────────────────────────────────────
echo ""
echo "--> Running type check..."

if npm run typecheck --silent 2>/dev/null; then
  echo "  ✓ Type check passed"
else
  echo "  ERROR: Type check failed"
  ERRORS=$((ERRORS + 1))
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "==> Validation complete"
echo "    Errors:   $ERRORS"
echo "    Warnings: $WARNINGS"
echo ""

if [ $ERRORS -gt 0 ]; then
  echo "FAILED: $ERRORS error(s) must be fixed before proceeding."
  exit 1
fi

if [ $WARNINGS -gt 0 ]; then
  echo "PASSED with $WARNINGS warning(s). Review the warnings above."
  exit 0
fi

echo "All checks passed."
exit 0

#!/usr/bin/env bash
# setup.sh — Initialize the project for local development.
# Run once after cloning. Safe to re-run.

set -euo pipefail

echo "==> [PROJECT_NAME] Setup"

# ── 1. Check prerequisites ──────────────────────────────────────────────────
echo ""
echo "--> Checking prerequisites..."

check_command() {
  if ! command -v "$1" &>/dev/null; then
    echo "ERROR: '$1' is required but not installed. Please install it and re-run."
    exit 1
  fi
  echo "  ✓ $1 found"
}

# Add your required tools here
check_command "node"
check_command "npm"
# check_command "python3"
# check_command "docker"
# check_command "psql"

# ── 2. Install dependencies ─────────────────────────────────────────────────
echo ""
echo "--> Installing dependencies..."
npm install
echo "  ✓ Dependencies installed"

# ── 3. Environment file ─────────────────────────────────────────────────────
echo ""
echo "--> Setting up environment..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  ✓ .env created from .env.example"
  echo "  ! Review .env and fill in any required values before running the app"
else
  echo "  ✓ .env already exists (skipping)"
fi

# ── 4. Database setup (if applicable) ───────────────────────────────────────
# echo ""
# echo "--> Setting up database..."
# npm run db:migrate
# echo "  ✓ Database migrated"

# ── 5. Verify setup ─────────────────────────────────────────────────────────
echo ""
echo "--> Verifying setup..."
bash scripts/validate.sh

echo ""
echo "==> Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your local configuration"
echo "  2. Run: npm test (confirm tests pass)"
echo "  3. Run: npm run dev (start development server)"

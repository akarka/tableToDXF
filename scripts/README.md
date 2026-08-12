# Scripts

Shell automation for setup, validation, and maintenance.

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `setup.sh` | Initialize local development environment | Once after cloning |
| `validate.sh` | Check for placeholders, debug artifacts, lint, types | Before commits; in CI |

---

## Running Scripts

```bash
# Make executable (once)
chmod +x scripts/*.sh

# Setup
bash scripts/setup.sh

# Validate
bash scripts/validate.sh
```

---

## Adding a New Script

- Keep scripts focused: one script, one purpose
- Always `set -euo pipefail` at the top (fail fast, catch unbound variables)
- Print clear status messages (`--> Step name...`)
- Exit with non-zero on failure
- Do NOT add scripts that deploy, migrate production data, or touch credentials

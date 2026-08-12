# Onboarding Guide

Everything needed to understand this project and start contributing — for both human developers and AI agents.

---

## For AI Agents: First-Time Setup

Read these files in this order before doing anything else:

1. `CLAUDE.md` — project mission, critical rules, tech stack, directory structure
2. `AGENTS.md` — multi-agent coordination protocol
3. `DOCS/Architecture/Architectural_Mandates.md` — non-negotiable rules
4. `DOCS/Architecture/System_Overview.md` — understand the system at a high level
5. `DOCS/Agents/AGENT_ROLES.md` — understand your role
6. `DOCS/Agents/WORKFLOW_PATTERNS.md` — understand how tasks flow

Then check your memory (`.claude/memory/MEMORY.md`) for any project-specific context.

**Do not start a task until you have read at least items 1-3.**

---

## For Human Developers: Environment Setup

### Prerequisites

- [ ] [Runtime: Node.js 20 / Python 3.12 / .NET 8 / etc.] installed
- [ ] [Package manager: npm / pip / etc.] installed
- [ ] [Database: PostgreSQL / etc.] running locally
- [ ] [Other: Docker / etc.] if applicable
- [ ] Git configured (`git config user.email`)

### Setup Steps

```bash
# 1. Clone and enter the project
git clone [REPO_URL]
cd [PROJECT_NAME]

# 2. Run the setup script
bash scripts/setup.sh

# 3. Configure environment
cp .env.example .env
# Edit .env with your local values

# 4. Run database migrations (if applicable)
[MIGRATION_COMMAND]

# 5. Verify setup
bash scripts/validate.sh

# 6. Run tests to confirm everything works
[TEST_COMMAND]
```

### Expected Output After Setup

```
✅ Dependencies installed
✅ Environment variables set
✅ Database connected
✅ Tests passing (X passed, 0 failed)
```

---

## Key Files to Understand

| File | Why It Matters |
|------|---------------|
| `CLAUDE.md` | The agent's primary instruction set; defines rules and tech stack |
| `AGENTS.md` | Multi-agent coordination; read before working with other agents |
| `DOCS/Architecture/Architectural_Mandates.md` | The non-negotiable design rules |
| `DOCS/Features/_INDEX.md` | What's been built, what's in progress, what's planned |
| `src/commands/ICommand.ts` | The interface every mutation must implement |
| `src/services/_TEMPLATE/` | The pattern every new service must follow |
| `.env.example` | All required configuration variables |

---

## Project Conventions

### File Naming
- Source files: `kebab-case.ts` (e.g., `user-service.ts`)
- Test files: `[source-name].test.ts` (e.g., `user-service.test.ts`)
- Feature docs: `F-[N].md` (e.g., `F-001.md`)
- ADRs: `ADR-[N]-[short-title].md` (e.g., `ADR-001-use-command-pattern.md`)

### Branch Naming
- Features: `feature/[short-name]`
- Bugs: `fix/[short-name]`
- Docs: `docs/[short-name]`

### Commit Message Format
```
<type>: <short description>

Types: feat | fix | refactor | test | docs | chore
Examples:
  feat: add email validation to UserService
  fix: handle null name in RenameCommand.undo()
  test: add integration test for POST /users
  docs: update F-003 with implementation decisions
```

---

## Running the Application

```bash
# Development mode (auto-reload)
[DEV_COMMAND]

# Production mode
[PROD_COMMAND]

# Run tests
[TEST_COMMAND]

# Run linter
[LINT_COMMAND]

# Check types (if TypeScript)
[TYPECHECK_COMMAND]
```

---

## Getting Help

1. Check `DOCS/Architecture/` for patterns and decisions
2. Check `DOCS/Features/` for the relevant feature spec
3. Ask the human developer for anything that requires domain knowledge not in the docs
4. If something seems wrong with the docs, say so — don't silently work around it

# Agentic Development Template

A production-ready project scaffold for software built primarily by AI coding agents (Claude Code, Gemini CLI, Cursor, GitHub Copilot Workspace, etc.).

## What This Template Provides

| Layer | Contents |
|-------|----------|
| **Agent Config** | `CLAUDE.md`, `AGENTS.md` — rules, roles, and hard constraints for AI agents |
| **Architecture** | Mandates, ADR system, system overview template |
| **Feature Docs** | Per-feature documentation with acceptance criteria |
| **Testing** | Strategy, test index, case templates, pattern library |
| **Agent Workflows** | Role definitions, workflow patterns, prompt library, memory protocol |
| **Runbooks** | Onboarding, deploy, incident response |
| **Code Scaffolding** | Service template, Command pattern, Logger, Test structure (TypeScript reference) |
| **CI/CD** | GitHub Actions pipeline: lint → test → build → security scan |

---

## Core Philosophy

> Design for the agent that will read this code at 3am, not the developer who wrote it.

AI agents perform best when:

- **Rules are explicit** — no hidden conventions, no "everyone knows" patterns
- **Context is layered** — `CLAUDE.md` → Architecture docs → Domain docs → Feature docs
- **Operations are reversible** — every mutation has an undo path
- **Tests define behavior** — specs are written before or alongside implementation
- **Decisions are recorded** — ADRs explain *why*, not just *what*
- **Human gates are named** — the template defines exactly what requires human approval

---

## Quick Start

```bash
# 1. Copy this template to your new project
cp -r agentic-dev-template my-new-project
cd my-new-project
git init

# 2. Fill in your project identity
#    CLAUDE.md         → replace [PROJECT_NAME], mission, tech stack, build command
#    DOCS/Architecture/System_Overview.md → C4-level overview of your system

# 3. Initialize
bash scripts/setup.sh

# 4. Verify no unfilled placeholders remain
bash scripts/validate.sh

# 5. Tell the agent to read CLAUDE.md before starting any task
```

---

## Directory Map

```
├── CLAUDE.md                     ← Start here (primary agent instructions)
├── AGENTS.md                     ← Multi-agent coordination protocol
├── .claude/                      ← Claude Code config + persistent memory
│   ├── settings.json
│   └── memory/
├── DOCS/
│   ├── Architecture/             ← Mandates, ADRs, system design
│   │   ├── Architectural_Mandates.md
│   │   ├── ADR_TEMPLATE.md
│   │   ├── ADR_000_EXAMPLE.md
│   │   └── System_Overview.md
│   ├── Features/                 ← Per-feature specs
│   │   ├── _INDEX.md
│   │   └── FEATURE_TEMPLATE.md
│   ├── Testing/                  ← Test strategy and registry
│   │   ├── TEST_STRATEGY.md
│   │   ├── TEST_INDEX.md
│   │   └── TESTCASE_TEMPLATE.md
│   ├── Agents/                   ← Agent roles, workflows, prompts
│   │   ├── AGENT_ROLES.md
│   │   ├── WORKFLOW_PATTERNS.md
│   │   ├── PROMPT_LIBRARY.md
│   │   └── MEMORY_PROTOCOL.md
│   └── Runbooks/                 ← Operational procedures
│       ├── ONBOARDING.md
│       ├── DEPLOY.md
│       └── INCIDENT_RESPONSE.md
├── src/
│   ├── services/_TEMPLATE/       ← Copy this to create a new service
│   ├── commands/                 ← Command pattern (undo/redo)
│   ├── models/
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── scripts/
│   ├── setup.sh
│   └── validate.sh
└── .github/workflows/ci.yml
```

---

## Removing Template Placeholders

Before first real commit, run:

```bash
bash scripts/validate.sh
```

Or manually:

```bash
grep -r "\[PROJECT" . --include="*.md"
grep -r "\[BUILD" . --include="*.md"
grep -r "TODO:" . --include="*.md" --include="*.ts"
```

---

## Adapting the Code Examples

Source files under `src/` use **TypeScript** as the reference language. The architectural patterns (Command, Service, Repository, Logger) are language-agnostic. Translate to your stack — the structure and the interfaces are what matter, not the syntax.

See `src/services/_TEMPLATE/README.md` for language-adaptation guidance.

---

## Template Principles Reference

| # | Principle | Where Encoded |
|---|-----------|--------------|
| 1 | Reversibility by default | `src/commands/`, Mandate §1 |
| 2 | Explicit over implicit | `CLAUDE.md`, `AGENTS.md` |
| 3 | Testability first | `DOCS/Testing/TEST_STRATEGY.md`, Mandate §7 |
| 4 | Human gates for risky operations | `CLAUDE.md` Critical Rules, `AGENTS.md` |
| 5 | Layered context loading | `CLAUDE.md` → Architecture → Feature |
| 6 | Decisions recorded (ADR) | `DOCS/Architecture/ADR_TEMPLATE.md` |
| 7 | Memory hygiene | `DOCS/Agents/MEMORY_PROTOCOL.md` |
| 8 | Multi-agent conflict prevention | `AGENTS.md` |
| 9 | Observable operations | Mandate §5, `src/utils/logger.ts` |
| 10 | Security baseline | Mandate §6 |

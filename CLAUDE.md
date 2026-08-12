# [PROJECT_NAME]: [ONE_LINE_DESCRIPTION]

## Project Mission

[2-3 sentences. What this software does, who it serves, why it exists.
Be specific — agents use this to judge whether a proposed change is in-scope.
Example: "A CLI tool that batch-edits JSON configuration files across monorepo packages.
Targets backend engineers who manage 50+ service configs. Replaces error-prone manual find-and-replace."]

---

## CRITICAL RULES (Read before every task)

- **NEVER run `[BUILD_COMMAND]`** — Build is always performed by the human. If build is needed, tell the user explicitly.
- **NEVER deploy** to any environment without explicit user instruction.
- **NEVER commit or push** without explicit user request.
- **NEVER modify** `.env`, secrets, API keys, or credential files.
- **NEVER delete** files, records, or data without confirming with the user.
- **NEVER force-push** or reset branches with uncommitted changes.
- Consult `DOCS/Architecture/Architectural_Mandates.md` before any structural change.
- Open a new ADR (`DOCS/Architecture/ADR_TEMPLATE.md`) before introducing a pattern not already in the codebase.

---

## Technical Architecture

- **Runtime:** [Node.js 20 / Python 3.12 / .NET 8 / Go 1.23 / etc.]
- **Framework:** [Express / FastAPI / ASP.NET / Gin / etc.]
- **Database:** [PostgreSQL / SQLite / MongoDB / Redis / etc. — or "none"]
- **Key Libraries:**
  - `[library-name]` — [one-line purpose]
  - `[library-name]` — [one-line purpose]
- **Pattern:** Command-based mutations + Stateless service layer + Repository abstraction

---

## Directory Structure

```
/src
  /services    — Domain logic; one class/module per bounded context
  /commands    — IUndoableCommand implementations; ALL mutations go here
  /models      — DTOs, domain entities, value objects (no logic)
  /utils       — Shared utilities (logger, config, validators, helpers)
/tests
  /unit        — No I/O; all dependencies mocked
  /integration — Real DB/filesystem; use fixtures
  /e2e         — Full stack; run against local environment
/DOCS
  /Architecture — Mandates, ADRs, system overview
  /Features     — Per-feature specs and acceptance criteria
  /Testing      — Strategy, test index, case templates
  /Agents       — Agent roles, workflow patterns, prompt library
  /Runbooks     — Onboarding, deploy, incident response
/scripts        — Shell automation (setup, validate, seed data)
```

---

## Architectural Mandates (Summary)

Full details: `DOCS/Architecture/Architectural_Mandates.md`

1. **All mutations are commands** — wrap in `IUndoableCommand`, execute through `CommandManager`
2. **Services are stateless** — no business state in instance variables
3. **Depend on abstractions** — services accept interfaces, not concrete implementations
4. **Validate at the boundary** — all external input validated before entering domain
5. **Log with context** — every error includes operation name, entity ID, and action
6. **No silent failures** — exceptions logged before re-throwing or converting

---

## Error Reporting

- Log prefix convention: `[APP]`, `[APP ERROR]`, `[APP WARNING]`, `[APP DEBUG]`
- Format: `[APP ERROR] op=CreateUser entityId=42 reason="email already exists"`
- Critical paths: write to log AND surface in UI/API response
- Never include stack traces or internal paths in user-facing messages

---

## Agent Coordination

This project may be developed by multiple AI agents simultaneously. See `AGENTS.md` for the full protocol.

- Run `git status` before starting any task
- Do not edit a file another agent is actively working on
- One feature branch per agent task; never commit directly to `main`

---

*Feature specs: `DOCS/Features/`*
*Architecture decisions: `DOCS/Architecture/`*
*Agent workflow guide: `DOCS/Agents/`*

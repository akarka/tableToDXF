# Multi-Agent Coordination Protocol

This project may be developed by multiple AI coding agents in parallel. This document defines how agents coordinate to prevent conflicts and maintain coherent progress.

---

## Agent Roster

| Agent | Primary Scope | Notes |
|-------|--------------|-------|
| **Claude Code** | Architecture, implementation, review | Default primary agent |
| **Gemini CLI** | Feature implementation, tests, docs | Secondary agent |
| **[Other Agent]** | [Define scope] | Add as needed |
| **Human Developer** | Build, deploy, merge, approve, unblock | Final authority on all decisions |

---

## Before Starting Any Task

Run this checklist:

```bash
git fetch origin
git status                   # check for uncommitted changes from other agents
git log --oneline -5         # check recent activity
```

Then check `DOCS/Features/_INDEX.md`:
- Verify the feature/file you're about to touch is not marked `IN_PROGRESS` by another agent
- Mark your task as `IN_PROGRESS` before beginning
- Mark it `DONE` or `BLOCKED` when you stop

---

## File Ownership Rules

- **One agent edits one file at a time.** If a file appears in another agent's active task, skip it and note the dependency.
- **`CLAUDE.md` / `AGENTS.md`** — treat as read-only during active tasks. Propose changes via a comment in your response; let the human apply them.
- **Migration files / schema changes** — never auto-generate. Always confirm with human first.
- **Lock files** (`package-lock.json`, `Pipfile.lock`, `*.lock`) — human-managed only.
- **CI/CD pipeline files** (`.github/workflows/`) — do not modify without explicit human instruction.

---

## Branch Strategy

```
main                    ← protected; human merges only
feature/[short-name]    ← one agent, one feature
fix/[short-name]        ← bug fixes
docs/[short-name]       ← documentation-only changes
refactor/[short-name]   ← refactoring with no behavior change
```

**Rules:**
- Never commit directly to `main`
- Branch names are lowercase with hyphens
- Delete branches after merge

---

## Commit Discipline

```bash
# Stage specific files — never `git add .` blindly
git add src/services/user-service.ts tests/unit/user-service.test.ts

# Commit message format: <type>: <what changed>
# Types: feat | fix | refactor | test | docs | chore
git commit -m "feat: add email validation to UserService.create"

# Never:
git push --force
git commit --amend          # only before push, never on shared branches
git reset --hard            # only with explicit human confirmation
git commit --no-verify      # only if human explicitly allows
```

---

## Handoff Protocol

When you stop mid-task and another agent may continue, write a handoff note in the relevant feature doc (`DOCS/Features/[FEATURE_NAME].md`):

```
## Agent Handoff — [DATE]

**Done:**
- [what was completed]
- Files changed: [list]

**Tests:**
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] E2E tests written

**Remaining:**
- [specific next step 1]
- [specific next step 2]

**Blockers:**
- [what's blocking, or "none"]

**Next agent should start with:**
[single most important next action]
```

---

## Escalation to Human

Stop and ask the human when:

- A decision requires domain knowledge not documented anywhere
- A change would touch more than **5 files** unexpectedly
- Tests are failing and root cause is unclear after **2 investigation attempts**
- A security-sensitive path needs modification (auth, crypto, permissions)
- Two agents have produced conflicting implementations of the same thing
- Any destructive operation: drop table, delete data, remove a public API

**Format for escalation:**
> "I need human input before continuing. Issue: [one sentence]. Options: A) ... B) ... My recommendation: A, because [reason]."

---

## Build & Deploy Policy

**Build and deploy are always human-owned.**

No agent should:
- Run `[BUILD_COMMAND]` (see `CLAUDE.md`)
- Apply database migrations in any environment
- Push to `main`
- Modify CI/CD pipeline without human review

When a build is needed, state it clearly:
> "Changes are ready. Please run `[BUILD_COMMAND]` to compile."

---

## Conflict Resolution

If two agents have made conflicting changes to the same file:

1. Do NOT silently overwrite the other agent's work
2. Present both versions clearly with a summary of the difference
3. Explain the trade-off in one sentence each
4. Wait for the human to decide
5. Implement the chosen version
6. Document the decision in the relevant ADR or feature doc

---

## Agent Behavior Standards

| Standard | What It Means |
|----------|--------------|
| **Be explicit about uncertainty** | "I'm not sure if X is the right pattern here" > silently guessing |
| **One thing at a time** | Complete the requested task before starting related cleanup |
| **No surprise refactors** | Don't restructure code outside the task scope |
| **Leave breadcrumbs** | If you stop mid-task, document where and why in the feature doc |
| **Cite your sources** | When referencing a pattern or decision, link to the ADR or mandate |
| **State what you didn't do** | "I did not write integration tests because X" is more useful than silence |

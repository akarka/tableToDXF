# Workflow Patterns

Standard playbooks for common development tasks. Each pattern defines who does what, in what order, and what the exit criteria are.

---

## Pattern 1: Feature Implementation

**Trigger:** A feature has status `PLANNED` in `DOCS/Features/_INDEX.md`
**Agents involved:** Implementor, Test Agent, Reviewer
**Human involvement:** Approves feature doc before work begins; merges PR

### Steps

```
1. [HUMAN] Feature doc (F-N.md) is complete with acceptance criteria
        ↓
2. [IMPLEMENTOR] Check git status; confirm no conflicts
        ↓
3. [IMPLEMENTOR] Create branch: git checkout -b feature/[name]
        ↓
4. [IMPLEMENTOR] Update _INDEX.md: status → IN_PROGRESS
        ↓
5. [IMPLEMENTOR] Implement: models → command → service method → handler/CLI
        ↓
6. [TEST AGENT] Write unit tests; confirm they pass
        ↓
7. [TEST AGENT] Write integration test for happy path
        ↓
8. [IMPLEMENTOR] Update F-N.md with any decisions made during implementation
        ↓
9. [IMPLEMENTOR] Update _INDEX.md: status → REVIEW
        ↓
10. [REVIEWER] Review against checklist in AGENT_ROLES.md
        ↓
11. [HUMAN] Merges to main; marks _INDEX.md as DONE
```

### Exit Criteria
- All acceptance criteria checked off in the feature doc
- Unit and integration tests passing
- No open checklist items in the reviewer's report
- No TODO comments left in changed files

---

## Pattern 2: Bug Fix

**Trigger:** A reported bug with reproduction steps
**Agents involved:** Implementor, Test Agent
**Human involvement:** Confirms reproduction; approves fix

### Steps

```
1. [HUMAN] Reports bug with: symptom, reproduction steps, expected vs. actual
        ↓
2. [IMPLEMENTOR] Reproduce the bug and identify root cause
        ↓
3. [TEST AGENT] Write a failing test that captures the bug (this is the regression test)
        ↓
4. [IMPLEMENTOR] Fix the root cause (not the symptom)
        ↓
5. [TEST AGENT] Confirm the regression test now passes
        ↓
6. [IMPLEMENTOR] Verify no other tests broke
        ↓
7. [HUMAN] Reviews and merges
```

**Key principle:** The regression test must be written BEFORE the fix. A test written after the fix may pass even with the wrong implementation.

### Exit Criteria
- Regression test: failing before fix, passing after fix
- No existing tests broken
- Root cause addressed (not patched around)

---

## Pattern 3: Refactor

**Trigger:** Code identified as violating mandates, too complex, or needing cleanup
**Agents involved:** Implementor, Architect, Reviewer
**Human involvement:** Approves scope before work begins

### Rules

1. **No behavior change.** If the refactor changes behavior, it is not a refactor — it is a feature or bug fix.
2. **Tests must pass before and after.** Run the full test suite before starting; all tests must still pass at the end.
3. **One concern at a time.** Don't rename, restructure, and improve logic in the same PR.
4. **Scope is pre-approved.** State exactly which files will change; get human confirmation before starting.

### Steps

```
1. [IMPLEMENTOR] State refactor scope: "I will change X in files A, B, C"
        ↓
2. [HUMAN] Approves scope
        ↓
3. [IMPLEMENTOR] Run tests: confirm all pass before starting
        ↓
4. [IMPLEMENTOR] Apply refactor in small commits (one logical change per commit)
        ↓
5. [IMPLEMENTOR] Run tests after each commit: confirm still passing
        ↓
6. [REVIEWER] Verify: no behavior change, mandates followed, no scope creep
        ↓
7. [HUMAN] Merges
```

---

## Pattern 4: Documentation Sync

**Trigger:** Code has changed and docs are out of date
**Agents involved:** Documentation Agent
**Human involvement:** Reviews accuracy

### Steps

```
1. [DOC AGENT] Identify stale docs (compare feature docs to implementation)
        ↓
2. [DOC AGENT] Update docs to reflect actual behavior
        ↓
3. [DOC AGENT] Flag anything that is undocumented and should be
        ↓
4. [HUMAN] Reviews for accuracy (agent may not know all implications)
```

### What to Update

- `DOCS/Features/[F-N].md` — ensure technical design section matches implementation
- `CLAUDE.md` — if the pipeline, mandates, or directory layout changed
- `README.md` — if user-facing behaviour changed
- `CLAUDE.md` — if build command, stack, or directory structure changed
- `DOCS/Runbooks/` — if operational procedures changed

---

## Pattern 5: Security Finding

**Trigger:** A security issue is identified (by agent during review, by a scan, or by a human)
**Agents involved:** Architect, Reviewer
**Human involvement:** Required for all remediation decisions

### Steps

```
1. [ANY AGENT] Report finding immediately with: location, severity, description
        ↓
2. [HUMAN] Decides: fix now (P0) / fix in next sprint (P1) / accept risk
        ↓
3. [IMPLEMENTOR] Implements fix per human direction
        ↓
4. [REVIEWER] Reviews fix does not introduce new issues
        ↓
5. [ARCHITECT] Updates Mandate §6 if pattern needs clarifying
```

**Never:** Silently fix a security issue without reporting it. The human must know what was found, even if it seems minor.

---

## Pattern 6: Agent Handoff

Use this when an agent must stop mid-task and another agent will continue.

### Handoff Checklist

Before handing off, the outgoing agent must:

- [ ] Commit all partial work to the feature branch (even WIP)
- [ ] Write a handoff note in the feature doc (see `AGENTS.md` format)
- [ ] Update `_INDEX.md` with current status and agent name
- [ ] List all files changed so far
- [ ] List what tests are passing and what tests are not yet written
- [ ] State the single most important next step
- [ ] Flag any open questions that need human input

### Incoming Agent Checklist

Before continuing:

- [ ] Read the handoff note in the feature doc
- [ ] Run `git log --oneline -10` on the feature branch
- [ ] Run the test suite: understand current state (pass/fail)
- [ ] Read the feature's acceptance criteria fresh
- [ ] Confirm your understanding of "done" before writing any code

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Harmful | Correct Pattern |
|-------------|-----------------|-----------------|
| "I'll fix it as I go" | Scope creep; untested changes | State scope upfront; get approval |
| Test after implementation | Tests that always pass are written to match the implementation | Write test spec first |
| One giant commit | Can't review, can't bisect | Small atomic commits |
| Silent refactor inside a feature PR | Reviewer can't tell what's behavior change vs. cleanup | Separate PRs for feature and refactor |
| Assuming undocumented behavior | Two agents will implement it differently | Ask the human; document the answer |
| "Best effort" error handling | Swallowed errors; hidden failures | Follow Mandate §4 strictly |

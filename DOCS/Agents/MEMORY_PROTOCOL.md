# Agent Memory Protocol

Defines what agents should remember, how to store it, and when to forget it. Consistent memory behavior prevents contradictions between sessions and keeps the memory index useful rather than cluttered.

---

## Memory Location

Claude Code memory lives in `.claude/memory/`. Each memory is a separate markdown file. `MEMORY.md` is the index.

Other agents (Gemini CLI, etc.) should maintain equivalent memory in their platform's equivalent location, or in `DOCS/Agents/memory/[agent-name]/`.

---

## What TO Save

### User Preferences and Feedback

Save when: the human corrects an agent approach, confirms an unusual choice, or states a preference.

```
Type: feedback
When to save: immediately after correction or confirmation
Format: Rule → Why → How to apply
Example:
  "Don't add print() debug statements in PRs — I can see diffs, I don't need narration"
  Saves as: feedback_no_debug_logs.md
```

### Project State

Save when: you learn about a deadline, decision, constraint, or initiative that is not in the docs.

```
Type: project
When to save: when you learn who is doing what, by when, or why
Format: Fact → Why → How this should shape suggestions
Example:
  "Auth rewrite is driven by a legal compliance requirement (session token storage)"
  Saves as: project_auth_rewrite_context.md
```

### User Profile

Save when: you learn about the user's role, expertise, or working style.

```
Type: user
When to save: when you learn something that should change how you explain or collaborate
Format: Plain description
Example:
  "User is a senior backend engineer unfamiliar with the frontend codebase"
  Saves as: user_profile.md
```

### External References

Save when: you learn where relevant information lives in external systems.

```
Type: reference
When to save: when you discover a Jira board, Slack channel, Grafana dashboard, etc.
Format: What it is → Where it is → When to use it
Example:
  "Bug tracker is Linear project PROJ-BACKEND"
  Saves as: reference_bug_tracker.md
```

---

## What NOT to Save

| Category | Why Not | Alternative |
|----------|---------|-------------|
| Code patterns and conventions | Derivable from the codebase | Read the code |
| File paths and directory structure | Derivable from `ls` / Glob | Search for the file |
| Git history (who changed what) | `git log` / `git blame` are authoritative | Use git tools |
| Current implementation of a feature | The code is the source of truth | Read the source |
| Debugging solutions or fix recipes | The fix is in the code; context is in the commit message | Read the code and git log |
| Anything already in CLAUDE.md | Redundant; CLAUDE.md is always loaded | Update CLAUDE.md instead |
| In-progress task state | Ephemeral; use the feature doc instead | Update F-N.md |
| ADR content | ADRs live in DOCS/Architecture | Keep ADRs current |

---

## Memory Lifecycle

### Before Using a Memory

Memories can go stale. Before acting on a saved memory:

1. **If the memory names a file:** verify the file still exists
2. **If the memory names a function/class:** grep for it to confirm it hasn't been renamed
3. **If the memory describes project state:** check git log for contradicting recent changes
4. **If in doubt:** read the current state; trust what you observe over what you remember

### Updating a Memory

When you discover a memory is wrong or outdated:
1. Update the memory file with the correct information
2. Note the date of the update
3. Do NOT keep the old content as "historical" — it causes confusion

### Deleting a Memory

When you discover a memory is no longer relevant:
1. Remove the file from `.claude/memory/`
2. Remove its entry from `MEMORY.md`

---

## MEMORY.md Format

```markdown
# Memory Index

- [Title](filename.md) — one-line hook: what this memory is about
- [Title](filename.md) — one-line hook
```

Rules:
- Keep under 200 lines total (the index is loaded into every context window)
- One line per entry; no multi-line entries in the index
- The hook must tell a future agent whether to read this memory, without reading it
- Organize by topic, not by date

---

## Memory File Format

```markdown
---
name: [short name]
description: [one sentence — used to judge relevance]
type: user | feedback | project | reference
---

[Content — for feedback/project, include: rule/fact, **Why:**, **How to apply:**]
```

---

## Anti-Patterns

| Anti-Pattern | Effect | Fix |
|-------------|--------|-----|
| Saving every fact learned | Index bloats; important memories buried | Save only what's non-obvious from reading the code |
| Saving implementation details | Stale on the next refactor | Read the code instead |
| Vague memory descriptions | Agent can't tell if it's relevant | Be specific: "user prefers X over Y because Z" |
| Never deleting memories | Old memories contradict current state | Audit memory when contradictions appear |
| Duplicate memories | Conflicting guidance | Check MEMORY.md before writing a new entry |

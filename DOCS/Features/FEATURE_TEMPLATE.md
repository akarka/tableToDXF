# F-[NUMBER]: [Feature Name]

**Status:** `PLANNED` | `IN_PROGRESS` | `REVIEW` | `TESTING` | `DONE` | `BLOCKED` | `CANCELLED`
**Priority:** `P0 — Critical` | `P1 — High` | `P2 — Medium` | `P3 — Low`
**Assigned Agent:** [Claude Code / Gemini CLI / unassigned]
**Requested By:** [human name or role]
**Target Date:** YYYY-MM-DD *(or "no deadline")*

---

## Goal

[One paragraph. What is this feature? What user problem does it solve?
Write from the user's perspective, not the technical perspective.
Example: "Allow users to bulk-rename files matching a glob pattern, so they don't need to process each file manually."]

---

## Acceptance Criteria

> These are the conditions that must ALL be true for the feature to be considered done.
> Write in Given/When/Then or plain-English "must" statements.

- [ ] **AC-1:** Given [context], when [action], then [observable outcome]
- [ ] **AC-2:** Given [context], when [action], then [observable outcome]
- [ ] **AC-3:** Error case — when [invalid input/state], the system [specific error behavior]
- [ ] **AC-4:** Performance — [operation] completes in under [N ms] for [N items]
- [ ] **AC-5:** Tests — unit + integration tests cover all ACs above

---

## Technical Design

### Affected Components

| Component | Change Type | Notes |
|-----------|------------|-------|
| `[ServiceName]` | New method / Modified / Unchanged | [brief note] |
| `[CommandName]` | New command class | [what it wraps] |
| `[ModelName]` | New field / Unchanged | [brief note] |
| `[HandlerName]` | New route / Modified | [brief note] |

### Data Model Changes

```python
# Yeni ya da değişen tipleri tarif et. Örnek:
@dataclass(frozen=True)
class Border:
    width_mm: float          # 0.0 = kenarlık yok
    color: Rgb
```

### New Commands

| Command Class | execute() behavior | undo() behavior |
|--------------|-------------------|-----------------|
| `[CommandName]` | [what it does] | [how it reverses] |

### Error Cases

| Condition | Error Code | User Message |
|-----------|-----------|--------------|
| [e.g., entity not found] | `ENTITY_NOT_FOUND` | "The item could not be found." |
| [e.g., name already taken] | `NAME_CONFLICT` | "That name is already in use." |

---

## Test Plan

### Unit Tests

- [ ] `[ServiceName].[methodName]` — happy path
- [ ] `[ServiceName].[methodName]` — [error condition]
- [ ] `[CommandName].execute()` — verify state change
- [ ] `[CommandName].undo()` — verify state reversal

### Integration Tests

- [ ] [Full flow description: input → service → DB → output]
- [ ] [Error flow: invalid input → validation error → correct HTTP status]

### Manual Verification

- [ ] [Step-by-step: what to do and what to observe]

---

## Agent Notes

> Use this section for handoff notes, open questions, and implementation decisions made during the work.

### Open Questions

- [ ] [Question that needs human input before implementation can proceed]

### Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| [what was decided] | [why] | YYYY-MM-DD |

### Handoff History

*(See `AGENTS.md` for handoff format)*

---

## Related

- ADR-[N]: [related architectural decision]
- F-[N]: [related feature]
- `CLAUDE.md` → Architectural Mandates §[madde]

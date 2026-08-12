# ADR-000: Use Command Pattern for All User-Initiated Mutations

**Date:** 2025-01-01
**Status:** ACCEPTED
**Deciders:** Architecture Agent, Human Developer

---

## Context

The application allows users to modify persistent data through a UI or CLI. Early prototypes used direct service method calls, where services mutated repositories directly. This caused three concrete problems:

1. **No undo path.** User mistakes (and AI agent mistakes) required manual database corrections.
2. **No audit trail.** There was no way to know what changed, when, or why.
3. **Difficult rollback.** Batch operations touching multiple entities had no atomicity guarantee from the application's perspective (the DB transaction didn't cover business-level "undo").

Compounding this: the project is primarily developed by AI agents, which have a non-zero error rate. Permanent mutations by an agent that acted incorrectly are unacceptable for user trust.

---

## Decision

We will wrap every user-initiated mutation in an `IUndoableCommand` object, executed through a central `CommandManager`. Services expose their mutation logic as methods called from within command `execute()` and `undo()` methods. Services do not mutate state when called directly from handlers.

This applies to all operations initiated by user action (UI click, CLI argument). It does not apply to background jobs or internal system maintenance.

---

## Options Considered

### Option A: Direct Service Calls (Status Quo)

Services called directly from handlers. No indirection layer.

**Pros:**
- Simple — minimal boilerplate
- Easy to follow call stack

**Cons:**
- No undo path
- No audit log
- Agent errors are permanent
- Batch rollback requires complex compensation logic

---

### Option B: Event Sourcing

Store events as the source of truth; derive current state by replaying events.

**Pros:**
- Complete history; time-travel debugging possible
- Natural audit log

**Cons:**
- Massively over-engineered for current scale
- High implementation cost (event schema design, projection rebuilding, event versioning)
- AI agents must understand event schemas to implement features — steep cognitive overhead

---

### Option C (Chosen): Command Pattern with Circular Buffer

Wrap mutations in `IUndoableCommand` objects. Keep the last N commands in a circular undo stack in memory.

**Pros:**
- Any agent-initiated mistake is undoable within the session
- Commands are independently unit-testable
- Natural audit log emerges from command execution history
- Batch operations can wrap N commands as one undo entry
- Implementation cost is proportional to feature count, not infrastructure

**Cons:**
- Every mutation requires a new command class (more files, more surface area)
- Undo is session-scoped — not persisted across application restarts (by design for now)

---

## Consequences

**Positive:**
- User and agent errors are recoverable without database intervention
- Each command is a self-contained unit of work that can be tested in isolation
- The undo stack doubles as a session audit log
- Future persistence of undo history is possible without changing the command interface

**Negative (accepted trade-offs):**
- More files per feature (service method + command class)
- Developers must remember to use `CommandManager.execute()` rather than calling services directly
- Commands must capture enough state in their constructor to reverse the operation

**Risks:**
- Developers or agents bypassing the command pattern for "small" changes — mitigated by a linting rule and code review gate
- Memory pressure from large undo buffers — mitigated by a configurable capacity cap (default: 20 entries)

---

## Related

- `DOCS/Architecture/Architectural_Mandates.md` §1 (Reversibility)
- `src/commands/README.md`
- `src/commands/ICommand.ts`
- `src/commands/CommandManager.ts`

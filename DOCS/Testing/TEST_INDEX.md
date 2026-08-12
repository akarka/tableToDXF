# Test Index

Registry of all test suites. Update this when adding or removing test files.

---

## Unit Tests

| Suite | File | Covers | Status |
|-------|------|--------|--------|
| UserService | `tests/unit/services/user-service.test.ts` | create, update, delete, findById | ✅ |
| CommandManager | `tests/unit/commands/command-manager.test.ts` | execute, undo, redo, capacity | ✅ |
| [Add rows as suites are created] | | | |

## Integration Tests

| Suite | File | Covers | Requires |
|-------|------|--------|----------|
| UserRepository | `tests/integration/repositories/user-repo.test.ts` | CRUD via real DB | Local DB |
| POST /users | `tests/integration/handlers/create-user.test.ts` | Full request cycle | Local server |
| [Add rows as suites are created] | | | |

## E2E Tests

| Flow | File | Critical Path |
|------|------|---------------|
| [Create and edit a record] | `tests/e2e/flows/create-edit.e2e.ts` | ✅ |
| [Add rows as flows are created] | | |

---

## Running Tests

```bash
# All tests
npm test

# Unit only (fast, no infrastructure)
npm run test:unit

# Integration (requires local DB)
npm run test:integration

# E2E (requires full local stack)
npm run test:e2e

# Coverage report
npm run test:coverage
```

---

## Known Skips / TODOs

| Test | Reason Skipped | Owner | Deadline |
|------|---------------|-------|----------|
| [test name] | [reason] | [agent/human] | YYYY-MM-DD |

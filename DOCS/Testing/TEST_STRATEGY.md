# Test Strategy

This document defines the testing philosophy, levels, and standards for this project. All agents must follow it. Deviations require an ADR.

---

## Core Principle

**Tests are the specification.** A test that passes is a proof that the system behaves as intended. Tests are not an afterthought — they are written alongside or before implementation.

A feature with no tests is not done.

---

## Testing Pyramid

```
         ┌─────────┐
         │   E2E   │  ← few, slow, high confidence on critical paths
         ├─────────┤
         │ Integr. │  ← moderate; test real I/O boundaries
         ├─────────┤
         │  Unit   │  ← many, fast, pure logic
         └─────────┘
```

### Unit Tests (base)

**What:** Pure domain logic — functions and methods with no I/O.
**Mock:** Everything external (repos, HTTP clients, time, randomness).
**Speed:** < 5ms per test.
**Coverage target:** > 90% branch coverage on domain logic and service layer.
**When to write:** Always. If a function has branching logic, it has unit tests.

```
tests/unit/
  services/       — service layer with mocked repos
  commands/       — command execute() and undo()
  models/         — domain model validation logic
  utils/          — utility functions
```

### Integration Tests (middle)

**What:** Tests that cross a real I/O boundary — database, filesystem, external API (use test doubles for third-party APIs).
**Mock:** External services (use stubs/wiremock). Use a real local database.
**Speed:** < 500ms per test.
**When to write:** For every repository method, every HTTP handler, every job.

```
tests/integration/
  repositories/   — real DB queries against a test database
  handlers/       — full HTTP request → response cycle
  jobs/           — background job execution with real side effects
```

### E2E Tests (top)

**What:** Full system tests from the user's entry point to the final output.
**Mock:** Nothing (uses a local running stack).
**Speed:** < 5 seconds per test.
**When to write:** For each critical user flow (the happy path + the most important error path).

```
tests/e2e/
  flows/          — user-journey scenarios
```

---

## Testing Rules

### Determinism

Tests must produce the same result every run, regardless of:
- Order of execution
- Time of day
- Other tests that ran before them
- Network state

**How:**
- No `Date.now()` or `new Date()` in tests — inject a fixed clock
- No `Math.random()` — inject a seeded random or use fixed fixtures
- No live HTTP calls in unit/integration tests — use mocks or local stubs
- No shared mutable state between tests — reset DB/state in `beforeEach`

### Isolation

Each test sets up its own data and tears it down. Tests do not depend on each other.

```typescript
// ✅ Correct — self-contained
beforeEach(async () => {
  await db.migrate.latest();
  testUser = await userFactory.create({ email: 'test@example.com' });
});

afterEach(async () => {
  await db.migrate.rollback();
});

// ❌ Wrong — depends on test order
it('finds the user created by the previous test') ...
```

### Test Naming

Test names describe observable behavior, written for a reader who doesn't know the implementation.

```typescript
// ✅ Reads like a specification
describe('UserService') {
  describe('create') {
    it('returns a user with a generated UUID when input is valid')
    it('throws UserExistsError when the email is already registered')
    it('throws ValidationError when email format is invalid')
  }
}

// ❌ Describes implementation, not behavior
describe('UserService') {
  it('calls repo.findByEmail')
  it('calls repo.save if no duplicate')
}
```

### Forbidden Patterns

| Pattern | Why Forbidden | Alternative |
|---------|--------------|-------------|
| `setTimeout` in tests | Makes tests slow and flaky | Use fake timers |
| `process.env` mutation in tests | Leaks between tests | Use a config injection |
| `console.log` for assertions | Not a real assertion | Use `expect()` |
| Testing private methods directly | Couples tests to implementation | Test through the public API |
| Snapshot tests for logic | Hides what's actually being tested | Use explicit assertions |
| `any` cast to bypass type errors in tests | Masks real bugs | Fix the type or use a typed factory |

---

## Coverage Requirements

| Layer | Branch Coverage Target |
|-------|-----------------------|
| Domain logic (pure functions) | ≥ 90% |
| Service layer | ≥ 85% |
| HTTP handlers | ≥ 80% |
| Repository layer | ≥ 75% (most complexity is in SQL, not control flow) |
| CLI handlers | ≥ 80% |

Coverage is a floor, not a goal. 100% coverage with bad tests is worse than 70% with good tests.

---

## Test Fixtures and Factories

Fixtures live in `tests/fixtures/`. See `tests/fixtures/README.md`.

**Use object factories** (builder pattern) for test data, not raw object literals:

```typescript
// ✅ Correct — readable, maintainable
const user = userFactory.build({ role: 'admin' });

// ❌ Wrong — brittle, verbose, breaks when model changes
const user = { id: '123', name: 'Test', email: 'test@test.com', role: 'admin', createdAt: new Date() };
```

---

## Agentic Testing Notes

When an AI agent writes tests:

1. **Write the test description first** (what behavior should be true?) before writing the implementation
2. **Red-green check:** state in the PR whether you verified the test fails before the implementation and passes after
3. **Do not use mocks to test that a mock was called** — this tests nothing about behavior
4. **If a test is hard to write**, that's a signal the code under test has too many responsibilities — raise it before implementing around it
5. **Do not generate tests with random data** unless using a property-based testing library with a fixed seed

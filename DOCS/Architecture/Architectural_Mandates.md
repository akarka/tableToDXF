# Architectural Mandates

These rules are **non-negotiable**. No feature, fix, or refactor may violate them.

If you believe a mandate needs to change, open an ADR. Do not silently deviate.

---

## Mandate 1: Reversibility (Command Pattern)

**Rule:** Every user-initiated mutation MUST be wrapped in an `IUndoableCommand` and executed through `CommandManager`.

**Why this matters:** AI agents and users both make mistakes. Without undo, errors become permanent data loss. The command pattern also forces explicit modeling of "what this operation does" separately from "how it works."

**Applies to:** All write operations (create, update, delete) triggered by user action.

**Exempt:** Internal system state (caches, counters, metrics), background jobs, read operations.

```typescript
// ✅ Correct
const cmd = new RenameItemCommand(itemId, newName, { previousName: item.name });
await commandManager.execute(cmd);

// ❌ Wrong — mutation outside the command layer
await repo.update(itemId, { name: newName });
```

**Testing:** Commands must be unit-testable in isolation. `execute()` → verify state. `undo()` → verify state reverted.

---

## Mandate 2: Stateless Services

**Rule:** Services must be stateless. No instance variables that hold business state between calls.

**Rule:** Services depend on interfaces, never on concrete implementations.

**Why this matters:** Stateful services create hidden coupling and require careful test ordering. Interface dependencies make unit testing trivial (swap the real repo for a fake).

```typescript
// ✅ Correct
class UserService {
  constructor(
    private readonly repo: IUserRepository,
    private readonly logger: ILogger
  ) {}

  async create(dto: CreateUserDto): Promise<User> { ... }
}

// ❌ Wrong — concrete dependency, testable only with a real DB
class UserService {
  private repo = new PostgresUserRepository(process.env.DATABASE_URL);
}
```

---

## Mandate 3: Boundary Validation

**Rule:** All external input MUST be validated at the system boundary before entering domain logic.

**Boundaries:** HTTP handlers, CLI argument parsers, file readers, message queue consumers, IPC handlers, webhook receivers.

**Rule:** Domain functions may assume their inputs are valid. Assertions inside domain code are for programmer errors only (invariants), not user input errors.

**Why this matters:** Mixing validation with business logic creates combinatorial test cases and obscures the domain model.

```typescript
// ✅ Correct — validate at handler, domain receives clean data
async function handleCreateUser(req: Request): Promise<Response> {
  const dto = CreateUserDto.parse(req.body);   // throws ValidationError on bad input
  const user = await userService.create(dto);
  return Response.ok(user);
}

// ❌ Wrong — domain doing boundary validation
async function createUser(name?: string, email?: string) {
  if (!name) throw new Error("name required");
  if (!email?.includes('@')) throw new Error("invalid email");
  // ... actual logic buried after guards
}
```

---

## Mandate 4: Error Handling Protocol

**Rule:** Never swallow exceptions silently.

**Rule:** Log error context (operation, entity ID, user action) BEFORE re-throwing or converting.

**Rule:** Convert infrastructure exceptions (DB errors, network errors) to domain exceptions at the service boundary. Callers should not need to know which database you use.

**Rule:** User-facing errors carry a stable error code (string, for i18n) and a safe message. Never expose stack traces, internal paths, or database details to callers.

```typescript
// ✅ Correct
try {
  await repo.save(user);
} catch (err) {
  this.logger.error('UserService.create failed', {
    userId: user.id,
    operation: 'create',
    reason: err instanceof Error ? err.message : String(err)
  });
  throw new DomainError('USER_SAVE_FAILED', 'Could not save user');
}

// ❌ Wrong — swallowed error
try {
  await repo.save(user);
} catch {
  return null;   // caller has no idea what happened
}
```

---

## Mandate 5: Logging Standards

**Rule:** Structured logs only. Key-value pairs, not interpolated strings.

```typescript
// ✅ Correct — parseable by log aggregators
logger.info('UserService.create', { userId, email, durationMs: 42 });

// ❌ Wrong — unsearchable string
logger.info(`Created user ${userId} with email ${email} in 42ms`);
```

**Levels:**

| Level | When to Use |
|-------|-------------|
| `error` | Something failed; a human must investigate |
| `warn` | Unexpected state; system recovered; may indicate a bug |
| `info` | Normal operational events (request received, job completed, state changed) |
| `debug` | Diagnostic detail; disabled in production by default |

**Required context in every log entry:** operation name + entity ID (if applicable) + outcome.

---

## Mandate 6: Security Baseline

### Secrets Management
- **No secrets in source code.** Not in comments, not in defaults, not in test fixtures.
- **No secrets in log output.** Redact tokens, passwords, and PII before logging.
- Secrets loaded from environment variables or a dedicated secret manager only.
- Provide `.env.example` with required keys and safe example values (never commit `.env`).

### Input Sanitization
- **SQL:** Parameterized queries only. Never concatenate user input into SQL strings.
- **HTML output:** Use template engine auto-escaping. Never call `innerHTML` with user data.
- **File paths:** Resolve paths and validate they fall within the allowed directory.
- **Shell commands:** Use argument arrays, never string interpolation of user input.

### Authentication & Authorization
- Never implement custom cryptographic primitives — use established libraries.
- Validate permissions at the **service layer**, not only at the UI or route handler.
- Log all authorization failures with the attempted operation and identity.

### Dependencies
- Run `npm audit` / `pip-audit` / equivalent in CI.
- No production dependencies with known high or critical CVEs.
- Review changelogs before major version upgrades.

---

## Mandate 7: Testing Requirements

**Rule:** No feature is "done" without tests at the appropriate level.

| Code Type | Required Tests |
|-----------|---------------|
| Pure domain logic | Unit tests; > 90% branch coverage |
| Service layer | Unit tests with mocked repositories |
| Repository layer | Integration tests with real data store |
| HTTP/CLI handlers | Integration tests (full request → response) |
| Critical user flows | E2E test for the happy path |

**Rule:** Tests must be deterministic. No `Math.random()`, `Date.now()`, or live network calls in unit tests. Use dependency injection or mocking for all external state.

**Rule:** Test names describe observable behavior, not implementation details.

```typescript
// ✅ Describes behavior
describe('UserService.create') {
  it('throws UserExistsError when email is already registered')
  it('returns the created user with a generated ID')
}

// ❌ Describes implementation
describe('UserService.create') {
  it('calls repo.findByEmail once')
  it('calls repo.save with the DTO')
}
```

---

## Mandate 8: Dependency Management

**Rule:** No circular dependencies between modules. Use a linter rule to enforce this (`eslint-plugin-import` cycles rule or equivalent).

**Rule:** `src/` modules must not import from `tests/`.

**Rule:** Prefer shallow dependency trees. If a utility is used by only one module, it belongs in that module's directory, not in `utils/`.

**Rule:** Do not add an external dependency for functionality that can be implemented correctly in fewer than 20 lines.

---

## Mandate 9: Async & Concurrency

**Rule:** No blocking I/O on the main thread or event loop.

**Rule:** All async operations have timeout handling. Never await indefinitely.

**Rule:** Concurrent mutations to the same entity require either optimistic locking (version field) or explicit serialization (queue, mutex). Document which approach is used per entity type.

---

## Mandate 10: Configuration Management

**Rule:** All configuration values come from environment variables or a config file. No hardcoded values in business logic.

**Rule:** Application fails fast on missing required config — at startup, not at runtime when the value is first needed.

**Rule:** Provide `.env.example` listing every required and optional variable with a description.

```typescript
// ✅ Fail fast at startup
const config = {
  dbUrl: requireEnv('DATABASE_URL'),
  port: parseInt(process.env.PORT ?? '3000', 10),
  debug: process.env.DEBUG === 'true',
};

function requireEnv(name: string): string {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required environment variable: ${name}`);
  return val;
}

// ❌ Fails silently at runtime, far from the config problem
async function connectDb() {
  await db.connect(process.env.DATABASE_URL);  // undefined passed silently
}
```

---

## Mandate Exceptions

If a mandate genuinely cannot apply to a specific case:

1. Create an ADR documenting why the exception is necessary
2. Add a code comment on the exception site referencing the ADR: `// ADR-007: exception — read-only projection does not need a command`
3. Get human review before merging the exception

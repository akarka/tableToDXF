# Test Patterns Reference

Common patterns and recipes for writing tests in this project. See `DOCS/Testing/TEST_STRATEGY.md` for the full strategy.

---

## Pattern 1: Service Unit Test

```typescript
// Arrange: mock all dependencies with fresh mocks per test
function makeMocks() {
  const repo: jest.Mocked<IUserRepository> = {
    findById: jest.fn(),
    save: jest.fn(),
    delete: jest.fn(),
  };
  const logger = { info: jest.fn(), error: jest.fn(), warn: jest.fn() };
  const service = new UserService(repo, logger);
  return { repo, logger, service };
}

it('throws UserNotFoundError when user does not exist', async () => {
  const { repo, service } = makeMocks();
  repo.findById.mockResolvedValue(null);  // Arrange

  await expect(service.findById('missing')).rejects.toThrow(UserNotFoundError);  // Act + Assert
});
```

---

## Pattern 2: Command Unit Test

```typescript
it('execute() renames the item and undo() reverses it', async () => {
  const service = { rename: jest.fn() };

  const cmd = new RenameItemCommand('item-1', 'New Name', service, {
    previousName: 'Old Name',
  });

  await cmd.execute();
  expect(service.rename).toHaveBeenCalledWith('item-1', 'New Name');

  await cmd.undo();
  expect(service.rename).toHaveBeenCalledWith('item-1', 'Old Name');
});
```

---

## Pattern 3: Integration Test (HTTP Handler)

```typescript
// Uses supertest or equivalent; real command manager; real service; real DB
describe('POST /users', () => {
  beforeEach(async () => {
    await db.seed([]);  // clean state
  });

  it('returns 201 with the created user on valid input', async () => {
    const response = await request(app)
      .post('/users')
      .send({ name: 'Alice', email: 'alice@example.com' });

    expect(response.status).toBe(201);
    expect(response.body.id).toBeDefined();
    expect(response.body.email).toBe('alice@example.com');

    // Verify DB state
    const saved = await userRepo.findById(response.body.id);
    expect(saved).not.toBeNull();
  });

  it('returns 400 when email is missing', async () => {
    const response = await request(app)
      .post('/users')
      .send({ name: 'Alice' });

    expect(response.status).toBe(400);
    expect(response.body.code).toBe('VALIDATION_ERROR');
  });
});
```

---

## Pattern 4: Time-Dependent Logic

Inject a clock — never use `new Date()` directly in testable code.

```typescript
// Production
interface IClock {
  now(): Date;
}
const realClock: IClock = { now: () => new Date() };

// Test
const fixedClock: IClock = { now: () => new Date('2025-06-01T12:00:00Z') };

// Usage in service
const entity = { ...dto, createdAt: this.clock.now() };
```

---

## Pattern 5: Error Case Coverage Checklist

For every service method, cover:
- [ ] Happy path
- [ ] Entity/resource not found
- [ ] Validation failure (if service validates)
- [ ] Repository failure (mock `.save()` to reject)
- [ ] Any domain-specific conflict (e.g., duplicate, state mismatch)

---

## Pattern 6: Test Data Factories

Avoid raw object literals. Use factories so tests don't break when the model changes.

```typescript
// tests/fixtures/factories.ts
export function makeUser(overrides: Partial<UserEntity> = {}): UserEntity {
  return {
    id: 'default-user-id',
    name: 'Test User',
    email: 'test@example.com',
    createdAt: new Date('2025-01-01'),
    updatedAt: new Date('2025-01-01'),
    ...overrides,
  };
}
```

---

## Pattern 7: Asserting Logs

When verifying that an error is logged (not just thrown):

```typescript
it('logs an error with operation context when save fails', async () => {
  const { repo, logger, service } = makeMocks();
  repo.save.mockRejectedValue(new Error('disk full'));

  try { await service.create(dto); } catch {}

  expect(logger.error).toHaveBeenCalledWith(
    expect.stringMatching(/UserService\.create/),
    expect.objectContaining({
      reason: expect.any(String),
    })
  );
});
```

---

## Anti-Patterns

| Anti-Pattern | Effect | Fix |
|-------------|--------|-----|
| `expect(mockFn).toHaveBeenCalled()` as the only assertion | Tests implementation, not behavior | Assert the state change or return value |
| `try/catch` suppressing assertion failures | Tests always pass | Use `rejects.toThrow()` |
| Shared mutable state between tests | Flaky; order-dependent | Fresh mocks in `beforeEach` |
| Testing private methods | Brittle; breaks on refactor | Test via public API |
| `setTimeout` in tests | Slow and flaky | Use fake timers |

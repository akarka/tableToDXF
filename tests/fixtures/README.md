# Test Fixtures

Test data, factories, and seed scripts for tests.

---

## Structure

```
fixtures/
  factories.ts      — Object factories (build in-memory test data)
  seed.ts           — Database seed for integration/e2e tests
  data/             — Static JSON/CSV test data (for file-processing tests)
```

---

## Using Factories

```typescript
import { makeUser, makeItem } from '../fixtures/factories';

const user = makeUser({ role: 'admin' });
const item = makeItem({ ownerId: user.id, name: 'My Item' });
```

---

## Writing a Factory

Every domain entity should have a factory. Rules:

- Always provide safe defaults for all required fields
- Accept `Partial<T>` overrides
- Use fixed (not random) defaults — `id: 'test-user-id'`, not `uuid()`
- If the test needs a unique value, pass it explicitly

```typescript
// factories.ts
export function makeUser(overrides: Partial<UserEntity> = {}): UserEntity {
  return {
    id: 'test-user-id',
    name: 'Test User',
    email: 'test@example.com',
    role: 'user',
    createdAt: new Date('2025-01-01T00:00:00Z'),
    updatedAt: new Date('2025-01-01T00:00:00Z'),
    ...overrides,
  };
}
```

---

## Database Seed (Integration Tests)

The seed script populates the test database with a known state:

```typescript
// seed.ts
export async function seedTestDatabase(db: Database): Promise<void> {
  await db.table('users').insert([
    makeUser({ id: 'seed-user-1', email: 'alice@example.com' }),
    makeUser({ id: 'seed-user-2', email: 'bob@example.com', role: 'admin' }),
  ]);
}
```

**Rule:** Integration tests that need data should call the seed function in `beforeEach` and roll back in `afterEach`. Do not assume data left over from a previous test.

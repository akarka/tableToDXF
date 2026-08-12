# Utils

Shared utilities used across multiple services or layers.

**Rule:** If a utility is only used by one service, it belongs in that service's directory, not here.

---

## `logger.ts`

Structured logger with key=value output format.

```typescript
import { createLogger, nullLogger } from './logger';

// Production use
const logger = createLogger({ prefix: 'UserService', level: 'info' });
logger.info('create', { userId: 'u1', email: 'a@b.com' });
// → 2025-01-01T00:00:00.000Z INFO [UserService] create userId="u1" email="a@b.com"

// In tests — suppress all output
const logger = nullLogger;
```

---

## Adding a New Utility

Before adding:
1. Is this logic used in more than one module? If not, put it in the module.
2. Is there an existing library that does this in < 5 lines? Use the library.
3. Is this purely a utility (no domain knowledge, no side effects)? If it has domain knowledge, it belongs in a service.

After adding:
- Export from `utils/index.ts` (if this project uses barrel exports)
- Add an entry to this README

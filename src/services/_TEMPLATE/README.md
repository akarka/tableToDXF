# Service Template

Copy this directory to create a new service:

```bash
cp -r src/services/_TEMPLATE src/services/[domain-name]
```

Then:
1. Rename `service.ts` → `[domain-name]-service.ts`
2. Rename `service.test.ts` → `[domain-name]-service.test.ts`
3. Replace all `[DOMAIN]` placeholders
4. Define the interface your service needs from its dependencies
5. Register in your DI container

---

## Service Rules (from Architectural Mandates §2)

- **Stateless** — no business state in instance variables
- **Interface-dependent** — accept `IRepository`, not `PostgresRepository`
- **No direct mutations** — call service methods from within command `execute()`/`undo()`; the service itself does not call `CommandManager`
- **Validate at boundary** — if called directly from a non-handler (e.g., another service or a background job), validate inputs here

---

## Language Adaptation Guide

The reference implementation is TypeScript. To adapt:

| TypeScript | Python | Go | C# |
|-----------|--------|----|----|
| `interface I[X]` | `Protocol` or `ABC` | `type I[X] interface` | `interface I[X]` |
| `class [X]Service` | `class [X]Service` | `type [X]Service struct` | `class [X]Service` |
| `async/await` | `async/await` | goroutine + channel | `async Task` |
| `readonly` constructor param | `__init__` + `@property` | unexported field | `readonly` field |
| `Result<T>` pattern | `tuple` or `dataclass` | `(T, error)` | `Result<T>` |

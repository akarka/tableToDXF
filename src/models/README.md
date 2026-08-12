# Models

Domain entities, DTOs (Data Transfer Objects), and value objects.

---

## Conventions

### Entities
- Have a stable `id` (UUID or string handle)
- Track `createdAt` and `updatedAt`
- Represent persisted domain objects

### DTOs
- Carry data across boundaries (HTTP body → service, service → HTTP response)
- Prefix with operation name: `CreateUserDto`, `UpdateUserDto`, `UserResponseDto`
- No methods, no behavior — pure data bags

### Value Objects
- Immutable; identified by their value, not an ID
- Examples: `Email`, `Money`, `DateRange`
- Belong here if used across multiple services; otherwise in the owning service's directory

---

## What Does NOT Belong Here

- Business logic (belongs in services)
- Database query logic (belongs in repositories)
- Validation rules (belong at the boundary — handlers or DTO parsers)

---

## Example Structure

```
models/
  user.ts          — UserEntity, CreateUserDto, UpdateUserDto, UserResponseDto
  email.ts         — Email value object with format validation
  pagination.ts    — PaginationParams, PaginatedResult<T>
```

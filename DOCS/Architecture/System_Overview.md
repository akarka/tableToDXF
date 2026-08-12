# System Overview

> **Template:** Replace all `[PLACEHOLDER]` sections with your project specifics.
> This document follows the [C4 model](https://c4model.com/) — Context → Containers → Components.

---

## C1: System Context

**[PROJECT_NAME]** is a [type: CLI tool / web service / desktop app / library] that [core purpose in one sentence].

```
         [External Actor / User]
                  │
                  │  [how they interact: HTTP / CLI / SDK / GUI]
                  ▼
    ┌─────────────────────────┐
    │      [PROJECT_NAME]     │◄──── [External System A: e.g. OAuth Provider]
    │                         │
    │                         │────► [External System B: e.g. Storage]
    └─────────────────────────┘
                  │
                  ▼
         [Data Store / Output]
```

### Users

| User Type | How They Interact | Primary Goal |
|-----------|------------------|--------------|
| [Power User] | [CLI / Web UI] | [e.g., batch process 100 files] |
| [End User] | [Web UI / API] | [e.g., view and edit records] |
| [Admin] | [Config file / Admin UI] | [e.g., configure system behavior] |

### External Dependencies

| System | Direction | Purpose | Failure Impact |
|--------|-----------|---------|----------------|
| [Dep A] | outbound | [what we call it for] | [degraded / fatal] |
| [Dep B] | inbound | [who calls us] | [none / blocks callers] |

---

## C2: Container Diagram

```
[PROJECT_NAME]
├── [API / CLI Layer]        — entry point; validates input; routes to services
├── [Service Layer]          — domain logic; orchestrates commands and repos
├── [Command Layer]          — undo/redo; wraps all mutations
├── [Repository Layer]       — data access abstraction
├── [Database / Store]       — [PostgreSQL / SQLite / file system / etc.]
└── [Background Worker]      — [scheduled jobs / async processing, if applicable]
```

---

## Key Flows

### [Primary Flow: e.g., "User Creates a Record"]

```
User Input
    │
    ▼
[Input Validator]    ← throws ValidationError on bad input
    │
    ▼
[Service.create()]   ← pure domain logic
    │
    ▼
[CreateCommand]      ← wraps mutation; pushed to undo stack
    │
    ▼
[Repository.save()]  ← persists to data store
    │
    ▼
Return result to user
```

### [Secondary Flow: e.g., "Background Sync Job"]

1. Scheduler triggers job every N minutes
2. Job reads source data
3. Job calls Service (bypasses command pattern — background, not user-initiated)
4. Result written to store
5. Status logged

---

## Non-Functional Requirements

| Attribute | Target | How Measured |
|-----------|--------|--------------|
| Response latency | < 200ms p95 | APM / request logs |
| Throughput | [N req/s] | Load test |
| Availability | 99.9% | Uptime monitor |
| Data retention | [N days] | Scheduled cleanup job |
| Max payload size | [N MB] | Enforced at boundary |

---

## Known Constraints

- [Constraint 1: e.g., "Must run on Windows x64 — no Linux/Mac support required"]
- [Constraint 2: e.g., "Cannot use external auth providers — all auth is internal"]
- [Constraint 3: e.g., "Max 10MB payload due to upstream gateway limit"]

---

## Out of Scope

Explicitly documenting what this system does NOT do prevents scope creep and clarifies agent task boundaries.

- [Feature A — e.g., "Real-time collaboration — use a dedicated sync service instead"]
- [Feature B — e.g., "Mobile client — web-only for now"]
- [Feature C — e.g., "Multi-tenancy — single-org deployment only"]

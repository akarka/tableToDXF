# Feature Index

This is the single source of truth for all feature work. Agents must check this before starting a task and update it when status changes.

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| `PLANNED` | Accepted for implementation; not started |
| `IN_PROGRESS` | Actively being worked on (include agent name) |
| `REVIEW` | Implementation done; awaiting code review |
| `TESTING` | In QA / test writing phase |
| `DONE` | Merged and deployed |
| `BLOCKED` | Cannot proceed; reason documented in feature file |
| `CANCELLED` | Will not be built; reason documented |

---

## Active Features

| ID | Feature | Status | Agent | Feature Doc |
|----|---------|--------|-------|-------------|
| F-001 | `.ods` seçiminden DXF tablo bloğu üretimi | `REVIEW` | Claude Code | [F-001.md](F-001.md) |

`REVIEW` gerekçesi: kod ve 168 otomatik test tamam; F-001'deki **Manual Verification** adımları
(AutoCAD'de görsel karşılaştırma, blok yeniden tanımlama, `ETRANSMIT`) insana bağlı ve bekliyor.

---

## Completed Features

| ID | Feature | Completed | Notes |
|----|---------|-----------|-------|
| — | — | — | — |

---

## Adding a New Feature

1. Copy `FEATURE_TEMPLATE.md` → `F-[next number].md`
2. Fill in all sections
3. Add a row to the Active Features table above
4. Set status to `PLANNED`
5. Assign to an agent when work begins (status → `IN_PROGRESS`)

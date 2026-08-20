# Test Case Template

Use this template to specify a test case before writing code. Specification-first testing reduces the chance of writing tests that pass trivially or test the wrong thing.

---

## TC-[NUMBER]: [Short Description of What Is Being Tested]

**Type:** `Unit` | `Integration` | `E2E`
**Layer:** `Service` | `Repository` | `Handler` | `Command` | `Flow`
**Feature:** F-[N] *(link to feature doc)*
**Priority:** `Required` | `Important` | `Nice to have`
**Status:** `NOT WRITTEN` | `WRITTEN — PASSING` | `WRITTEN — FAILING` | `SKIPPED`

---

### Scenario

> Describe what situation is being tested. Give enough context that someone unfamiliar with the code could understand the intent.

**Given:** [initial state / preconditions]
**When:** [action / trigger]
**Then:** [expected observable outcome]

---

### Test Data

```
Input:  [describe input, or paste the fixture/factory call]
Setup:  [describe DB state, mocked return values, or environment]
```

---

### Expected Outcome

```
Return value:  [describe or show the expected return]
Side effects:  [describe DB writes, log entries, events emitted, etc.]
Error thrown:  [describe error type and message if testing an error path]
```

---

### Edge Cases Covered by This Test

- [edge case 1: e.g., empty array input]
- [edge case 2: e.g., Unicode characters in name]
- [edge case 3: e.g., concurrent execution]

---

### Notes for Agent Implementing This Test

- [Implementation hint: e.g., "Use the `userFactory.build()` helper, not raw objects"]
- [Gotcha: e.g., "The service is async — make sure to `await` the result before asserting"]
- [Scope reminder: e.g., "This is a unit test — mock the repository, do not hit the DB"]

---

## Example — Filled In

### TC-007: UserService.create throws when email is duplicate

**Type:** Unit
**Layer:** Service
**Feature:** F-001
**Priority:** Required
**Status:** WRITTEN — PASSING

**Given:** Seçimin kenarını kesen bir birleştirme (`C4:D4`, seçim `B2:C7`)
**When:** `ods_reader.read(...)` çağrılır
**Then:** `MERGE_CROSSES_SELECTION` koduyla `TableToDxfError` atar ve hiçbir dosya yazılmaz

**Setup:**
```python
spec = SheetSpec(name="Mahal", col_widths=["2cm", "2cm", "2cm"], rows=[...])
source = build_ods(tmp_path / "kaynak.ods", [spec])
```

**Expected:**
```python
with pytest.raises(TableToDxfError) as excinfo:
    ods_reader.read(source, "Mahal", "B2:C7", report)
assert excinfo.value.code == MERGE_CROSSES_SELECTION
assert not list(tmp_path.glob("*.dxf"))
```

**Edge cases covered:**
- Seçimin tamamen içinde kalan birleştirme hata **vermez** (sınır durumu)

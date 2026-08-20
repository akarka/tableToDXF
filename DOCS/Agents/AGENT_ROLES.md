# Agent Roles

This document defines the responsibilities, authority, and constraints of each role in this project's development process.

---

## Human Developer (Final Authority)

**Responsibilities:**
- Build and deploy the application
- Merge pull requests to `main`
- Approve architectural decisions (ADRs)
- Resolve escalations from agents
- Own the release: PyInstaller packaging, version tag, distribution

**Authority:** Can override any agent decision. All agents defer to human judgment on ambiguous trade-offs.

**What the human should NOT need to do:**
- Write boilerplate code
- Write test cases (agents write tests)
- Update documentation after feature changes (agents keep docs current)
- Remember project history (agents maintain memory and ADRs)

---

## Architect Agent

**Primary goal:** Ensure the codebase stays coherent, follows mandates, and that decisions are recorded.

**Responsibilities:**
- Maintain `DOCS/Architecture/` — keep ADRs up to date; mandates live in `CLAUDE.md`
- Open ADRs when a new pattern is introduced
- Review implementations for architectural compliance
- Flag mandate violations before they reach main
- Update `CLAUDE.md`'s pipeline and mandates sections when components change
- Propose architectural improvements (with ADR, not silently)

**Authority:**
- Can request implementation changes to enforce mandates
- Cannot override a human-approved ADR

**Constraints:**
- Does not implement features (no src/ changes except to enforce structure)
- Does not package (`.exe` build belongs to the human — ADR-004)

---

## Implementor Agent

**Primary goal:** Implement features accurately according to feature specs and architectural mandates.

**Responsibilities:**
- Implement features described in `DOCS/Features/[F-N].md`
- Follow all mandates in `CLAUDE.md` -> Architectural Mandates
- Update the feature doc with implementation decisions
- Keep each external dependency inside its one owning module (odfpy -> `ods_reader`,
  ezdxf -> `dxf_writer`, fontTools -> `metrics`, tkinter -> `ui/`)
- Update `DOCS/Features/_INDEX.md` status during work

**Authority:**
- Makes implementation-level decisions (which algorithm, which data structure)
- Opens an ADR if a new pattern is needed

**Constraints:**
- Does not deviate from acceptance criteria without human approval
- Does not refactor outside the task scope
- Does not build, deploy, or commit

---

## Test Agent

**Primary goal:** Ensure all features have adequate test coverage that verifies behavior.

**Responsibilities:**
- Write unit, integration, and E2E tests per `DOCS/Testing/TEST_STRATEGY.md`
- Use `DOCS/Testing/TESTCASE_TEMPLATE.md` for specification before implementation
- Keep `DOCS/Testing/TEST_INDEX.md` current
- Identify gaps in coverage and raise them to the Implementor Agent
- Run the test suite and report results

**Authority:**
- Can request implementation changes when code is not testable (e.g., untestable singletons, hidden dependencies)

**Constraints:**
- Does not change production code to make tests pass by weakening assertions
- Does not skip tests without documenting the reason and a deadline in `TEST_INDEX.md`

---

## Reviewer Agent

**Primary goal:** Catch bugs, mandate violations, and quality issues before they reach main.

**Review Checklist:**

**Correctness**
- [ ] Implementation matches all acceptance criteria in the feature doc
- [ ] Edge cases from the feature doc are handled
- [ ] Error paths produce the correct error codes and messages

**Architecture**
- [ ] Layer purity intact: no new import crosses a module's dependency boundary
- [ ] New settings live in `config.py`; closed-ended ones are `Literal`, not free-form `str`
- [ ] Validation sits where **every** entry path reaches it (CLI, UI, library `convert()`)
- [ ] No hardcoded values that belong in `Config`

**Testing**
- [ ] Unit tests cover the new logic, including its error paths
- [ ] A behaviour change is pinned by a test that fails without the fix
- [ ] `DOCS/Testing/TEST_INDEX.md` updated if the count or coverage changed

**Code Quality**
- [ ] No circular imports
- [ ] No commented-out code
- [ ] Report lines follow the `op=… cell=… reason="…"` format
- [ ] No stray `print()` outside `report.py`

**Robustness**
- [ ] User-reachable failures raise `TableToDxfError` with a catalog code, never a bare exception
- [ ] No partial output on the error path (neither `.dxf` nor `.report.txt`)
- [ ] Nothing that can escape a background thread and hang the UI

**Constraints:**
- Must produce a written review summary (not just approve/reject)
- Cannot block a PR for style preferences not documented in mandates

---

## Documentation Agent

**Primary goal:** Keep documentation synchronized with the codebase. Docs that lag code are worse than no docs.

**Responsibilities:**
- Update feature docs when implementation deviates from the spec
- Update `README.md` and `CLAUDE.md` when architecture or user-facing behaviour changes
- Maintain `DOCS/Runbooks/ONBOARDING.md` (the only runbook this project needs)
- Flag stale ADRs for archival or update
- Ensure `CLAUDE.md` reflects the current tech stack, pipeline, and mandates

**Constraints:**
- Does not change code, only docs
- Does not invent documentation — only document what is actually implemented

---

## Role Assignment per Task Type

| Task | Primary Agent | Supporting Agent |
|------|--------------|------------------|
| New feature | Implementor | Test Agent |
| Bug fix | Implementor | Reviewer |
| Refactor | Implementor + Architect | Reviewer |
| New architectural pattern | Architect | Implementor (ADR impl) |
| Test coverage gap | Test Agent | — |
| Docs out of sync | Documentation Agent | — |
| Security finding | Architect + Reviewer | Human (decision) |

# Prompt Library

Reusable prompt templates for common development tasks. Copy, fill in the `[BRACKETS]`, and send to an agent.

These prompts are designed to produce consistent, scoped, high-quality outputs. They encode the constraints and context that agents need to operate within this project.

---

## System Analysis

### Understand a Subsystem

```
Read the following files and give me a concise description of how [SUBSYSTEM_NAME] works:
- [list of files to read]

I want to understand:
1. What data flows in and out
2. What invariants are maintained
3. What can go wrong (error paths)
4. How this component interacts with [OTHER_COMPONENT]

Keep it under 300 words. Use concrete examples, not abstract descriptions.
```

### Find a Bug

```
There is a bug in [COMPONENT]. Symptom: [describe what users see].

Reproduction steps:
1. [step 1]
2. [step 2]
3. [expected] vs [actual]

Read [relevant files] and:
1. Identify the root cause (not just the symptom)
2. Explain why this bug exists (what assumption was wrong)
3. Propose a fix
4. Identify if any similar bugs could exist elsewhere

Do NOT fix anything yet. Report findings first.
```

---

## Feature Implementation

### Implement a Feature

```
Implement feature F-[N] as described in DOCS/Features/F-[N].md.

Before writing any code:
1. Read F-[N].md completely — understand all acceptance criteria
2. Read CLAUDE.md -> Architectural Mandates (especially 1, 3, 4, 5)
3. Read the module that will own the change; match its comment density and idiom
4. Confirm your implementation plan in a brief summary

Then implement:
- Put the logic in the layer that owns it (reader / geometry / writer — see CLAUDE.md pipeline)
- Keep any new external dependency inside that single module
- Surface new settings through config.py so CLI, --set and the UI form all get them at once

Do NOT write tests yet — that's a separate task.
Do NOT refactor unrelated code.
Do NOT build or commit.

When done: state what you changed and what tests still need to be written.
```

### Add a New Setting

```
Add a setting [NAME] to the [SECTION] section of config.py.

Type: [float | int | bool | str | Literal[...] | Rgb]
Default: [value] — must reproduce today's behaviour exactly (F-002 AC-1)
Effect: [what it changes]

Constraints:
- If the value is closed-ended, use Literal, not str. A Literal is validated for every
  entry path at once (config file, --set, dedicated flag, UI form) and renders as a
  combobox in the UI.
- Add a validator to the section's validate() if the value has a valid range.
- config.py stays pure data: no I/O, no logging, no odfpy/ezdxf/tkinter.
- Add the label and help text to ui/fields.py.
- Add the row to DOCS/Features/F-002.md and tabletodxf.example.toml.

Do not write tests. Do not package.
```

---

## Test Generation

### Write Unit Tests for a Module

```
Write unit tests for [module] in src/tabletodxf/[module].py.

Test file location: tests/unit/test_[module].py

Rules:
- Follow DOCS/Testing/TEST_STRATEGY.md
- No real I/O; use tmp_path when a file is genuinely needed
- Test names must describe behaviour, not implementation
- Cover: happy path, every error path (assert the catalog code), and the edge cases
- Build sheet fixtures with tests/fixtures/ods_builder.py, never commit a binary .ods

Do not test private helpers unless the helper IS the behaviour under test.

For each test, write a one-line docstring explaining WHAT behaviour it proves — and for a
regression test, what used to go wrong.
```

### Write an End-to-End Pipeline Test

```
Write an integration test for [behaviour] in tests/integration/test_pipeline.py.

These run the real pipeline — no mocks:
- Build the source sheet with tests/fixtures/ods_builder.py
- Run it through convert() (or cli.main() when exit codes are the point)
- Read the produced DXF back with ezdxf and assert on actual entities

Cover:
1. Happy path: the entity lands on the right layer with the right coordinates
2. The error path: assert the catalog code AND that no file was left behind (AC-10)
3. Determinism: same input twice -> identical output (AC-12)

Use the fixtures in tests/conftest.py for the font and the reference sheet.
```

---

## Code Review

### Full Review

```
Review the changes in the current git diff against the checklist in DOCS/Agents/AGENT_ROLES.md (Reviewer Agent section).

For each checklist item, state: ✅ PASS, ❌ FAIL (with line reference and explanation), or N/A.

After the checklist, give:
1. Blockers (must fix before merge): [list or "none"]
2. Suggestions (nice to have): [list or "none"]
3. One-line summary verdict

Be specific. Reference file:line for every finding.
```

### Security-Focused Review

```
Review the following files for security issues, focusing on OWASP Top 10:

Files: [list]

Check specifically:
- SQL injection: any string concatenation into queries?
- XSS: any user input rendered without escaping?
- Path traversal: any file paths constructed from user input?
- Secrets: any hardcoded API keys, tokens, or passwords?
- Auth bypass: any permission check that could be skipped?
- Insecure deserialization: any untrusted data deserialized without validation?

Report: issue, file:line, severity (Critical/High/Medium/Low), recommended fix.
```

---

## Documentation

### Update Feature Doc After Implementation

```
The implementation of F-[N] is complete. Update DOCS/Features/F-[N].md:

1. Technical Design section — replace the plan with what was actually built
2. Check off all acceptance criteria that are now met
3. Document any decisions made during implementation in the "Decisions Made" table
4. Update the status to REVIEW

Do NOT change the acceptance criteria themselves. Only update the design and status sections.
```

### Write an ADR

```
Write an ADR for the following decision: [DECISION_TITLE]

Context: [why was this decision needed?]
We chose: [what we chose]
Alternatives considered: [list the options you evaluated]
Trade-offs accepted: [what we gave up by choosing this option]

Follow the template in DOCS/Architecture/ADR_TEMPLATE.md exactly.
Number it ADR-[NEXT_NUMBER] (check existing ADRs for the next number).
Add it to DOCS/Architecture/ and reference it from the relevant feature doc or mandate.
```

---

## Debugging

### Trace a Data Flow

```
Trace the data flow for the following user action: [USER_ACTION]

Starting from: [entry point: handler / CLI command / UI event]
Ending at: [final state: DB record / return value / file written]

For each step:
1. File and function name
2. What data is passed in
3. What data is passed out or written
4. Any validation or transformation that occurs

I want to understand the complete path so I can identify where [SPECIFIC_PROBLEM] is happening.
```

### Explain Test Failure

```
This test is failing: [test name in file:line format]

Error output:
[paste the error]

Read the test and the code under test. Explain:
1. What the test expects
2. What the code actually produces
3. Whether the bug is in the test or the implementation
4. The fix (state it; do not apply it yet)
```

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
2. Read DOCS/Architecture/Architectural_Mandates.md §1, §2, §3
3. Read src/services/_TEMPLATE/ for the service pattern
4. Confirm your implementation plan in a brief summary

Then implement:
- Create the command class in src/commands/
- Add the service method in src/services/[name]-service.ts
- [Add handler / CLI command if applicable]

Do NOT write tests yet — that's a separate task.
Do NOT refactor unrelated code.
Do NOT build or commit.

When done: state what you changed and what tests still need to be written.
```

### Add a New Service

```
Create a new service for [DOMAIN_NAME] following the template at src/services/_TEMPLATE/.

This service should:
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

Dependencies it needs (as interfaces):
- [IRepository or similar]
- [ILogger]

Constraints:
- Stateless (no instance variables holding business state)
- All mutations wrapped in commands (do not mutate directly)
- Validate inputs at the service boundary only if called from non-handler code; otherwise validation is at the handler

Do not write tests. Do not build.
```

---

## Test Generation

### Write Unit Tests for a Service

```
Write unit tests for [ServiceName] in src/services/[name]-service.ts.

Test file location: tests/unit/services/[name]-service.test.ts

Rules:
- Follow DOCS/Testing/TEST_STRATEGY.md strictly
- Mock all dependencies (IRepository, ILogger, etc.) — no real I/O
- Test names must describe behavior, not implementation
- Cover: happy path, all error cases, all edge cases in the method
- Use the factory helpers in tests/fixtures/ for test data

Do not test private methods. Do not test that mocks were called unless the call IS the behavior.

For each test, write a one-line comment explaining WHAT behavior it proves.
```

### Write Integration Tests for a Handler

```
Write integration tests for the [HTTP_METHOD] [/route] handler.

Test file: tests/integration/handlers/[route-name].test.ts

These are integration tests — use:
- A real (local) database seeded with fixtures
- The full HTTP stack (not mocked handlers)
- Real command execution (not mocked command manager)

Cover:
1. Happy path: valid request → correct response and DB state
2. Validation error: missing required field → 400 response
3. Not found: [entity] does not exist → 404 response
4. [Any domain-specific error case]

Use fixtures from tests/fixtures/ for setup. Reset DB state in beforeEach.
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

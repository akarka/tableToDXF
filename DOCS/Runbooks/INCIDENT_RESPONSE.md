# Incident Response

Procedures for when something goes wrong in production or staging.

---

## Severity Levels

| Level | Definition | Response Time | Example |
|-------|-----------|---------------|---------|
| **P0 — Critical** | System down or data loss in progress | Immediate | All users affected; data corrupting |
| **P1 — High** | Major feature broken; significant user impact | < 1 hour | Core workflow failing for some users |
| **P2 — Medium** | Feature degraded; workaround exists | < 4 hours | Slow responses; minor feature broken |
| **P3 — Low** | Cosmetic or edge case issue | Next sprint | UI glitch; rare error in logs |

---

## Incident Response Flow

```
1. DETECT   → Monitoring alert / user report / agent finds anomaly
      ↓
2. TRIAGE   → Assess severity; assign P-level
      ↓
3. CONTAIN  → Stop the bleeding (disable feature, rollback, toggle flag)
      ↓
4. DIAGNOSE → Find root cause
      ↓
5. FIX      → Apply fix to staging; verify; promote to production
      ↓
6. RESOLVE  → Confirm system stable; communicate to stakeholders
      ↓
7. REVIEW   → Post-mortem within 48 hours (P0/P1)
```

---

## Immediate Response Actions

### P0: System Down

```bash
# 1. Check health endpoint
curl [HEALTH_ENDPOINT]

# 2. Check recent deploys (did we cause this?)
git log --oneline -5

# 3. Check error logs
[LOG_COMMAND] --since 30min | grep ERROR

# 4. If last deploy is the cause: ROLLBACK IMMEDIATELY
# See DEPLOY.md → Rollback Procedure

# 5. If not a deploy issue: check infrastructure
# [DB status, disk space, memory, etc.]
```

### P1/P2: Feature Broken

```bash
# 1. Identify affected feature from logs
[LOG_COMMAND] | grep "ERROR" | grep "[FEATURE_NAME]"

# 2. Check if this is a known bug (search git issues / ADRs)

# 3. If safe: apply a feature flag to disable the broken path
[FEATURE_FLAG_COMMAND]

# 4. Assign to a developer/agent for root cause analysis
```

---

## Agent Role During Incidents

AI agents can assist with:
- Reading and analyzing logs
- Searching for the root cause in code
- Proposing a fix
- Writing regression tests for the bug

AI agents must NOT:
- Deploy fixes without human approval
- Apply database migrations
- Access production data directly
- Make changes to production configuration

---

## Log Analysis Guide

```bash
# Recent errors
[LOG_COMMAND] --since 1h | grep "ERROR"

# Errors for a specific operation
[LOG_COMMAND] | grep 'op=CreateUser' | grep ERROR

# Error frequency over time
[LOG_COMMAND] | grep ERROR | [GROUP_BY_MINUTE_COMMAND]

# Specific user's session
[LOG_COMMAND] | grep 'userId=[USER_ID]'
```

Common patterns:

| Log Pattern | Likely Cause |
|------------|--------------|
| `ECONNREFUSED` | Database or external service unreachable |
| `ETIMEDOUT` | Slow external dependency; no timeout set |
| `ValidationError` spike | Changed input format from upstream |
| `OutOfMemory` | Memory leak or large payload |
| `UNIQUE constraint` | Concurrent writes creating duplicates |

---

## Post-Mortem Template (P0/P1 Required)

File as: `DOCS/Runbooks/incidents/YYYY-MM-DD-[short-title].md`

```markdown
# Incident Post-Mortem: [TITLE]

**Date:** YYYY-MM-DD
**Severity:** P0 / P1
**Duration:** [start time] → [resolution time] ([total duration])
**Impact:** [how many users affected? what data? what functionality?]

## Timeline

| Time | Event |
|------|-------|
| HH:MM | [event] |
| HH:MM | [event] |

## Root Cause

[One paragraph: what was the actual technical cause?]

## Contributing Factors

- [Factor 1: e.g., no timeout on external API call]
- [Factor 2: e.g., no monitoring on DB connection pool]

## Resolution

[What was done to resolve the incident?]

## Action Items

| Action | Owner | Deadline |
|--------|-------|----------|
| Add timeout to [API call] | [engineer] | YYYY-MM-DD |
| Add alert for [metric] | [engineer] | YYYY-MM-DD |
| Write regression test for [scenario] | [agent] | YYYY-MM-DD |

## What Went Well

- [Thing 1: e.g., rollback procedure worked quickly]

## What Could Be Improved

- [Thing 1: e.g., we had no alerting on this failure mode]
```

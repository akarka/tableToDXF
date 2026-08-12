# Deploy Runbook

**Important:** Deployments are always performed by a human. AI agents do not deploy.

---

## Environments

| Environment | URL / Location | Purpose | Who Deploys |
|-------------|---------------|---------|-------------|
| Local | `localhost:[PORT]` | Development | Developer |
| Staging | `[STAGING_URL]` | Pre-production testing | Human only |
| Production | `[PROD_URL]` | Live system | Human only |

---

## Pre-Deploy Checklist

Before deploying to any non-local environment:

- [ ] All tests passing: `[TEST_COMMAND]`
- [ ] No linter errors: `[LINT_COMMAND]`
- [ ] Build succeeds: `[BUILD_COMMAND]`
- [ ] Security scan clean: `[AUDIT_COMMAND]` (e.g., `npm audit`)
- [ ] PR merged to `main` (not a feature branch)
- [ ] `.env` for the target environment is configured
- [ ] Database migrations reviewed (if any)
- [ ] Changelog or release notes prepared (if customer-facing)

---

## Deploy Steps

### Staging

```bash
# 1. Confirm you're on main and up to date
git checkout main && git pull origin main

# 2. Build
[BUILD_COMMAND]

# 3. Run migrations (if applicable)
[MIGRATION_COMMAND] --env staging

# 4. Deploy
[DEPLOY_COMMAND] --env staging

# 5. Verify (see Post-Deploy Verification below)
```

### Production

```bash
# Same as staging, but:
# - Requires second human confirmation before step 4
# - Deploy during [MAINTENANCE_WINDOW or "off-peak hours"]
# - Monitor for 15 minutes after deploy

[DEPLOY_COMMAND] --env production
```

---

## Post-Deploy Verification

Run this after every deploy:

```bash
# 1. Health check
curl [HEALTH_ENDPOINT] | jq .

# Expected: { "status": "ok", "version": "[EXPECTED_VERSION]" }

# 2. Smoke test — verify the most critical user flow works
[SMOKE_TEST_COMMAND]

# 3. Check logs for errors in the first 5 minutes
[LOG_COMMAND] | grep "ERROR" | head -20
```

If any check fails: proceed to Rollback.

---

## Rollback Procedure

```bash
# Option A: Revert to previous release (if versioned releases)
[ROLLBACK_COMMAND] --to=[PREVIOUS_VERSION]

# Option B: Revert the commit and redeploy
git revert HEAD
git push origin main
# Then re-run deploy steps

# Option C: Toggle feature flag (if feature-flagged)
[FEATURE_FLAG_DISABLE_COMMAND]
```

After rollback:
1. Confirm the system is stable via health check
2. Document what failed and why in `DOCS/Runbooks/INCIDENT_RESPONSE.md`
3. Create a bug fix task before attempting re-deploy

---

## Database Migrations

- **Never auto-apply migrations in production.** Always review SQL before running.
- **Always take a backup before running migrations on production data.**
- Test migrations on staging with a production-size data snapshot if possible.

```bash
# Review pending migrations
[MIGRATION_STATUS_COMMAND]

# Apply (staging)
[MIGRATION_COMMAND] --env staging

# Apply (production — requires human + backup confirmation)
[MIGRATION_COMMAND] --env production
```

---

## Emergency Contacts

| Role | Contact |
|------|---------|
| [On-call engineer] | [contact] |
| [Infrastructure owner] | [contact] |
| [Database admin] | [contact] |

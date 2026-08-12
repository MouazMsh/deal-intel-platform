# Deployment

## Pre-deploy verification (re-checked for this Phase 4 deployment)

Re-checked immediately before writing this runbook, per Guardrail #1 --
not from memory or an earlier snapshot in this repo:

- **GitHub Actions**: standard hosted runners remain completely free and
  unlimited on public repositories. A self-hosted-runner platform charge
  was proposed in December 2025 for a March 2026 start, but was postponed
  after community pushback and never took effect -- and it only ever
  targeted self-hosted runners on private repos, which doesn't apply here
  regardless.
- **Neon**: free tier is unchanged in the ways that matter and improved in
  one way -- compute allowance doubled from 50 to 100 CU-hours/month
  (October 2025). Still no credit card required; still suspends (not
  bills) past the limit. One fact worth tracking going forward: Neon was
  acquired by Databricks (completed ~January 2026) -- nothing has gotten
  worse yet, but an ownership change is exactly the kind of event that can
  eventually affect free-tier terms, so re-check this specifically next
  time, not just the numbers.
- **Render**: not re-checked this phase -- Render isn't used until Phase 6.
  Re-verify then, not now; checking it today would just go stale by the
  time it's relevant.

## What Phase 4 actually deploys

**Important:** `providers/registry.py` refuses to return a mock provider
whenever `ENVIRONMENT=production` (Guardrail #2). Since no real
marketplace provider exists yet (Phase 5), running the scan with
`ENVIRONMENT=production` today will correctly raise
`MockProviderInProductionError` on every run -- that's the guardrail
working, not a bug. So Phase 4 deploys and proves the **infrastructure**
works; it does not run a live scan-and-publish cycle yet. The scheduled
cron trigger in `scheduled-scan.yml` stays commented out until Phase 5.

## Step-by-step runbook

### 1. GitHub repository

1. Create a **public** GitHub repository (public is what makes Actions
   genuinely free and unlimited -- see ARCHITECTURE.md §7/§16).
2. Push this codebase to it.
3. In the repo, go to **Settings → Environments → New environment**, name
   it exactly `production`. This is what scopes the secrets below so they
   are never exposed to PR-triggered workflow runs, including from forks
   (SECURITY.md).

### 2. Neon (production database)

1. Create a free account at neon.com, no card required.
2. Create a new project (e.g. `deal-intel-platform`).
3. Copy the connection string Neon gives you -- it should look like
   `postgresql://<user>:<password>@<host>/<db>?sslmode=require`.
4. **Adapt it for our async driver**: SQLAlchemy needs the `+asyncpg`
   dialect marker. Change:
   `postgresql://...` → `postgresql+asyncpg://...`
   (keep everything else, including `?sslmode=require`).
5. **Run migrations against it, once, from your own machine** -- this is
   not a CI job (a real DB credential has no business living in a
   throwaway migration workflow when a one-off local command does the
   same job more simply):
   ```bash
   # In your activated venv, in the project root:
   set DATABASE_URL=postgresql+asyncpg://...        # Windows (temporary, this shell only)
   export DATABASE_URL=postgresql+asyncpg://...      # macOS/Linux
   alembic upgrade head
   ```
   Confirm in the Neon console's table browser that all 8 tables now
   exist.

### 3. Telegram bot and channel

1. Message **@BotFather** on Telegram, `/newbot`, follow the prompts.
   Save the bot token it gives you.
2. Create your **public channel** (this is the real production
   destination). Add the bot as an administrator with permission to post.
   Get the channel's `@username` (or its numeric `-100...` chat ID if it's
   private) -- this is `TELEGRAM_CHANNEL_ID`.
3. Also create a **private test channel**, add the bot there too --
   this is `TELEGRAM_TEST_CHANNEL_ID`, used by every non-production
   environment (Gate B, `telegram/publisher.py`).
4. **Verify it actually works before touching GitHub secrets**:
   ```bash
   # .env: set TELEGRAM_BOT_TOKEN and TELEGRAM_TEST_CHANNEL_ID
   python scripts/smoke_test_telegram.py
   ```
   You should see a message land in your test channel within a couple of
   seconds. If this doesn't work, nothing downstream will either --
   fix it here first.

### 4. GitHub Environment secrets

In **Settings → Environments → production → Environment secrets**, add:

| Secret | Value |
|---|---|
| `DATABASE_URL` | The `postgresql+asyncpg://...` string from step 2 |
| `TELEGRAM_BOT_TOKEN` | From step 3 |
| `TELEGRAM_CHANNEL_ID` | Your **public** channel's ID from step 3 |

Never paste these anywhere else -- not into `.env` in a commit, not into
a workflow file, not into an issue for debugging.

### 5. Trigger the workflow manually and confirm the guardrail

1. In GitHub, go to **Actions → Scheduled Deal Scan → Run workflow**.
2. Expect it to **fail** -- specifically with `MockProviderInProductionError`
   in the logs. This is the correct, intended outcome (see above): it
   proves secrets/environment wiring and Neon connectivity work, and that
   the guardrail holds in a real production environment, not just in
   local tests.
3. If it fails with anything *else* (a connection error to Neon, a missing
   secret, an import error), that's a real problem to fix before Phase 5.

## Production topology (target -- built out across Phase 4 and Phase 6)

```text
Phase 4 (this phase): GitHub Actions (manual trigger) -> Neon Postgres -> Telegram Bot API
Phase 5: uncomment the cron schedule once a real provider exists
Phase 6: + Render free web service (admin dashboard, bot webhook, redirects)
```

No component requires an always-on local machine or personal device. See
`ARCHITECTURE.md` for the full diagrams and reasoning.

## Environments

- **GitHub Environment `production`**: holds `TELEGRAM_BOT_TOKEN`,
  `DATABASE_URL` (Neon), and (from Phase 5) `AMAZON_API_KEY`/`AMAZON_API_SECRET`.
  Only `scheduled-scan.yml` references it.
- **Local development**: `.env` file (gitignored), SQLite, `DRY_RUN=true`.
- **CI**: no secrets at all -- runs against SQLite and dry-run configuration.

## Rollback

Each Alembic migration has a `downgrade()`. Standard procedure:
`alembic downgrade -1` against the target database, then redeploy the
previous application version.

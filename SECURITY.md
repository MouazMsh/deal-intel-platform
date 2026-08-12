# Security

This repository is public. Everything in this document exists to make that
safe.

## Secrets

- No real secret is ever committed. `.env` is gitignored from the first
  commit; `.env.example` documents every variable name with an empty or
  placeholder value only.
- **Production secrets** (`TELEGRAM_BOT_TOKEN`, `DATABASE_URL` for Neon, and
  future `AMAZON_API_KEY`/`AMAZON_API_SECRET`) live in a **GitHub
  Environment** named `production` (Settings → Environments in the GitHub
  repo UI), not plain repository secrets. This matters specifically because
  the repo is public: GitHub does not expose environment secrets to
  workflow runs triggered by pull requests from forks, so this also closes
  off secret exfiltration via a malicious PR that modifies a workflow file
  — not just a hygiene practice.
- `scheduled-scan.yml` (added in Phase 4) is the only workflow that
  references the `production` environment and its secrets. `ci.yml` (this
  phase) never references them — CI runs entirely against local
  SQLite/dry-run configuration and needs no real secret at all.
- Render environment variables (added in Phase 6) are set through Render's
  dashboard/API directly, never committed or templated into a tracked file.

## Secret scanning

`ci.yml` runs a secrets scanner (`gitleaks`) as a blocking step on every
push and pull request, in addition to `bandit` (static security analysis)
and `pip-audit` (dependency vulnerability scanning). Any of the three
failing blocks merge.

## Logging

`app/core/logging.py` redacts any log field whose key matches a
secret-shaped pattern (`token`, `secret`, `api_key`, `password`,
`bot_token`) before it's ever written out, as a defensive backstop on top of
the rule that call sites must not pass secrets into log calls at all.

## Guardrails as code, not just policy

Two production-safety guardrails are implemented as code that fails loudly,
not as conventions:

- `app/providers/registry.py` refuses to return a mock provider while
  `ENVIRONMENT=production` (`MockProviderInProductionError`).
- `app/telegram/publisher.py` only ever resolves the production channel ID
  when `ENVIRONMENT=production`; every other environment is restricted to a
  separate test channel or dry-run mode (`PublishGuardrailError`).

See `OPERATIONAL_GUARDRAILS.md` (from the Phase 0 architecture review) for
the full reasoning, and `tests/unit/` for the tests that prove each one
fires.

## Reporting

This is a personal/small-team project without a formal disclosure program
at this stage; if you find an issue, open a private security advisory on
the repository rather than a public issue.

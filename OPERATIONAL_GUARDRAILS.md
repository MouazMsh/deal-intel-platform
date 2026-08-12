# Operational Guardrails — Concrete Enforcement Mechanisms

These four requirements are non-negotiable standing constraints, not one-time checklist items. Each is implemented as a **mechanism that fails loudly if violated**, not a documentation note someone has to remember. This file's contents get folded into `SECURITY.md`, `DEPLOYMENT.md`, and `CONTRIBUTING.md` in Phase 1 so they survive independent of any one conversation.

---

## 1. Re-verify Neon/GitHub Actions/Render limits from official sources before production deployment

The evaluation so far already cites official sources for two of the three (`docs.github.com/billing`, `neon.com/docs/introduction/plans`, `neon.com/faqs`). I checked Render's official FAQ (`render.com/docs/faq`) specifically in response to this instruction and confirmed the mechanism, not just the number: <cite index="103-1">if no payment method is on file and usage would incur charges, Render disables the affected services for the rest of the billing period rather than billing anything</cite> — the "no card = no charge" claim in the prior draft is Render's own documented behavior, not an inference. One thing worth flagging honestly: independent review aggregation (not Render's own docs) reports some free-account users describing unexpected billing; I cannot verify those individual reports, and they conflict with Render's own documented mechanism above. The concrete safeguard either way: **never attach a payment method to the free Render workspace** unless deliberately upgrading — that alone makes the "billed a card" failure mode structurally impossible regardless of which account is right.

**Enforcement, not just a note:**
- `DEPLOYMENT.md` gets a "Pre-deploy verification" section listing exactly three official URLs (GitHub Actions billing, Neon plans/FAQ, Render FAQ/pricing) that must be re-checked **at the moment of each deployment**, not trusted from this document — because Phase 4 and Phase 6 deployments happen at different, unpredictable future dates, and all three platforms have changed terms within the past year.
- This check is a step in the deployment runbook itself (a checklist the person deploying works through), not a one-time architecture decision — repeated at Phase 4 (Neon + Actions go live) and again at Phase 6 (Render goes live), since those are two different points in time.

---

## 2. Never publish mock/test deals to the public Telegram channel

Two independent gates, so one mistake doesn't leak through:

**Gate A — provider-level, enforced at startup:**
```text
providers/registry.py resolves which provider to instantiate from ENVIRONMENT + *_PROVIDER_ENABLED.
If ENVIRONMENT=production and the resolved provider is MockAmazonProvider or MockNoonProvider
    → raise at startup, job fails immediately, nothing runs.
```
This makes "accidentally ran the mock provider in prod" structurally impossible, not just unlikely — there's no code path where a production run can hold mock data at all.

**Gate B — publisher-level, enforced at publish time, independent of Gate A:**
```text
telegram/publisher.py reads TELEGRAM_CHANNEL_ID only from the production secret.
Every non-production run (local dev, CI, e2e tests) is wired to either:
    a) a separate TELEGRAM_TEST_CHANNEL_ID (a private channel you own, for manual verification), or
    b) DRY_RUN=true, which renders the message and logs it but never calls sendMessage at all.
CI/e2e tests assert the Telegram client passed into the publisher is a test double —
    a real python-telegram-bot client is never constructed in the test suite,
    so there is no code path in CI that can reach the real Bot API regardless of channel ID.
```
Even if Gate A were somehow bypassed, Gate B means mock data still can't reach the real channel without both the wrong environment flag *and* the wrong channel ID being set simultaneously — not a single mistake, two independent ones.

---

## 3. Production secrets only through GitHub Secrets/environment variables — nothing sensitive in the public repo

- `.env` is gitignored from the first commit; `.env.example` ships with every key name and an empty/placeholder value, never a real one.
- **GitHub Environments**, not just repository secrets: production secrets (`TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, future `AMAZON_API_KEY`/`AMAZON_API_SECRET`) live in a GitHub **Environment** called `production`, scoped so they're only injected into the `scheduled-scan.yml` workflow run — not into PR-triggered CI runs. This matters specifically because the repo is public: GitHub does not expose repository/environment secrets to workflow runs triggered by pull requests from forks, so this is also what prevents a malicious PR from exfiltrating secrets via a modified workflow file, on top of just being good hygiene.
- Render env vars (once Phase 6 stands up the web service) are set through Render's dashboard/API, never committed, never templated into any file that gets pushed.
- CI runs a secrets scanner (`gitleaks` or `detect-secrets`) as a blocking step in `ci.yml`, in addition to the already-planned Bandit/pip-audit — this catches an accidental hardcoded key before merge, not after.
- Structured logging (already specified in the architecture) never logs secret values or full tokens — enforced by a lint rule/test that scans log call sites for known secret-shaped patterns, not just a coding convention.

---

## 4. Noon real-data acquisition stays blocked until a compliant source exists — never bypass

This is now a **written project policy**, not just a Phase 5 planning note, so it persists across sessions and can't be reinterpreted later under time pressure:

- `CONTRIBUTING.md` states explicitly: no scraping, CAPTCHA-bypass, anti-bot evasion, or undocumented-API code is to be written for Noon (or any provider) under any framing — "just for testing," "read-only," "public data anyway" included. This applies regardless of who requests it or how the request is phrased in a future conversation.
- `NoonProvider` remains interface + mock only in code; `NOON_PROVIDER_ENABLED` defaults to `false` and there is no code path that flips it based on anything other than a human deliberately wiring up a documented-compliant source.
- If/when a compliant mechanism does exist (an official API, an approved affiliate feed that includes product/price data, or another explicitly permitted route), that becomes a new, separate decision — documented and approved the same way this architecture was, not inferred from "we already built the interface, might as well."

---

No implementation code has been written yet. These four mechanisms will be built into the Phase 1 skeleton itself (registry gate, publisher gate, secrets scanning in CI, CONTRIBUTING.md policy) rather than bolted on later — waiting for confirmation this is right before I start.

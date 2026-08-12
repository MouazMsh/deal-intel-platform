# Saudi Deal Intelligence Platform

A deal intelligence platform for Amazon.sa and Noon Saudi Arabia — not a
scraper, a system that determines whether a marketplace discount is
*actually* a good deal using independently tracked price history, then
publishes qualifying deals to a public Telegram channel in Arabic.

**Status: Phase 4 (Cloud Deployment infrastructure) delivered** — the
application code from Phases 1-3 is unchanged; this phase adds the
deployment runbook, the manual-trigger GitHub Actions workflow, and a
Telegram smoke-test script. See `DEPLOYMENT.md` for the full step-by-step
guide, `ARCHITECTURE.md` for the approved design and phased plan,
`OPERATIONAL_GUARDRAILS.md` for the four standing safety mechanisms.

**Important:** the scheduled scan cannot run with `ENVIRONMENT=production`
until Phase 5 delivers a real marketplace provider — Guardrail #2
(`providers/registry.py`) correctly refuses to use a mock provider in
production. `scheduled-scan.yml` ships with `workflow_dispatch` (manual)
only; the cron trigger is commented out until Phase 5.

## What's new in Phase 4

- `.github/workflows/scheduled-scan.yml` — the production scan workflow,
  wired to the GitHub `production` Environment's secrets.
- `scripts/smoke_test_telegram.py` — verifies a bot token + test channel
  work, independent of the app's guardrailed production path.
- `DEPLOYMENT.md` — the concrete runbook: Neon setup, migrations against
  the real database, Telegram bot/channel setup, GitHub Environment
  secrets, and what to expect when triggering the workflow for the first
  time (an intentional, guardrail-driven failure — see above).

## What existed after Phase 3

Everything from Phases 1-2, plus:

- **Formatter** (`app/telegram/formatter.py`) — pure functions rendering
  Arabic-first Telegram messages: classification header (🔥🔥🔥/⚡/etc.),
  price with strikethrough original, coupon line, real (not advertised)
  discount vs 30-day average, a historical-minimum claim gated on Deal
  Confidence, grade badge, confidence-tiered data-quality line, the
  deterministic "why is this a deal?" bullets from Phase 2, shipping/seller
  trust lines, and a single "buy" inline button (the other two buttons from
  the original sketch — price history, track price — are added in the
  phases that actually build their destinations, Phase 6/8; a button
  linking nowhere would be a fabricated feature, not a real one).
- **Client** (`app/telegram/client.py`) — `sendMessage`/`editMessageText`
  with inline keyboard support.
- **Publisher** (`app/telegram/publisher.py`) — Gate B, extended to carry
  rich message content (buttons, not just text) and to support editing an
  existing message in place.
- **Publishing orchestration** (`app/deals/publishing.py`) — turns a
  pipeline result into real Telegram activity: new posts, in-place edits
  when a deal improves further or comes back in stock, and expiration
  notices when a previously-published deal no longer qualifies. Includes a
  final `PublishGate` (defense-in-depth on top of the pipeline: valid
  title/price/URL, not blacklisted) immediately before any Telegram call.
- **`scheduler/runner.py`** now runs the complete discover → normalize →
  price → score → dedup → publish cycle for both marketplaces — the
  production entrypoint is functionally complete against mock data.
- One lifecycle gap flagged at the end of Phase 2 is now closed: the
  transition table didn't previously handle a `PUBLISHED` deal being
  re-evaluated. `pipeline.py`'s target-lifecycle logic is now
  publish-state-aware.

**Not yet built**: real marketplace data (Phase 5 — Amazon pending
Associates approval; Noon pending a compliant data source per
`CONTRIBUTING.md`), cloud deployment (Phase 4), admin dashboard (Phase 6),
interactive bot (Phase 7), alerts/personalization/analytics (Phase 8).

## What existed after Phase 2

Everything from Phase 1, plus:

- **Matching** (`app/matching/`) — title normalization and canonical
  product resolution (GTIN exact → brand+model exact → brand-scoped fuzzy
  title match → new canonical product), so the same physical product is
  recognized across Amazon and Noon listings.
- **Pricing** (`app/pricing/`) — price history recording and rolling
  statistics (7/30/90-day averages, median, historical min/max, previous
  price, % change), all pure functions independently unit-tested.
- **Scoring** (`app/scoring/`) — deterministic, config-driven Deal Score,
  Deal Confidence (calculated *separately* from Score, based on
  observation count/history age/price consistency/data completeness), Deal
  Grade (derived from Score, downgraded when Confidence is low — directly
  implementing the "Score 94, Confidence 35" vs "Score 94, Confidence 94"
  example from the approved architecture), Deal Classification, and a
  deterministic "why is this a deal?" explanation renderer.
- **Deal engine** (`app/deals/`) — the lifecycle state machine
  (idempotent, invalid transitions raise), the republish/dedup decision
  logic (spam prevention), freshness classification, and
  `pipeline.py`, which orchestrates all of the above end-to-end for a
  batch of provider observations.

**Not yet built**: Telegram message formatting/publishing integration with
the pipeline (Phase 3 — the publisher itself exists from Phase 1, but
nothing calls it with real Deal data yet), real marketplace data, admin
dashboard, interactive bot, alerts.

## What existed after Phase 1

- Project structure, configuration model, structured logging.
- 8 database tables (Marketplace, Category, Seller, CanonicalProduct,
  MarketplaceListing, PriceHistory, Deal, PublishedDeal) with Alembic
  migrations.
- `MarketplaceProvider` interface + `MockAmazonProvider`/`MockNoonProvider`
  with realistic fixtures.
- `AmazonProvider`/`NoonProvider` real-provider stubs (interface-complete,
  intentionally not implemented — see `ARCHITECTURE.md` §8/§12).
- The four operational guardrails, implemented as code:
  1. Deployment verification checklist (`DEPLOYMENT.md`).
  2. Mock-data protection: provider-level (`providers/registry.py`) and
     publisher-level (`telegram/publisher.py`) gates.
  3. Production secrets via GitHub Environments + secret scanning in CI.
  4. Noon hard-blocked at the config layer (`core/config.py`) and the
     provider layer (`providers/noon/provider.py`).
- Unit + integration tests covering all of the above.
- CI (`ci.yml`) and security scanning (`security.yml`) workflows.

**Not yet built** (by design — see the approved phased plan): normalization/
matching, price history calculations, deal scoring/confidence/grading,
Telegram message formatting, real marketplace data, admin dashboard,
interactive bot, alerts.

## Local development

### Prerequisites

- Python 3.12+
- Git

### Setup

```bash
git clone <repo-url>
cd deal-intel-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

The default `.env.example` values are safe out of the box: local SQLite,
`ENVIRONMENT=development`, `DRY_RUN=true`. No Telegram token or marketplace
credentials are required to run tests or the Phase 1 smoke entrypoint.

### Database

```bash
alembic upgrade head
```

Creates the 8 Phase 1 tables in `dev.db` (local SQLite).

### Run the tests

```bash
pytest
```

### Run linting/type-checking (same checks CI runs)

```bash
ruff check .
black --check .
mypy app
bandit -r app
pip-audit
```

### Run the Phase 1 smoke entrypoint

```bash
python -m app.scheduler.runner
```

Wires config → providers → registry → DB engine together end-to-end against
mock data and logs what it found. This is not the real deal pipeline yet
(that's Phase 2) — it exists to prove the foundation works.

## Troubleshooting

**`zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key Asia/Riyadh'` (Windows)**
Windows has no OS-level IANA timezone database, unlike Linux/macOS. Fix:
`pip install tzdata` (already added to `pyproject.toml` — reinstall with
`pip install -e ".[dev]"` if you're on an older checkout).

## Documentation

- `ARCHITECTURE.md` — full approved architecture (diagrams, ER schema, cloud
  infrastructure evaluation, deal intelligence design, phased plan).
- `OPERATIONAL_GUARDRAILS.md` — the four standing safety mechanisms and how
  each is enforced in code.
- `SECURITY.md` — secrets management, GitHub Environments, scanning.
- `DEPLOYMENT.md` — pre-deploy verification checklist, production topology.
- `CONTRIBUTING.md` — code style, testing expectations, and the standing
  Noon data-acquisition policy.

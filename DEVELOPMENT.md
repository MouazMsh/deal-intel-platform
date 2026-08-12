# Development

## Workflow

This project is built in phases (see `ARCHITECTURE.md`), each requiring
explicit approval before the next begins. Within a phase:

1. Implement against the approved design.
2. Run the full local check suite (`ruff`, `black --check`, `mypy`, `pytest`,
   `bandit`, `pip-audit`) — the same checks CI runs.
3. Update documentation for anything that changed.

## Adding a database change

1. Edit/add the SQLAlchemy model(s) in `app/db/models/`.
2. Generate a migration: `alembic revision --autogenerate -m "description"`
   (requires a real DB connection — point `DATABASE_URL` at a local SQLite
   file or a disposable Neon branch first).
3. Review the generated migration by hand — autogenerate is a starting
   point, not a guarantee, especially for enum/constraint changes.
4. Add/update the corresponding integration test in `tests/integration/`.

## Adding a marketplace provider

1. Add the marketplace to `MarketplaceCode` (`app/domain/enums.py`).
2. Implement `MarketplaceProvider` under `app/providers/<name>/provider.py`
   (real) and `mock.py` + `fixtures.py` (mock) — mirror the Amazon/Noon
   layout exactly.
3. Wire it into `ProviderRegistry._resolve()`.
4. The deal engine, pricing, and Telegram modules should need **zero**
   changes — if they do, that's a sign the provider abstraction leaked.

## Testing conventions

- `tests/unit/` — pure logic, no I/O, no DB, no network.
- `tests/integration/` — real (temp/in-memory) SQLite, mocked external
  clients.
- `tests/e2e/` — full pipeline against mock providers only, added starting
  Phase 2 once there's a pipeline to run end-to-end.
- Guardrail tests are non-optional: any change to `providers/registry.py`,
  `telegram/publisher.py`, or the guardrail validators in `core/config.py`
  needs its accompanying test updated in the same change.

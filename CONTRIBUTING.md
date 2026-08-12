# Contributing

## Standing policy: Noon data acquisition

**No scraping, CAPTCHA bypass, anti-bot evasion, or undocumented/reverse-engineered
API usage is to be implemented for Noon Saudi Arabia — or any marketplace —
under any framing.** This includes requests framed as "just for testing,"
"read-only," "the data is public anyway," "just a prototype," or any other
justification. This applies regardless of who requests it or how a future
conversation or issue phrases it.

Why: no compliant, official product/price data API exists for Noon at this
time. What exists is affiliate **link generation** through third-party
affiliate networks (ArabClicks, DCMnetwork, admitad, etc.) — not a product or
price data feed. `NoonProvider` (`app/providers/noon/provider.py`) reflects
this: it is not merely unimplemented, it actively refuses to be constructed,
and `Settings.NOON_PROVIDER_ENABLED` cannot be set to `true`
(`app/core/config.py`).

If a compliant mechanism becomes available later — an official API, an
approved affiliate feed that includes product/price data, or another
explicitly permitted route — that is a new, separate, documented decision to
be made deliberately, not inferred from "the interface already exists."

The same standard applies to Amazon and any future marketplace: only
official APIs, official affiliate/product APIs, or other explicitly
permitted mechanisms. See `ARCHITECTURE.md` for the current status of each
provider.

## Secrets

Never commit a real secret, token, or credential to this repository — it is
public. See `SECURITY.md` for exactly how secrets are managed.

## Code style

- `ruff` + `black` for linting/formatting, `mypy` for type checking — all
  run in CI (`.github/workflows/ci.yml`) and block merge on failure.
- Type hints on all public functions.
- No bare `except:`; no commented-out dead code; no `TODO` on core
  functionality — if something can't be built yet (e.g. real Noon data),
  it gets a documented, typed stub that fails loudly, not a silent gap.

## Tests

New logic needs a test. Guardrail logic (`providers/registry.py`,
`telegram/publisher.py`, `core/config.py` validators) needs a test that
specifically proves the guardrail fires — see `tests/unit/` for the
existing pattern.

"""Production entrypoint for the scheduled job.

This is the ONLY entrypoint GitHub Actions calls in production
(``python -m app.scheduler.runner``). A separate, explicitly local-only
``dev_runner.py`` (not created yet -- added only if it proves useful in
later-phase development) would wrap the same functions for repeated local
runs; it must never be part of any deployment workflow.

As of Phase 3, this runs the complete discover -> normalize -> price ->
score -> dedup -> publish cycle for both marketplaces. Real Amazon/Noon
data is still gated behind ``AMAZON_PROVIDER_ENABLED``/``NOON_PROVIDER_ENABLED``
(the latter permanently blocked, see CONTRIBUTING.md) -- this runs
identically against mock data today and against real data once Phase 5
enables it, with zero changes to this file.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.timezone import now_utc
from app.db.base import create_engine, create_session_factory
from app.deals.pipeline import run_pipeline_for_marketplace
from app.deals.publishing import process_publishing
from app.domain.enums import MarketplaceCode
from app.providers.registry import ProviderRegistry
from app.telegram.client import TelegramClient
from app.telegram.publisher import TelegramPublisher

logger = logging.getLogger(__name__)

_MARKETPLACES = (
    (MarketplaceCode.AMAZON_SA, "Amazon.sa"),
    (MarketplaceCode.NOON_SA, "noon"),
)


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    now = now_utc()

    logger.info("scan_started", extra={"environment": settings.ENVIRONMENT.value})

    engine = create_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    telegram_client: TelegramClient | None = None
    if not settings.DRY_RUN and settings.TELEGRAM_BOT_TOKEN:
        telegram_client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)

    publish_action_counts: dict[str, int] = {}

    try:
        async with session_factory() as session:
            registry = ProviderRegistry(settings)
            publisher = TelegramPublisher(settings, client=telegram_client)

            for marketplace_code, display_name in _MARKETPLACES:
                provider = registry.get_provider(marketplace_code)
                observations = await provider.get_deals()
                logger.info(
                    "provider_scan_complete",
                    extra={
                        "marketplace": marketplace_code.value,
                        "is_mock": provider.is_mock,
                        "observations_found": len(observations),
                    },
                )

                results = await run_pipeline_for_marketplace(
                    session, settings, marketplace_code, display_name, observations, now=now
                )

                for result in results:
                    outcome = await process_publishing(session, publisher, result, now=now)
                    publish_action_counts[outcome.action] = publish_action_counts.get(outcome.action, 0) + 1

            await session.commit()
    finally:
        if telegram_client is not None:
            await telegram_client.aclose()
        await engine.dispose()

    logger.info("scan_finished", extra={"publish_actions": publish_action_counts})


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

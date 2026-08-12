"""Standalone smoke test: confirms your bot token + a channel actually work.

Deliberately outside the app's normal guardrailed path -- this always runs
with ENVIRONMENT=development and always targets TELEGRAM_TEST_CHANNEL_ID,
never the production channel, regardless of what's in your .env. Use this
to verify your Telegram setup BEFORE wiring real secrets into GitHub.

Usage:
    python scripts/smoke_test_telegram.py

Requires in your .env (or exported in your shell):
    TELEGRAM_BOT_TOKEN=<your bot token from @BotFather>
    TELEGRAM_TEST_CHANNEL_ID=<your private test channel, bot added as admin>
"""

from __future__ import annotations

import asyncio
import sys

from app.core.config import Settings
from app.telegram.client import TelegramClient
from app.telegram.formatter import InlineButton, TelegramPost
from app.telegram.publisher import TelegramPublisher


async def main() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        DRY_RUN=False,
    )

    if not settings.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in your .env", file=sys.stderr)
        sys.exit(1)
    if not settings.TELEGRAM_TEST_CHANNEL_ID:
        print("ERROR: TELEGRAM_TEST_CHANNEL_ID is not set in your .env", file=sys.stderr)
        sys.exit(1)

    client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
    publisher = TelegramPublisher(settings, client=client)

    post = TelegramPost(
        text="✅ Smoke test: bot token and channel are wired up correctly.",
        buttons=[[InlineButton(text="Repo", url="https://github.com")]],
    )

    try:
        result = await publisher.publish(post)
        print(f"Sent successfully. channel_id={result.channel_id} message_id={result.message_id}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

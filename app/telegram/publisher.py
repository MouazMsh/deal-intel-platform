"""TelegramPublisher -- the enforcement point for Guardrail #2's publisher
side (Gate B), independent of the provider-side gate in
``providers/registry.py``.

Design choice worth calling out (unchanged from Phase 1): ``publish()`` and
``update_message()`` never accept a channel id as a parameter. The
destination is always resolved internally from settings. This means there
is no call site anywhere in the codebase that can pass "the production
channel" as a parameter by mistake -- the only way messages reach the real
public channel is if ``ENVIRONMENT=production`` is actually set, which is
the same condition Gate A (``providers/registry.py``) depends on.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import PublishGuardrailError
from app.domain.enums import Environment
from app.telegram.client import TelegramClient
from app.telegram.formatter import TelegramPost

logger = logging.getLogger(__name__)


class PublishResult(BaseModel):
    dry_run: bool
    channel_id: str
    message_id: int | None


class TelegramPublisher:
    def __init__(self, settings: Settings, client: TelegramClient | None = None) -> None:
        self._settings = settings
        self._client = client

    def _resolve_channel(self) -> str:
        if self._settings.ENVIRONMENT == Environment.PRODUCTION:
            if not self._settings.TELEGRAM_CHANNEL_ID:
                # Settings validation should already prevent this, but the
                # publisher does not trust that invariant blindly.
                raise PublishGuardrailError("TELEGRAM_CHANNEL_ID is required in production.")
            return self._settings.TELEGRAM_CHANNEL_ID

        # Any non-production environment: never eligible to target the
        # production channel, regardless of what TELEGRAM_CHANNEL_ID holds.
        if self._settings.DRY_RUN:
            return self._settings.TELEGRAM_TEST_CHANNEL_ID or "DRY_RUN_NO_CHANNEL"

        if not self._settings.TELEGRAM_TEST_CHANNEL_ID:
            raise PublishGuardrailError(
                "Non-production environments must use TELEGRAM_TEST_CHANNEL_ID "
                "or DRY_RUN=true. Publishing to the production channel from a "
                "non-production environment is not supported."
            )
        return self._settings.TELEGRAM_TEST_CHANNEL_ID

    async def publish(self, post: TelegramPost) -> PublishResult:
        channel_id = self._resolve_channel()

        if self._settings.DRY_RUN:
            logger.info(
                "dry_run_publish",
                extra={"channel_id": channel_id, "text_preview": post.text[:80]},
            )
            return PublishResult(dry_run=True, channel_id=channel_id, message_id=None)

        if self._client is None:
            raise PublishGuardrailError("DRY_RUN is false but no TelegramClient was configured.")

        message_id = await self._client.send_message(channel_id, post.text, buttons=post.buttons)
        logger.info("published", extra={"channel_id": channel_id, "message_id": message_id})
        return PublishResult(dry_run=False, channel_id=channel_id, message_id=message_id)

    async def update_message(self, existing_message_id: int, post: TelegramPost) -> PublishResult:
        """Edit a previously-published message in place -- used for price
        changes, back-in-stock re-activation, and expiration notices. Never
        creates a new message, which is what keeps republishing idempotent
        (ARCHITECTURE.md: never leave a stale price/status presented as
        current).
        """
        channel_id = self._resolve_channel()

        if self._settings.DRY_RUN:
            logger.info(
                "dry_run_update",
                extra={
                    "channel_id": channel_id,
                    "message_id": existing_message_id,
                    "text_preview": post.text[:80],
                },
            )
            return PublishResult(dry_run=True, channel_id=channel_id, message_id=existing_message_id)

        if self._client is None:
            raise PublishGuardrailError("DRY_RUN is false but no TelegramClient was configured.")

        await self._client.edit_message_text(channel_id, existing_message_id, post.text, buttons=post.buttons)
        logger.info("updated", extra={"channel_id": channel_id, "message_id": existing_message_id})
        return PublishResult(dry_run=False, channel_id=channel_id, message_id=existing_message_id)

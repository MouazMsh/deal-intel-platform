from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.exceptions import PublishGuardrailError
from app.telegram.formatter import TelegramPost
from app.telegram.publisher import TelegramPublisher
from tests.conftest import make_settings


def _post(text: str = "test message") -> TelegramPost:
    return TelegramPost(text=text, buttons=[])


@pytest.mark.asyncio
async def test_development_dry_run_never_calls_telegram_client() -> None:
    settings = make_settings(ENVIRONMENT="development", DRY_RUN=True)
    client = AsyncMock()
    publisher = TelegramPublisher(settings, client=client)

    result = await publisher.publish(_post())

    assert result.dry_run is True
    client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_development_dry_run_false_without_test_channel_is_rejected_at_settings_layer() -> None:
    # This condition is actually rejected earlier, at Settings validation --
    # proving the two layers agree with each other.
    with pytest.raises(Exception, match="Non-production environments must"):
        make_settings(ENVIRONMENT="development", DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="")


@pytest.mark.asyncio
async def test_development_publishes_to_test_channel_only() -> None:
    settings = make_settings(
        ENVIRONMENT="development", DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="@my_test_channel"
    )
    client = AsyncMock()
    client.send_message.return_value = 12345
    publisher = TelegramPublisher(settings, client=client)

    result = await publisher.publish(_post())

    assert result.dry_run is False
    assert result.channel_id == "@my_test_channel"
    client.send_message.assert_awaited_once_with("@my_test_channel", "test message", buttons=[])


@pytest.mark.asyncio
async def test_production_publishes_to_production_channel() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://user:pass@host/db",
        TELEGRAM_CHANNEL_ID="@real_public_channel",
        DRY_RUN=False,
    )
    client = AsyncMock()
    client.send_message.return_value = 999
    publisher = TelegramPublisher(settings, client=client)

    result = await publisher.publish(_post("a real deal"))

    assert result.channel_id == "@real_public_channel"
    client.send_message.assert_awaited_once_with("@real_public_channel", "a real deal", buttons=[])


@pytest.mark.asyncio
async def test_no_call_site_can_override_the_resolved_channel() -> None:
    """publish()/update_message() intentionally take no channel argument --
    this test exists to document that guarantee and fail loudly if either
    signature ever changes to accept one.
    """
    import inspect

    publish_signature = inspect.signature(TelegramPublisher.publish)
    assert list(publish_signature.parameters.keys()) == ["self", "post"]

    update_signature = inspect.signature(TelegramPublisher.update_message)
    assert list(update_signature.parameters.keys()) == ["self", "existing_message_id", "post"]


@pytest.mark.asyncio
async def test_dry_run_true_but_no_client_still_never_raises() -> None:
    settings = make_settings(ENVIRONMENT="development", DRY_RUN=True)
    publisher = TelegramPublisher(settings, client=None)
    result = await publisher.publish(_post())
    assert result.dry_run is True


@pytest.mark.asyncio
async def test_dry_run_false_without_client_raises_guardrail_error() -> None:
    settings = make_settings(
        ENVIRONMENT="development", DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="@test_channel"
    )
    publisher = TelegramPublisher(settings, client=None)
    with pytest.raises(PublishGuardrailError):
        await publisher.publish(_post())


@pytest.mark.asyncio
async def test_update_message_edits_in_place_and_never_creates_new_message() -> None:
    settings = make_settings(
        ENVIRONMENT="development", DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="@my_test_channel"
    )
    client = AsyncMock()
    publisher = TelegramPublisher(settings, client=client)

    result = await publisher.update_message(555, _post("updated text"))

    assert result.message_id == 555
    client.edit_message_text.assert_awaited_once_with("@my_test_channel", 555, "updated text", buttons=[])
    client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_update_message_dry_run_never_calls_client() -> None:
    settings = make_settings(ENVIRONMENT="development", DRY_RUN=True)
    client = AsyncMock()
    publisher = TelegramPublisher(settings, client=client)

    result = await publisher.update_message(555, _post())

    assert result.dry_run is True
    client.edit_message_text.assert_not_called()

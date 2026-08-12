from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.telegram.client import TelegramClient, _build_reply_markup
from app.telegram.formatter import InlineButton


def test_build_reply_markup_none_for_empty_buttons() -> None:
    assert _build_reply_markup(None) is None
    assert _build_reply_markup([]) is None


def test_build_reply_markup_shape() -> None:
    buttons = [[InlineButton(text="Buy", url="https://example.com/product")]]
    markup = _build_reply_markup(buttons)
    assert markup == {"inline_keyboard": [[{"text": "Buy", "url": "https://example.com/product"}]]}


def test_client_requires_bot_token() -> None:
    with pytest.raises(ValueError):
        TelegramClient("")


@pytest.mark.asyncio
async def test_send_message_posts_expected_payload_and_returns_message_id() -> None:
    http_client = AsyncMock()
    response = MagicMock()
    response.json.return_value = {"result": {"message_id": 42}}
    response.raise_for_status = MagicMock()
    http_client.post.return_value = response

    client = TelegramClient("fake-token", http_client=http_client)
    message_id = await client.send_message(
        "@channel", "hello", buttons=[[InlineButton(text="Buy", url="https://example.com")]]
    )

    assert message_id == 42
    call = http_client.post.call_args
    assert call.args[0] == "https://api.telegram.org/botfake-token/sendMessage"
    payload = call.kwargs["json"]
    assert payload["chat_id"] == "@channel"
    assert payload["text"] == "hello"
    assert payload["reply_markup"] == {"inline_keyboard": [[{"text": "Buy", "url": "https://example.com"}]]}


@pytest.mark.asyncio
async def test_send_message_without_buttons_omits_reply_markup() -> None:
    http_client = AsyncMock()
    response = MagicMock()
    response.json.return_value = {"result": {"message_id": 1}}
    response.raise_for_status = MagicMock()
    http_client.post.return_value = response

    client = TelegramClient("fake-token", http_client=http_client)
    await client.send_message("@channel", "hello")

    payload = http_client.post.call_args.kwargs["json"]
    assert "reply_markup" not in payload


@pytest.mark.asyncio
async def test_edit_message_text_posts_message_id() -> None:
    http_client = AsyncMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    http_client.post.return_value = response

    client = TelegramClient("fake-token", http_client=http_client)
    await client.edit_message_text("@channel", 555, "updated")

    payload = http_client.post.call_args.kwargs["json"]
    assert payload["message_id"] == 555
    assert payload["text"] == "updated"

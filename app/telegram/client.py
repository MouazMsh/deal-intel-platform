"""A minimal async Telegram Bot API client.

Only what the channel publisher needs: ``sendMessage`` and
``editMessageText``, both with optional inline keyboards. A richer client
(``python-telegram-bot``, for the interactive bot's webhook handling) is
introduced in Phase 7 when that feature is actually built -- not pulled in
now as an unused dependency.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.telegram.formatter import InlineButton

_API_BASE = "https://api.telegram.org"


def _build_reply_markup(buttons: list[list[InlineButton]] | None) -> dict[str, Any] | None:
    if not buttons:
        return None
    return {
        "inline_keyboard": [
            [{"text": button.text, "url": button.url} for button in row] for row in buttons
        ]
    }


class TelegramClient:
    def __init__(self, bot_token: str, http_client: httpx.AsyncClient | None = None) -> None:
        if not bot_token:
            raise ValueError("TelegramClient requires a non-empty bot_token")
        self._bot_token = bot_token
        self._http_client = http_client or httpx.AsyncClient(timeout=10.0)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        buttons: list[list[InlineButton]] | None = None,
        parse_mode: str = "HTML",
    ) -> int:
        """Send a message, return the resulting Telegram message_id."""
        url = f"{_API_BASE}/bot{self._bot_token}/sendMessage"
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        reply_markup = _build_reply_markup(buttons)
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        response = await self._http_client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        return int(result["result"]["message_id"])

    async def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        *,
        buttons: list[list[InlineButton]] | None = None,
        parse_mode: str = "HTML",
    ) -> None:
        url = f"{_API_BASE}/bot{self._bot_token}/editMessageText"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        reply_markup = _build_reply_markup(buttons)
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        response = await self._http_client.post(url, json=payload)
        response.raise_for_status()

    async def aclose(self) -> None:
        await self._http_client.aclose()

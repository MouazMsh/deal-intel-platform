"""Renders Deal data into Arabic Telegram messages.

Deliberately takes a plain ``DealMessageData`` DTO, not ORM objects --
keeps this module pure (no DB session, no I/O) and independently testable
with hand-built fixtures, matching the rest of the codebase's pattern of
pure business logic + a thin orchestration layer around it
(``deals/publishing.py`` assembles the DTO from ORM state).

Design choices worth documenting:
- HTML parse_mode (Telegram supports a small safe subset: <b>, <s>, etc.)
  rather than MarkdownV2, which requires escaping a long list of characters
  that are extremely common in product titles (., -, (, ), !) and is a
  frequent source of "message failed to send" bugs in Telegram bots.
- Only ONE inline button is wired up in Phase 3: "buy the deal", linking
  directly to the marketplace product URL. The original design sketch
  showed three buttons ("buy", "price history", "track price"), but the
  latter two point at features that don't exist yet (a public price-history
  page is Phase 6/8's admin+API work; price tracking is Phase 8's alerts
  feature). Shipping buttons that link nowhere would be a fabricated
  feature, not a real one -- they're added in the phase that actually
  builds their destination.
- Historical superlative claims ("lowest price in N days") are gated on
  Deal Confidence, not just on the raw numbers being true -- per the
  approved architecture, a claim like this must be backed by actual
  tracked history, not just be numerically accurate from too little data.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from decimal import Decimal

# Confidence below this: never make a specific historical superlative claim,
# even if the underlying numbers would technically support it.
MIN_CONFIDENCE_FOR_HISTORICAL_CLAIM = 50

_CLASSIFICATION_HEADER = {
    "INSANE_DEAL": "🔥🔥🔥 عرض جنوني",
    "GREAT_DEAL": "🔥🔥 عرض قوي",
    "GOOD_DEAL": "🔥 عرض جيد",
    "FLASH_DEAL": "⚡ عرض خاطف",
    "NORMAL": "🔥 عرض",
}

_GRADE_BADGE = {
    "A+": "🏆 A+",
    "A": "🏆 A",
    "B": "⭐ B",
    "C": "✔️ C",
}


@dataclass(frozen=True)
class InlineButton:
    text: str
    url: str


@dataclass(frozen=True)
class TelegramPost:
    text: str
    buttons: list[list[InlineButton]] = field(default_factory=list)


@dataclass(frozen=True)
class DealMessageData:
    title: str
    price: Decimal
    original_price: Decimal | None
    effective_price: Decimal
    currency: str
    coupon_code: str | None
    coupon_savings: Decimal | None
    deal_score: int
    deal_confidence: int
    deal_grade: str
    deal_classification: str
    discount_pct_vs_avg30: Decimal | None
    discount_pct_vs_min: Decimal | None
    score_breakdown: dict
    seller_name: str | None
    seller_rating: float | None
    shipping_cost: Decimal
    product_url: str
    is_back_in_stock: bool = False


def _esc(text: str) -> str:
    """HTML-escape any dynamic content before it goes into the message --
    titles/seller names originate from marketplace data we don't control.
    """
    return html.escape(text, quote=False)


def _format_price(amount: Decimal, currency_label: str) -> str:
    return f"{amount:,.0f} {currency_label}" if amount == amount.to_integral_value() else f"{amount:,.2f} {currency_label}"


def format_deal_message(data: DealMessageData, *, lang: str = "ar") -> TelegramPost:
    from app.scoring.explanation import build_explanation  # local import avoids a cycle at module load time

    currency_label = "ريال" if data.currency == "SAR" else data.currency
    lines: list[str] = []

    header = _CLASSIFICATION_HEADER.get(data.deal_classification, _CLASSIFICATION_HEADER["NORMAL"])
    if data.is_back_in_stock:
        header = "🚨 عاد للمخزون: " + header
    lines.append(header)
    lines.append("")
    lines.append(f"<b>{_esc(data.title)}</b>")
    lines.append("")

    price_line = f"💰 <b>{_format_price(data.effective_price, currency_label)}</b>"
    if data.original_price is not None and data.original_price > data.price:
        price_line += f"\n<s>{_format_price(data.original_price, currency_label)}</s>"
    lines.append(price_line)

    if data.coupon_code and data.coupon_savings is not None and data.coupon_savings > 0:
        lines.append(f"💳 كوبون <code>{_esc(data.coupon_code)}</code> يوفر {_format_price(data.coupon_savings, currency_label)}")

    if data.discount_pct_vs_avg30 is not None and data.discount_pct_vs_avg30 > 0:
        lines.append(f"📉 أقل من متوسط 30 يوم بـ {data.discount_pct_vs_avg30:.0f}%")

    if (
        data.discount_pct_vs_min is not None
        and data.discount_pct_vs_min >= 0
        and data.deal_confidence >= MIN_CONFIDENCE_FOR_HISTORICAL_CLAIM
    ):
        lines.append("📊 أقل سعر مسجل في البيانات المتتبعة")

    lines.append("")
    grade_badge = _GRADE_BADGE.get(data.deal_grade, data.deal_grade)
    lines.append(f"{grade_badge} DEAL — تقييم الصفقة: {data.deal_score}/100")

    if data.deal_confidence >= 70:
        lines.append(f"📈 دقة البيانات: عالية ({data.deal_confidence}%)")
    elif data.deal_confidence >= MIN_CONFIDENCE_FOR_HISTORICAL_CLAIM:
        lines.append(f"📈 دقة البيانات: متوسطة ({data.deal_confidence}%)")
    else:
        lines.append("📊 بيانات السعر: محدودة")

    explanation = build_explanation(data.score_breakdown, lang=lang)
    if explanation:
        lines.append("")
        lines.append("🔎 لماذا هذه الصفقة؟")
        for reason in explanation:
            lines.append(f"✓ {_esc(reason)}")

    lines.append("")
    if data.shipping_cost == 0:
        lines.append("🚚 شحن متاح")
    else:
        lines.append(f"🚚 شحن: {_format_price(data.shipping_cost, currency_label)}")

    if data.seller_rating is not None and data.seller_rating >= 4.5:
        lines.append(f"⭐ بائع موثوق ({data.seller_rating:.1f}/5)")
    elif data.seller_name:
        lines.append(f"🏪 البائع: {_esc(data.seller_name)}")

    text = "\n".join(lines)
    buttons = [[InlineButton(text="🛒 شراء العرض", url=data.product_url)]]
    return TelegramPost(text=text, buttons=buttons)


def format_unavailable_message(title: str, product_url: str, *, reason_ar: str) -> TelegramPost:
    """Used to edit a previously-published post when the deal no longer
    qualifies (price rose, availability lost, etc.) -- per the approved
    architecture, a stale price/status must never keep being presented as
    an active deal.
    """
    lines = [
        f"⚠️ {reason_ar}",
        "",
        f"<b>{_esc(title)}</b>",
    ]
    text = "\n".join(lines)
    buttons = [[InlineButton(text="🛒 عرض المنتج", url=product_url)]]
    return TelegramPost(text=text, buttons=buttons)

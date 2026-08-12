from __future__ import annotations

from decimal import Decimal

from app.telegram.formatter import DealMessageData, format_deal_message, format_unavailable_message


def _data(**overrides: object) -> DealMessageData:
    defaults: dict[str, object] = dict(
        title="Sony WH-1000XM5 Wireless Headphones",
        price=Decimal("899.00"),
        original_price=Decimal("1399.00"),
        effective_price=Decimal("899.00"),
        currency="SAR",
        coupon_code=None,
        coupon_savings=None,
        deal_score=88,
        deal_confidence=75,
        deal_grade="A",
        deal_classification="GREAT_DEAL",
        discount_pct_vs_avg30=Decimal("29.47"),
        discount_pct_vs_min=Decimal("0"),
        score_breakdown={
            "discount_vs_avg30": {
                "weighted_points": 34.4,
                "reason_ar": "أقل من متوسط 30 يوم بـ 29%",
                "reason_en": "29% below the 30-day average",
            },
            "discount_vs_min": {
                "weighted_points": 20.0,
                "reason_ar": "أقل سعر مسجل في التاريخ المتتبع",
                "reason_en": "Lowest price ever recorded",
            },
        },
        seller_name="Amazon.sa",
        seller_rating=4.6,
        shipping_cost=Decimal("0"),
        product_url="https://www.amazon.sa/dp/B09JQMJHXY",
    )
    defaults.update(overrides)
    return DealMessageData(**defaults)  # type: ignore[arg-type]


def test_message_contains_title_and_price() -> None:
    post = format_deal_message(_data())
    assert "Sony WH-1000XM5 Wireless Headphones" in post.text
    assert "899" in post.text
    assert "ريال" in post.text


def test_original_price_shown_strikethrough_when_discounted() -> None:
    post = format_deal_message(_data())
    assert "<s>" in post.text
    assert "1,399" in post.text or "1399" in post.text


def test_no_strikethrough_when_no_discount() -> None:
    post = format_deal_message(_data(original_price=Decimal("899.00")))
    assert "<s>" not in post.text


def test_classification_header_insane_deal() -> None:
    post = format_deal_message(_data(deal_classification="INSANE_DEAL"))
    assert "🔥🔥🔥" in post.text


def test_classification_header_flash_deal() -> None:
    post = format_deal_message(_data(deal_classification="FLASH_DEAL"))
    assert "⚡" in post.text


def test_back_in_stock_prefix() -> None:
    post = format_deal_message(_data(is_back_in_stock=True))
    assert "عاد للمخزون" in post.text


def test_coupon_line_shown_when_present() -> None:
    post = format_deal_message(
        _data(coupon_code="SAVE50", coupon_savings=Decimal("50.00"))
    )
    assert "SAVE50" in post.text
    assert "كوبون" in post.text


def test_coupon_line_absent_when_no_coupon() -> None:
    post = format_deal_message(_data(coupon_code=None, coupon_savings=None))
    assert "كوبون" not in post.text


def test_historical_claim_shown_when_confidence_high_and_at_minimum() -> None:
    post = format_deal_message(_data(deal_confidence=80, discount_pct_vs_min=Decimal("0")))
    assert "أقل سعر مسجل" in post.text


def test_historical_claim_hidden_when_confidence_low() -> None:
    post = format_deal_message(
        _data(
            deal_confidence=20,
            discount_pct_vs_min=Decimal("0"),
            score_breakdown={
                "discount_vs_avg30": {
                    "weighted_points": 30.0,
                    "reason_ar": "أقل من متوسط 30 يوم بـ 29%",
                    "reason_en": "29% below the 30-day average",
                }
            },
        )
    )
    assert "أقل سعر مسجل" not in post.text
    assert "بيانات السعر: محدودة" in post.text


def test_explanation_bullets_included() -> None:
    post = format_deal_message(_data())
    assert "لماذا هذه الصفقة" in post.text
    assert "✓" in post.text


def test_grade_badge_rendered() -> None:
    post = format_deal_message(_data(deal_grade="A+"))
    assert "A+" in post.text


def test_html_special_characters_are_escaped() -> None:
    post = format_deal_message(_data(title="Product <script>alert(1)</script> & Co"))
    assert "<script>" not in post.text
    assert "&lt;script&gt;" in post.text


def test_single_buy_button_only() -> None:
    post = format_deal_message(_data())
    assert len(post.buttons) == 1
    assert len(post.buttons[0]) == 1
    assert post.buttons[0][0].url == "https://www.amazon.sa/dp/B09JQMJHXY"
    assert "شراء" in post.buttons[0][0].text


def test_free_shipping_line() -> None:
    post = format_deal_message(_data(shipping_cost=Decimal("0")))
    assert "شحن متاح" in post.text


def test_paid_shipping_line() -> None:
    post = format_deal_message(_data(shipping_cost=Decimal("25.00")))
    assert "شحن متاح" not in post.text
    assert "25" in post.text


def test_trusted_seller_line() -> None:
    post = format_deal_message(_data(seller_rating=4.8))
    assert "بائع موثوق" in post.text


def test_format_unavailable_message_out_of_stock() -> None:
    post = format_unavailable_message(
        "Sony WH-1000XM5", "https://www.amazon.sa/dp/B09JQMJHXY", reason_ar="نفدت الكمية حالياً"
    )
    assert "نفدت الكمية حالياً" in post.text
    assert "Sony WH-1000XM5" in post.text
    assert len(post.buttons) == 1

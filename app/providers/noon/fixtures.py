"""Fixture data for MockNoonProvider.

Includes one listing whose title deliberately matches an Amazon fixture
(the Sony WH-1000XM5) so Phase 2's canonical-product matching and
Amazon-vs-Noon comparison have a real cross-marketplace pair to resolve.
"""

from __future__ import annotations

from datetime import datetime

from app.core.timezone import RIYADH_TZ

_NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=RIYADH_TZ)

RAW_FIXTURES: list[dict] = [
    # Normal product.
    {
        "marketplace_code": "noon_sa",
        "marketplace_product_id": "N-APPRO2-001",
        "sku": "N-APPRO2-001",
        "title": "Apple AirPods Pro (2nd Generation)",
        "brand": "Apple",
        "product_url": "https://www.noon.com/saudi-en/apple-airpods-pro-2nd-gen",
        "seller_external_id": "NOON_SA",
        "seller_name": "noon",
        "seller_rating": 4.5,
        "seller_review_count": 90000,
        "seller_fulfillment_type": "noon_express",
        "rating": 4.6,
        "review_count": 5400,
        "availability": "in_stock",
        "price": "899.00",
        "original_price": "999.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Cross-marketplace match: same product family as the Amazon Sony fixture,
    # cheaper here — exercises the Amazon-vs-Noon comparison in Phase 2.
    {
        "marketplace_code": "noon_sa",
        "marketplace_product_id": "N-SONYWH5-001",
        "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "product_url": "https://www.noon.com/saudi-en/sony-wh-1000xm5",
        "seller_external_id": "NOON_SA",
        "seller_name": "noon",
        "seller_rating": 4.5,
        "seller_review_count": 90000,
        "seller_fulfillment_type": "noon_express",
        "rating": 4.7,
        "review_count": 1100,
        "availability": "in_stock",
        "price": "849.00",
        "original_price": "1399.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Out of stock.
    {
        "marketplace_code": "noon_sa",
        "marketplace_product_id": "N-OOS-001",
        "title": "Samsung Galaxy S24 Ultra",
        "brand": "Samsung",
        "product_url": "https://www.noon.com/saudi-en/samsung-galaxy-s24-ultra",
        "seller_external_id": "NOON_SA",
        "seller_name": "noon",
        "availability": "out_of_stock",
        "price": "4999.00",
        "original_price": "4999.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Coupon product.
    {
        "marketplace_code": "noon_sa",
        "marketplace_product_id": "N-COUPON-001",
        "title": "Instant Pot Duo 7-in-1 Pressure Cooker",
        "brand": "Instant Pot",
        "product_url": "https://www.noon.com/saudi-en/instant-pot-duo",
        "seller_external_id": "NOON_SA",
        "seller_name": "noon",
        "seller_rating": 4.5,
        "rating": 4.4,
        "review_count": 780,
        "availability": "in_stock",
        "price": "349.00",
        "original_price": "349.00",
        "currency": "SAR",
        "coupon_code": "NOONSAVE30",
        "coupon_discount_value": "30.00",
        "coupon_discount_type": "fixed",
        "observed_at": _NOW,
    },
    # Malformed: missing required title -> validation error.
    {
        "marketplace_code": "noon_sa",
        "marketplace_product_id": "N-BADDATA-001",
        "title": "",
        "product_url": "https://www.noon.com/saudi-en/bad-data",
        "availability": "in_stock",
        "price": "10.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
]

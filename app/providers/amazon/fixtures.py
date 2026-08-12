"""Fixture data for MockAmazonProvider.

``RAW_FIXTURES`` holds plain dicts (not yet validated) so we can include one
deliberately malformed entry and exercise per-item error handling, exactly
like a real provider's response might contain one bad record among many.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.core.timezone import RIYADH_TZ

_NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=RIYADH_TZ)

RAW_FIXTURES: list[dict] = [
    # Normal product, no discount.
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B08N5WRWNW",
        "asin": "B08N5WRWNW",
        "title": "Echo Dot (4th Gen) | Smart speaker",
        "brand": "Amazon",
        "product_url": "https://www.amazon.sa/dp/B08N5WRWNW",
        "seller_external_id": "AMZN_SA",
        "seller_name": "Amazon.sa",
        "seller_rating": 4.6,
        "seller_review_count": 120000,
        "seller_fulfillment_type": "FBA",
        "rating": 4.5,
        "review_count": 8500,
        "availability": "in_stock",
        "price": "199.00",
        "original_price": "199.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Discounted product — genuine, moderate discount.
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B09JQMJHXY",
        "asin": "B09JQMJHXY",
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "product_url": "https://www.amazon.sa/dp/B09JQMJHXY",
        "seller_external_id": "AMZN_SA",
        "seller_name": "Amazon.sa",
        "seller_rating": 4.6,
        "seller_review_count": 120000,
        "seller_fulfillment_type": "FBA",
        "rating": 4.7,
        "review_count": 3200,
        "availability": "in_stock",
        "price": "899.00",
        "original_price": "1399.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Huge/flash price drop.
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B0BXYZ1234",
        "sku": "GPU-RTX5070",
        "title": "NVIDIA GeForce RTX 5070 Graphics Card",
        "brand": "NVIDIA",
        "model": "RTX 5070",
        "product_url": "https://www.amazon.sa/dp/B0BXYZ1234",
        "seller_external_id": "SELLER_TECHSA",
        "seller_name": "TechSA Store",
        "seller_rating": 4.2,
        "seller_review_count": 950,
        "seller_fulfillment_type": "seller_fulfilled",
        "rating": 4.4,
        "review_count": 410,
        "availability": "in_stock",
        "price": "799.00",
        "original_price": "1299.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Duplicate/near-duplicate title of the Sony headphones above, different ID.
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B09JQMJHXZ",
        "asin": "B09JQMJHXZ",
        "title": "Sony WH1000XM5 Wireless Noise Cancelling Headphones",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "product_url": "https://www.amazon.sa/dp/B09JQMJHXZ",
        "seller_external_id": "SELLER_OTHER",
        "seller_name": "Other Seller",
        "seller_rating": 3.9,
        "seller_review_count": 200,
        "seller_fulfillment_type": "seller_fulfilled",
        "rating": 4.6,
        "review_count": 50,
        "availability": "in_stock",
        "price": "920.00",
        "original_price": "1399.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Out of stock.
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B07OOS0001",
        "asin": "B07OOS0001",
        "title": "PlayStation 5 Console",
        "brand": "Sony",
        "product_url": "https://www.amazon.sa/dp/B07OOS0001",
        "seller_external_id": "AMZN_SA",
        "seller_name": "Amazon.sa",
        "availability": "out_of_stock",
        "price": "2199.00",
        "original_price": "2199.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
    # Coupon product.
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B0COUPON01",
        "title": "Anker PowerCore 20000mAh Power Bank",
        "brand": "Anker",
        "product_url": "https://www.amazon.sa/dp/B0COUPON01",
        "seller_external_id": "AMZN_SA",
        "seller_name": "Amazon.sa",
        "seller_rating": 4.6,
        "rating": 4.5,
        "review_count": 1200,
        "availability": "in_stock",
        "price": "399.00",
        "original_price": "399.00",
        "currency": "SAR",
        "coupon_code": "SAVE50",
        "coupon_discount_value": "50.00",
        "coupon_discount_type": "fixed",
        "observed_at": _NOW,
    },
    # Malformed: negative price. Will fail RawProductObservation validation
    # on purpose, to exercise per-item error handling (one bad record must
    # not crash the batch).
    {
        "marketplace_code": "amazon_sa",
        "marketplace_product_id": "B0BADDATA1",
        "title": "Malformed Fixture Product",
        "product_url": "https://www.amazon.sa/dp/B0BADDATA1",
        "availability": "in_stock",
        "price": "-10.00",
        "currency": "SAR",
        "observed_at": _NOW,
    },
]

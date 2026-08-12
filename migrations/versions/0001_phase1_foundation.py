"""Phase 1 foundation: the 8 approved MVP tables.

Revision ID: 0001
Revises:
Create Date: 2026-08-10

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.domain.enums import (
    Availability,
    DealClassification,
    DealGrade,
    DiscountType,
    LifecycleStatus,
    MarketplaceCode,
    PublishedDealStatus,
)

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "code", sa.Enum(MarketplaceCode, native_enum=False, length=32, validate_strings=True), nullable=False
        ),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_marketplace_code"),
    )
    op.create_index("ix_marketplaces_code", "marketplaces", ["code"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name_ar", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("emoji", sa.String(8), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("code", name="uq_category_code"),
    )
    op.create_index("ix_categories_code", "categories", ["code"])

    op.create_table(
        "sellers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marketplace_id", sa.Integer(), sa.ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_seller_id", sa.String(150), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("fulfillment_type", sa.String(50), nullable=True),
        sa.Column("blacklisted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("marketplace_id", "external_seller_id", name="uq_seller_marketplace_external_id"),
    )

    op.create_table(
        "canonical_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_title", sa.String(300), nullable=False),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("gtin", sa.String(14), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_canonical_products_canonical_title", "canonical_products", ["canonical_title"])
    op.create_index("ix_canonical_products_brand", "canonical_products", ["brand"])
    op.create_index("ix_canonical_products_gtin", "canonical_products", ["gtin"])

    op.create_table(
        "marketplace_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "canonical_product_id",
            sa.Integer(),
            sa.ForeignKey("canonical_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("marketplace_id", sa.Integer(), sa.ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("sellers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("marketplace_product_id", sa.String(150), nullable=False),
        sa.Column("asin", sa.String(20), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("normalized_title", sa.String(500), nullable=False),
        sa.Column("match_confidence", sa.Integer(), nullable=True),
        sa.Column("match_method", sa.String(50), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("product_url", sa.String(1000), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column(
            "availability",
            sa.Enum(Availability, native_enum=False, length=20, validate_strings=True),
            nullable=False,
            server_default=Availability.UNKNOWN.value,
        ),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("final_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blacklisted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint(
            "marketplace_id", "marketplace_product_id", name="uq_listing_marketplace_product_id"
        ),
    )
    op.create_index("ix_listing_canonical_product_id", "marketplace_listings", ["canonical_product_id"])
    op.create_index("ix_listing_marketplace_id", "marketplace_listings", ["marketplace_id"])
    op.create_index("ix_listing_asin", "marketplace_listings", ["asin"])
    op.create_index("ix_listing_sku", "marketplace_listings", ["sku"])
    op.create_index("ix_listing_normalized_title", "marketplace_listings", ["normalized_title"])
    op.create_index("ix_listing_current_price", "marketplace_listings", ["current_price"])
    op.create_index("ix_listing_availability", "marketplace_listings", ["availability"])
    op.create_index("ix_listing_last_seen_at", "marketplace_listings", ["last_seen_at"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id", sa.Integer(), sa.ForeignKey("marketplace_listings.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("effective_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("coupon_code", sa.String(50), nullable=True),
        sa.Column("coupon_discount_value", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "coupon_discount_type",
            sa.Enum(DiscountType, native_enum=False, length=20, validate_strings=True),
            nullable=True,
        ),
        sa.Column(
            "availability", sa.Enum(Availability, native_enum=False, length=20, validate_strings=True), nullable=False
        ),
        sa.Column("source", sa.String(50), nullable=False),
    )
    op.create_index("ix_price_history_listing_id", "price_history", ["listing_id"])
    op.create_index("ix_price_history_observed_at", "price_history", ["observed_at"])
    op.create_index("ix_price_history_listing_observed_at", "price_history", ["listing_id", "observed_at"])

    op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("deal_confidence", sa.Integer(), nullable=True),
        sa.Column(
            "deal_grade", sa.Enum(DealGrade, native_enum=False, length=10, validate_strings=True), nullable=True
        ),
        sa.Column(
            "deal_classification",
            sa.Enum(DealClassification, native_enum=False, length=20, validate_strings=True),
            nullable=True,
        ),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("confidence_breakdown", sa.JSON(), nullable=True),
        sa.Column("discount_pct_advertised", sa.Numeric(5, 2), nullable=True),
        sa.Column("discount_pct_vs_avg30", sa.Numeric(5, 2), nullable=True),
        sa.Column("discount_pct_vs_min", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "lifecycle_status",
            sa.Enum(LifecycleStatus, native_enum=False, length=20, validate_strings=True),
            nullable=False,
            server_default=LifecycleStatus.DISCOVERED.value,
        ),
        sa.Column("rejection_reason", sa.String(200), nullable=True),
        sa.Column("first_qualified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deal_listing_id", "deals", ["listing_id"], unique=True)
    op.create_index("ix_deal_score", "deals", ["deal_score"])
    op.create_index("ix_deal_lifecycle_status", "deals", ["lifecycle_status"])

    op.create_table(
        "published_deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("telegram_channel_id", sa.String(100), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("tracking_slug", sa.String(50), nullable=False, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(PublishedDealStatus, native_enum=False, length=20, validate_strings=True),
            nullable=False,
            server_default=PublishedDealStatus.ACTIVE.value,
        ),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_published_deals_tracking_slug", "published_deals", ["tracking_slug"])


def downgrade() -> None:
    op.drop_table("published_deals")
    op.drop_table("deals")
    op.drop_table("price_history")
    op.drop_table("marketplace_listings")
    op.drop_table("canonical_products")
    op.drop_table("sellers")
    op.drop_table("categories")
    op.drop_table("marketplaces")

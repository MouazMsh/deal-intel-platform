from __future__ import annotations

from decimal import Decimal

import pytest

from app.providers.amazon.mock import MockAmazonProvider
from app.providers.noon.mock import MockNoonProvider


@pytest.mark.asyncio
async def test_mock_amazon_skips_malformed_fixture_and_keeps_valid_ones() -> None:
    provider = MockAmazonProvider()
    observations = provider._parsed_fixtures()

    # 7 fixtures defined, 1 malformed (negative price) -> 6 valid.
    assert len(observations) == 6
    assert all(o.price > 0 for o in observations)


@pytest.mark.asyncio
async def test_mock_amazon_get_deals_only_returns_discounted_items() -> None:
    provider = MockAmazonProvider()
    deals = await provider.get_deals()
    assert len(deals) >= 1
    assert all(d.original_price is not None and d.original_price > d.price for d in deals)


@pytest.mark.asyncio
async def test_mock_amazon_get_product_by_id() -> None:
    provider = MockAmazonProvider()
    product = await provider.get_product("B09JQMJHXY")
    assert product is not None
    assert "Sony" in product.title


@pytest.mark.asyncio
async def test_mock_amazon_get_product_unknown_id_returns_none() -> None:
    provider = MockAmazonProvider()
    assert await provider.get_product("does-not-exist") is None


@pytest.mark.asyncio
async def test_mock_amazon_get_price() -> None:
    provider = MockAmazonProvider()
    price = await provider.get_price("B09JQMJHXY")
    assert price == Decimal("899.00")


@pytest.mark.asyncio
async def test_mock_amazon_search_products() -> None:
    provider = MockAmazonProvider()
    results = await provider.search_products("sony")
    assert len(results) >= 1
    assert all("sony" in r.title.lower() for r in results)


def test_mock_amazon_is_flagged_as_mock() -> None:
    assert MockAmazonProvider.is_mock is True
    assert MockAmazonProvider.name == "amazon_sa"


@pytest.mark.asyncio
async def test_mock_noon_skips_malformed_fixture() -> None:
    provider = MockNoonProvider()
    observations = provider._parsed_fixtures()
    # 5 fixtures defined, 1 malformed (empty title) -> 4 valid.
    assert len(observations) == 4


def test_mock_noon_is_flagged_as_mock() -> None:
    assert MockNoonProvider.is_mock is True
    assert MockNoonProvider.name == "noon_sa"


@pytest.mark.asyncio
async def test_cross_marketplace_fixture_pair_exists_for_matching() -> None:
    """A Phase 2 prerequisite: at least one product title should be
    resolvable to the same canonical product on both marketplaces.
    """
    amazon_provider = MockAmazonProvider()
    noon_provider = MockNoonProvider()

    amazon_results = await amazon_provider.search_products("WH-1000XM5")
    noon_results = await noon_provider.search_products("WH-1000XM5")

    assert len(amazon_results) >= 1
    assert len(noon_results) >= 1

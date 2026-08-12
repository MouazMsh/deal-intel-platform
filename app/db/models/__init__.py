"""Import every model so ``Base.metadata`` is fully populated as soon as
``app.db.models`` is imported -- required for both Alembic autogenerate and
``Base.metadata.create_all()`` in tests.
"""

from app.db.models.canonical_product import CanonicalProduct
from app.db.models.category import Category
from app.db.models.deal import Deal
from app.db.models.marketplace import Marketplace
from app.db.models.marketplace_listing import MarketplaceListing
from app.db.models.price_history import PriceHistory
from app.db.models.published_deal import PublishedDeal
from app.db.models.seller import Seller

__all__ = [
    "CanonicalProduct",
    "Category",
    "Deal",
    "Marketplace",
    "MarketplaceListing",
    "PriceHistory",
    "PublishedDeal",
    "Seller",
]

from app.core.cache import get_redis
from app.core.config import get_settings
from app.pipelines.prices import PricePipeline
from app.providers.base import MarketDataProvider
from app.providers.cached import CachedMarketDataProvider
from app.providers.yahoo import YahooMarketDataProvider


def get_price_pipeline() -> PricePipeline:
    provider: MarketDataProvider = YahooMarketDataProvider()
    settings = get_settings()
    if settings.redis_url:
        provider = CachedMarketDataProvider(provider, get_redis(), settings)
    return PricePipeline(provider)

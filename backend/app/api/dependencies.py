from app.core.cache import get_redis
from app.core.config import get_settings
from app.pipelines.news import NewsPipeline
from app.pipelines.prices import PricePipeline
from app.providers.base import MarketDataProvider
from app.providers.cached import CachedMarketDataProvider
from app.providers.news.sec_edgar import SecFilingsNewsProvider
from app.providers.news.yahoo_rss import YahooRssNewsProvider
from app.providers.news.yfinance_news import YfinanceNewsProvider
from app.providers.yahoo import YahooMarketDataProvider


def get_price_pipeline() -> PricePipeline:
    provider: MarketDataProvider = YahooMarketDataProvider()
    settings = get_settings()
    if settings.redis_url:
        provider = CachedMarketDataProvider(provider, get_redis(), settings)
    return PricePipeline(provider)


def get_news_pipeline() -> NewsPipeline:
    settings = get_settings()
    return NewsPipeline(
        [
            YahooRssNewsProvider(settings.http_user_agent),
            YfinanceNewsProvider(),
            SecFilingsNewsProvider(settings.sec_user_agent),
        ]
    )

from app.core.cache import get_redis
from app.core.config import get_settings
from app.llm.gemini import GeminiClient
from app.pipelines.analysis import AnalysisPipeline
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


class AnalysisUnavailableError(RuntimeError):
    pass


def get_analysis_pipeline() -> AnalysisPipeline:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise AnalysisUnavailableError("GEMINI_API_KEY is not set, so analysis is unavailable.")
    return AnalysisPipeline(
        prices=get_price_pipeline(),
        news=get_news_pipeline(),
        client=GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=settings.gemini_timeout_seconds,
            max_attempts=settings.gemini_max_attempts,
        ),
        news_days=settings.news_lookback_days,
    )

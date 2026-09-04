from app.pipelines.prices import PricePipeline
from app.providers.yahoo import YahooMarketDataProvider


def get_price_pipeline() -> PricePipeline:
    return PricePipeline(YahooMarketDataProvider())

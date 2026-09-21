import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collections.abc import AsyncIterator, Callable  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.api.dependencies import get_price_pipeline  # noqa: E402
from app.db.session import get_db_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.pipelines.prices import PricePipeline  # noqa: E402
from app.providers.base import MarketDataProvider  # noqa: E402


async def _no_database() -> AsyncIterator[None]:
    """Route tests exercise the no-persistence path; the pipeline skips a None session."""
    yield None


@pytest.fixture
def make_client() -> Callable[..., httpx.AsyncClient]:
    def _make(provider: MarketDataProvider | None = None) -> httpx.AsyncClient:
        app = create_app()
        if provider is not None:
            app.dependency_overrides[get_price_pipeline] = lambda: PricePipeline(provider)
        app.dependency_overrides[get_db_session] = _no_database
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    return _make

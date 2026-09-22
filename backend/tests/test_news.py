from datetime import UTC, datetime, timedelta

import pytest

from app.pipelines.news import NewsPipeline, deduplicate
from app.providers.news.base import NewsItem, NewsProvider, normalize_title
from app.providers.news.yahoo_rss import YahooRssNewsProvider

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)


def item(title: str, source: str = "yahoo_rss", minutes: int = 0, ticker: str = "NVDA") -> NewsItem:
    return NewsItem(
        ticker=ticker,
        published_at=NOW - timedelta(minutes=minutes),
        source=source,
        title=title,
        url=f"https://example.test/{abs(hash(title))}",
    )


class StubNewsProvider(NewsProvider):
    def __init__(self, name: str, items: list[NewsItem] | None = None, failure: Exception | None = None) -> None:
        self.name = name
        self.items = items or []
        self.failure = failure

    async def fetch(self, ticker: str) -> list[NewsItem]:
        if self.failure is not None:
            raise self.failure
        return self.items


def test_the_same_headline_from_two_feeds_is_one_story() -> None:
    merged = deduplicate([item("Nvidia beats estimates"), item("Nvidia beats estimates", source="yfinance")])

    assert len(merged) == 1


@pytest.mark.parametrize(
    "variant",
    ["Nvidia Beats Estimates", "nvidia beats estimates.", "Nvidia   beats   estimates", "Nvidia beats estimates  "],
)
def test_syndicated_copies_differing_only_in_form_collapse(variant: str) -> None:
    """Syndication changes casing, spacing and trailing punctuation far more than wording."""
    assert len(deduplicate([item("Nvidia beats estimates"), item(variant, source="yfinance")])) == 1


def test_genuinely_different_headlines_are_kept_apart() -> None:
    assert len(deduplicate([item("Nvidia beats estimates"), item("Nvidia misses estimates")])) == 2


def test_the_same_story_about_two_tickers_is_two_rows() -> None:
    """Dedup is per ticker: one story can matter to several holdings."""
    pair = [item("Chip tariffs announced"), item("Chip tariffs announced", ticker="AMD")]

    assert len({i.ticker for i in deduplicate(pair)}) == 2


def test_the_earliest_sighting_wins() -> None:
    """Keeping the earliest timestamp is what dates the story to when it broke."""
    merged = deduplicate([item("Nvidia beats estimates", minutes=5), item("Nvidia beats estimates", source="yfinance", minutes=90)])

    assert merged[0].published_at == NOW - timedelta(minutes=90)


def test_results_are_newest_first() -> None:
    merged = deduplicate([item("older", minutes=600), item("newest", minutes=1), item("middle", minutes=60)])

    assert [i.title for i in merged] == ["newest", "middle", "older"]


async def test_one_failing_source_does_not_sink_the_others() -> None:
    """SEC being slow must not cost you the headlines."""
    pipeline = NewsPipeline(
        [
            StubNewsProvider("yahoo_rss", [item("Nvidia beats estimates")]),
            StubNewsProvider("sec_edgar", failure=TimeoutError("sec timed out")),
        ]
    )

    items, available, failed = await pipeline.collect("NVDA")

    assert [i.title for i in items] == ["Nvidia beats estimates"]
    assert available == ["yahoo_rss"]
    assert failed == ["sec_edgar"]


async def test_no_sources_returning_anything_is_not_an_error() -> None:
    pipeline = NewsPipeline([StubNewsProvider("yahoo_rss"), StubNewsProvider("yfinance")])

    items, available, failed = await pipeline.collect("NVDA")

    assert items == []
    assert failed == []
    assert available == ["yahoo_rss", "yfinance"]


def test_rss_entries_without_a_usable_date_or_link_are_dropped() -> None:
    feed = """<rss><channel>
      <item><title>Good one</title><link>https://example.test/a</link>
            <pubDate>Mon, 21 Sep 2026 18:30:00 GMT</pubDate></item>
      <item><title>No date</title><link>https://example.test/b</link></item>
      <item><title>No link</title><pubDate>Mon, 21 Sep 2026 18:30:00 GMT</pubDate></item>
    </channel></rss>"""

    parsed = YahooRssNewsProvider("StockSage/test")._parse("NVDA", feed)

    assert [i.title for i in parsed] == ["Good one"]
    assert parsed[0].published_at == datetime(2026, 9, 21, 18, 30, tzinfo=UTC)


def test_unparseable_feed_yields_nothing_rather_than_raising() -> None:
    assert YahooRssNewsProvider("StockSage/test")._parse("NVDA", "<html>rate limited</html>") == []


def test_normalize_title_is_stable_across_presentation() -> None:
    assert normalize_title("  Nvidia  BEATS Estimates.. ") == normalize_title("nvidia beats estimates")


def test_sec_stays_off_until_a_contact_address_is_configured() -> None:
    """The SEC answers 403 to a User-Agent naming no contact, so the source is opt-in."""
    from app.providers.news.sec_edgar import SecFilingsNewsProvider

    assert not SecFilingsNewsProvider("StockSage/0.1").enabled
    assert SecFilingsNewsProvider("StockSage/0.1 (someone@example.com)").enabled


async def test_disabled_sec_returns_nothing_without_calling_out() -> None:
    from app.providers.news.sec_edgar import SecFilingsNewsProvider

    provider = SecFilingsNewsProvider("StockSage/0.1")
    provider._ticker_to_cik = {}  # any network use would have to populate this

    assert await provider.fetch("NVDA") == []
    assert provider._ticker_to_cik == {}


def test_sec_keeps_material_filings_and_drops_insider_noise() -> None:
    """Form 4 and 144 are about 80% of a large filer's recent submissions and are not
    events; 8-K and the periodic reports are."""
    from app.providers.news.sec_edgar import SecFilingsNewsProvider

    recent = {
        "form": ["4", "8-K", "144", "10-Q", "4", "SC 13G/A"],
        "filingDate": ["2026-09-18", "2026-09-03", "2026-09-02", "2026-08-26", "2026-08-20", "2026-08-01"],
        "primaryDocDescription": ["FORM 4", "8-K", "", "10-Q", "FORM 4", ""],
    }

    items = SecFilingsNewsProvider("x (a@b.com)")._to_items("NVDA", 1045810, recent)

    assert [i.published_at.date().isoformat() for i in items] == ["2026-09-03", "2026-08-26"]
    assert items[0].title == "NVDA filed 8-K on 2026-09-03: Material event reported to the SEC"
    assert all(i.source == "sec_edgar" and i.publisher == "SEC EDGAR" for i in items)


def test_two_filings_of_the_same_form_are_two_stories() -> None:
    """Without the date in the headline, every 8-K a company ever filed shares a title
    and deduplication keeps one -- dated to the oldest, which then falls outside any
    recent window."""
    from app.pipelines.news import deduplicate
    from app.providers.news.sec_edgar import SecFilingsNewsProvider

    recent = {
        "form": ["8-K", "8-K"],
        "filingDate": ["2026-09-03", "2026-08-17"],
        "primaryDocDescription": ["8-K", "8-K"],
        "accessionNumber": ["0001045810-26-000078", "0001045810-26-000069"],
        "primaryDocument": ["nvda-20260902.htm", "nvda-20260817.htm"],
        "items": ["2.02,9.01", "8.01"],
    }

    parsed = SecFilingsNewsProvider("x (a@b.com)")._to_items("NVDA", 1045810, recent)

    assert len({item.content_hash for item in parsed}) == 2
    assert len(deduplicate(parsed)) == 2


def test_a_filing_links_to_the_document_and_names_its_items() -> None:
    from app.providers.news.sec_edgar import SecFilingsNewsProvider

    recent = {
        "form": ["8-K"],
        "filingDate": ["2026-09-03"],
        "primaryDocDescription": ["8-K"],
        "accessionNumber": ["0001045810-26-000078"],
        "primaryDocument": ["nvda-20260902.htm"],
        "items": ["2.02,9.01"],
    }

    item = SecFilingsNewsProvider("x (a@b.com)")._to_items("NVDA", 1045810, recent)[0]

    assert item.title == "NVDA filed 8-K on 2026-09-03: Material event reported to the SEC"
    assert item.url == (
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000078/nvda-20260902.htm"
    )
    assert "2.02 (results of operations)" in (item.summary or "")

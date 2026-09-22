import logging
from datetime import UTC, datetime, time

import httpx

from app.providers.news.base import NewsItem, NewsProvider


logger = logging.getLogger(__name__)

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FILING_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik:010d}&type={form}"

# Roughly 80% of a large filer's recent submissions are Form 4 and 144 -- insider
# transactions and sale notices. Those are not events; these are.
MATERIAL_FORMS = {"8-K", "10-Q", "10-K", "S-1", "424B5", "DEFA14A"}

FORM_DESCRIPTIONS = {
    "8-K": "Material event reported to the SEC",
    "10-Q": "Quarterly report filed with the SEC",
    "10-K": "Annual report filed with the SEC",
    "S-1": "Registration statement filed with the SEC",
    "424B5": "Prospectus supplement filed with the SEC",
    "DEFA14A": "Additional proxy material filed with the SEC",
}


class SecFilingsNewsProvider(NewsProvider):
    """Material SEC filings as news. Official, free and unmetered, and it catches
    events the headline feeds report late or not at all."""

    name = "sec_edgar"

    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        # The SEC's fair-access policy expects a declared User-Agent, ideally with a
        # contact address. It is configuration so nobody's address ends up in the repo.
        self.user_agent = user_agent
        self.timeout = timeout
        self._ticker_to_cik: dict[str, int] | None = None

    @property
    def enabled(self) -> bool:
        """The SEC answers 403 unless the User-Agent names a contact address, so this
        source stays off until one is configured rather than retrying a refusal."""
        return "@" in self.user_agent

    async def fetch(self, ticker: str) -> list[NewsItem]:
        if not self.enabled:
            logger.info(
                "sec filings skipped: set SEC_USER_AGENT to include a contact address",
                extra={"ticker": ticker},
            )
            return []
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers={"User-Agent": self.user_agent}
            ) as client:
                cik = await self._lookup_cik(client, ticker)
                if cik is None:
                    return []
                response = await client.get(SUBMISSIONS_URL.format(cik=cik))
                response.raise_for_status()
                recent = response.json()["filings"]["recent"]
        except Exception:
            logger.warning("sec filings fetch failed", exc_info=True, extra={"ticker": ticker})
            return []

        return self._to_items(ticker, cik, recent)

    def _to_items(self, ticker: str, cik: int, recent: dict) -> list[NewsItem]:
        items: list[NewsItem] = []
        for index, form in enumerate(recent.get("form", [])):
            if form not in MATERIAL_FORMS:
                continue
            published = _parse_filing_date(recent["filingDate"][index])
            if published is None:
                continue
            description = (recent.get("primaryDocDescription") or [None] * (index + 1))[index]
            items.append(
                NewsItem(
                    ticker=ticker,
                    published_at=published,
                    source=self.name,
                    # The form itself is the story; its own description is usually just
                    # the form number again, so the headline has to be built.
                    title=f"{ticker} filed {form}: {FORM_DESCRIPTIONS.get(form, form)}",
                    url=FILING_URL.format(cik=cik, form=form),
                    publisher="SEC EDGAR",
                    summary=str(description) if description else None,
                )
            )
        return items

    async def _lookup_cik(self, client: httpx.AsyncClient, ticker: str) -> int | None:
        if self._ticker_to_cik is None:
            response = await client.get(TICKER_MAP_URL)
            response.raise_for_status()
            self._ticker_to_cik = {
                str(row["ticker"]).upper(): int(row["cik_str"]) for row in response.json().values()
            }
        return self._ticker_to_cik.get(ticker.upper())


def _parse_filing_date(value: str) -> datetime | None:
    try:
        return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time(0, 0), tzinfo=UTC)
    except (TypeError, ValueError):
        return None

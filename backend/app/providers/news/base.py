import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


_WHITESPACE = re.compile(r"\s+")
_TRAILING = re.compile(r"[\s\-–—:.,!?'\"]+$")


@dataclass(frozen=True)
class NewsItem:
    ticker: str
    published_at: datetime
    source: str
    title: str
    url: str
    publisher: str | None = None
    summary: str | None = None

    @property
    def content_hash(self) -> str:
        """Identity of the story, so the same headline arriving from several feeds
        lands once. Syndicated copies differ in punctuation and casing far more often
        than in wording, and their URLs differ almost always."""
        return hashlib.sha256(normalize_title(self.title).encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    return _TRAILING.sub("", _WHITESPACE.sub(" ", title.strip().lower()))


class NewsProvider(ABC):
    name: str

    @abstractmethod
    async def fetch(self, ticker: str) -> list[NewsItem]:
        """Recent stories for the ticker. Implementations return what the feed offers
        and never raise for an empty feed -- the pipeline decides what is missing."""
        raise NotImplementedError

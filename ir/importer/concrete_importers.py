from typing import List, Optional
from urllib.parse import urlsplit

from aqt.utils import getText

from ir.lib.feedparser import parse
from ir.importer.exceptions import ErrorLevel
from ir.importer.web import Web
from ir.settings import SettingsManager
from ir.util import Article, selectEntriesToImport2

from .base_importer import BaseImporter
from .models import NoteModel
from .exceptions import ImporterError, ErrorLevel


class WebpageImporter(BaseImporter):
    def __init__(self, settings: SettingsManager, web: Web):
        super().__init__(settings)
        self.web = web

    def _getArticles(self) -> List[Article]:
        url, accepted = getText("Enter URL:", title="Import Webpage")
        if not url or not accepted:
            return []

        if not urlsplit(url).scheme:
            url = "http://" + url

        return [Article(title=url, data=url)]

    def _selectArticles(self, articles: List[Article]) -> List[Article]:
        return articles

    def _processArticle(self, article: Article, priority: Optional[str]) -> NoteModel:
        webpage = self.web.download(article.data)
        return NoteModel(webpage.title, webpage.body, webpage.url, priority)

    def _getProgressLabel(self) -> str:
        return "Importing webpage..."


class FeedImporter(BaseImporter):
    def __init__(self, settings: SettingsManager, web: Web):
        super().__init__(settings)
        self.web = web
        self.log = settings["feedLog"]

    def _getArticles(self) -> List[Article]:
        feedUrl, accepted = getText("Enter RSS URL:", title="Import Feed")
        if not feedUrl or not accepted:
            return []

        if not urlsplit(feedUrl).scheme:
            feedUrl = "http://" + feedUrl

        try:
            feed = parse(
                feedUrl,
                agent=self.settings["userAgent"],
                etag=self.log[feedUrl]["etag"],
                modified=self.log[feedUrl]["modified"],
            )
        except KeyError:
            self.log[feedUrl] = {"downloaded": []}
            feed = parse(feedUrl, agent=self.settings["userAgent"])

        if feed["status"] not in [200, 301, 302]:
            raise ImporterError(
                ErrorLevel.WARNING,
                f"The remote server returned an unexpected status: {feed['status']}",
            )

        articles = [
            Article(title=e["title"], data={"feedUrl": feedUrl, "feed": feed, "url": e["link"]})
            for e in feed["entries"]
            if e["link"] not in self.log[feedUrl]["downloaded"]
        ]

        if not articles:
            raise ImporterError(
                ErrorLevel.WARNING, "There are no new entries in the feed."
            )

        return articles

    def _selectArticles(self, articles: List[Article]) -> List[Article]:
        return selectEntriesToImport2(articles)

    def _processArticle(self, article: Article, priority: Optional[str]) -> NoteModel:
        url = article.data["url"]
        webpage = self.web.download(url)

        # TODO: maybe add postprocessing method
        feedUrl = article.data["feedUrl"]
        feed = article.data["feed"]
        self.log[feedUrl]["downloaded"].append(url)
        self.log[feedUrl]["etag"] = feed.etag if hasattr(feed, "etag") else ""
        self.log[feedUrl]["modified"] = feed.modified if hasattr(feed, "modified") else ""

        return NoteModel(webpage.title, webpage.body, webpage.url, priority)

    def _getProgressLabel(self) -> str:
        return "Importing feed..."

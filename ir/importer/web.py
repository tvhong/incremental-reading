from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import url2pathname
from attr import dataclass
from bs4 import BeautifulSoup, Comment, PageElement, Tag
from requests import get
from aqt import mw

from ir.settings import SettingsManager
from .exceptions import ErrorLevel, ImporterError


@dataclass
class Webpage:
    url: str
    title: str
    body: str


class Web:
    def __init__(self, settings: SettingsManager):
        self._settings = settings

    def processWebpage(self, url: str) -> Webpage:
        webpage = self._fetchWebpage(url)
        return self._parseWebpage(url, webpage)

    def _fetchWebpage(self, url: str) -> BeautifulSoup:
        if urlsplit(url).scheme not in ["http", "https"]:
            raise ImporterError(
                ErrorLevel.CRITICAL, "Only HTTP requests are supported."
            )

        try:
            html = get(
                url, headers={"User-Agent": self._settings["userAgent"]}, timeout=5
            ).content
            webpage = self._cleanWebpage(html, url)
        except HTTPError as error:
            raise ImporterError(
                ErrorLevel.WARNING,
                f"The remote server has returned an error: HTTP Error {error.code} ({error.reason})",
            ) from error
        except ConnectionError as error:
            raise ImporterError(
                ErrorLevel.WARNING, "There was a problem connecting to the website."
            ) from error

        return webpage

    def _parseWebpage(self, url: str, webpage: BeautifulSoup):
        body = "\n".join(map(str, webpage.find("body").children))
        title = webpage.title.string if webpage.title else url

        return Webpage(url, title, body)

    def _cleanWebpage(self, html, url, local=False):
        webpage = BeautifulSoup(html, "html.parser")

        for tagName in self._settings["badTags"]:
            for tag in webpage.find_all(tagName):
                tag.decompose()

        for c in webpage.find_all(text=lambda s: isinstance(s, Comment)):
            c.extract()

        for a in webpage.find_all("a"):
            self._processATag(url, a)

        for img in webpage.find_all("img"):
            self._processImgTag(url, img, local)

        for link in webpage.find_all("link"):
            self._processLinkTag(url, link, local)

        return webpage

    def _processATag(self, url: str, a: PageElement):
        if a.get("href"):
            if a["href"].startswith("#"):
                # Need to override onclick for named anchor to work
                # See https://forums.ankiweb.net/t/links-to-named-anchors-malfunction/5157
                if not a.get("onclick"):
                    named_anchor = a["href"][1:]  # Remove first hash
                    a["href"] = "javascript:;"
                    a["onclick"] = f"document.location.hash='{named_anchor}';"
            else:
                a["href"] = urljoin(url, a["href"])

    def _processImgTag(self, url: str, img: Tag, local=False):
        """
        Copy image from local storage to Anki media folder and replace src with local path
        """
        if not img.get("src"):
            return

        img["src"] = urljoin(url, img["src"])
        if local and urlsplit(img["src"]).scheme == "file":
            filepath = url2pathname(urlsplit(img["src"]).path)
            mediafilepath = mw.col.media.add_file(filepath)
            img["src"] = mediafilepath

        # Some webpages send broken base64-encoded URI in srcset attribute.
        # Remove them for now.
        del img["srcset"]

    def _processLinkTag(self, url: str, link: Tag, local=False):
        if link.get("href"):
            link["href"] = urljoin(url, link.get("href", ""))
        if local and urlsplit(link["href"]).scheme == "file":
            filepath = url2pathname(urlsplit(link["href"]).path)
            mediafilepath = mw.col.media.add_file(filepath)
            print(filepath, "===>", mediafilepath)
            link["href"] = mediafilepath

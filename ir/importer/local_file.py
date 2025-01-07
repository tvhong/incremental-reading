import os
from pathlib import Path
from urllib.parse import urlunsplit
from attr import dataclass
from bs4 import BeautifulSoup

from ir.settings import SettingsManager

from .exceptions import ErrorLevel, ImporterError
from .html_cleaner import HtmlCleaner


@dataclass
class ParsedFile:
    title: str
    body: str


class LocalFile:
    def __init__(self, settings: SettingsManager) -> None:
        self._settings = settings
        self._htmlCleaner = HtmlCleaner()
        
    def process(self, filepath: str) -> ParsedFile:
        if not filepath:
            raise ValueError("Filepath is empty")

        filepath = Path(filepath).as_posix()  # Convert Windows Path to Linux
        if not os.path.isfile(filepath):
            raise ImporterError(
                ErrorLevel.CRITICAL, f"File [{filepath}] Not exists."
            )

        localPage = self._fetchLocalPage(filepath)

        return self._parseFile(filepath, localPage)

    def _fetchLocalPage(self, filepath: str) -> BeautifulSoup:
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
            url = urlunsplit(("file", "", filepath, None, None))
            return self._htmlCleaner.clean(html, url, True)

    def _parseFile(self, filepath: str, localPage: BeautifulSoup):
        body = "\n".join(map(str, localPage.find("body").children))
        title = localPage.title.string if localPage.title else filepath

        return ParsedFile(title, body)
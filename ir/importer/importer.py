# Copyright 2018 Timothée Chauvin
# Copyright 2017-2019 Joseph Lorimer <joseph@lorimer.me>
#
# Permission to use, copy, modify, and distribute this software for any purpose
# with or without fee is hereby granted, provided that the above copyright
# notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

from datetime import date
from typing import Optional, List
from urllib.parse import urlsplit

from anki.notes import Note

from .exceptions import ErrorLevel, ImporterError
from .html_cleaner import HtmlCleaner
from .local_file import LocalFile
from .web import Web

try:
    from PyQt6.QtCore import Qt
except ModuleNotFoundError:
    from PyQt5.QtCore import Qt

from aqt import mw
from aqt.qt import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)
from aqt.utils import (
    chooseList,
    getFile,
    getText,
    showCritical,
    showInfo,
    showWarning,
    tooltip,
)

from ir.lib.feedparser import parse
from ir.settings import SettingsManager
from ir.util import setField, selectEntriesToImport

from .concrete_importers import WebpageImporter, FeedImporter, EpubImporter, PocketImporter
from .epub import getEpubToc
from .pocket import Pocket


class Importer:
    _pocket: Optional[Pocket] = None
    _web: Optional[Web] = None
    _localFile: Optional[LocalFile] = None
    _htmlCleaner: Optional[HtmlCleaner] = None
    _settings: Optional[SettingsManager] = None

    _webImporter: Optional[WebpageImporter] = None
    _feedImporter: Optional[FeedImporter] = None
    _epubImporter: Optional[EpubImporter] = None
    _pocketImporter: Optional[PocketImporter] = None

    @property
    def pocket(self) -> Pocket:
        if not self._pocket:
            raise ValueError("Pocket is not initialized")
        return self._pocket

    @property
    def web(self) -> Web:
        if not self._web:
            raise ValueError("Web is not initialized")
        return self._web

    @property
    def localFile(self) -> LocalFile:
        if not self._localFile:
            raise ValueError("LocalFile is not initialized")
        return self._localFile

    @property
    def htmlCleaner(self) -> HtmlCleaner:
        if not self._htmlCleaner:
            raise ValueError("HtmlCleaner is not initialized")
        return self._htmlCleaner

    @property
    def settings(self) -> SettingsManager:
        if not self._settings:
            raise ValueError("Settings is not initialized")
        return self._settings

    @property
    def webImporter(self) -> WebpageImporter:
        if not self._webImporter:
            raise ValueError("WebpageImporter is not initialized")
        return self._webImporter

    @property
    def feedImporter(self) -> FeedImporter:
        if not self._feedImporter:
            raise ValueError("FeedImporter is not initialized")
        return self._feedImporter

    @property
    def epubImporter(self) -> EpubImporter:
        if not self._epubImporter:
            raise ValueError("EpubImporter is not initialized")
        return self._epubImporter

    @property
    def pocketImporter(self) -> PocketImporter:
        if not self._pocketImporter:
            raise ValueError("PocketImporter is not initialized")
        return self._pocketImporter

    def changeProfile(self, settings: SettingsManager):
        self._settings = settings
        self._web = Web(self._settings)
        self._localFile = LocalFile()
        self._htmlCleaner = HtmlCleaner()
        self._pocket = Pocket()

        self._webImporter = WebpageImporter(self._settings, self._web)
        self._feedImporter = FeedImporter(self._settings, self._web)
        self._epubImporter = EpubImporter(self._settings, self._localFile)
        self._pocketImporter = PocketImporter(self._settings, self._pocket, self._web)

    def importWebpage(self):
        self.webImporter.importContent()


    def oldImportWebpage(self, url=None, priority=None, silent=False, title=None):
        # Template:
        # 1. Get the URL and maybe a list of entries
        # 2. Get prirotiy
        # 3. Show progress bar
        # 4. Download all entries
        # 5. Import each entry and update progress bar
        # 6. Finish progress bar
        if not url:
            url, accepted = getText("Enter URL:", title="Import Webpage")
        else:
            accepted = True

        if not url or not accepted:
            return

        if not urlsplit(url).scheme:
            url = "http://" + url

        if self.settings["prioEnabled"] and not priority:
            priority = self._getPriority(title)

        try:
            webpage = self.web.process(url)
        except ImporterError as e:
            if e.errorLevel == ErrorLevel.CRITICAL:
                showCritical(e.message)
            elif e.errorLevel == ErrorLevel.WARNING:
                showWarning(e.message)
            return

        source = self.settings["sourceFormat"].format(
            date=date.today(), url=f'<a href="{url}">{url}</a>'
        )
        if not title:
            title = webpage.title

        deck = self._createNote(title, webpage.body, source, priority)

        if not silent:
            tooltip(f"Added to deck: {deck}")

        return deck

    def importFeed(self):
        self.feedImporter.importContent()

    def importPocket(self):
        self.pocketImporter.importContent()

    def importEpub(self):
        self._epubImporter.importContent()

    def _getPriority(self, name=None) -> str:
        if name:
            prompt = f"Select priority for <b>{name}</b>"
        else:
            prompt = "Select priority for import"
        return self.settings["priorities"][
            chooseList(prompt, self.settings["priorities"])
        ]

    def _createNote(self, title, text, source, priority=None):
        if self.settings["importDeck"]:
            deck = mw.col.decks.by_name(self.settings["importDeck"])
            if not deck:
                showWarning(
                    "Destination deck no longer exists. " "Please update your settings."
                )
                return
            deckId = deck["id"]
        else:
            deckId = mw.col.conf["curDeck"]

        model = mw.col.models.by_name(self.settings["modelName"])
        note = Note(mw.col, model)
        setField(note, self.settings["titleField"], title)
        setField(note, self.settings["textField"], text)
        setField(note, self.settings["sourceField"], source)
        if priority:
            setField(note, self.settings["prioField"], priority)

        note.note_type()["did"] = deckId
        mw.col.addNote(note)

        return mw.col.decks.get(deckId)["name"]

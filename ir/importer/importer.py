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

import os
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from anki.notes import Note

from ir.importer.html_cleaner import HtmlCleaner
from ir.importer.web import Web

from .exceptions import ErrorLevel, ImporterError

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
from ir.util import setField

from .epub import get_epub_toc
from .pocket import Pocket


class Importer:
    _pocket: Optional[Pocket] = None
    _web: Optional[Web] = None
    _htmlCleaner: Optional[HtmlCleaner] = None
    _settings: Optional[SettingsManager] = None

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
    def htmlCleaner(self) -> HtmlCleaner:
        if not self._htmlCleaner:
            raise ValueError("HtmlCleaner is not initialized")
        return self._htmlCleaner

    @property
    def settings(self) -> SettingsManager:
        if not self._settings:
            raise ValueError("Settings is not initialized")
        return self._settings

    def changeProfile(self, settings: SettingsManager):
        self._settings = settings
        self._web = Web(self._settings)
        self._pocket = Pocket()

    def importWebpage(self, url=None, priority=None, silent=False, title=None):
        # Template:
        # 1. Get the URL and maybe a list of entries
        # 2. Download all entries
        # 3. Get prirotiy
        # 4. Show progress
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
            webpage = self.web.processWebpage(url)
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
        url, accepted = getText("Enter URL:", title="Import Feed")

        if not url or not accepted:
            return

        if not urlsplit(url).scheme:
            url = "http://" + url

        priority = self._getPriority() if self.settings["prioEnabled"] else None

        log = self.settings["feedLog"]
        try:
            feed = parse(
                url,
                agent=self.settings["userAgent"],
                etag=log[url]["etag"],
                modified=log[url]["modified"],
            )
        except KeyError:
            log[url] = {"downloaded": []}
            feed = parse(url, agent=self.settings["userAgent"])

        if feed["status"] not in [200, 301, 302]:
            showWarning(
                "The remote server has returned an unexpected status: "
                f'{feed["status"]}'
            )

        entries = [
            {"text": e["title"], "data": e}
            for e in feed["entries"]
            if e["link"] not in log[url]["downloaded"]
        ]

        if not entries:
            showInfo("There are no new items in this feed.")
            return

        selected = self._selectEntriesToImport(entries)

        if not selected:
            return

        n = len(selected)

        mw.progress.start(label="Importing feed entries...", max=n, immediate=True)

        for i, entry in enumerate(selected, start=1):
            deck = self.importWebpage(entry["link"], priority, True)
            log[url]["downloaded"].append(entry["link"])
            mw.progress.update(value=i)

        log[url]["etag"] = feed.etag if hasattr(feed, "etag") else ""
        log[url]["modified"] = feed.modified if hasattr(feed, "modified") else ""

        mw.progress.finish()
        tooltip(f"Added {n} item(s) to deck: {deck}")

    def importPocket(self):
        articles = self.pocket.getArticles()
        if not articles:
            return

        selected = self._selectEntriesToImport(articles)

        priority = self._getPriority() if self.settings["prioEnabled"] else None

        if selected:
            n = len(selected)
            mw.progress.start(
                label="Importing Pocket articles...", max=n, immediate=True
            )

            for i, article in enumerate(selected, start=1):
                deck = self.importWebpage(
                    article["given_url"], priority, True, article["resolved_title"]
                )
                if self.settings["pocketArchive"]:
                    self.pocket.archive(article)
                mw.progress.update(value=i)

            mw.progress.finish()
            tooltip(f"Added {n} item(s) to deck: {deck}")

    def importEpub(self, epub_file_path=None):
        if not epub_file_path:
            epub_file_path = getFile(
                None, "Enter epub File path", None, filter="*.epub"
            )

        if not epub_file_path:
            return

        articles = get_epub_toc(epub_file_path)
        if not articles:
            showInfo(f"No articles found in {epub_file_path}.")
            return
        selected = self._selectEntriesToImport(articles)

        priority = self._getPriority() if self.settings["prioEnabled"] else None

        if selected:
            n = len(selected)

            mw.progress.start(label="Importing Epub articles...", max=n, immediate=True)

            importedArticle = []
            for i, article in enumerate(selected, start=1):
                text = article.get("text")
                href = article["href"]
                if href not in importedArticle:
                    deck = self._importLocalFile(href, priority, True, text)
                    importedArticle.append(href)
                else:
                    print(href, "Already imported, Skipping")
                mw.progress.update(value=i)

            mw.progress.finish()
            tooltip(f"Added {len(importedArticle)} item(s) to deck: {deck}")

    def _getPriority(self, name=None):
        if name:
            prompt = f"Select priority for <b>{name}</b>"
        else:
            prompt = "Select priority for import"
        return self.settings["priorities"][
            chooseList(prompt, self.settings["priorities"])
        ]

    def _selectEntriesToImport(self, choices):
        if not choices:
            return []

        dialog = QDialog(mw)
        layout = QVBoxLayout()

        textWidget = QLabel()
        textWidget.setText("Select entries to import: ")

        listWidget = QListWidget()
        listWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        for c in choices:
            item = QListWidgetItem(c["text"])
            item.setData(Qt.ItemDataRole.UserRole, c["data"])
            listWidget.addItem(item)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
            | QDialogButtonBox.StandardButton.SaveAll
        )
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        buttonBox.setOrientation(Qt.Orientation.Horizontal)

        layout.addWidget(textWidget)
        layout.addWidget(listWidget)
        layout.addWidget(buttonBox)

        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.resize(500, 500)
        choice = dialog.exec()

        if choice == 1:
            return [
                listWidget.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(listWidget.count())
                if listWidget.item(i).isSelected()
            ]
        return []

    def _importLocalFile(self, filepath=None, priority=None, silent=False, title=None):
        if not filepath:
            filepath = getFile(None, "Import Local File", None, filter="*")

        if not filepath:
            return

        filepath = Path(filepath).as_posix()  # Convert Windows Path to Linux
        if not os.path.isfile(filepath):
            showCritical(f"File [{filepath}] Not exists.")
            return

        localPage = self._fetchLocalPage(filepath)

        body = "\n".join(map(str, localPage.find("body").children))
        source = self.settings["sourceFormat"].format(
            date=date.today(), url=f'<a href="{filepath}">{filepath}</a>'
        )

        if not title:
            title = localPage.title.string if localPage.title else filepath

        if self.settings["prioEnabled"] and not priority:
            priority = self._getPriority(title)

        deck = self._createNote(title, body, source, priority)

        if not silent:
            tooltip(f"Added to deck: {deck}")

        return deck

    def _fetchLocalPage(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
            url = urlunsplit(("file", "", filepath, None, None))
            return self.htmlCleaner.clean(html, url, True)

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

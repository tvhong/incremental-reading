from typing import List, Optional
from urllib.parse import urlsplit

from aqt.utils import getText

from ir.importer.web import Web
from ir.settings import SettingsManager
from ir.util import ImportEntry

from .base_importer import BaseImporter
from .models import NoteModel


class WebpageImporter(BaseImporter):
    def __init__(self, settings: SettingsManager, web: Web):
        super().__init__(settings)
        self.web = web

    def _getEntries(self) -> List[ImportEntry]:
        url, accepted = getText("Enter URL:", title="Import Webpage")
        if not url or not accepted:
            return []

        if not urlsplit(url).scheme:
            url = "http://" + url

        return [ImportEntry(text=url, data=url)]

    def _selectEntries(self, entries: List[ImportEntry]) -> List[ImportEntry]:
        return entries

    def _processEntry(self, entry: ImportEntry, priority: Optional[str]) -> NoteModel:
        webpage = self.web.process(entry.data)
        return NoteModel(webpage.title, webpage.body, webpage.url, priority)

    def _getProgressLabel(self) -> str:
        return "Importing webpage..."

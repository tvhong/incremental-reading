from typing import List, Optional
from urllib.parse import urlsplit

from aqt.utils import getText
from ir.importer.models import ImportEntry, NoteModel

from .base_importer import BaseImporter


class WebpageImporter(BaseImporter):
    def __init__(self, settings, web):
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

    def _processEntry(self, entry: ImportEntry, priority: Optional[str]) -> Optional[str]:
        webpage = self.web.process(entry.data)
        noteModel = NoteModel(webpage.title, webpage.body, entry.data, priority)
        return self._createNote(noteModel)

    def _getProgressLabel(self) -> str:
        return "Importing webpage..."

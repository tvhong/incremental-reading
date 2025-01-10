from dataclasses import dataclass
from typing import Any


@dataclass
class ImportEntry:
    text: str
    data: Any


@dataclass
class NoteModel:
    title: str
    content: str
    source: str
    priority: str

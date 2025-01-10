from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ImportEntry:
    text: str
    data: Any


@dataclass
class NoteModel:
    title: str
    content: str
    source: str
    priority: Optional[str]

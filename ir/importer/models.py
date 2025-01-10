from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class NoteModel:
    title: str
    content: str
    # TODO: rename to url
    source: str
    priority: Optional[str]

from dataclasses import dataclass
from typing import Any


@dataclass
class EntryChoice:
    text: str
    data: Any

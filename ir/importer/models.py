from dataclasses import dataclass
from typing import Any


@dataclass
class ImportEntry:
    text: str
    data: Any

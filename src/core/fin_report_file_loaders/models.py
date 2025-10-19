from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ReportFileData:
    content: str
    metadata: Dict[str, Any]

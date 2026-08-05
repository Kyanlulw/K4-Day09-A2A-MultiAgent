import json
from pathlib import Path
from typing import Any


def write_trace(path: Path, event: dict[str, Any]) -> None:
    """Append one actual pipeline event as one JSONL line."""
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

"""The last spoken texts, oldest first."""

import json
import os
import tempfile
from pathlib import Path

_KEPT = 50
_CHIPS = 12
_LABEL = 40


def _path() -> Path:
    # Home is read on each call, not at import.
    return Path.home() / ".quenya-speak" / "history.jsonl"


def load() -> list[str]:
    """Return spoken texts, oldest first. A damaged line is skipped."""
    path = _path()
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    items: list[str] = []
    for line in raw.splitlines():
        text = _text(line)
        if text is not None:
            items.append(text)
    return items[-_KEPT:]


def _text(line: str) -> str | None:
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict):
        return None
    text = record.get("text")
    if not isinstance(text, str):
        return None
    return text


def remember(text: str) -> list[str]:
    """Drop an earlier equal text, append this one, and keep the last 50."""
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    items = [item for item in load() if item != text]
    items.append(text)
    items = items[-_KEPT:]
    _replace(path, items)
    return items


def _replace(path: Path, items: list[str]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".history-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for item in items:
                json.dump({"text": item}, handle, ensure_ascii=False)
                handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def chips(items: list[str]) -> list[tuple[str, str]]:
    """The last 12 texts, newest first, as ``(label, full text)``."""
    return [(_label(text), text) for text in reversed(items[-_CHIPS:])]


def _label(text: str) -> str:
    lines = text.splitlines()
    first = lines[0].strip() if lines else ""
    if len(first) > _LABEL:
        return first[:_LABEL] + "\u2026"
    return first

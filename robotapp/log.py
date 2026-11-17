"""Logging that cannot leak a password.

Two rules from the plan (§5.1): a secret is fetched at the moment it is typed and dropped right after, and it
never reaches a log, an event, an exception or a screenshot. This module is the enforcement: `Secret` wraps a
value so that `str()`/`repr()`/f-strings show `***`, and a logging filter rewrites any registered value that
some other code path happens to print.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

REDACTED = "***"
_secrets: list[str] = []


class Secret:
    """A value that must not be printed. `.reveal()` is the only way to get it, and callers do that once."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value
        register_secret(value)

    def reveal(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __str__(self) -> str:
        return REDACTED

    def __repr__(self) -> str:
        return f"Secret({REDACTED})"

    def __format__(self, spec: str) -> str:
        return format(REDACTED, spec)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and other._value == self._value

    def __hash__(self) -> int:
        return hash(self._value)


def register_secret(value: str) -> None:
    """Teach the log filter a value to hide. Short values are ignored (they would redact ordinary words)."""
    if value and len(value) >= 4 and value not in _secrets:
        _secrets.append(value)


def redact(text: str) -> str:
    for value in _secrets:
        text = text.replace(value, REDACTED)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        return True


def setup(logs_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """One logger (`robotapp`) writing to stderr and, when a folder is given, to `data/logs/<date>.log`."""
    logger = logging.getLogger("robotapp")
    logger.setLevel(level)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    stream.addFilter(RedactingFilter())
    logger.addHandler(stream)

    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        path = logs_dir / f"{datetime.now():%Y-%m-%d}.log"
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(fmt)
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
    return logger


def short(text: str, limit: int = 300) -> str:
    """adb output is noisy: keep log lines readable (PLAN: 'keep adb output short')."""
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"

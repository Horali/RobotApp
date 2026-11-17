"""Reading the screen and touching it (PLAN §6.2).

uiautomator2 is attached only while a screen must be read, and detached between steps. Buttons are found by
text or description first (TikTok's resource-ids are scrambled and change with every version), then by a
resource-id learned for this app version. Every step waits for a signature — a few texts that must be on the
next screen — instead of sleeping a fixed time.

Taps land on a random point inside the element, and typing has human timing. Passwords are typed here, through
the uiautomator2 connection, and never through `adb shell input text` (§5.1).
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .log import Secret
from .window import WindowGuard


@dataclass
class Element:
    text: str = ""
    desc: str = ""
    resource_id: str = ""
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
    enabled: bool = True
    clickable: bool = False

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bounds
        return (x1 + x2) // 2, (y1 + y2) // 2

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bounds
        return max(0, x2 - x1) * max(0, y2 - y1)

    def matches(self, needle: str) -> bool:
        needle = needle.lower()
        return needle in self.text.lower() or needle in self.desc.lower() or needle == self.resource_id

    def says(self, label: str) -> bool:
        """Exact label, ignoring case and surrounding spaces: for buttons like "Post" that are also words."""
        label = label.strip().lower()
        return self.text.strip().lower() == label or self.desc.strip().lower() == label


@dataclass
class Signature:
    """What must be on screen for a step to be considered reached (`any_of` and `all_of` are substrings)."""

    name: str
    any_of: tuple[str, ...] = ()
    all_of: tuple[str, ...] = ()

    def matches(self, elements: list[Element]) -> bool:
        haystack = " \u241f ".join(f"{e.text} \u241f {e.desc}" for e in elements).lower()
        if self.all_of and not all(needle.lower() in haystack for needle in self.all_of):
            return False
        if self.any_of and not any(needle.lower() in haystack for needle in self.any_of):
            return False
        return True


class ScreenTimeout(RuntimeError):
    pass


class Screen(Protocol):
    def elements(self) -> list[Element]: ...
    def tap(self, element: Element) -> None: ...
    def long_press(self, element: Element) -> None: ...
    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None: ...
    def type_secret(self, secret: Secret) -> None: ...
    def set_text(self, text: str) -> None: ...
    def clear_field(self) -> None: ...
    def press_back(self) -> None: ...
    def swipe_up(self) -> None: ...
    def screenshot(self, path: Path) -> None: ...
    def size(self) -> tuple[int, int]: ...
    def clipboard(self) -> str | None: ...
    def focused_text(self) -> str | None: ...


def jitter(low_ms: int, high_ms: int) -> None:
    time.sleep(random.uniform(low_ms, high_ms) / 1000.0)


class U2Screen:
    """The real screen, through uiautomator2."""

    def __init__(self, device, guard: WindowGuard | None = None) -> None:
        self.device = device
        self.guard = guard or WindowGuard()

    @classmethod
    def connect(cls, serial: str, guard: WindowGuard | None = None) -> "U2Screen":
        import uiautomator2 as u2  # imported here so tests and the FakePhone never need it

        return cls(u2.connect(serial), guard)

    def elements(self) -> list[Element]:
        self.guard.check("read the screen")
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(self.device.dump_hierarchy())
        except ET.ParseError:
            return []
        out: list[Element] = []
        for node in root.iter("node"):
            bounds = (0, 0, 0, 0)
            m = re.match(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", node.get("bounds", ""))
            if m:
                bounds = tuple(int(v) for v in m.groups())  # type: ignore[assignment]
            out.append(
                Element(
                    text=node.get("text", ""),
                    desc=node.get("content-desc", ""),
                    resource_id=node.get("resource-id", ""),
                    bounds=bounds,  # type: ignore[arg-type]
                    enabled=node.get("enabled", "true") == "true",
                    clickable=node.get("clickable", "false") == "true",
                )
            )
        return out

    def tap(self, element: Element) -> None:
        self.guard.check("tap the screen")
        x, y = element.center
        x += random.randint(-8, 8)
        y += random.randint(-6, 6)
        self.device.click(x, y)
        jitter(350, 900)

    def long_press(self, element: Element) -> None:
        self.guard.check("long-press the screen")
        x, y = element.center
        self.device.long_click(x, y, 1.0)
        jitter(400, 900)

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.guard.check("type")
        for char in text:
            self.device.send_keys(char)
            jitter(min_ms, max_ms)

    def type_secret(self, secret: Secret) -> None:
        """Human-speed, and the value is dropped by the caller right after (it is never logged)."""
        self.type_text(secret.reveal(), min_ms=90, max_ms=260)

    def set_text(self, text: str) -> None:
        """Paste-like entry for a caption: one call, so newlines and emoji survive (a paste is what people do)."""
        self.guard.check("type")
        try:
            self.device(focused=True).set_text(text)
        except Exception:  # noqa: BLE001 - some fields refuse setText; the IME still works
            self.device.send_keys(text)
        jitter(300, 700)

    def clear_field(self) -> None:
        self.device(focused=True).clear_text()

    def press_back(self) -> None:
        self.device.press("back")
        jitter(250, 600)

    def swipe_up(self) -> None:
        width, height = self.device.window_size()
        self.device.swipe(width // 2, int(height * 0.72), width // 2, int(height * 0.3), 0.25)
        jitter(900, 2600)

    def screenshot(self, path: Path) -> None:
        self.guard.check("take a screenshot")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.device.screenshot(str(path))

    def size(self) -> tuple[int, int]:
        width, height = self.device.window_size()
        return int(width), int(height)

    def clipboard(self) -> str | None:
        try:
            value = self.device.clipboard
            return str(value) if value else None
        except Exception:  # noqa: BLE001 - the IME may not expose the clipboard
            return None

    def focused_text(self) -> str | None:
        try:
            info = self.device(focused=True).info
            return str(info.get("text") or "") or None
        except Exception:  # noqa: BLE001
            return None


def wait_for(screen: Screen, signature: Signature, timeout_s: float = 45.0, poll_s: float = 1.0) -> list[Element]:
    """Poll the screen until the signature matches. Raises ScreenTimeout with the texts it did see."""
    deadline = time.monotonic() + timeout_s
    seen: list[Element] = []
    while time.monotonic() < deadline:
        seen = screen.elements()
        if signature.matches(seen):
            return seen
        time.sleep(poll_s)
    texts = ", ".join(sorted({e.text or e.desc for e in seen if e.text or e.desc})[:12])
    raise ScreenTimeout(f"waited {timeout_s:.0f}s for '{signature.name}'; on screen: {texts or '(nothing readable)'}")


def find(elements: list[Element], needle: str) -> Element | None:
    for element in elements:
        if element.enabled and element.matches(needle):
            return element
    return None


def find_exact(elements: list[Element], label: str) -> Element | None:
    """A button whose whole label is `label` — used for Post/Share/Upload, where a substring is dangerous."""
    for element in elements:
        if element.enabled and element.says(label):
            return element
    return None

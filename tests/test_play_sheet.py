"""Play's "TikTok needs to download additional files" sheet (measured 2026-11-20/21, PLAN Progress).

The base APK of musically makes Play offer the bundle's dynamic modules: the sheet takes the screen after
Create and again when the camera/editor is asked for. The robot must (a) find its Dismiss control even
though the label is text and the control appears a moment after the sheet, and (b) when it keeps coming
back, stop *before* the press with the fix named in the reason - instead of burning the post on it.
"""

from pathlib import Path

import pytest

from robotapp.fake import FakePhone, fake_guard
from robotapp.journal import FAILED, Journal
from robotapp.post.base import PostSpec
from robotapp.post.tiktok import TikTokPoster
from robotapp.ui import Element


def el(text: str = "", desc: str = "", bounds=(0, 0, 100, 100), clickable: bool = False) -> Element:
    return Element(text=text, desc=desc, bounds=bounds, clickable=clickable)


SHEET = [
    el("TikTok needs to download additional files to add features", bounds=(25, 900, 1055, 1000)),
    el("Download from Play", bounds=(100, 1400, 900, 1500), clickable=True),
    el("Dismiss update dialog", bounds=(100, 1600, 900, 1700), clickable=True),
]

HOME = [
    el("For You", bounds=(0, 2200, 200, 2300)),
    el(desc="Create", bounds=(480, 2200, 600, 2320), clickable=True),
    el(desc="Profile", bounds=(900, 2200, 1080, 2320), clickable=True),
]

EDITOR = [el("Next", bounds=(900, 2200, 1050, 2320), clickable=True), el("Add sound", bounds=(0, 100, 200, 200))]


class SheetScreen:
    """A screen that shows Play's sheet for its first `sheet_reads` reads, then `then`."""

    def __init__(self, sheet_reads: int, then: list[Element], every: int = 0) -> None:
        self.sheet_reads = sheet_reads
        self.every = every          # >0: the sheet comes back after every `every` reads
        self.then = then
        self.reads = 0
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.shots: list[Path] = []

    def elements(self) -> list[Element]:
        self.reads += 1
        if self.sheet_reads > 0:
            self.sheet_reads -= 1
            return SHEET
        if self.every and self.reads % self.every == 0:
            return SHEET
        return self.then

    def tap(self, element: Element) -> None:
        label = element.text or element.desc
        self.taps.append(label)
        if "Dismiss" in label:
            self.then = self.then if self.then is not HOME else HOME

    def press_back(self) -> None:
        self.taps.append("back")

    def size(self) -> tuple[int, int]:
        return (1080, 2400)

    def clipboard(self) -> str | None:
        return None

    def focused_text(self) -> str | None:
        return self.typed[-1] if self.typed else None

    def set_text(self, text: str) -> None:
        self.typed.append(text)

    def clear_field(self) -> None:
        self.typed.clear()

    def screenshot(self, path: Path) -> None:
        self.shots.append(path)


def poster(screen, phone: FakePhone) -> TikTokPoster:
    return TikTokPoster(
        phone, screen, Journal(Path(":memory:")), "job-play-sheet",
        package="com.zhiliaoapp.musically", user=11,
    )


def spec() -> PostSpec:
    return PostSpec(upload_id="92a0c985", platform="tiktok", video=Path("clip.mp4"), caption="hai")


def test_the_sheet_is_dismissed_and_the_app_opens():
    screen = SheetScreen(sheet_reads=2, then=HOME)
    poster(screen, FakePhone(guard=fake_guard()))._open()
    assert "Dismiss update dialog" in screen.taps


def test_the_sheet_mid_flow_is_dismissed_and_the_editor_arrives():
    screen = SheetScreen(sheet_reads=1, then=EDITOR)
    from robotapp.post.tiktok import EDITOR as EDITOR_SIGNATURE

    poster(screen, FakePhone(guard=fake_guard()))._wait_past_play(EDITOR_SIGNATURE, 20)
    assert screen.taps == ["Dismiss update dialog"]


def test_a_sheet_that_never_stops_fails_before_any_press_and_names_the_fix():
    screen = SheetScreen(sheet_reads=1000, then=HOME)
    phone = FakePhone(guard=fake_guard())
    result = poster(screen, phone).post(spec())
    assert result.outcome == FAILED
    assert "bundle" in (result.reason or "").lower()
    assert "Post" not in screen.taps          # nothing was pressed

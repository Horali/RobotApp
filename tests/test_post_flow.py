"""The whole TikTok post flow, against a screen that changes when it is tapped (PLAN §6.4).

This is the closest thing to the real phone that runs on the laptop: it catches a step that looks for the wrong
label, a signature that never arrives, or a caption written into the wrong field — without touching the phone.
The screen sequence is the one TikTok 47.x shows in English.
"""

from pathlib import Path

import pytest

from robotapp.fake import FakePhone, fake_guard
from robotapp.journal import PRESSED, Journal
from robotapp.post.base import PostSpec
from robotapp.post.tiktok import TikTokPoster
from robotapp.ui import Element


def el(text: str = "", desc: str = "", bounds=(0, 0, 100, 100), clickable: bool = False) -> Element:
    return Element(text=text, desc=desc, bounds=bounds, clickable=clickable)


NAV = [
    el(desc="Create", bounds=(480, 2200, 600, 2320), clickable=True),
    el(desc="Profile", bounds=(900, 2200, 1080, 2320), clickable=True),
    el(desc="Search", bounds=(700, 2200, 800, 2320), clickable=True),
]

SCREENS = {
    "home": [el("For You", bounds=(0, 2200, 200, 2300)), el("Following", bounds=(200, 2200, 400, 2300)), *NAV],
    "profile": [el("Edit profile", bounds=(100, 300, 400, 350)), el("Followers", bounds=(100, 400, 300, 450)), el("@g2gchannel", bounds=(100, 500, 400, 550)), *NAV],
    "video": [el(desc="Share", bounds=(900, 1200, 1050, 1300), clickable=True), el(desc="Like", bounds=(900, 1000, 1050, 1100), clickable=True)],
    "share_sheet": [el("Copy link", bounds=(100, 1800, 900, 1900), clickable=True), el("Save video", bounds=(100, 1900, 900, 2000), clickable=True)],
    "camera": [el("Upload", bounds=(900, 2100, 1050, 2200), clickable=True), el("Record", bounds=(480, 2100, 600, 2200))],
    "gallery": [
        el("Videos", bounds=(0, 200, 200, 300), clickable=True),
        el("0:41", bounds=(100, 400, 200, 450)),
        el("", desc="video thumbnail", bounds=(0, 500, 540, 900), clickable=True),
    ],
    "editor": [el("Next", bounds=(900, 2200, 1050, 2320), clickable=True), el("Add sound", bounds=(100, 2100, 300, 2200))],
    "post": [
        el("Add description", bounds=(100, 1800, 900, 1900), clickable=True),
        el("Everyone can view", bounds=(100, 1700, 500, 1750)),
        el("Post", bounds=(900, 2200, 1050, 2320), clickable=True),
    ],
    "uploading": [el("Your video is being uploaded", bounds=(0, 1000, 1080, 1100))],
}


class ScriptedScreen:
    """A fake screen that moves to the next screen when the right thing is tapped."""

    def __init__(self, state: str = "home") -> None:
        self.state = state
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.shots: list[Path] = []
        self._clipboard = "https://www.tiktok.com/@g2gchannel/video/7300000000000000001"

    def elements(self) -> list[Element]:
        return SCREENS[self.state]

    def tap(self, element: Element) -> None:
        label = element.text or element.desc
        self.taps.append(label)
        moves = {
            ("home", "Profile"): "profile",
            ("profile", "Profile"): "profile",
            ("home", "Create"): "camera",
            ("profile", "Create"): "camera",
            ("camera", "Upload"): "gallery",
            ("gallery", "video thumbnail"): "editor",
            ("editor", "Next"): "post",
            ("post", "Post"): "uploading",
            ("video", "Share"): "share_sheet",
        }
        target = moves.get((self.state, label))
        if target:
            self.state = target
        if self.state == "uploading":
            self.state = "home"  # the overlay finishes before the next read

    def tap_point(self, x: int, y: int) -> None:
        """The robot taps a fixed point for the newest video tile; on the profile that opens the video."""
        self.taps.append(f"point:{x},{y}")
        if self.state == "profile":
            self.state = "video"

    def long_press(self, element: Element) -> None:
        self.taps.append(f"long:{element.text or element.desc}")

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.typed.append(text)

    def type_secret(self, secret) -> None:
        self.typed.append(secret.reveal())

    def set_text(self, text: str) -> None:
        self.typed.append(text)

    def clear_field(self) -> None:
        self.typed.clear()

    def press_back(self) -> None:
        self.taps.append("back")
        if self.state == "video":
            self.state = "home"

    def swipe_up(self) -> None:
        self.taps.append("swipe")

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG fake")
        self.shots.append(path)

    def size(self) -> tuple[int, int]:
        return 1080, 2400

    def clipboard(self) -> str | None:
        return self._clipboard

    def focused_text(self) -> str | None:
        return self.typed[-1] if self.typed else None


class LinkedPhone(FakePhone):
    """A fake phone whose fixed-point taps reach the scripted screen (the tile tap in `_read_link`)."""

    def __init__(self, screen: ScriptedScreen) -> None:
        super().__init__(guard=fake_guard())
        self.screen = screen

    def tap(self, x: int, y: int) -> None:
        super().tap(x, y)
        self.screen.tap_point(x, y)


@pytest.fixture()
def journal(tmp_path):
    j = Journal(tmp_path / "robot.db")
    j.start_job("job-1", "post")
    yield j
    j.close()


def test_the_flow_walks_tiktok_screens_and_stops_before_post(journal) -> None:
    screen = ScriptedScreen()
    poster = TikTokPoster(LinkedPhone(screen), screen, journal, "job-1")
    spec = PostSpec(upload_id="u1", platform="tiktok", video=Path("x.mp4"), length_s=41.0, caption="a caption", hashtags=["#g2g"])
    result = poster.post(spec, dry_run=True)

    assert result.outcome == "dry_run"
    assert screen.state == "post"  # the post screen, nothing pressed
    assert "Post" not in screen.taps
    assert screen.taps[:6] == ["Profile", "Create", "Upload", "Videos", "video thumbnail", "Next"]
    assert screen.typed[0] == "a caption"
    assert journal.pressed("job-1", "u1") is False
    assert not journal.has("job-1", PRESSED, "u1")


def test_a_wrong_length_video_is_refused_before_the_press(journal) -> None:
    screen = ScriptedScreen()
    poster = TikTokPoster(LinkedPhone(screen), screen, journal, "job-1")
    spec = PostSpec(upload_id="u1", platform="tiktok", video=Path("x.mp4"), length_s=12.0, caption="c")
    result = poster.post(spec)
    assert result.outcome == "failed_before_post"
    assert "the gallery shows" in (result.reason or "")
    assert "Post" not in screen.taps


def test_the_press_happens_once_and_the_link_is_read(journal, monkeypatch) -> None:
    monkeypatch.setattr("robotapp.post.tiktok.engage", lambda phone: 5.0)
    screen = ScriptedScreen()
    poster = TikTokPoster(LinkedPhone(screen), screen, journal, "job-1")
    spec = PostSpec(upload_id="u1", platform="tiktok", video=Path("x.mp4"), length_s=41.0, caption="c")
    result = poster.post(spec)
    assert result.outcome == "posted"
    assert result.url == "https://www.tiktok.com/@g2gchannel/video/7300000000000000001"
    assert screen.taps.count("Post") == 1
    assert journal.pressed("job-1", "u1") is True
    assert journal.outcome("job-1", "u1") == "posted"

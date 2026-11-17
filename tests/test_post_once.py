"""The rule the user cares about most: Post is pressed once (PLAN §6.4 step 9).

The flow around the press is stubbed out; what is under test is the journal gate and the outcome the caller sees.
"""

from pathlib import Path

import pytest

from robotapp.fake import FakePhone, FakeScreen, fake_guard
from robotapp.journal import POSTED, PRESSED, UNSURE, Journal
from robotapp.post.base import PostSpec
from robotapp.post.tiktok import TikTokPoster
from robotapp.ui import Element


def elements() -> list[Element]:
    return [
        Element(text="For You", bounds=(0, 2200, 200, 2300)),
        Element(desc="Create", bounds=(480, 2200, 600, 2320), clickable=True),
        Element(text="Upload", bounds=(900, 2100, 1050, 2200), clickable=True),
        Element(text="Videos", bounds=(0, 200, 200, 300), clickable=True),
        Element(text="0:41", bounds=(100, 400, 200, 450)),
        Element(text="Next", bounds=(900, 2200, 1050, 2320), clickable=True),
        Element(text="Add description", bounds=(100, 1800, 900, 1900), clickable=True),
        Element(text="Post", bounds=(900, 2200, 1050, 2320), clickable=True),
        Element(text="Edit profile", bounds=(100, 300, 400, 350)),
    ]


class StubPoster(TikTokPoster):
    """Skips the real screens; keeps the journal gate and the press."""

    def __init__(self, *args, fail_post_tap: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fail_post_tap = fail_post_tap

    def _open(self) -> None: ...
    def _handle(self) -> str:
        return "@throwaway"

    def _pick_video(self, spec) -> None: ...
    def _add_sound_if_asked(self, spec) -> None: ...
    def _write_caption(self, spec) -> None: ...
    def _ensure_public(self) -> None: ...
    def _wait_uploaded(self) -> None: ...
    def _read_link(self) -> str:
        return "https://www.tiktok.com/@throwaway/video/7300000000000000000"

    def _tap_exact(self, label: str) -> None:
        if label == "Post" and self.fail_post_tap:
            raise RuntimeError("the tap did not land")
        super()._tap_exact(label)


def spec() -> PostSpec:
    return PostSpec(upload_id="u1", platform="tiktok", video=Path("x.mp4"), length_s=41.0, caption="hi", hashtags=["#test"])


@pytest.fixture()
def journal(tmp_path):
    j = Journal(tmp_path / "robot.db")
    j.start_job("job-1", "post")
    yield j
    j.close()


def test_a_good_post_records_the_link(journal, monkeypatch) -> None:
    monkeypatch.setattr("robotapp.post.tiktok.engage", lambda phone: 12.0)
    screen = FakeScreen(elements())
    poster = StubPoster(FakePhone(guard=fake_guard()), screen, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == POSTED
    assert result.url == "https://www.tiktok.com/@throwaway/video/7300000000000000000"
    assert result.handle == "@throwaway"
    assert screen.taps.count("Post") == 1
    assert journal.pressed("job-1", "u1") is True


def test_a_failed_tap_after_the_press_is_never_retried(journal, monkeypatch) -> None:
    monkeypatch.setattr("robotapp.post.tiktok.engage", lambda phone: 0.0)
    screen = FakeScreen(elements())
    first = StubPoster(FakePhone(guard=fake_guard()), screen, journal, "job-1", fail_post_tap=True)
    result = first.post(spec())
    assert result.outcome == UNSURE
    assert journal.pressed("job-1", "u1") is True

    screen.taps.clear()
    second = StubPoster(FakePhone(guard=fake_guard()), screen, journal, "job-1")
    again = second.post(spec())
    assert again.outcome == UNSURE
    assert "already pressed" in (again.reason or "")
    assert "Post" not in screen.taps  # the one thing that must never happen


def test_a_failure_before_the_press_leaves_no_press(journal) -> None:
    screen = FakeScreen(elements())
    poster = StubPoster(FakePhone(guard=fake_guard()), screen, journal, "job-1")
    poster._write_caption = lambda spec: (_ for _ in ()).throw(RuntimeError("no caption field"))
    result = poster.post(spec())
    assert result.outcome == "failed_before_post"
    assert journal.pressed("job-1", "u1") is False
    assert "Post" not in screen.taps

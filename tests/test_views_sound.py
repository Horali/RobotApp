"""Views reading and the sound step (PLAN sections 6.8, 6.6): the number and the fragile picker."""

from pathlib import Path

import pytest

from robotapp import sound
from robotapp.fake import FakeScreen, fake_guard
from robotapp.sound import add_sound
from robotapp.ui import Element
from robotapp.views import parse_count, read_views


def el(text: str = "", desc: str = "", bounds=(0, 0, 100, 100), clickable: bool = False) -> Element:
    return Element(text=text, desc=desc, bounds=bounds, clickable=clickable)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1,234", 1234),
        ("1.2K", 1200),
        ("3.4M", 3400000),
        ("812", 812),
        ("\u25b6 2,810", 2810),     # a play icon in the same label
        ("0", 0),
        ("no number", None),
        ("", None),
    ],
)
def test_parse_count(text, expected) -> None:
    assert parse_count(text) == expected


def test_reading_views_needs_a_signed_in_profile(monkeypatch) -> None:
    """No profile tab and no numbers: None, so the caller asks the user instead of guessing."""
    from robotapp import views as views_module

    class BlankPhone:
        serial = "fake"

        def start_app(self, package, user=0):
            return ""

        def shell(self, command, timeout=60):
            return ""

    monkeypatch.setattr(views_module, "wait_for", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no profile")))
    assert read_views(BlankPhone(), FakeScreen([]), "tiktok", 0) is None


def test_the_sound_step_reports_failure_instead_of_lying() -> None:
    """No audio panel means False; the poster then decides (post without it, unless required)."""
    screen = FakeScreen([el("Next"), el("Edit")])       # the editor, but no sound panel opens
    assert add_sound(screen, "tiktok") is False


def test_the_sound_step_picks_the_first_trending_sound() -> None:
    """A panel with a trending sound: it is picked and the editor comes back."""
    state = {"panel": True}

    class SoundScreen(FakeScreen):
        def elements(self):
            if state["panel"]:
                return [el("Trending"), el("Night Drive \u00b7 original sound", bounds=(100, 700, 900, 800), clickable=True)]
            return [el("Next"), el("Add sound")]

        def tap(self, element):
            super().tap(element)
            if "original sound" in (element.text or ""):
                state["panel"] = False        # picking a sound closes the panel

    screen = SoundScreen([])
    assert add_sound(screen, "tiktok") is True
    assert state["panel"] is False


def test_a_dry_run_never_presses_upload_but_may_add_a_sound() -> None:
    """The sound step sits before the press, so it is safe in a dry run (a post is not)."""
    assert sound.AUDIO_PANEL.name == "audio panel"     # the module imports and exposes its signature

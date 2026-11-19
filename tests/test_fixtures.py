"""The signature fixtures (PLAN section 6.2, step 3): reality against the guesses.

Each fixture is a real screen dump (saved by `robot screen --save-as` on the phone). This test
replays it and asserts the flow's signature matches, and that the button the flow taps is present
with the right label. When TikTok updates and a screen changes, this test is the early warning:
fix the signature here, on the laptop, before the phone ever runs the flow again.
"""

import json
from pathlib import Path

import pytest

from robotapp.post.tiktok import (
    CAMERA,
    EDITOR,
    HOME,
    POST_SCREEN,
    PROFILE,
    SHARE_ON_TIKTOK,
)
from robotapp.post.instagram import HOME as INSTAGRAM_HOME, PROFILE as INSTAGRAM_PROFILE
from robotapp.ui import Element, find, find_exact

FIXTURES = Path(__file__).parent / "fixtures" / "screens"


def load(name: str) -> list[Element]:
    body = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return [
        Element(
            text=row["text"],
            desc=row["desc"],
            resource_id=row["resource_id"],
            bounds=tuple(row["bounds"]),  # type: ignore[arg-type]
            clickable=row["clickable"],
            enabled=row["enabled"],
        )
        for row in body["elements"]
    ]


@pytest.mark.parametrize(
    "fixture, signature",
    [
        ("tiktok-feed", HOME),
        ("tiktok-profile", PROFILE),
        ("tiktok-editor", EDITOR),
        # saved after the first real Instagram login (vtubersclips90, 2026-11-19)
        ("instagram-home", INSTAGRAM_HOME),
        ("instagram-profile", INSTAGRAM_PROFILE),
    ],
)
def test_a_real_screen_matches_its_signature(fixture: str, signature) -> None:
    elements = load(fixture)
    assert signature.matches(elements), (
        f"the {signature.name} signature no longer matches the real {fixture} screen; "
        "TikTok probably updated. Fix the signature before the next phone run."
    )


def test_the_real_editor_has_the_next_button() -> None:
    editor = load("tiktok-editor")
    assert find_exact(editor, "Next") is not None or find(editor, "Next") is not None


def test_the_real_feed_has_the_bottom_bar() -> None:
    """The nav taps (exact label, bottom bar) need Create and Profile to be there."""
    feed = load("tiktok-feed")
    labels = [e.text.strip().lower() or e.desc.strip().lower() for e in feed if e.enabled]
    for label in ("create", "profile"):
        assert label in labels


def test_every_fixture_is_a_real_dump() -> None:
    """A fixture with no labelled elements is a capture of the launcher, not the app."""
    for path in FIXTURES.glob("*.json"):
        elements = load(path.stem)
        labelled = [e for e in elements if e.text or e.desc]
        assert len(elements) > 40, f"{path.name} looks too small to be a real dump"
        assert labelled, f"{path.name} has no labelled elements"

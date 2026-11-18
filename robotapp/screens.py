"""Save real screen dumps as fixtures (PLAN section 6.2, step 3).

The signatures the robot matches (For You, Add sound, Next, Post...) are guesses until they have
been checked against a real dump. This tool saves what uiautomator2 actually saw, one file per
screen, into tests/fixtures/screens/. A test then replays each dump and asserts the signature
matches. Run it (inside 06:00-10:00, or with ROBOTAPP_BUILD_MODE=1) while the phone shows each
screen; it reads only, it never taps.

Usage:  python -m robotapp.cli screen --save-as <name> [--user N]
"""

from __future__ import annotations

import json
from pathlib import Path

from .cli import build, screen_for, enter_space
from .config import Settings

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "screens"


def save_screen(name: str, user: int | None, fake: bool = False) -> Path:
    """Read the current screen and write it as a fixture. Returns the path."""
    import argparse

    settings = Settings.load()
    args = argparse.Namespace(fake=fake)
    phone, _ = build(args, settings)
    if user is not None:
        enter_space(phone, user)
    screen = screen_for(phone, settings)
    elements = screen.elements()
    body = {
        "name": name,
        "size": list(screen.size()),
        "elements": [
            {
                "text": e.text,
                "desc": e.desc,
                "resource_id": e.resource_id,
                "bounds": list(e.bounds),
                "clickable": e.clickable,
                "enabled": e.enabled,
            }
            for e in elements
        ],
    }
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / f"{name}.json"
    path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return path

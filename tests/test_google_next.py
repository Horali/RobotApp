"""Google's Next: tapped at its real place, and Back only when the keyboard covers it (2026-11-20).

The first version closed the keyboard whenever the button sat low on the screen - but Google's own
Next sits at the bottom, so Back dismissed the whole sign-in sheet and the sign-in died.
"""

import pytest

from robotapp.login.google import GoogleLogin
from robotapp.ui import Element


def el(text: str = "", bounds=(0, 0, 100, 100), resource_id: str = "") -> Element:
    return Element(text=text, bounds=bounds, resource_id=resource_id, clickable=True)


class Screen:
    """Just enough screen for the helper: elements, taps, a keyboard flag."""

    def __init__(self, elements, keyboard: bool = False) -> None:
        self.current = elements
        self.keyboard = keyboard
        self.taps: list[str] = []

    def elements(self):
        rows = list(self.current)
        if self.keyboard:
            rows = rows + [el("Clipboard"), el("Voice"), el("", resource_id="android:id/input_method_nav_back")]
        return rows

    def tap(self, element) -> None:
        self.taps.append(element.text or "")

    def press_back(self) -> None:
        self.taps.append("back")
        self.keyboard = False          # closing the keyboard is what a back press does here

    def size(self) -> tuple[int, int]:
        return 1080, 2460


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)


def test_next_at_the_bottom_is_tapped_not_dismissed() -> None:
    screen = Screen([el("Next", bounds=(756, 2280, 1020, 2424))])      # Google's real place, no keyboard
    GoogleLogin(phone=None, screen=screen, chameleon=None)._tap_any(("Next", "Continue"), timeout_s=2)
    assert screen.taps == ["Next"]                                    # tapped, never backed out of


def test_a_keyboard_over_the_button_is_closed_then_next_is_tapped() -> None:
    screen = Screen([el("Next", bounds=(756, 2280, 1020, 2424))], keyboard=True)
    GoogleLogin(phone=None, screen=screen, chameleon=None)._tap_any(("Next", "Continue"), timeout_s=3)
    assert screen.taps == ["back", "Next"]


class SwallowingScreen(Screen):
    """The tap lands on the keyboard: the page only moves after the keyboard is closed."""

    def __init__(self, elements, keyboard: bool = True) -> None:
        super().__init__(elements, keyboard)
        self.swallowed = 0

    def tap(self, element) -> None:
        super().tap(element)
        if self.keyboard:
            self.swallowed += 1          # nothing happens
        else:
            self.current = [el("Enter your password"), el("Show password"), el("Next")]

    def press_back(self) -> None:
        super().press_back()
        self.keyboard = False


def test_advance_notices_the_tap_was_eaten_and_tries_again() -> None:
    """Measured 2026-11-20: Next was tapped, the keyboard took the click, the page never changed and
    the sign-in timed out waiting for the password screen. _advance verifies the move."""
    screen = SwallowingScreen([el("Next", bounds=(756, 2280, 1020, 2424))])
    GoogleLogin(phone=None, screen=screen, chameleon=None)._advance("google email", tries=4)
    assert screen.swallowed == 1 and "back" in screen.taps      # first tap eaten, then the keyboard closed

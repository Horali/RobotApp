"""The TikTok login flow on a scripted screen (PLAN §5.2, §5.4).

Two things this proves without a phone: the password reaches the field through the secret type path (never as a
plain `input text`), and a CAPTCHA stops the robot with `NeedsHuman` instead of guessing.
"""

import logging
from pathlib import Path

import pytest

from robotapp.errors import NeedsHuman
from robotapp.fake import FakePhone, fake_guard
from robotapp.log import Secret
from robotapp.login.tiktok import TikTokLogin
from robotapp.ui import Element

PASSWORD = "fake-TikTok-Pass-123!"


def el(text: str = "", desc: str = "", bounds=(0, 0, 100, 100), clickable: bool = False) -> Element:
    return Element(text=text, desc=desc, bounds=bounds, clickable=clickable)


SCREENS = {
    "home": [el("For You"), el(desc="Profile", bounds=(900, 2200, 1080, 2320), clickable=True)],
    "profile": [el("Log in", bounds=(100, 1000, 400, 1100), clickable=True), el(desc="Profile", clickable=True)],
    "login_choice": [el("Use phone / email / username", bounds=(100, 800, 900, 900), clickable=True)],
    "email_form": [el("Email / Username", bounds=(100, 500, 900, 600), clickable=True), el("Continue", bounds=(100, 1200, 900, 1300), clickable=True)],
    "email_entry": [el("Email", bounds=(100, 500, 900, 600), clickable=True), el("Continue", bounds=(100, 1200, 900, 1300), clickable=True)],
    "password_form": [el("Password", bounds=(100, 500, 900, 600), clickable=True), el("Log in", bounds=(100, 1200, 900, 1300), clickable=True)],
    "code_form": [el("Verify it's you", bounds=(100, 300, 900, 400)), el("Enter the code", bounds=(100, 500, 900, 600), clickable=True)],
    "logged_in": [el("Edit profile"), el("Followers"), el("@throwaway", bounds=(100, 500, 400, 550)), el(desc="Profile", clickable=True)],
    "captcha": [el("Confirm you're human"), el("Slide to verify")],
}


class LoginScreen:
    def __init__(self, state: str = "home", captcha_after_login: bool = False) -> None:
        self.state = state
        self.captcha_after_login = captcha_after_login
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.secrets: list[str] = []
        self.shots: list[Path] = []

    def elements(self) -> list[Element]:
        return SCREENS[self.state]

    def tap(self, element: Element) -> None:
        label = element.text or element.desc
        self.taps.append(label)
        if (self.state, label) == ("password_form", "Log in") and self.captcha_after_login:
            self.state = "captcha"
            return
        moves = {
            ("home", "Profile"): "profile",
            ("profile", "Log in"): "login_choice",
            ("login_choice", "Use phone / email / username"): "email_form",
            ("email_form", "Email / Username"): "email_entry",
            ("email_entry", "Continue"): "password_form",
            ("password_form", "Log in"): "code_form",
            ("code_form", "Enter the code"): "logged_in",
        }
        target = moves.get((self.state, label))
        if target:
            self.state = target

    def long_press(self, element: Element) -> None:
        self.taps.append("long")

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.typed.append(text)

    def type_secret(self, secret: Secret) -> None:
        self.secrets.append(secret.reveal())  # the fake records it; the real one types it and drops it

    def set_text(self, text: str) -> None:
        self.typed.append(text)

    def clear_field(self) -> None:
        self.typed.clear()

    def press_back(self) -> None:
        self.taps.append("back")

    def swipe_up(self) -> None:
        self.taps.append("swipe")

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG fake")
        self.shots.append(path)

    def size(self) -> tuple[int, int]:
        return 1080, 2400

    def clipboard(self) -> str | None:
        return None

    def focused_text(self) -> str | None:
        return None


class FakeChameleon:
    def platform_password(self, profile_id: str, platform: str) -> Secret:
        assert platform == "tiktok"
        return Secret(PASSWORD)


def test_a_login_walks_the_screens_and_never_prints_the_password(caplog) -> None:
    screen = LoginScreen()
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(), code_provider=lambda: "123456")
    with caplog.at_level(logging.DEBUG):
        result = login.login("profile-1", "throwaway@example.com", "com.zhiliaoapp.musically")

    assert result.logged_in is True
    assert result.handle == "@throwaway"
    assert "throwaway@example.com" in screen.typed
    assert screen.secrets == [PASSWORD]  # typed through the secret path
    assert PASSWORD not in caplog.text
    assert "123456" in screen.typed


def test_a_captcha_stops_the_login_and_asks_for_a_human() -> None:
    screen = LoginScreen(captcha_after_login=True)
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(), code_provider=lambda: "123456")
    with pytest.raises(NeedsHuman) as caught:
        login.login("profile-1", "throwaway@example.com", "com.zhiliaoapp.musically")
    assert "CAPTCHA" in str(caught.value)


class BirthdateScreen:
    """musically's wall with the wheel rules as measured on the phone (2026-11-19): a drag on any
    wheel initialises an unset wall to today, the year wheel's down-drag is one year older, and
    Continue only becomes tappable once the wheels hold a date."""

    def __init__(self, wheel_moves: bool = True) -> None:
        self.wall = True
        self.wheel_moves = wheel_moves
        self.year = 0          # 0 = the wheels are unset
        self.taps: list[str] = []
        self.drags: list[str] = []

    def elements(self) -> list[Element]:
        if not self.wall:
            return SCREENS["home"]
        out = [
            el("When's your birthdate?"),
            el(f"November 19, {self.year}" if self.year else "Birthday", bounds=(96, 768, 984, 912)),
            el(desc="Month picker", bounds=(120, 1346, 360, 1743)),
            el(desc="Day picker", bounds=(420, 1346, 660, 1743)),
            el(desc="Year picker", bounds=(720, 1346, 960, 1743)),
        ]
        button = el("Continue", bounds=(96, 2175, 984, 2307), clickable=True)
        button.enabled = bool(self.year)      # an unset wall's button is not tappable yet
        out.append(button)
        return out

    def tap(self, element: Element) -> None:
        self.taps.append(element.text or element.desc)
        if (element.text or "") == "Continue" and self.year:
            self.wall = False

    def drag(self, x1: int, y1: int, x2: int, y2: int, steps: int = 20) -> None:
        self.drags.append(f"{x1},{y1}->{x2},{y2}")
        if not self.wheel_moves:
            return                          # a wheel that refuses to move
        if self.year == 0:
            self.year = 2026                # any drag initialises the unset wheels to today
        elif 720 <= x1 <= 960:
            self.year -= 1                  # the year wheel, one year older per drag


def test_the_birthdate_wall_dials_an_adult_year(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)
    screen = BirthdateScreen()
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
    login._birthday()
    assert screen.year <= 2004
    assert "Continue" in screen.taps
    assert screen.wall is False
    assert len(screen.drags) >= 22          # 2026 down to 2004: one year wheel drag at a time


def test_a_stuck_birthdate_wheel_stops_for_a_human(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)
    screen = BirthdateScreen(wheel_moves=False)
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
    with pytest.raises(NeedsHuman) as caught:
        login._birthday()
    assert "wheels" in str(caught.value) or "birthdate" in str(caught.value)

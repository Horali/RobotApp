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
    "logged_in": [el("Edit profile"), el("Followers"), el("@throwaway", bounds=(100, 500, 400, 550)),
                  el(desc="Profile", bounds=(900, 2200, 1080, 2320), clickable=True)],
    "captcha": [el("Confirm you're human"), el("Slide to verify")],
    "terms": [el("Agree and continue", bounds=(96, 2100, 984, 2200), clickable=True),
              el("By tapping 'Agree and continue', you agree to our Terms of Service")],
    "notifications": [el("Allow TikTok to send you notifications?"),
                      el("DON\u2019T ALLOW", bounds=(48, 2133, 1032, 2292), clickable=True)],
    "feed_trap": [el("For You"),
                  el(desc="spryzen.ae profile", bounds=(36, 800, 400, 900), clickable=True),
                  el(desc="Profile", bounds=(900, 2200, 1080, 2320), clickable=True)],
    "author": [el("Following"), el("Followers"), el("3.5M"), el("Likes")],
    "email_code": [el("Verify email"),
                   el("Use the link or enter the code sent to horalixscripts7@gmail.com"),
                   el("Resend code", bounds=(96, 858, 394, 975), clickable=True)],
}


class LoginScreen:
    def __init__(self, state: str = "home", captcha_after_login: bool = False,
                 code_instead_of_password: bool = False) -> None:
        self.state = state
        self.captcha_after_login = captcha_after_login
        self.code_instead_of_password = code_instead_of_password
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
            ("feed_trap", "Profile"): "profile",           # the bottom bar's tab
            ("feed_trap", "spryzen.ae profile"): "author",  # the video author's page: a dead end
            ("terms", "Agree and continue"): "notifications",
            ("notifications", "DON\u2019T ALLOW"): "home",
            ("home", "Profile"): "profile",
            ("profile", "Log in"): "login_choice",
            ("login_choice", "Use phone / email / username"): "email_form",
            ("email_form", "Email / Username"): "email_entry",
            ("email_entry", "Continue"): "email_code" if self.code_instead_of_password else "password_form",
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
        # a full 6-digit code submits itself on both code screens
        if self.state in ("code_form", "email_code") and len(text.strip()) == 6 and text.strip().isdigit():
            self.state = "logged_in"

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


def test_musicallys_first_run_gates_are_all_answered() -> None:
    """musically's measured journey (2026-11-19): Terms of Service, then the notifications permission
    (printed "DON'T ALLOW", all caps and a curly apostrophe), then the feed."""
    screen = LoginScreen(state="terms")
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(), code_provider=lambda: "123456")
    result = login.login("profile-1", "throwaway@example.com", "com.zhiliaoapp.musically")
    assert result.logged_in is True
    assert "Agree and continue" in screen.taps
    assert "DON\u2019T ALLOW" in screen.taps


def test_the_profile_tab_is_tapped_not_the_video_author() -> None:
    """On the feed a video author's link also says 'profile' (2026-11-19, musically: the login opened
    @spryzen.ae's page instead of the tab and never reached the login choice)."""
    screen = LoginScreen(state="feed_trap")
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(), code_provider=lambda: "123456")
    result = login.login("profile-1", "throwaway@example.com", "com.zhiliaoapp.musically")
    assert result.logged_in is True
    assert "spryzen.ae profile" not in screen.taps


def test_musically_goes_from_the_email_straight_to_the_code() -> None:
    """musically 47.9.1 (2026-11-19): after the email's Continue there is no password form - TikTok
    emails a code ("Verify email"). No secret is fetched at all on this path."""
    screen = LoginScreen(state="home", code_instead_of_password=True)
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(), code_provider=lambda: "123456")
    result = login.login("profile-1", "throwaway@example.com", "com.zhiliaoapp.musically")
    assert result.logged_in is True
    assert "123456" in screen.typed
    assert screen.secrets == []          # no password was ever fetched
    assert "Resend code" not in screen.taps   # the unlabeled field is typed into, never tapped at


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


def test_email_step_stops_immediately_on_account_not_found_or_captcha(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)

    class ImmediateStopScreen(LoginScreen):
        def __init__(self, landing_state: str) -> None:
            super().__init__(state="home")
            self.landing_state = landing_state

        def elements(self) -> list[Element]:
            if self.state == "account_missing":
                return [el("Couldn't find this account")]
            return super().elements()

        def tap(self, element: Element) -> None:
            label = element.text or element.desc
            if self.state == "email_entry" and label == "Continue":
                self.taps.append(label)
                self.state = self.landing_state
                return
            super().tap(element)

    for landing in ("captcha", "account_missing"):
        screen = ImmediateStopScreen(landing)
        login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
        with pytest.raises(NeedsHuman):
            login.login("profile-1", "nobody@example.com", "com.zhiliaoapp.musically")


def test_cmd_login_resolves_account_id_with_explicit_email_and_leaves_space(tmp_path, monkeypatch) -> None:
    import argparse
    import robotapp.cli as cli_mod
    from robotapp.config import Settings

    phone = FakePhone(guard=fake_guard())
    phone.current = 0
    seen_calls: list[tuple] = []

    class StubChameleon:
        def __init__(self, url, token) -> None:
            pass

        def login_identity(self, profile_id: str, platform: str):
            return ("horalixscripts3@gmail.com", "email-acct-3")

    class FailingGoogleLogin:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def login(self, email: str, account_id: str, user: int):
            seen_calls.append((email, account_id, user))
            raise NeedsHuman("blocked by test")

    monkeypatch.setattr(cli_mod, "build", lambda args, settings: (phone, "fake:5555"))
    monkeypatch.setattr(cli_mod, "screen_for", lambda ph, settings: object())
    monkeypatch.setattr(cli_mod, "Chameleon", StubChameleon)
    monkeypatch.setattr("robotapp.login.google.GoogleLogin", FailingGoogleLogin)
    monkeypatch.setattr("time.sleep", lambda s: None)

    args = argparse.Namespace(
        platform="youtube",
        user=10,
        profile_id="prof-yt-10",
        email="override@gmail.com",
        package="",
        job="test-login-1",
        code="",
        code_file="",
        fake=False,
        json=True,
    )
    settings = Settings(data_dir=tmp_path)
    code = cli_mod.cmd_login(args, settings)
    assert code == cli_mod.EXIT_NEEDS
    assert seen_calls == [("override@gmail.com", "email-acct-3", 10)]
    assert "am switch-user 0" in phone.commands


def test_extract_gmail_code_reads_six_digit_otp_only() -> None:
    from robotapp.cli import _extract_gmail_code

    dump = (
        "  NotificationRecord(0x1: pkg=com.other.app user=10)\n"
        "    android.title=Delivery update 123456\n"
        "  NotificationRecord(0x2: pkg=com.google.android.gm user=10)\n"
        "    android.title=TikTok\n"
        "    android.text=482910 is your verification code\n"
    )
    assert _extract_gmail_code(dump) == "482910"
    assert _extract_gmail_code("NotificationRecord(0x2: pkg=com.google.android.gm)\nandroid.text=hello") == ""


def test_ensure_vpn_up_wakes_sleeping_sfa_before_login(monkeypatch) -> None:
    import robotapp.cli as cli_mod
    from robotapp.ui import Element as UiElement
    from robotapp.vpn import SFA_PACKAGE

    phone = FakePhone(guard=fake_guard())
    states = iter([
        {"up": False, "always_on_app": SFA_PACKAGE, "lockdown": True, "detail": ""},
        {"up": False, "always_on_app": SFA_PACKAGE, "lockdown": True, "detail": ""},
        {"up": True, "always_on_app": SFA_PACKAGE, "lockdown": True, "detail": "VPN CONNECTED"},
    ])
    monkeypatch.setattr(cli_mod, "vpn_state", lambda ph, u: next(states))
    monkeypatch.setattr("time.sleep", lambda s: None)

    class WakeScreen:
        def __init__(self) -> None:
            self.taps: list[str] = []

        def elements(self):
            return [UiElement(text="", desc="Start", bounds=(864, 1950, 1020, 2106), clickable=True)]

        def tap(self, elem) -> None:
            self.taps.append(elem.desc or elem.text)

    screen = WakeScreen()
    events: list[dict] = []
    cli_mod._ensure_vpn_up(phone, screen, 10, events.append, wait_s=10)
    assert f"monkey -p {SFA_PACKAGE} --user 10 1" in phone.commands
    assert screen.taps == ["Start"]
    assert any(e.get("name") == "vpn wake" and e.get("up") is True for e in events)


def test_tiktok_tap_any_dismisses_emoji_keyboard_terms_overlay(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)

    class OverlayScreen(LoginScreen):
        def __init__(self) -> None:
            super().__init__(state="overlay")

        def elements(self) -> list[Element]:
            if self.state == "overlay":
                return [
                    el("By using this keyboard, you agree to Privacy Policy of Emoji Keyboard"),
                    el("Agree And Continue", bounds=(72, 2000, 1008, 2140), clickable=True),
                ]
            return super().elements()

        def tap(self, element: Element) -> None:
            label = element.text or element.desc
            if self.state == "overlay" and label == "Agree And Continue":
                self.taps.append(label)
                self.state = "email_entry"
                return
            super().tap(element)

    screen = OverlayScreen()
    login = TikTokLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
    login._tap_any(("Continue",))
    assert screen.taps == ["Agree And Continue", "Continue"]

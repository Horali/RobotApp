"""Signing a TikTok account in on the phone (PLAN §5.2).

The password is fetched from Chameleon at the moment it is typed, typed at human speed through uiautomator2, and
dropped right after: it never touches a file, a log line or a screenshot. One login attempt per account per day.

What the robot does alone: the first-run screens, "Use phone / email / username", the password, "Not now" on the
save-login and notification offers, and a 6-digit code from the account's email. What it refuses to guess: a
slider/puzzle CAPTCHA, an SMS code, "tap Yes on your other device", a selfie check, a wrong password, or a
screen it does not recognise for 60 s (§5.4). Those become `NeedsHuman` / `NeedsCode`.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..adb import Phone
from ..errors import NeedsCode, NeedsHuman
from ..secrets import Chameleon
from ..ui import Element, Screen, ScreenTimeout, Signature, find, find_exact, wait_for

log = logging.getLogger("robotapp")

HOME = Signature("tiktok home", any_of=("For You", "Following", "Inbox"))
LOGIN_CHOICE = Signature("login choice", any_of=("Use phone / email / username", "Continue with Google", "Log in"))
EMAIL_FORM = Signature("email form", any_of=("Email / Username", "Email or username", "Log in with email"))
PASSWORD_FORM = Signature("password form", any_of=("Password", "Forgot password"))
CODE_FORM = Signature("code form", any_of=("Verify it's you", "Enter the code", "We sent a code", "6-digit code"))
PROFILE = Signature("profile", any_of=("Edit profile", "Followers", "Following"))
CAPTCHA = Signature("captcha", any_of=("Confirm you're human", "Slide to verify", "Verify", "puzzle", "Rotate"))

# Screens the robot must not try to clear on its own (§5.4).
STOP_WORDS = (
    "incorrect password",
    "too many attempts",
    "suspicious",
    "try again later",
    "couldn't find this account",
    "account is disabled",
    "tap yes",
    "send code via sms",
    "sms",
)


@dataclass
class LoginResult:
    handle: str | None
    logged_in: bool
    reason: str | None = None


class TikTokLogin:
    def __init__(
        self,
        phone: Phone,
        screen: Screen,
        chameleon: Chameleon,
        emit=None,
        shots_dir: Path | None = None,
        code_provider: Callable[[], str] | None = None,
    ) -> None:
        self.phone = phone
        self.screen = screen
        self.chameleon = chameleon
        self.emit = emit or (lambda event: None)
        self.shots_dir = shots_dir
        self.code_provider = code_provider or (lambda: "")
        self.handle: str | None = None

    def login(self, profile_id: str, email: str, package: str, platform: str = "tiktok") -> LoginResult:
        self.phone.force_stop(package)
        self.phone.start_app(package)
        self._first_run()

        elements = wait_for(self.screen, HOME, 45)
        self._guard_screen(elements, "the TikTok home screen")
        self._tap_desc("Profile")
        time.sleep(1.5)
        elements = self.screen.elements()
        if find(elements, "Log in") is not None:
            self.screen.tap(find(elements, "Log in"))  # type: ignore[arg-type]
        wait_for(self.screen, LOGIN_CHOICE, 30)
        self._tap_any(("Use phone / email / username", "Log in with email"))
        wait_for(self.screen, EMAIL_FORM, 30)
        self._tap_any(("Email / Username", "Email or username"))
        time.sleep(1.0)

        self._type_into_field(email, label="Email")
        self._tap_any(("Continue", "Next", "Log in"))
        wait_for(self.screen, PASSWORD_FORM, 30)
        self._guard_screen(self.screen.elements(), "the password screen")

        # The secret exists only inside this block.
        password = self.chameleon.platform_password(profile_id, platform)
        try:
            field = find(self.screen.elements(), "Password")
            if field is not None:
                self.screen.tap(field)
                time.sleep(0.5)
            self.screen.type_secret(password)
        finally:
            del password
        self._tap_any(("Log in", "Continue", "Next"))

        self._after_password()
        handle = self._read_handle()
        return LoginResult(handle=handle, logged_in=handle is not None)

    # -- screens -----------------------------------------------------------------------------------
    def _first_run(self) -> None:
        """Interests → Skip, the swipe tutorial → swipe, notifications → Don't allow (§5.2 step 1)."""
        for _ in range(6):
            time.sleep(1.5)
            elements = self.screen.elements()
            for label in ("Skip", "Not now", "Don't allow", "Cancel"):
                button = find_exact(elements, label)
                if button is not None:
                    self.screen.tap(button)
                    break
            else:
                if find(elements, "For You") is not None:
                    return
                self.screen.swipe_up()

    def _after_password(self) -> None:
        """The code screen, the save-login offer, and the things only a human can clear."""
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            time.sleep(1.5)
            elements = self.screen.elements()
            text = " ".join(e.text + " " + e.desc for e in elements).lower()
            if CAPTCHA.matches(elements):
                raise NeedsHuman("TikTok shows a CAPTCHA", self._shot("tiktok-captcha"))
            for word in STOP_WORDS:
                if word in text:
                    raise NeedsHuman(f"TikTok says: {word}", self._shot("tiktok-stop"))
            if CODE_FORM.matches(elements):
                self._enter_code()
                continue
            for label in ("Not now", "Skip", "Don't allow", "Later"):
                button = find_exact(elements, label)
                if button is not None:
                    self.screen.tap(button)
                    break
            if PROFILE.matches(elements) or find(elements, "For You") is not None:
                return
        raise NeedsHuman("TikTok did not reach the profile in 90 s", self._shot("tiktok-login-timeout"))

    def _enter_code(self) -> None:
        code = self.code_provider()
        if not code:
            raise NeedsCode("tiktok")
        digits = re.sub(r"\D", "", code)
        if len(digits) != 6:
            raise NeedsCode("tiktok")
        field = find(self.screen.elements(), "code") or find(self.screen.elements(), "Enter")
        if field is not None:
            self.screen.tap(field)
        self.screen.type_text(digits, min_ms=120, max_ms=300)

    def _read_handle(self) -> str | None:
        try:
            self._tap_desc("Profile")
            elements = wait_for(self.screen, PROFILE, 20)
        except ScreenTimeout:
            return None
        for element in elements:
            if element.text.startswith("@"):
                return element.text.strip()
        return None

    # -- helpers -----------------------------------------------------------------------------------
    def _type_into_field(self, value: str, label: str) -> None:
        field = find(self.screen.elements(), label) or find(self.screen.elements(), "email")
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.6)
        self.screen.type_text(value, min_ms=60, max_ms=160)

    def _tap_any(self, labels: tuple[str, ...]) -> None:
        elements = self.screen.elements()
        for label in labels:
            button = find(elements, label)
            if button is not None:
                self.screen.tap(button)
                return
        raise RuntimeError(f"none of {labels} is on screen")

    def _tap_desc(self, desc: str) -> None:
        button = find(self.screen.elements(), desc)
        if button is None:
            raise RuntimeError(f"'{desc}' is not on screen")
        self.screen.tap(button)

    def _guard_screen(self, elements: list[Element], where: str) -> None:
        if CAPTCHA.matches(elements):
            raise NeedsHuman(f"a CAPTCHA on {where}", self._shot("tiktok-captcha"))

    def _shot(self, name: str) -> str | None:
        if not self.shots_dir:
            return None
        path = self.shots_dir / f"{name}-{int(time.time())}.png"
        try:
            self.screen.screenshot(path)
            return str(path)
        except Exception:  # noqa: BLE001
            return None

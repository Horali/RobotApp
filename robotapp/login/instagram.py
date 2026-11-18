"""Signing an Instagram account in on the phone (PLAN section 5.3).

The password is fetched from Chameleon at the moment it is typed, typed at human speed through
uiautomator2, and dropped right after. What the robot does alone: the login form, the password, a
6-digit code from the account's email, and the "Not now" offers. What it refuses to guess: a
CAPTCHA, an SMS code, "add your phone", a selfie check, a wrong password (section 5.4).

Honest note: like the post flow, these signatures follow the plan's description; no Instagram
account exists on the robot phone yet, so they have not been checked against the real app.
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

HOME = Signature("instagram home", any_of=("Search", "For you", "Following", "Home"))
LOGIN = Signature("instagram login", any_of=("Log in", "Log in with Facebook", "Sign up"))
FORM = Signature("instagram login form", any_of=("Username", "Phone", "Email"))
PASSWORD_FORM = Signature("instagram password form", any_of=("Password", "Log in"))
CODE_FORM = Signature("instagram code form", any_of=("Enter code", "Verification code", "code", "Security code"))
UNUSUAL = Signature("instagram unusual login", any_of=("Unusual login attempt", "unusual", "Verify"))
CAPTCHA = Signature("captcha", any_of=("Confirm you're human", "Slide to verify", "Verify you are human",
                                       "puzzle", "Rotate the image", "drag the slider"))
PROFILE = Signature("instagram profile", any_of=("Edit profile", "Followers", "Following", "Posts"))

# Only the email code is taken automatically; anything else asks for the user (section 5.4).
STOP_WORDS = (
    "incorrect password",
    "couldn't find your account",
    "too many attempts",
    "try again later",
    "suspicious",
    "disabled",
    "your phone number",
    "add your phone",
    "selfie",
    "video selfie",
    "upload a photo of yourself",
)


@dataclass
class LoginResult:
    handle: str | None
    logged_in: bool
    reason: str | None = None


class InstagramLogin:
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

    def login(self, profile_id: str, username: str, package: str) -> LoginResult:
        self.phone.force_stop(package)
        time.sleep(1.0)
        self.phone.start_app(package)
        time.sleep(6.0)
        elements = wait_for(self.screen, _LOGIN_ANY, 45)
        if LOGIN.matches(elements):
            button = find_exact(elements, "Log in") or find(elements, "Log in")
            if button is not None:
                self.screen.tap(button)
        wait_for(self.screen, FORM, 30)
        self._guard(elements)

        self._type_into(username, "Username")
        self._tap_any(("Log in", "Next", "Continue"))
        wait_for(self.screen, PASSWORD_FORM, 30)
        self._guard(self.screen.elements())

        # The secret exists only inside this block.
        password = self.chameleon.platform_password(profile_id, "instagram")
        try:
            self._type_secret(password)
        finally:
            del password
        self._tap_any(("Log in", "Next", "Continue"))

        self._after_password()
        handle = self._read_handle()
        return LoginResult(handle=handle, logged_in=handle is not None)

    # -- the screens after the password -------------------------------------------------------------
    def _after_password(self) -> None:
        """The code screen, the unusual-login offer, the save-login offer, and the stop words."""
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            time.sleep(1.5)
            elements = self.screen.elements()
            text = " ".join(e.text + " " + e.desc for e in elements).lower()
            if CAPTCHA.matches(elements):
                raise NeedsHuman("Instagram shows a CAPTCHA", self._shot("instagram-captcha"))
            for word in STOP_WORDS:
                if word in text:
                    raise NeedsHuman(f"Instagram says: {word}", self._shot("instagram-stop"))
            if UNUSUAL.matches(elements):
                # Only the email code is taken automatically; anything else asks for the user.
                button = (find_exact(elements, "Send code") or find(elements, "email")
                          or find(elements, "Send code via email"))
                if button is None:
                    raise NeedsHuman("an unusual login check with no email choice",
                                     self._shot("instagram-unusual"))
                self.screen.tap(button)
                time.sleep(1.5)
                continue
            if CODE_FORM.matches(elements):
                self._enter_code()
                continue
            for label in ("Not now", "Skip", "Later", "Cancel"):
                button = find_exact(elements, label)
                if button is not None:
                    self.screen.tap(button)
                    break
            if HOME.matches(elements) or PROFILE.matches(elements):
                return
        raise NeedsHuman("Instagram did not reach its feed in 120 s", self._shot("instagram-timeout"))

    def _enter_code(self) -> None:
        code = self.code_provider()
        digits = re.sub(r"\D", "", code)
        if len(digits) != 6:
            raise NeedsCode("instagram")
        field = find(self.screen.elements(), "code") or find(self.screen.elements(), "Code")
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.5)
        self.screen.type_text(digits, min_ms=120, max_ms=300)
        confirm = find_exact(self.screen.elements(), "Confirm") or find_exact(self.screen.elements(), "Verify")
        if confirm is not None:
            self.screen.tap(confirm)

    def _read_handle(self) -> str | None:
        try:
            height = self.screen.size()[1]
            for element in self.screen.elements():
                if element.enabled and element.says("Profile") and element.bounds[1] >= height * 0.85:
                    self.screen.tap(element)
                    break
            elements = wait_for(self.screen, PROFILE, 20)
        except ScreenTimeout:
            return None
        for element in elements:
            if element.text.startswith("@"):
                return element.text.strip()
        return None

    # -- helpers -----------------------------------------------------------------------------------
    def _type_into(self, value: str, label: str) -> None:
        field = find(self.screen.elements(), label)
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.6)
        self.screen.type_text(value, min_ms=60, max_ms=160)

    def _type_secret(self, secret) -> None:
        field = find(self.screen.elements(), "Password")
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.5)
        self.screen.type_secret(secret)

    def _tap_any(self, labels: tuple[str, ...]) -> None:
        for label in labels:
            button = find(self.screen.elements(), label)
            if button is not None:
                self.screen.tap(button)
                return
        raise RuntimeError(f"none of {labels} is on screen")

    def _guard(self, elements: list[Element]) -> None:
        if CAPTCHA.matches(elements):
            raise NeedsHuman("a CAPTCHA on the login form", self._shot("instagram-captcha"))

    def _shot(self, name: str) -> str | None:
        if not self.shots_dir:
            return None
        path = self.shots_dir / f"{name}-{int(time.time())}.png"
        try:
            self.screen.screenshot(path)
            return str(path)
        except Exception:  # noqa: BLE001
            return None


_LOGIN_ANY = Signature("instagram login or feed", any_of=("Log in", "Log in with Facebook", "Sign up", "Search", "For you"))

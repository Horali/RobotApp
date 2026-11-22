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

HOME = Signature("instagram home", any_of=("For you", "Home Feed", "Your story", "reels tray container"))
LOGIN = Signature("instagram login", any_of=("Log in", "Log in with Facebook", "Sign up"))
# Never a launcher word: "Search" is on the phone's home screen, which made the flow race ahead of a
# slow first launch (the real login run, 2026-11-19 10:37 WIB).
ONBOARD = Signature(
    "instagram login or feed",
    any_of=("Instagram from Meta", "Username, email or mobile number", "Mobile number or email",
            "Forgot password?", "Log in with Facebook", "Create new account", "For you"),
)
FORM = Signature(
    "instagram login form",
    any_of=("Username, email or mobile number", "Mobile number or email", "Username", "Email"),
)
PASSWORD_FORM = Signature("instagram password form", any_of=("Password", "Log in"))
CODE_FORM = Signature("instagram code form", any_of=("Enter code", "Verification code", "code", "Security code"))
UNUSUAL = Signature("instagram unusual login", any_of=("Unusual login attempt", "unusual", "Verify"))
# The plan's section 5.4 list: a device approval and an SMS code both stop and ask the user.
CONFIRM_DEVICE = Signature(
    "instagram confirm it's you",
    any_of=("Choose a way to confirm it", "Approve the login from another device",
            "Notification on another device", "Text message, We'll send a code"),
)
CAPTCHA = Signature(
    "captcha",
    any_of=("Confirm you're human", "Slide to verify", "Verify you are human",
            "puzzle", "Rotate the image", "drag the slider",
            "Enter the characters", "real human behind this"),
)
PROFILE = Signature("instagram profile", any_of=("Edit profile", "Followers", "Following", "Posts"))

# Only the email code is taken automatically; anything else asks for the user (section 5.4).
STOP_WORDS = (
    "incorrect password",
    "couldn't find your account",
    "too many attempts",
    "try again later",
    "unexpected error",
    "sorry, there was a problem",
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
        user: int = 0,
    ) -> None:
        self.phone = phone
        self.screen = screen
        self.chameleon = chameleon
        self.emit = emit or (lambda event: None)
        self.shots_dir = shots_dir
        self.code_provider = code_provider or (lambda: "")
        self.user = user
        self.handle: str | None = None

    def login(self, profile_id: str, username: str, package: str) -> LoginResult:
        self.phone.force_stop(package, self.user)
        time.sleep(1.0)
        self.phone.start_app(package, self.user)
        # Instagram is heavy: a first launch after a force-stop can take well over ten seconds, and the
        # launcher underneath would otherwise answer first. Wait for the app to be in front, then for its
        # own words.
        for attempt in range(3):
            time.sleep(8.0)
            if self._in_front(package):
                break
            self.phone.start_app(package, self.user)
        # The launcher answers its own words, and a fresh install shows a terms sheet (and the phone's
        # keyboard its own dialog) over the login form: clear those while waiting, not after.
        deadline = time.monotonic() + 150
        elements: list[Element] = []
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if ONBOARD.matches(elements):
                break
            if not self._in_front(package):
                # Another app's window is on top: the keyboard's terms dialog, most often. Back closes it.
                self.screen.press_back()
                time.sleep(1.5)
                continue
            self._handle_terms()
            time.sleep(1.5)
        else:
            raise ScreenTimeout("Instagram did not show its login screen in 150 s")
        if LOGIN.matches(elements) and not FORM.matches(elements):
            button = find_exact(elements, "Log in") or find(elements, "Log in")
            if button is not None:
                self.screen.tap(button)
                time.sleep(2.0)
        self._handle_terms()
        wait_for(self.screen, FORM, 30)
        self._guard(elements)

        self._type_into(username, "Username, email or mobile number")
        self._require_typed(username)
        if find(self.screen.elements(), "Password") is None:
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
            if CONFIRM_DEVICE.matches(elements):
                # The plan's "tap Yes on your other device" / "phone code": only the user can do it.
                raise NeedsHuman(
                    "Instagram asks how to confirm it's you: approve the login on your other phone, "
                    "or take the SMS code (it offers a text message to a number ending 71)",
                    self._shot("instagram-confirm"),
                )
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
            for label in ("Not now", "Skip", "Later", "Cancel", "Don't allow", "Allow", "Save"):
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
        skip = {"profile", "instagram", "posts", "followers", "following", "edit"}
        for element in elements:
            text = (element.text or "").strip()
            if (
                80 <= element.bounds[1] < 320
                and not text.isdigit()
                and text.lower() not in skip
                and re.fullmatch(r"[A-Za-z0-9._]{3,30}", text)
            ):
                return f"@{text}"
        return None

    # -- helpers -----------------------------------------------------------------------------------
    def _handle_terms(self) -> None:
        """Terms sheets and other apps' dialogs: answer them so the login form is reachable.

        Two are real on this phone (2026-11-19): Instagram's own terms ("Agree And Continue") and the
        Facemoji keyboard's privacy dialog, which reappears every time a field takes focus until it is
        answered. Both are answered by their own button; a back press does not dismiss the keyboard's.
        """
        for _ in range(4):
            elements = self.screen.elements()
            agree = (find_exact(elements, "Agree And Continue")
                     or find(elements, "Agree And Continue")
                     or find_exact(elements, "I agree") or find_exact(elements, "Accept"))
            if agree is not None:
                self.screen.tap(agree)
                time.sleep(2.0)
                continue
            close = find_exact(elements, "Close")
            if close is not None:      # the keyboard's dialog's X, when it offers one
                self.screen.tap(close)
                time.sleep(1.5)
                continue
            if FORM.matches(elements):
                return
            time.sleep(1.0)

    def _require_typed(self, value: str) -> None:
        """The field must hold what was typed before anything is submitted.

        A real run (2026-11-19) tapped Log in on an empty field, because the IME is not enabled in a
        fresh space; a login attempt with an empty form is noise the account does not need.
        """
        typed = (self.screen.focused_text() or "").strip()
        page = " ".join(e.text for e in self.screen.elements())
        if value.lower() not in (typed.lower() + " " + page.lower()):
            raise RuntimeError(f"the login field is empty after typing {value[:3]}***; not submitting")

    def _in_front(self, package: str) -> bool:
        """The app actually resumed must be Instagram's: the launcher answers its own words."""
        try:
            fore, _ = self.phone.fore_app()
        except Exception:  # noqa: BLE001
            return True
        if not fore:
            return True
        return fore == package

    def _type_into(self, value: str, label: str) -> None:
        els = self.screen.elements()
        field = (
            find(els, label)
            or find(els, "Mobile number or email")
            or find(els, "email")
            or find(els, "Username")
        )
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.6)
            self._handle_terms()
        self.screen.type_text(value, min_ms=60, max_ms=160)
        self._handle_terms()

    def _type_secret(self, secret) -> None:
        field = find(self.screen.elements(), "Password")
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.5)
            self._handle_terms()
        self.screen.type_secret(secret)

    def _tap_any(self, labels: tuple[str, ...]) -> None:
        for _ in range(2):
            self._handle_terms()
            if hasattr(self.screen, "hide_keyboard"):
                self.screen.hide_keyboard()
                time.sleep(0.4)
            elements = self.screen.elements()
            for label in labels:
                button = find_exact(elements, label) or find(elements, label)
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

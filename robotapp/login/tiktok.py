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
CODE_FORM = Signature(
    "code form",
    # musically 47.9.1 (2026-11-19): the email's Continue goes straight here, "Verify email",
    # and the entry field carries no label - only "Resend code" names the screen.
    any_of=("Verify it's you", "Enter the code", "We sent a code", "6-digit code", "Verify email", "Resend code"),
)
PROFILE = Signature("profile", any_of=("Edit profile", "Followers", "Following"))
BIRTHDAY = Signature(
    "tiktok birthdate wall",
    any_of=("your birthdate", "Month picker"),        # the title and the body both carry the words
)
# musically 47.9.1 asks for a birthdate before anything else (trill never did: G2G was logged in by
# hand). The three wheels are SeekBars; the field only DISPLAYS their date, and Continue only
# becomes tappable once the wheels hold one (measured 2026-11-19): one drag on any wheel
# initialises them to today, and each ~200px down-drag on the year wheel is one year older.
# The date itself is arbitrary: the flow dials the year back until the age is an adult's, reading
# the field after every drag and never pressing Continue on a guess.
ADULT_YEAR = 2004        # 21+ years old in 2026; the wheels keep today's month and day
CAPTCHA = Signature(
    "captcha",
    any_of=(
        "Confirm you're human",
        "Slide to verify",
        "Verify you are human",
        "puzzle",
        "Rotate the image",
        "drag the slider",
    ),
)

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

    def login(self, profile_id: str, email: str, package: str, platform: str = "tiktok") -> LoginResult:
        self.phone.force_stop(package, self.user)
        self.phone.start_app(package, self.user)
        self._birthday()
        self._first_run()

        elements = wait_for(self.screen, HOME, 45)
        self._guard_screen(elements, "the TikTok home screen")
        self._tap_profile_tab()
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

        # trill asked for the password after the email; musically 47.9.1 goes straight to a code it
        # emails ("Verify email", no password form at all - measured 2026-11-19). Whichever appears.
        deadline = time.monotonic() + 30
        elements: list[Element] = []
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            if PASSWORD_FORM.matches(elements) or CODE_FORM.matches(elements):
                break
            time.sleep(1.5)
        else:
            raise ScreenTimeout("waited 30 s for the password or the code form")

        if CODE_FORM.matches(elements) and not PASSWORD_FORM.matches(elements):
            self._enter_code()          # the code path: no secret is fetched at all
        else:
            self._guard_screen(elements, "the password screen")

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
    _DATE = re.compile(r"^\s*[A-Za-z]+\s+\d{1,2},\s*(\d{4})\s*$")

    def _birthday(self) -> None:
        """musically's birthdate wall, before anything else: dial the wheels to an adult date.

        The field takes typed text but the wheels are the real input - typing alone leaves Continue
        disabled (measured 2026-11-19). The flow drags a wheel once to initialise them, then the year
        wheel down until the field shows an adult year, presses Continue once and waits for the wall
        to clear (it takes ~8 s) before moving on.
        """
        for _ in range(3):
            time.sleep(1.5)
            elements = self.screen.elements()
            if not BIRTHDAY.matches(elements):
                return
            if not self._adult_birthday(elements):
                raise NeedsHuman("TikTok's birthdate wheels would not dial to an adult year",
                                 self._shot("tiktok-birthday"))
            button = find_exact(self.screen.elements(), "Continue")
            if button is None:
                raise NeedsHuman("TikTok's birthdate Continue is not tappable",
                                 self._shot("tiktok-birthday"))
            self.screen.tap(button)
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                time.sleep(1.5)
                if not BIRTHDAY.matches(self.screen.elements()):
                    return              # the wall is accepted; the terms dialog follows in ~8 s
            raise NeedsHuman("TikTok's birthdate wall did not clear after Continue",
                             self._shot("tiktok-birthday"))
        raise NeedsHuman("TikTok's birthdate wall keeps coming back", self._shot("tiktok-birthday"))

    def _adult_birthday(self, elements: list[Element]) -> bool:
        """True once the field shows a date old enough. One drag on any wheel initialises an unset
        wall; one drag on the year wheel is a year older. Every drag is verified by reading the
        field - a wheel that does not move stops the login instead of spinning forever."""
        moved = False
        for _ in range(45):
            before = self._field_year(elements)
            if before is not None and before <= ADULT_YEAR:
                return True
            wheel = self._wheel(elements, "Month picker") if before is None and not moved \
                else self._wheel(elements, "Year picker")
            if wheel is None:
                return False
            self._drag_wheel(wheel)
            moved = True
            time.sleep(1.2)
            elements = self.screen.elements()
            after = self._field_year(elements)
            if before is not None and after == before:
                return False        # the wheel did not move: a stuck wheel is a human's problem
        return False

    def _drag_wheel(self, wheel: Element) -> None:
        """A ~200px drag inside the wheel, downward = older (measured: -1 year per drag)."""
        x1, y1, x2, y2 = wheel.bounds
        centre = x1 + (x2 - x1) // 2
        self.screen.drag(centre, y1 + (y2 - y1) // 4, centre, y1 + 3 * (y2 - y1) // 4, steps=20)

    def _field_year(self, elements: list[Element]) -> int | None:
        for element in elements:
            match = self._DATE.match(element.text or "")
            if match:
                return int(match.group(1))
        return None

    def _wheel(self, elements: list[Element], desc: str) -> Element | None:
        return next((e for e in elements if e.desc == desc and e.enabled), None)

    def _first_run(self) -> None:
        """The whole onboarding, with a deadline: dismiss every first-run gate until the feed.

        musically's measured sequence (2026-11-19): birthdate wall (another method) -> Terms of
        Service dialog ("Agree and continue", ~8 s after Continue) -> the notifications permission
        ("ALLOW" / "DON'T ALLOW" - all caps and a curly apostrophe, so `says` normalises them) ->
        the feed. Interests screens and the swipe tutorial still answer to Skip or a swipe.
        """
        deadline = time.monotonic() + 40
        idle = 0
        while time.monotonic() < deadline:
            time.sleep(1.5)
            elements = self.screen.elements()
            for label in ("Skip", "Not now", "Don't allow", "Cancel", "Agree and continue"):
                button = find_exact(elements, label)
                if button is not None:
                    self.screen.tap(button)
                    idle = 0
                    break
            else:
                if find(elements, "For You") is not None:
                    return
                idle += 1
                if idle >= 3:      # nothing to dismiss and no feed: the tutorial wants a swipe
                    self.screen.swipe_up()
                    idle = 0
        log.warning("tiktok: the first-run screens did not reach the feed in 40 s")

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
            for label in ("Not now", "Skip", "Don't allow", "Later", "Agree and continue"):
                button = find_exact(elements, label)
                if button is not None:
                    self.screen.tap(button)
                    break
            if PROFILE.matches(elements) or find(elements, "For You") is not None:
                return
        raise NeedsHuman("TikTok did not reach the profile in 90 s", self._shot("tiktok-login-timeout"))

    def _enter_code(self) -> None:
        """The emailed code. musically's field carries no label and "Resend code" does - so the
        code is typed straight into the screen's editable (index 0), never tapped at by name."""
        code = self.code_provider()
        if not code:
            raise NeedsCode("tiktok")
        digits = re.sub(r"\D", "", code)
        if len(digits) != 6:
            raise NeedsCode("tiktok")
        self.screen.type_text(digits, min_ms=120, max_ms=300)
        time.sleep(2.0)      # a full 6 boxes submits itself

    def _read_handle(self) -> str | None:
        try:
            self._tap_profile_tab()
            elements = wait_for(self.screen, PROFILE, 20)
        except ScreenTimeout:
            return None
        for element in elements:
            if element.text.startswith("@"):
                return element.text.strip()
        return None

    # -- helpers -----------------------------------------------------------------------------------
    def _tap_profile_tab(self) -> None:
        """The bottom bar's Profile tab: exact label, lower part of the screen only.

        A video author's profile link also says 'profile' and opens someone else's page - the trap
        the post flow already fixed (2026-11-19, musically: the login opened @spryzen.ae instead).
        """
        height = self.screen.size()[1]
        for element in self.screen.elements():
            if element.enabled and element.says("Profile") and element.bounds[1] >= height * 0.85:
                self.screen.tap(element)
                return
        raise RuntimeError("the Profile tab is not on screen")

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

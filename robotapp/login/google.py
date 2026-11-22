"""Signing a brand's Google account in, in a space, for YouTube (PLAN section 5.6).

The plan's order: Settings -> Passwords & accounts -> Add account -> Google -> email -> password ->
possible checks -> "I agree" -> the services screen (Backup off, Location off) -> done. Then
YouTube's avatar is checked to be the brand's channel.

Honest note: the signatures follow the plan's description of Google's screens. Google's checks are
the strictest of the three platforms and the plan itself says a code's destination is unknown until
it appears; anything the robot cannot finish alone (a code to a place it cannot read, a "couldn't
sign you in") stops with NeedsHuman, exactly as the plan orders (section 5.4).
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
from ..log import Secret
from ..secrets import Chameleon
from ..ui import Element, Screen, ScreenTimeout, Signature, find, find_exact, wait_for

log = logging.getLogger("robotapp")

YOUTUBE = "com.google.android.youtube"
GMS = "com.google.android.gms"

SETTINGS_ACCOUNTS = Signature("accounts in settings", any_of=("Passwords & accounts", "Accounts", "Add account"))
GOOGLE_PICK = Signature("pick an account type", any_of=("Google", "Other", "Email"))
EMAIL_FORM = Signature("google email", any_of=("Sign in", "Email or phone", "your Google Account"))
PASSWORD_FORM = Signature("google password", any_of=("Enter your password", "password", "Welcome"))
CODE_FORM = Signature("google code", any_of=("Verify it", "2-Step Verification", "code", "Get a code"))
TERMS = Signature("google terms", any_of=("I agree", "Google Terms of Service", "Accept"))
SERVICES = Signature("google services", any_of=("Backup to Google Drive", "Google services", "Web & App Activity"))
DONE = Signature("google done", any_of=("Account added", "signed in", "Done", "Set up"))

CAPTCHA = Signature("captcha", any_of=("Confirm you're human", "Slide to verify", "Verify you are human",
                                       "puzzle", "Rotate the image", "drag the slider"))

# Only what the robot can finish alone; anything else asks for the user (section 5.6).
STOP_WORDS = (
    "couldn't sign you in",
    "couldn't find your google account",
    "wrong password",
    "too many attempts",
    "try again later",
    "this device isn't recognized",
    "couldn't create a profile",
    "verify it's you",
    "your account has been disabled",
    "tap yes on your",
    "use your phone",
    "selfie",
    "video selfie",
    "government id",
)


@dataclass
class LoginResult:
    channel: str | None
    logged_in: bool
    reason: str | None = None


class GoogleLogin:
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
        self.channel: str | None = None

    def login(self, email: str, email_account_id: str, user: int) -> LoginResult:
        """Add the brand's Google account to a space, for YouTube. Never types the Gmail password
        anywhere but Google's own password field."""
        self.phone.force_stop(GMS, user)
        self.phone.force_stop("com.android.settings", user)
        time.sleep(1.0)
        self._open_accounts(user)
        self._add_google_account(email)
        self._password(email_account_id)
        self._after_password()
        channel = self._check_channel(user)
        return LoginResult(channel=channel, logged_in=channel is not None)

    # -- the settings walk -----------------------------------------------------------------------
    def _open_accounts(self, user: int) -> None:
        """Settings -> Passwords & accounts, over the settings activity (no launcher icon)."""
        self.phone.shell(f"am start --user {user} -a android.settings.SYNC_SETTINGS", timeout=30)
        try:
            elements = wait_for(self.screen, SETTINGS_ACCOUNTS, 30)
        except ScreenTimeout:
            # Some builds call the page just "Accounts" under a different settings action.
            self.phone.shell(f"am start --user {user} -a android.settings.SETTINGS", timeout=30)
            elements = wait_for(self.screen, SETTINGS_ACCOUNTS, 30)
        add = find_exact(elements, "Add account") or find(elements, "Add account")
        if add is None:
            # The list may need a scroll to reach "Add account".
            self.screen.swipe_up()
            time.sleep(1.0)
            add = find_exact(self.screen.elements(), "Add account") or find(self.screen.elements(), "Add account")
        if add is None:
            raise RuntimeError("'Add account' is not in Settings")
        self.screen.tap(add)
        wait_for(self.screen, GOOGLE_PICK, 30)

    def _add_google_account(self, email: str) -> None:
        elements = self.screen.elements()
        google = find_exact(elements, "Google") or find(elements, "Google")
        if google is None:
            raise RuntimeError("'Google' is not in the account-type list")
        self.screen.tap(google)
        # A "checking info" spinner can sit between the pick and the email form.
        wait_for(self.screen, EMAIL_FORM, 60)
        els = self.screen.elements()
        field = (
            find_exact(els, "Email or phone")
            or find(els, "Email or phone")
            or next((e for e in els if e.resource_id == "identifierId"), None)
        )
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.6)
        self.screen.type_text(email, min_ms=60, max_ms=160)
        self._require_typed(email)
        self._advance("google email")
        wait_for(self.screen, PASSWORD_FORM, 45)

    def _password(self, email_account_id: str) -> None:
        """The Gmail password, fetched at the moment it is typed and dropped right after.

        Google's page has ONE field, so the secret goes into editable 0. The old call used the
        default index 1 (Instagram has two fields): nothing was typed and Google answered "Enter a
        password" (measured on the phone, 2026-11-20). The field is then checked not to be empty
        before anything is submitted.
        """
        elements = self.screen.elements()
        if CAPTCHA.matches(elements):
            raise NeedsHuman("Google shows a CAPTCHA before the password",
                             self._shot("google-captcha"))
        field = find(elements, "password") or find(elements, "Enter your password")
        if field is not None:
            self.screen.tap(field)
            time.sleep(0.6)
        password = self.chameleon.email_password(email_account_id)
        try:
            self.screen.type_secret(password, index=0)
        finally:
            del password
        time.sleep(0.8)
        if not (self.screen.focused_text() or "").strip():
            raise NeedsHuman("Google's password field stayed empty after typing",
                             self._shot("google-password-empty"))
        self._advance("google password")

    # -- everything Google may ask after the password ----------------------------------------------
    def _after_password(self) -> None:
        """The plan's honest part: a code's destination is unknown until it appears.

        The robot finishes alone only a code to the brand's own Gmail (read by the caller). Any
        other destination is shown to the user with the masked address Google displays, and a
        'couldn't sign you in' stops for at least 24 h (the plan's rule), never in a loop.
        """
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            time.sleep(1.5)
            elements = self.screen.elements()
            text = " ".join(e.text + " " + e.desc for e in elements).lower()
            if CAPTCHA.matches(elements):
                raise NeedsHuman("Google shows a CAPTCHA", self._shot("google-captcha"))
            for word in STOP_WORDS:
                if word in text:
                    raise NeedsHuman(f"Google says: {word}", self._shot("google-stop"))
            if TERMS.matches(elements):
                button = find_exact(elements, "I agree") or find(elements, "I agree")
                if button is not None:
                    self.screen.tap(button)
                    continue
            if SERVICES.matches(elements):
                self._services_off(elements)
                continue
            if DONE.matches(elements):
                return
            if CODE_FORM.matches(elements):
                self._code_or_ask(elements, text)
                continue
            for label in ("Skip", "Not now", "Later", "No thanks", "More options", "Cancel"):
                button = find_exact(elements, label)
                if button is not None:
                    self.screen.tap(button)
                    break
        raise NeedsHuman("Google did not finish the sign-in in 180 s", self._shot("google-timeout"))

    def _code_or_ask(self, elements: list[Element], text: str) -> None:
        """A code screen: only the brand's own Gmail is automatic; anything else asks the user."""
        # The masked destination Google shows, e.g. "a code to j•••@gmail.com" or "•• 12".
        masked = next((e.text.strip() for e in elements if "@" in e.text and "\u2022" in e.text), None)
        wants_email = masked is not None and "@" in masked
        if wants_email:
            code = self.code_provider()
            digits = re.sub(r"\D", "", code)
            if len(digits) != 6:
                raise NeedsCode("google")
            self.screen.type_text(digits, min_ms=120, max_ms=300)
            self._tap_any(("Next", "Continue", "Verify"))
            return
        # Any other destination (a phone number, "tap Yes on your phone"): ask, with what Google shows.
        why = f"Google wants a code sent somewhere else{f': {masked}' if masked else ''}"
        raise NeedsHuman(why, self._shot("google-code"))

    def _services_off(self, elements: list[Element]) -> None:
        """The Google services screen: Backup off, Location off; then Accept/Save."""
        for label in ("Backup to Google Drive", "Backup", "Back up to Google Drive"):
            toggle = find_exact(elements, label) or find(elements, label)
            if toggle is not None and self._is_on(elements, label):
                self.screen.tap(toggle)
                time.sleep(1.0)
                break
        for label in ("Accept", "Save", "I agree", "More", "More options"):
            button = find_exact(elements, label)
            if button is not None:
                self.screen.tap(button)
                return

    @staticmethod
    def _is_on(elements: list[Element], label: str) -> bool:
        """A switch is on when a sibling says ON; a text-only guess is not good enough."""
        for element in elements:
            if element.text.strip().upper() == "ON" and abs(element.center[1] - find(elements, label).center[1]) < 120:
                return True
        return False

    # -- YouTube ---------------------------------------------------------------------------------
    def _check_channel(self, user: int) -> str | None:
        """YouTube's avatar or You tab -> the account sheet: the signed-in account's name, or None.

        A None here means the sign-in did not take (or the account sheet could not be read); the
        caller reports it as a failed login, never as a success.
        """
        self.phone.force_stop(YOUTUBE, user)
        time.sleep(1.0)
        self.phone.start_app(YOUTUBE, user)
        time.sleep(8.0)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            avatar = next((e for e in elements if "Account" in (e.desc or "")), None)
            if avatar is None:
                height = self.screen.size()[1] if hasattr(self.screen, "size") else 2400
                avatar = next(
                    (e for e in elements if e.enabled and e.says("You") and e.bounds[1] >= height * 0.80),
                    None,
                )
            if avatar is not None:
                self.screen.tap(avatar)
                time.sleep(2.5)
                name = self._account_name(self.screen.elements())
                if name:
                    self.screen.press_back()      # close the account sheet, back to the feed
                    time.sleep(1.0)
                    return name
                self.screen.press_back()
                time.sleep(1.0)
            time.sleep(1.5)
        return None

    @staticmethod
    def _account_name(elements: list[Element]) -> str | None:
        """The account sheet: the signed-in account's email, its name part, or @handle. A Gmail address is
        the strongest marker of the signed-in account (names can be anything)."""
        for element in elements:
            text = element.text.strip()
            if "@" in text and "." in text.split("@")[-1]:
                return text.split("@")[0].strip()
        for element in elements:
            text = element.text.strip()
            if text.startswith("@") and " " not in text and len(text) > 1:
                return text
        return None

    # -- helpers ---------------------------------------------------------------------------------
    def _advance(self, where: str, tries: int = 5) -> None:
        """Press Next/Continue and make sure the screen actually moved on.

        Clicking a button by its coordinates can land on the keyboard that sits over it (measured
        2026-11-20: the tap "worked" and the page never changed). So every try is verified: if the
        screen still shows the same form, the keyboard is closed and the button is pressed again.
        """
        for attempt in range(tries):
            elements = self.screen.elements()
            button = None
            for label in ("Next", "Continue", "Sign in"):
                button = find_exact(elements, label) or find(elements, label)
                if button is not None:
                    break
            if button is not None:
                self.screen.tap(button)
                time.sleep(2.5)
                after = self.screen.elements()
                after_text = " ".join(e.text + " " + e.desc for e in after).lower()
                if (
                    PASSWORD_FORM.matches(after)
                    or CODE_FORM.matches(after)
                    or TERMS.matches(after)
                    or SERVICES.matches(after)
                    or DONE.matches(after)
                    or CAPTCHA.matches(after)
                    or any(word in after_text for word in STOP_WORDS)
                ):
                    return
                # still on the same form: the keyboard most likely ate the tap
                if attempt < tries - 1:
                    self.screen.press_back()
                    time.sleep(1.5)
            else:
                time.sleep(1.5)
        raise ScreenTimeout(f"Google did not move past {where}")

    def _require_typed(self, value: str) -> None:
        """Never submit an empty form: the field (or the page) must show what was typed.

        The IME is not enabled in a fresh space, so a typed email can vanish silently - the same
        mistake the first Instagram login made (2026-11-19).
        """
        typed = (self.screen.focused_text() or "").strip()
        page = " ".join(e.text for e in self.screen.elements())
        if value.lower() not in (typed.lower() + " " + page.lower()):
            raise RuntimeError(f"the Google account field is empty after typing {value[:3]}***; not submitting")

    def _tap_any(self, labels: tuple[str, ...], timeout_s: float = 20.0) -> None:
        """Tap the first of `labels` that shows up, waiting for it.

        A single look is not enough: Google's "Next" appears a beat after the email lands, and the
        keyboard can sit over it (measured 2026-11-20 - the first run typed the email and then failed
        with "none of ('Next', 'Continue') is on screen" while Next was there a second later). When the
        button is under the keyboard, the keyboard is closed once and the screen re-read.
        """
        deadline = time.monotonic() + timeout_s
        closed_keyboard = False
        while time.monotonic() < deadline:
            elements = self.screen.elements()
            for label in labels:
                button = find_exact(elements, label) or find(elements, label)
                if button is None:
                    continue
                # Only when the keyboard is actually up AND covers the button: Google's own Next
                # sits low on its screen, so a plain height test dismissed the sign-in sheet.
                if not closed_keyboard and self._keyboard_open(elements) and button.bounds[1] > self.screen.size()[1] * 0.62:
                    self.screen.press_back()
                    closed_keyboard = True
                    time.sleep(1.5)
                    break
                self.screen.tap(button)
                return
            else:
                time.sleep(1.5)
        raise RuntimeError(f"none of {labels} appeared on screen in {timeout_s:.0f}s")

    @staticmethod
    def _keyboard_open(elements: list[Element]) -> bool:
        """The IME's own toolbar is on screen (the keyboard's ids or its shortcut row)."""
        for element in elements:
            rid = (element.resource_id or "").lower()
            if "input_method" in rid or "inputmethod" in rid:
                return True
        text = " ".join(e.text for e in elements)
        return "Clipboard" in text and "Voice" in text

    def _shot(self, name: str) -> str | None:
        if not self.shots_dir:
            return None
        path = self.shots_dir / f"{name}-{int(time.time())}.png"
        try:
            self.screen.screenshot(path)
            return str(path)
        except Exception:  # noqa: BLE001
            return None

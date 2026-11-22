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


def test_advance_accepts_services_done_or_captcha_without_backing_out() -> None:
    for landing in (
        [el("Backup to Google Drive"), el("Accept")],
        [el("Account added"), el("Done")],
        [el("Confirm you're human"), el("Slide to verify")],
        [el("Couldn't find your Google Account")],
    ):
        screen = Screen([el("Next", bounds=(756, 2280, 1020, 2424))])
        orig_tap = screen.tap

        def move_to_landing(element, dest=landing, s=screen, base=orig_tap) -> None:
            base(element)
            s.current = dest

        screen.tap = move_to_landing  # type: ignore[method-assign]
        GoogleLogin(phone=None, screen=screen, chameleon=None)._advance("google step", tries=3)
        assert screen.taps == ["Next"]


def test_services_off_only_taps_backup_toggle_when_on() -> None:
    on_screen = Screen([
        el("Backup to Google Drive", bounds=(80, 900, 700, 980)),
        el("ON", bounds=(880, 900, 1000, 980)),
        el("Accept", bounds=(750, 2200, 1020, 2320)),
    ])
    GoogleLogin(phone=None, screen=on_screen, chameleon=None)._services_off(on_screen.elements())
    assert on_screen.taps == ["Backup to Google Drive", "Accept"]

    off_screen = Screen([
        el("Backup to Google Drive", bounds=(80, 900, 700, 980)),
        el("OFF", bounds=(880, 900, 1000, 980)),
        el("Accept", bounds=(750, 2200, 1020, 2320)),
    ])
    GoogleLogin(phone=None, screen=off_screen, chameleon=None)._services_off(off_screen.elements())
    assert off_screen.taps == ["Accept"]


def test_add_google_account_does_not_tap_forgot_email_when_hint_is_blank() -> None:
    from robotapp.fake import FakePhone, fake_guard

    phone = FakePhone(guard=fake_guard())
    screen = Screen([
        el("Google", bounds=(210, 663, 894, 728)),
        el("Sign in"),
        el("Forgot email?", bounds=(72, 1080, 320, 1140)),
        el("", bounds=(72, 860, 1000, 1000), resource_id="identifierId"),
        el("Next", bounds=(756, 2280, 1020, 2424)),
    ])
    typed: list[str] = []
    screen.typed = typed
    screen.focused_text = lambda: "user@gmail.com"  # type: ignore[attr-defined]
    screen.type_text = lambda txt, **kw: typed.append(txt)  # type: ignore[attr-defined]

    def adv_tap(element) -> None:
        Screen.tap(screen, element)
        if element.text == "Next":
            screen.current = [el("Enter your password"), el("Next")]

    screen.tap = adv_tap  # type: ignore[method-assign]
    GoogleLogin(phone=phone, screen=screen, chameleon=None)._add_google_account("user@gmail.com")
    assert "Forgot email?" not in screen.taps
    assert typed == ["user@gmail.com"]


def test_optional_selfie_prompt_with_not_now_is_dismissed_not_stopped() -> None:
    from robotapp.errors import NeedsHuman

    # Optional enrollment offer with "Not now" -> taps "Not now" and completes on "Done".
    screen = Screen([
        el("Add a selfie for sign-in"),
        el("Take a short video of your face"),
        el("Not now"),
        el("Continue"),
    ])
    orig_tap = screen.tap

    def tap_to_done(element) -> None:
        orig_tap(element)
        if element.text == "Not now":
            screen.current = [el("Account added")]

    screen.tap = tap_to_done  # type: ignore[method-assign]
    GoogleLogin(phone=None, screen=screen, chameleon=None)._after_password()
    assert "Not now" in screen.taps

    # Mandatory selfie challenge with no dismiss button -> still stops with NeedsHuman.
    locked_screen = Screen([el("Verify it's you"), el("Take a video selfie"), el("Next")])
    with pytest.raises(NeedsHuman, match="verify it's you|selfie"):
        GoogleLogin(phone=None, screen=locked_screen, chameleon=None)._after_password()


def test_account_present_and_check_channel_dismisses_notification_dialog() -> None:
    from robotapp.fake import FakePhone, fake_guard

    phone = FakePhone(guard=fake_guard())
    phone.expect(
        r"dumpsys account",
        "User UserInfo{0:Owner:13}:\n"
        "  Account {name=owner@gmail.com, type=com.google}\n"
        "User UserInfo{10:Speed Clips:410}:\n"
        "  Account {name=speed@gmail.com, type=com.google}\n"
        "User UserInfo{12:Timmy Clips:410}:\n",
    )
    gl = GoogleLogin(phone=phone, screen=None, chameleon=None)
    assert gl._account_present(10, "speed@gmail.com") is True
    assert gl._account_present(10, "owner@gmail.com") is False
    assert gl._account_present(12, "speed@gmail.com") is False

    screen = Screen([
        el("Allow YouTube to send you notifications?"),
        el("DON\u2019T ALLOW", bounds=(48, 2157, 1032, 2316)),
    ])
    orig_tap = screen.tap

    def flow_tap(element) -> None:
        orig_tap(element)
        if element.text == "DON\u2019T ALLOW":
            screen.current = [el("You", bounds=(864, 2180, 1080, 2320))]
        elif element.text == "You":
            screen.current = [el("Speed Clips"), el("@SpeedExpediaClips", bounds=(200, 300, 600, 360))]

    screen.tap = flow_tap  # type: ignore[method-assign]
    gl_ui = GoogleLogin(phone=phone, screen=screen, chameleon=None)
    assert gl_ui._check_channel(10) == "@SpeedExpediaClips"
    assert "DON\u2019T ALLOW" in screen.taps
    assert "You" in screen.taps

    # When You tab omits @handle from uiautomator2, tap "Accounts" to read the Gmail address.
    screen2 = Screen([el("You", bounds=(864, 2180, 1080, 2320))])

    def you_to_accounts_tap(element) -> None:
        Screen.tap(screen2, element)
        if element.text == "You":
            screen2.current = [el("Speed Travel Fan"), el("", bounds=(36, 120, 406, 240)), el("Accounts")]
        elif element.text == "Accounts":
            screen2.current = [el("horalixscripts3@gmail.com")]

    screen2.tap = you_to_accounts_tap  # type: ignore[method-assign]
    assert GoogleLogin(phone=phone, screen=screen2, chameleon=None)._check_channel(10) == "horalixscripts3"


def test_advance_dismisses_emoji_keyboard_terms_overlay() -> None:
    screen = Screen([
        el("Terms and Conditions"),
        el("By using this keyboard, you agree to Privacy Policy and Terms of Use Agreement of Emoji Keyboard"),
        el("Agree And Continue", bounds=(72, 2000, 1008, 2140)),
    ])
    orig_tap = screen.tap

    def flow(element) -> None:
        orig_tap(element)
        if element.text == "Agree And Continue":
            screen.current = [el("Next", bounds=(756, 2160, 1020, 2304))]
        elif element.text == "Next":
            screen.current = [el("Enter your password"), el("Next")]

    screen.tap = flow  # type: ignore[method-assign]
    GoogleLogin(phone=None, screen=screen, chameleon=None)._advance("google email", tries=3)
    assert screen.taps == ["Agree And Continue", "Next"]

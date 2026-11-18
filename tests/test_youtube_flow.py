"""The YouTube Shorts flow and the Google sign-in on a scripted screen (PLAN sections 6.7, 5.6).

Like the other scripted tests: a screen that moves when the right thing is tapped catches a wrong
label or a signature that never arrives, without touching the phone or any account.
"""

from pathlib import Path

import pytest

from robotapp.errors import NeedsHuman
from robotapp.fake import FakePhone, fake_guard
from robotapp.journal import PRESSED, Journal
from robotapp.log import Secret
from robotapp.login.google import GoogleLogin
from robotapp.post.base import PostSpec
from robotapp.post.youtube import YOUTUBE, YouTubePoster
from robotapp.ui import Element

PASSWORD = "fake-Gmail-Pass-77!"


def el(text: str = "", desc: str = "", bounds=(0, 0, 100, 100), clickable: bool = False) -> Element:
    return Element(text=text, desc=desc, bounds=bounds, clickable=clickable)


SCREENS = {
    "home": [el("Home"), el("Shorts"), el(desc="Create a video or Short", bounds=(432, 2193, 648, 2340), clickable=True), el("You")],
    "create_sheet": [el("Create a Short", bounds=(100, 1700, 500, 1800), clickable=True), el("Upload a video"), el("Go live")],
    "shorts_camera": [el("Add sound"), el("Upload", bounds=(100, 2100, 400, 2200), clickable=True), el("Record")],
    "gallery": [
        el("Recents", bounds=(100, 200, 300, 300), clickable=True),
        el("1:02", bounds=(100, 400, 200, 450)),
        el("", desc="video thumbnail", bounds=(100, 500, 540, 900), clickable=True),
    ],
    "trim": [el("Done", bounds=(900, 2200, 1050, 2320), clickable=True), el("1:02"), el("Preview")],
    "details": [
        el("Title", bounds=(100, 1700, 900, 1800), clickable=True),
        el("Upload Short", bounds=(900, 2200, 1050, 2320), clickable=True),
    ],
    "uploaded": [el("Upload complete"), el("Home"), el("Shorts"), el("You")],
    "you": [el("View channel"), el("Your videos", bounds=(100, 900, 500, 1000), clickable=True), el("Switch account")],
    "videos": [el("Your videos"), el("", desc="Big win #shorts", bounds=(100, 700, 900, 850), clickable=True)],
    "video": [el(desc="More options", bounds=(900, 200, 1050, 350), clickable=True), el("Like")],
    "share_sheet": [el("Copy link", bounds=(100, 1800, 900, 1900), clickable=True), el("Share to")],
    # Google sign-in
    "settings": [el("Passwords & accounts"), el("Add account", bounds=(100, 1600, 500, 1700), clickable=True)],
    "account_pick": [el("Google", bounds=(100, 900, 500, 1000), clickable=True), el("Other"), el("Email")],
    "email_form": [el("Email or phone", bounds=(100, 900, 900, 1000), clickable=True), el("Next", bounds=(100, 1500, 900, 1600), clickable=True)],
    "password_form": [el("Enter your password"), el("password", bounds=(100, 1100, 900, 1200), clickable=True), el("Next", bounds=(100, 1600, 900, 1700), clickable=True)],
    "terms": [el("Google Terms of Service"), el("I agree", bounds=(100, 1900, 500, 2000), clickable=True)],
    "services": [el("Backup to Google Drive"), el("ON", bounds=(300, 1300, 400, 1360)), el("Accept", bounds=(100, 2000, 500, 2100), clickable=True)],
    "done": [el("Account added"), el("Done")],
    # YouTube after the sign-in: an avatar, and the account sheet it opens
    "youtube_after": [el("Home"), el("Shorts"), el("You"),
                      el(desc="Account and Notifications", bounds=(900, 100, 1050, 250), clickable=True)],
    "account_sheet": [el("Timmy Clips"), el("timmy.clips@gmail.com"), el("Switch account")],
}


class ScriptedScreen:
    def __init__(self, state: str = "home") -> None:
        self.state = state
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.secrets: list[str] = []
        self.shots: list[Path] = []
        self._clipboard = "https://youtube.com/shorts/j1a7ETNYOAI"

    def elements(self) -> list[Element]:
        return SCREENS[self.state]

    def tap(self, element: Element) -> None:
        label = element.text or element.desc
        self.taps.append(label)
        moves = {
            ("home", "Create a video or Short"): "create_sheet",
            ("home", "Create"): "create_sheet",
            ("create_sheet", "Create a Short"): "shorts_camera",
            ("shorts_camera", "Upload"): "gallery",
            ("gallery", "video thumbnail"): "trim",
            ("trim", "Done"): "details",
            ("details", "Upload Short"): "uploaded",
            ("uploaded", "You"): "you",
            ("home", "You"): "you",
            ("you", "Your videos"): "videos",
            ("video", "More options"): "share_sheet",
            ("settings", "Add account"): "account_pick",
            ("account_pick", "Google"): "email_form",
            ("email_form", "Next"): "password_form",
            ("password_form", "Next"): "terms",
            ("terms", "I agree"): "services",
            ("services", "Accept"): "done",
            ("youtube_after", "Account and Notifications"): "account_sheet",
        }
        target = moves.get((self.state, label))
        if target:
            self.state = target
        if self.state == "account_sheet" and label == "back":
            self.state = "youtube_after"
        # The services screen's Backup toggle: tapping it turns it off.
        if self.state == "services" and label == "Backup to Google Drive":
            SCREENS["services"] = [el("Backup to Google Drive"), el("OFF", bounds=(300, 1300, 400, 1360)), el("Accept", bounds=(100, 2000, 500, 2100), clickable=True)]

    def tap_point(self, x: int, y: int) -> None:
        self.taps.append(f"point:{x},{y}")
        if self.state == "you":
            self.state = "video"
        elif self.state == "videos":
            self.state = "video"

    def long_press(self, element: Element) -> None:
        self.taps.append(f"long:{element.text or element.desc}")

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.typed.append(text)

    def type_secret(self, secret) -> None:
        self.secrets.append(secret.reveal())

    def set_text(self, text: str) -> None:
        self.typed.append(text)
        self.typed.append(text)      # the field reports it back

    def clear_field(self) -> None:
        self.typed.clear()

    def press_back(self) -> None:
        self.taps.append("back")
        if self.state in ("details", "trim", "gallery", "shorts_camera", "create_sheet"):
            self.state = "home"
        elif self.state == "you":
            self.state = "home"

    def swipe_up(self) -> None:
        self.taps.append("swipe")

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG fake")
        self.shots.append(path)

    def size(self) -> tuple[int, int]:
        return 1080, 2400

    def clipboard(self) -> str | None:
        return self._clipboard

    def focused_text(self) -> str | None:
        return self.typed[-1] if self.typed else None


class LinkedPhone(FakePhone):
    def __init__(self, screen: ScriptedScreen) -> None:
        super().__init__(guard=fake_guard())
        self.screen = screen

    def tap(self, x: int, y: int) -> None:
        super().tap(x, y)
        self.screen.tap_point(x, y)


@pytest.fixture()
def journal(tmp_path):
    j = Journal(tmp_path / "robot.db")
    j.start_job("job-1", "post")
    yield j
    j.close()


def spec() -> PostSpec:
    return PostSpec(upload_id="u1", platform="youtube", video=Path("x.mp4"), length_s=62.0,
                    title="Big win #shorts", caption="Big win #shorts", hashtags=["#shorts"])


def test_the_short_flow_walks_youtube_screens_and_stops_before_upload(journal) -> None:
    screen = ScriptedScreen()
    # The account avatar: the flow taps it to read the channel name, then comes back.
    original = screen.elements

    def with_avatar():
        elements = original()
        return elements + [el(desc="Account and Notifications", bounds=(900, 100, 1050, 250), clickable=True)]

    screen.elements = with_avatar
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec(), dry_run=True)

    assert result.outcome == "dry_run"
    assert screen.state == "details"
    assert "Upload Short" not in screen.taps
    # the channel check (avatar -> back), then create -> Create a Short -> gallery -> the tile -> Done -> Title
    assert screen.taps[:9] == ["Account and Notifications", "Account and Notifications", "back",
                               "Create a video or Short", "Create a Short", "Upload",
                               "video thumbnail", "Done", "Title"]
    assert journal.pressed("job-1", "u1") is False


def test_a_wrong_length_video_is_refused_before_upload(journal) -> None:
    screen = ScriptedScreen()
    original = screen.elements

    def with_avatar():
        return original() + [el(desc="Account and Notifications", bounds=(900, 100, 1050, 250), clickable=True)]

    screen.elements = with_avatar
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    bad = PostSpec(upload_id="u2", platform="youtube", video=Path("x.mp4"), length_s=9.0, title="T")
    result = poster.post(bad)
    assert result.outcome == "failed_before_post"
    assert "the gallery shows" in (result.reason or "")
    assert "Upload Short" not in screen.taps


def test_upload_is_pressed_once_and_the_link_is_read(journal, monkeypatch) -> None:
    monkeypatch.setattr("robotapp.post.youtube.engage", lambda phone: 5.0)
    screen = ScriptedScreen()
    original = screen.elements

    def with_avatar():
        return original() + [el(desc="Account and Notifications", bounds=(900, 100, 1050, 250), clickable=True)]

    screen.elements = with_avatar
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == "posted"
    assert result.url == "https://youtube.com/shorts/j1a7ETNYOAI"
    assert screen.taps.count("Upload Short") == 1
    assert journal.pressed("job-1", "u1") is True
    assert journal.outcome("job-1", "u1") == "posted"


def test_no_avatar_means_not_signed_in(journal) -> None:
    screen = ScriptedScreen()          # no avatar element: YouTube not signed in
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == "failed_before_post"
    assert "signed in" in (result.reason or "")
    assert "Upload Short" not in screen.taps


class FakeChameleon:
    def email_password(self, account_id: str) -> Secret:
        return Secret(PASSWORD)


def test_the_google_sign_in_walks_its_screens_and_never_prints_the_password(caplog) -> None:
    import logging

    screen = ScriptedScreen("settings")

    class AfterPhone(FakePhone):
        def start_app(self, package, user=0):
            super().start_app(package, user)
            if package == "com.google.android.youtube":
                screen.state = "youtube_after"   # YouTube opens signed in, with the avatar
            return "started"

    login = GoogleLogin(AfterPhone(guard=fake_guard()), screen, FakeChameleon(),
                        code_provider=lambda: "")
    with caplog.at_level(logging.DEBUG):
        result = login.login("timmy.clips@gmail.com", "acct-1", user=11)

    assert result.logged_in is True
    assert result.channel == "timmy.clips"
    assert "timmy.clips@gmail.com" in screen.typed
    assert screen.secrets == [PASSWORD]       # the Gmail password, typed once through the secret path
    assert PASSWORD not in caplog.text
    assert "Accept" in screen.taps            # the services screen was accepted


def test_a_code_to_another_destination_asks_for_a_human() -> None:
    screen = ScriptedScreen("settings")
    # A code screen whose destination is not an email: only the brand's own Gmail is automatic.
    SCREENS["code_other"] = [el("2-Step Verification"), el("Get a code"), el("\u2022\u2022 12 345 678")]
    original_tap = screen.tap

    def tap(element):
        label = element.text or element.desc
        if screen.state == "password_form" and label == "Next":
            # Google answers the submitted password with a code to another destination.
            screen.state = "code_other"
            screen.taps.append(label)
            return
        return original_tap(element)

    screen.tap = tap
    login = GoogleLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(),
                        code_provider=lambda: "123456")
    with pytest.raises(NeedsHuman) as caught:
        login.login("timmy.clips@gmail.com", "acct-1", user=11)
    assert "code" in str(caught.value).lower()

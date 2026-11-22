"""The Instagram Reel flow and login on a scripted screen (PLAN sections 6.5, 5.3).

Like the TikTok scripted tests: a screen that moves when the right thing is tapped catches a
wrong label or a signature that never arrives, without touching the phone or any account.
"""

from pathlib import Path

import pytest

from robotapp.errors import NeedsHuman
from robotapp.fake import FakePhone, fake_guard
from robotapp.journal import PRESSED, Journal
from robotapp.log import Secret
from robotapp.login.instagram import InstagramLogin
from robotapp.post.base import PostSpec
from robotapp.post.instagram import INSTAGRAM, InstagramPoster
from robotapp.ui import Element

PASSWORD = "fake-IG-Pass-99!"


def el(text: str = "", desc: str = "", bounds=(0, 0, 100, 100), clickable: bool = False) -> Element:
    return Element(text=text, desc=desc, bounds=bounds, clickable=clickable)


NAV = [
    el(desc="Home", bounds=(0, 2193, 216, 2340), clickable=True),
    el(desc="Search", bounds=(216, 2193, 432, 2340), clickable=True),
    el(desc="Create", bounds=(432, 2193, 648, 2340), clickable=True),
    el(desc="Profile", bounds=(864, 2193, 1080, 2340), clickable=True),
]

SCREENS = {
    "home": [el("For you"), el("Following"), *NAV],
    "profile": [el("Edit profile"), el("Followers"), el("@g2g.clips"), el("Reels", bounds=(100, 1200, 300, 1300)), *NAV],
    # IG 456 (measured 2026-11-21): the top-left Create goes straight to the post picker, the newest
    # video is already selected, and there is no REEL tab anywhere in this flow.
    "new_post": [
        el("Cancel", bounds=(20, 60, 140, 200), clickable=True),
        el("New post", bounds=(300, 60, 700, 200)),
        el("Next", bounds=(900, 60, 1050, 200), clickable=True),
        el("Recents", bounds=(40, 1300, 300, 1400), clickable=True),
        el("Select", bounds=(40, 600, 300, 700), clickable=True),
        el("1:02", bounds=(40, 2100, 200, 2160)),
        el("", desc="Selected Video thumbnail created on November 21, 2026 6:01 AM",
           bounds=(0, 1450, 353, 1750), clickable=True),
        el("", desc="Unselected Video thumbnail created on November 21, 2026 5:34 AM",
           bounds=(360, 1450, 713, 1750), clickable=True),
    ],
    "editor": [el("Next", bounds=(900, 2200, 1050, 2320), clickable=True), el("Edit"), el("Audio")],
    "caption": [
        el("Write a caption", bounds=(100, 1800, 900, 1900), clickable=True),
        el("Share", bounds=(900, 2200, 1050, 2320), clickable=True),
    ],
    "shared": [el("Your reel has been shared", bounds=(300, 1200, 800, 1300)), *NAV],
    "reel": [el(desc="More options", bounds=(900, 150, 1050, 300), clickable=True), el("Like")],
    "share_sheet": [el("Copy link", bounds=(100, 1800, 900, 1900), clickable=True), el("Share to")],
    # an older build's way in, kept tested: a create sheet with a REEL tab, then the reel camera
    "create_sheet": [el("REEL", bounds=(100, 1800, 400, 1900), clickable=True), el("POST"), el("LIVE")],
    "reel_camera": [el("Preview"), el("Recents", bounds=(100, 2100, 400, 2200), clickable=True), el("Gallery")],
    "gallery": [
        el("Select", bounds=(100, 200, 300, 300), clickable=True),
        el("1:02", bounds=(100, 400, 200, 450)),
        el("", desc="video thumbnail", bounds=(100, 500, 540, 900), clickable=True),
    ],
    # login screens
    "login": [el("Log in", bounds=(100, 2000, 900, 2100), clickable=True), el("Sign up"), el("Log in with Facebook")],
    "login_form": [el("Username", bounds=(100, 900, 900, 1000), clickable=True), el("Phone"), el("Email"),
                   el("Log in", bounds=(100, 1500, 900, 1600), clickable=True)],
    "password_form": [el("Password", bounds=(100, 1100, 900, 1200), clickable=True), el("Log in", bounds=(100, 1600, 900, 1700), clickable=True)],
    "captcha": [el("Confirm you're human"), el("Slide to verify")],
    "code_form": [el("Enter code", bounds=(100, 900, 900, 1000), clickable=True), el("Confirm", bounds=(100, 1400, 900, 1500), clickable=True)],
    "save_info": [el("Save your login info?"), el("Not now", bounds=(100, 1800, 500, 1900), clickable=True)],
    "logged_in_feed": [el("For you"), el("Following"), *NAV],
}


class ScriptedScreen:
    """A fake screen that moves to the next screen when the right thing is tapped.

    ``legacy`` replays the older way in (create sheet -> REEL -> the reel camera -> its gallery), so
    both routes stay covered while the real app moves on.
    """

    def __init__(self, state: str = "home", captcha_after_password: bool = False, legacy: bool = False) -> None:
        self.state = state
        self.captcha_after_password = captcha_after_password
        self.legacy = legacy
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.secrets: list[str] = []
        self.shots: list[Path] = []
        self._clipboard = "https://www.instagram.com/reel/C1xYzAbCdEf/"

    def elements(self) -> list[Element]:
        return SCREENS[self.state]

    def tap(self, element: Element) -> None:
        label = element.text or element.desc
        self.taps.append(label)
        if self.state == "password_form" and label == "Log in" and self.captcha_after_password:
            self.state = "captcha"
            return
        moves = {
            ("home", "Profile"): "profile",
            ("home", "Create"): "create_sheet" if self.legacy else "new_post",
            ("create_sheet", "REEL"): "reel_camera",
            ("reel_camera", "Recents"): "gallery",
            ("reel_camera", "Gallery"): "gallery",
            ("gallery", "video thumbnail"): "editor",
            ("new_post", "Next"): "editor",
            ("editor", "Next"): "caption",
            ("caption", "Share"): "shared",
            ("reel", "More options"): "share_sheet",
            ("login", "Log in"): "login_form",
            ("login_form", "Log in"): "password_form",
            ("password_form", "Log in"): "code_form",
            ("code_form", "Confirm"): "save_info",
            ("save_info", "Not now"): "logged_in_feed",
            ("logged_in_feed", "Profile"): "profile",
            ("shared", "Profile"): "profile",
        }
        target = moves.get((self.state, label))
        if target:
            self.state = target

    def tap_point(self, x: int, y: int) -> None:
        self.taps.append(f"point:{x},{y}")
        if self.state == "profile":
            self.state = "reel"      # the newest Reel tile
        elif self.state == "gallery":
            self.state = "editor"

    def long_press(self, element: Element) -> None:
        self.taps.append(f"long:{element.text or element.desc}")

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.typed.append(text)

    def type_secret(self, secret) -> None:
        self.secrets.append(secret.reveal())

    def set_text(self, text: str) -> None:
        self.typed.append(text)
        if self.state == "caption":
            self.typed.append(text)   # the field reports it back on the next read

    def clear_field(self) -> None:
        self.typed.clear()

    def hide_keyboard(self) -> None:
        self.taps.append("hide_keyboard")

    def press_back(self) -> None:
        self.taps.append("back")
        if self.state == "caption":
            self.state = "editor"
        elif self.state == "profile":
            self.state = "home"      # back from the profile returns to the feed
        elif self.state == "share_sheet":
            self.state = "reel"
        elif self.state in ("editor", "gallery", "reel_camera", "create_sheet", "reel"):
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
    return PostSpec(upload_id="u1", platform="instagram", video=Path("x.mp4"), length_s=62.0,
                    caption="nice one", hashtags=["#g2g"])


def test_the_reel_flow_walks_instagram_screens_and_stops_before_share(journal) -> None:
    screen = ScriptedScreen()
    poster = InstagramPoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec(), dry_run=True)

    assert result.outcome == "dry_run"
    assert screen.state == "caption"           # the caption screen, nothing pressed
    assert "Share" not in screen.taps
    # the handle check (Profile -> back), then create: Create -> the picker (newest preselected)
    # -> Next -> the editor's Next -> the caption field. No REEL tab exists on this build.
    assert screen.taps[:6] == ["Profile", "back", "Create", "Next", "Next", "Write a caption"]
    assert "REEL" not in screen.taps
    assert journal.pressed("job-1", "u1") is False


def test_an_older_build_still_walks_the_reel_sheet(journal) -> None:
    """The way in the plan described (a REEL tab, then the reel camera's gallery) must keep working."""
    screen = ScriptedScreen(legacy=True)
    poster = InstagramPoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec(), dry_run=True)

    assert result.outcome == "dry_run"
    assert screen.taps[:6] == ["Profile", "back", "Create", "REEL", "Gallery", "video thumbnail"]


def test_a_wrong_length_video_is_refused_before_share(journal) -> None:
    screen = ScriptedScreen()
    poster = InstagramPoster(LinkedPhone(screen), screen, journal, "job-1")
    bad = PostSpec(upload_id="u2", platform="instagram", video=Path("x.mp4"), length_s=9.0, caption="c")
    result = poster.post(bad)
    assert result.outcome == "failed_before_post"
    assert "the gallery shows" in (result.reason or "")
    assert "Share" not in screen.taps


def test_share_is_pressed_once_and_the_link_is_read(journal, monkeypatch) -> None:
    monkeypatch.setattr("robotapp.post.instagram.engage", lambda phone: 4.0)
    screen = ScriptedScreen()
    poster = InstagramPoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == "posted"
    assert result.url == "https://www.instagram.com/reel/C1xYzAbCdEf/"
    assert result.handle == "@g2g.clips"
    assert screen.taps.count("Share") == 1
    assert journal.pressed("job-1", "u1") is True
    assert journal.outcome("job-1", "u1") == "posted"


def test_a_logged_out_app_stops_the_post(journal) -> None:
    screen = ScriptedScreen("login")
    poster = InstagramPoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == "failed_before_post"
    assert "logged out" in (result.reason or "")
    assert "Share" not in screen.taps


class FakeChameleon:
    def platform_password(self, profile_id: str, platform: str) -> Secret:
        assert platform == "instagram"
        return Secret(PASSWORD)


def test_a_login_walks_the_screens_and_never_prints_the_password(caplog) -> None:
    import logging

    screen = ScriptedScreen("login")
    login = InstagramLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(),
                           code_provider=lambda: "123456")
    with caplog.at_level(logging.DEBUG):
        result = login.login("profile-1", "g2g.clips", INSTAGRAM)

    assert result.logged_in is True
    assert result.handle == "@g2g.clips"
    assert "g2g.clips" in screen.typed
    assert screen.secrets == [PASSWORD]      # typed through the secret path, once
    assert PASSWORD not in caplog.text
    assert "123456" in screen.typed


def test_a_captcha_stops_the_login_and_asks_for_a_human() -> None:
    screen = ScriptedScreen("login", captcha_after_password=True)
    login = InstagramLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon(),
                           code_provider=lambda: "123456")
    with pytest.raises(NeedsHuman) as caught:
        login.login("profile-1", "g2g.clips", INSTAGRAM)
    assert "CAPTCHA" in str(caught.value)


def test_single_page_instagram_form_and_topbar_handle_fallback(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)

    class SinglePageScreen(ScriptedScreen):
        def __init__(self) -> None:
            super().__init__(state="single_page")

        def elements(self) -> list[Element]:
            extra = {
                "single_page": [
                    el("Username, email or mobile number", bounds=(100, 900, 980, 1000), clickable=True),
                    el("Password", bounds=(100, 1050, 980, 1150), clickable=True),
                    el("Log in", bounds=(100, 1250, 980, 1360), clickable=True),
                    el("Forgot password?", bounds=(300, 1400, 780, 1480), clickable=True),
                ],
                "profile_no_at": [
                    el("Edit profile"),
                    el("Followers"),
                    el("speedexpediaclips", bounds=(80, 130, 500, 190)),
                    *NAV,
                ],
            }
            return extra[self.state] if self.state in extra else super().elements()

        def tap(self, element: Element) -> None:
            label = element.text or element.desc
            if self.state == "single_page" and label == "Log in":
                self.taps.append(label)
                self.state = "logged_in_feed"
                return
            if self.state == "logged_in_feed" and label == "Profile":
                self.taps.append(label)
                self.state = "profile_no_at"
                return
            super().tap(element)

    screen = SinglePageScreen()
    login = InstagramLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
    result = login.login("profile-1", "faizchess55@gmail.com", INSTAGRAM)
    assert result.logged_in is True
    assert result.handle == "@speedexpediaclips"
    assert screen.secrets == [PASSWORD]
    assert screen.taps.count("Log in") == 1


def test_mobile_number_or_email_placeholder_is_tapped_before_typing(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)

    class MetaBloksScreen(ScriptedScreen):
        def __init__(self) -> None:
            super().__init__(state="meta_login")
            self.field_tapped = False

        def elements(self) -> list[Element]:
            extra = {
                "meta_login": [
                    el("Mobile number or email", bounds=(96, 1038, 607, 1095)),
                    el("Password", bounds=(96, 1254, 312, 1311)),
                    el("Log in", bounds=(48, 1410, 1032, 1542), clickable=True),
                    el("Create new account", bounds=(48, 2058, 1032, 2190), clickable=True),
                ],
                "profile_no_at": [
                    el("Edit profile"),
                    el("Followers"),
                    el("timmy.clips", bounds=(80, 130, 500, 190)),
                    *NAV,
                ],
            }
            return extra[self.state] if self.state in extra else super().elements()

        def tap(self, element: Element) -> None:
            label = element.text or element.desc
            if label == "Mobile number or email":
                self.taps.append(label)
                self.field_tapped = True
                return
            if self.state == "meta_login" and label == "Log in":
                self.taps.append(label)
                self.state = "logged_in_feed"
                return
            if self.state == "logged_in_feed" and label == "Profile":
                self.taps.append(label)
                self.state = "profile_no_at"
                return
            super().tap(element)

        def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
            assert self.field_tapped is True
            super().type_text(text, min_ms=min_ms, max_ms=max_ms)

    screen = MetaBloksScreen()
    login = InstagramLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
    result = login.login("profile-1", "horalixscripts6@gmail.com", INSTAGRAM)
    assert result.logged_in is True
    assert result.handle == "@timmy.clips"
    assert "Mobile number or email" in screen.taps
    assert "hide_keyboard" in screen.taps


def test_instagram_character_captcha_stops_immediately(monkeypatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)
    screen = ScriptedScreen("login")
    orig_elements = screen.elements

    def elements_with_chars() -> list[Element]:
        if screen.state == "code_form":
            return [el("Enter the characters you see"), el("We just need to make sure there's a real human behind this login attempt.")]
        return orig_elements()

    screen.elements = elements_with_chars  # type: ignore[method-assign]
    login = InstagramLogin(FakePhone(guard=fake_guard()), screen, FakeChameleon())
    with pytest.raises(NeedsHuman, match="CAPTCHA"):
        login.login("profile-1", "g2g.clips", INSTAGRAM)

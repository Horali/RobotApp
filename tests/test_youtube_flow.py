"""The YouTube Shorts flow and the Google sign-in on a scripted screen (PLAN sections 6.7, 5.6).

The posting screens are the ones **measured on YouTube 21.46 on 2026-11-21**: Create opens the Shorts
camera directly (no sheet), the way in is "Import video from photo library", the picker and the editor
each carry a Next, and the details screen's rows are "Add details" / "Upload Short". The Google
sign-in's screens are the plan's and are exercised against the login, which has not changed.
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


NAV = [
    el("Home", desc="Home", bounds=(0, 2316, 270, 2460), clickable=True),
    el("Shorts", desc="Shorts", bounds=(270, 2316, 540, 2460), clickable=True),
    el("", desc="Create", bounds=(540, 2316, 810, 2460), clickable=True),
    el("You", desc="You", bounds=(810, 2316, 1080, 2460), clickable=True),
]

SCREENS = {
    "home": [el("Home", bounds=(48, 292, 192, 357)), el("Shorts", bounds=(270, 292, 540, 357)), *NAV],
    # the You tab: the channel's name sits right under "View channel" (no avatar in this build's top bar)
    "you": [el("View channel", bounds=(24, 300, 500, 360)), el("Horali Cript", bounds=(24, 360, 500, 420)),
            el("Get Premium"), el("Accounts"), el("Notifications"), el("Search"), el("Settings", bounds=(24, 1500, 500, 1560)),
            *NAV],
    "you_signed_out": [el("Sign in", bounds=(300, 1200, 800, 1300), clickable=True),
                       el("Accounts"), el("Settings"), *NAV],
    "camera": [
        el("", desc="Deselect", bounds=(456, 1729, 624, 1849), clickable=True),
        el("", desc="Record button", bounds=(431, 1681, 647, 1897), clickable=True),
        el("", desc="Import video from photo library", bounds=(0, 1662, 216, 1926), clickable=True),
        el("", desc="Close camera", bounds=(0, 60, 120, 180), clickable=True),
        el("Add", bounds=(900, 1700, 1050, 1800), clickable=True),
    ],
    "picker": [
        el("Close", bounds=(0, 60, 120, 180), clickable=True),
        el("Create video", bounds=(0, 200, 300, 300)),
        el("Create from gallery", bounds=(300, 200, 700, 300)),
        el("Recents", bounds=(700, 200, 900, 300), clickable=True),
        el("0:48", bounds=(10, 600, 120, 640)),
        el("", desc="", bounds=(3, 641, 357, 1270), clickable=True),
        el("", desc="", bounds=(363, 641, 717, 1270), clickable=True),
        el("Next", bounds=(552, 2272, 1032, 2419), clickable=True),
    ],
    "editor": [
        el("Swipe up to edit", bounds=(0, 300, 1080, 400)),
        el("Text", bounds=(0, 2100, 200, 2200)),
        el("Effects", bounds=(200, 2100, 400, 2200)),
        el("More tools", bounds=(400, 2100, 700, 2200)),
        el("Exit editor", bounds=(0, 60, 200, 180), clickable=True),
        el("Next", bounds=(558, 2310, 1032, 2430), clickable=True),
    ],
    "details": [
        el("", desc="Navigate up", bounds=(24, 120, 120, 220), clickable=True),
        el("Add details", bounds=(216, 139, 520, 220), clickable=True),
        el("Edit thumbnail", bounds=(700, 139, 1000, 220)),
        el("Caption your Short", bounds=(300, 260, 780, 320), clickable=True),
        el("Show more", bounds=(36, 1518, 1044, 1662), clickable=True),
        el("Save draft", bounds=(36, 2170, 520, 2290), clickable=True),
        el("Upload Short", bounds=(540, 2170, 1044, 2290), clickable=True),
    ],
    "title_sheet": [
        el("Title", bounds=(48, 700, 1000, 760)),
        el("", desc="Title", bounds=(48, 760, 1000, 900), clickable=True),
        el("Done", bounds=(900, 200, 1040, 300), clickable=True),
    ],
    "uploaded": [el("Upload complete"), el("Home"), el("Shorts"), el("You"), *NAV],
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
    # YouTube after the sign-in: the You tab carries the account's own name
    "youtube_after": [el("Home"), el("Shorts"), el("You", bounds=(810, 2316, 1080, 2460), clickable=True),
                      el(desc="Account and Notifications", bounds=(900, 100, 1050, 250), clickable=True)],
    "account_sheet": [el("Timmy Clips"), el("timmy.clips@gmail.com"), el("Switch account")],
}


class ScriptedScreen:
    def __init__(self, state: str = "home", title_hint: bool = False) -> None:
        self.state = state
        self.title_hint = title_hint        # a build whose details screen exposes "Add a title"
        self.taps: list[str] = []
        self.typed: list[str] = []
        self.secrets: list[str] = []
        self.secret_indexes: list[int] = []
        self.shots: list[Path] = []
        self._clipboard = "https://youtube.com/shorts/j1a7ETNYOAI"

    def elements(self) -> list[Element]:
        if self.title_hint and self.state == "details":
            return SCREENS["details"] + [el("Add a title that describes your video", bounds=(300, 700, 780, 760))]
        return SCREENS[self.state]

    def tap(self, element: Element) -> None:
        label = (element.text or element.desc).strip()
        if not label:
            label = "video thumbnail"
            self.taps.append(label)
        else:
            self.taps.append(label)
        moves = {
            ("home", "You"): "you",
            ("you", "Home"): "home",
            ("home", "Create"): "camera",
            ("camera", "Import video from photo library"): "picker",
            ("picker", "Next"): "editor",
            ("editor", "Next"): "details",
            ("details", "Add details"): "title_sheet",
            ("title_sheet", "Done"): "details",
            ("details", "Upload Short"): "uploaded",
            ("uploaded", "You"): "you",
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

    def type_secret(self, secret, index: int = 1) -> None:
        self.secrets.append(secret.reveal())
        self.secret_indexes.append(index)
        self.typed.append("\u2022" * 8)      # the field holds it, masked: focused_text is not empty

    def set_text(self, text: str) -> None:
        self.typed.append(text)
        self.typed.append(text)      # the field reports it back

    def clear_field(self) -> None:
        self.typed.clear()

    def hide_keyboard(self) -> None:
        self.taps.append("hide_keyboard")

    def press_back(self) -> None:
        self.taps.append("back")
        if self.state in ("details", "editor", "picker", "camera", "title_sheet"):
            self.state = "details" if self.state == "title_sheet" else "home"
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
    return PostSpec(upload_id="u1", platform="youtube", video=Path("x.mp4"), length_s=48.0,
                    title="Big win #shorts", caption="Big win #shorts", hashtags=["#shorts"])


def test_the_short_flow_walks_youtube_screens_and_stops_before_upload(journal) -> None:
    screen = ScriptedScreen()
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec(), dry_run=True)

    assert result.outcome == "dry_run"
    assert screen.state == "details"
    assert "Upload Short" not in screen.taps
    # You tab -> the channel's own name -> back to Home -> Create (straight to the camera) ->
    # import -> the newest tile -> Next (picker) -> Next (editor) -> the title row
    assert screen.taps[:7] == ["You", "Home", "Create", "Import video from photo library",
                               "video thumbnail", "Next", "Next"]
    assert "Add details" not in screen.taps     # this build exposes no title field to type into
    assert journal.pressed("job-1", "u1") is False


def test_a_build_with_a_title_field_gets_the_title_typed(journal) -> None:
    """When the details screen does expose a title field, the flow types ClipMaker's title into it."""
    screen = ScriptedScreen(title_hint=True)
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec(), dry_run=True)

    assert result.outcome == "dry_run"
    assert "Add details" in screen.taps
    assert "hide_keyboard" in screen.taps
    assert screen.typed and "Big win #shorts" in screen.typed[-1]


def test_a_wrong_length_video_is_refused_before_upload(journal) -> None:
    screen = ScriptedScreen()
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    bad = PostSpec(upload_id="u2", platform="youtube", video=Path("x.mp4"), length_s=9.0, title="T")
    result = poster.post(bad)
    assert result.outcome == "failed_before_post"
    assert "the gallery shows" in (result.reason or "")
    assert "Upload Short" not in screen.taps


def test_upload_is_pressed_once_and_the_link_is_read(journal, monkeypatch) -> None:
    monkeypatch.setattr("robotapp.post.youtube.engage", lambda phone: 5.0)
    screen = ScriptedScreen()
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == "posted"
    assert result.url == "https://youtube.com/shorts/j1a7ETNYOAI"
    assert screen.taps.count("Upload Short") == 1
    assert journal.pressed("job-1", "u1") is True
    assert journal.outcome("job-1", "u1") == "posted"


def test_an_upload_tap_that_starts_nothing_says_so(journal, monkeypatch) -> None:
    """The details screen staying up means the tap missed; it must not be called an upload."""
    from robotapp.post import youtube as youtube_module

    monkeypatch.setattr(youtube_module.YouTubePoster, "UPLOAD_START_GRACE_S", 0.1)

    class StuckOnUpload(ScriptedScreen):
        def tap(self, element) -> None:
            label = element.text or element.desc
            if label == "Upload Short" and self.state == "details":
                self.taps.append(label)   # the tap lands on nothing: the screen never moves
                return
            super().tap(element)

    stuck = StuckOnUpload()
    poster = YouTubePoster(LinkedPhone(stuck), stuck, journal, "job-1")
    result = poster.post(spec())
    assert result.outcome == "unsure_after_post"
    assert "did not start an upload" in (result.reason or "")
    assert stuck.taps.count("Upload Short") == 1


    screen = ScriptedScreen("you_signed_out")     # the You tab has no channel name on it
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
                screen.state = "youtube_after"   # YouTube opens signed in
            return "started"

    login = GoogleLogin(AfterPhone(guard=fake_guard()), screen, FakeChameleon(),
                        code_provider=lambda: "")
    with caplog.at_level(logging.DEBUG):
        result = login.login("timmy.clips@gmail.com", "acct-1", user=11)

    assert result.logged_in is True
    assert result.channel == "timmy.clips"
    assert "timmy.clips@gmail.com" in screen.typed
    assert screen.secrets == [PASSWORD]       # the Gmail password, typed once through the secret path
    assert screen.secret_indexes == [0]       # Google's page has ONE field (index 1 typed nothing, 2026-11-20)
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


def test_check_channel_ignores_systemui_home_button(journal) -> None:
    """Android's SystemUI Home button must never be tapped instead of YouTube's bottom Home tab."""
    tapped_bounds: list[tuple[int, int, int, int]] = []
    sys_home = Element(text="", desc="Home", resource_id="com.android.systemui:id/home",
                       bounds=(420, 2340, 660, 2460), clickable=True)
    yt_home = Element(text="Home", desc="Home", resource_id="", bounds=(0, 2196, 270, 2340), clickable=True)

    class SysUiYouScreen(ScriptedScreen):
        def elements(self) -> list[Element]:
            if self.state == "you":
                base = [e for e in SCREENS["you"] if (e.desc or e.text).strip() != "Home"]
                return [sys_home, *base, yt_home]
            return super().elements()

        def tap(self, element: Element) -> None:
            tapped_bounds.append(element.bounds)
            super().tap(element)

    screen = SysUiYouScreen("home")
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-sysui")
    channel = poster._check_channel()

    assert channel == "Horali Cript"
    assert sys_home.bounds not in tapped_bounds
    assert yt_home.bounds in tapped_bounds
    assert screen.state == "home"


def test_pick_video_skips_drafts_create_video_and_scrim_and_checks_tile_duration(journal) -> None:
    """The measured 2026-11-23 picker includes clickable Drafts/Create video cards and touch_outside scrim."""
    real_picker = [
        Element(resource_id="com.google.android.youtube:id/touch_outside", bounds=(0, 108, 1080, 2340), clickable=True),
        Element(desc="Close", resource_id="com.google.android.youtube:id/gallery_header_close_button",
                bounds=(18, 156, 162, 228), clickable=True),
        Element(desc="Drafts", bounds=(24, 270, 528, 462), clickable=True),
        Element(desc="Create video", bounds=(552, 270, 1056, 462), clickable=True),
        Element(text="Create from gallery", bounds=(0, 504, 779, 629)),
        Element(text="Recents", desc="Recents", bounds=(779, 504, 1080, 629), clickable=True),
        Element(bounds=(3, 641, 357, 1270), clickable=True),
        Element(desc="robot-20261123-060018.mp4",
                resource_id="com.google.android.youtube:id/thumb_image_view",
                bounds=(3, 641, 357, 1270), clickable=False),
        Element(text="0:48", resource_id="com.google.android.youtube:id/duration_text_view",
                bounds=(231, 1186, 339, 1252)),
        Element(bounds=(363, 641, 717, 1270), clickable=True),
        Element(desc="2026-11-21-180344356.mp4",
                resource_id="com.google.android.youtube:id/thumb_image_view",
                bounds=(363, 641, 717, 1270), clickable=False),
        Element(text="0:56", resource_id="com.google.android.youtube:id/duration_text_view",
                bounds=(591, 1186, 699, 1252)),
    ]

    class RealPickerScreen(ScriptedScreen):
        def __init__(self) -> None:
            super().__init__("picker")
            self.tapped_tiles: list[Element] = []

        def elements(self) -> list[Element]:
            return real_picker

        def tap(self, element: Element) -> None:
            self.tapped_tiles.append(element)

    screen = RealPickerScreen()
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-picker")
    poster._pick_video(spec())

    assert len(screen.tapped_tiles) == 1
    assert screen.tapped_tiles[0].bounds == (3, 641, 357, 1270)
    assert screen.tapped_tiles[0].desc == "robot-20261123-060018.mp4"


def test_open_create_does_not_tap_create_video_when_gallery_is_already_open(journal) -> None:
    """When Create opens directly into the gallery grid, never tap 'Create video' (Dream Screen)."""

    class DirectPickerScreen(ScriptedScreen):
        def tap(self, element: Element) -> None:
            label = (element.text or element.desc).strip()
            self.taps.append(label)
            if self.state == "home" and label == "Create":
                self.state = "picker"

    screen = DirectPickerScreen("home")
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-direct-picker")
    poster._open_create()

    assert screen.state == "picker"
    assert "Create video" not in screen.taps


def test_inline_caption_and_litho_audience_picker_are_completed(journal) -> None:
    """Measured 2026-11-23: details shows clickable 'Caption your Short' and unlabelled Litho audience rows."""
    tapped: list[tuple[int, int, int, int]] = []
    vis_row = Element(bounds=(0, 1170, 1080, 1338), clickable=True)
    aud_row = Element(bounds=(0, 1338, 1080, 1506), clickable=True)
    yes_kids = Element(bounds=(0, 714, 1080, 930), clickable=True)
    learn_more = Element(desc="Learn more", bounds=(672, 762, 792, 882), clickable=True)
    no_kids = Element(bounds=(0, 930, 1080, 1098), clickable=True)
    age_row = Element(bounds=(0, 1149, 1080, 1317), clickable=True)
    back_btn = Element(desc="Back", bounds=(24, 108, 168, 252), clickable=True)

    class LithoDetailsScreen(ScriptedScreen):
        def elements(self) -> list[Element]:
            if self.state == "details":
                return [
                    Element(desc="Navigate up", bounds=(0, 108, 168, 252), clickable=True),
                    Element(text="Add details", bounds=(216, 139, 520, 220), clickable=False),
                    Element(text="Caption your Short", bounds=(329, 315, 1044, 429), clickable=True),
                    vis_row,
                    aud_row,
                    Element(desc="Show more", bounds=(36, 1518, 1044, 1662), clickable=True),
                    Element(text="Upload Short", bounds=(558, 2184, 1044, 2304), clickable=True),
                ]
            if self.state == "audience":
                return [back_btn, yes_kids, learn_more, no_kids, age_row]
            return super().elements()

        def tap(self, element: Element) -> None:
            tapped.append(element.bounds)
            if self.state == "details" and element.bounds == aud_row.bounds:
                self.state = "audience"
                self.taps.append("Select audience")
                return
            if self.state == "audience" and element.bounds == back_btn.bounds:
                self.state = "details"
                self.taps.append("Back")
                return
            super().tap(element)

    screen = LithoDetailsScreen("details")
    poster = YouTubePoster(LinkedPhone(screen), screen, journal, "job-litho")
    s = spec()
    poster._write_title(s)
    poster._set_visibility()

    assert s.title in screen.typed
    assert "Caption your Short" in screen.taps
    assert aud_row.bounds in tapped
    assert vis_row.bounds not in tapped
    assert no_kids.bounds in tapped
    assert yes_kids.bounds not in tapped
    assert screen.state == "details"



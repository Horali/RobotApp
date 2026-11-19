"""The password-leak test (PLAN section 12, step 3): no secret reaches an output channel.

Runs the login flow on the fake phone with a known password and then greps every channel a secret
could leak into: the journal database, the log file, the events the flow emitted, and the
exception messages. A test greps real output because a rule that was never grepped is a wish.
"""

import json
import logging
from pathlib import Path

from robotapp.fake import FakePhone, FakeScreen, fake_guard
from robotapp.journal import Journal
from robotapp.log import Secret
from robotapp.login.tiktok import TikTokLogin
from robotapp.ui import Element

PASSWORD = "LeakMe-Not-123!"  # a fake value with no real use
EMAIL = "throwaway@example.com"


class RecordingChameleon:
    def platform_password(self, profile_id: str, platform: str) -> Secret:
        return Secret(PASSWORD)


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
}


class LeakScreen(FakeScreen):
    """A fake screen that behaves like the scripted login screens."""

    def __init__(self) -> None:
        super().__init__()
        self.state = "home"
        self.secrets_typed: list[str] = []
        self.elements_list: list[Element] = SCREENS["home"]

    def elements(self) -> list[Element]:
        return SCREENS[self.state]

    def tap(self, element) -> None:
        label = element.text or element.desc
        moves = {
            ("home", "Profile"): "profile",
            ("profile", "Log in"): "login_choice",
            ("login_choice", "Use phone / email / username"): "email_form",
            ("email_form", "Email / Username"): "email_entry",
            ("email_entry", "Continue"): "password_form",
            ("password_form", "Log in"): "code_form",
            ("code_form", "Enter the code"): "logged_in",
        }
        target = moves.get((self.state, label))
        if target:
            self.state = target

    def type_secret(self, secret) -> None:
        self.secrets_typed.append(secret.reveal())

    def set_text(self, text: str) -> None:
        self.typed.append(text)

    def type_text(self, text: str, min_ms: int = 40, max_ms: int = 110) -> None:
        self.typed.append(text)
        # a full 6-digit code submits itself: the real flow types into the unlabeled field
        if self.state == "code_form" and len(text.strip()) == 6 and text.strip().isdigit():
            self.state = "logged_in"

    def size(self) -> tuple[int, int]:
        return 1080, 2400


def test_a_login_flow_leaks_no_password_anywhere(tmp_path, monkeypatch) -> None:
    # Pin the environment: the window tests taught us a shell variable can leak in.
    monkeypatch.setenv("ROBOTAPP_BUILD_MODE", "1")

    # A log file in a temp dir, the journal in a temp db, and an events sink.
    log_file = tmp_path / "leak-test.log"
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger("robotapp")
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    journal = Journal(tmp_path / "robot.db")
    journal.start_job("leak-test", "login")

    events: list[dict] = []
    screen = LeakScreen()
    login = TikTokLogin(
        FakePhone(guard=fake_guard()),
        screen,
        RecordingChameleon(),
        emit=events.append,
        shots_dir=tmp_path / "shots",
        code_provider=lambda: "123456",
    )
    result = login.login("profile-1", EMAIL, "com.zhiliaoapp.musically")
    root.removeHandler(handler)
    handler.close()

    assert result.logged_in is True
    assert screen.secrets_typed == [PASSWORD]  # the secret was used, exactly once

    # Grep every channel the password could have reached.
    channels = {
        "journal db": (tmp_path / "robot.db").read_bytes(),
        "journal wal": (tmp_path / "robot.db-wal").read_bytes() if (tmp_path / "robot.db-wal").exists() else b"",
        "log file": log_file.read_bytes(),
        "events": json.dumps(events, ensure_ascii=False).encode(),
        "exception": str(result).encode(),
    }
    for name, blob in channels.items():
        assert PASSWORD.encode() not in blob, f"the password leaked into the {name}"

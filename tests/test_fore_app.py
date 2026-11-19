"""Whose app is in front: topResumedActivity, not mCurrentFocus (found on the phone, 2026-11-19).

`dumpsys window` prints mCurrentFocus once per root task on this XOS build: with the user's own
Instagram open in user 0, its stale line came FIRST and the reader blamed user 0 while the space's
TikTok was on screen - the same misread class as the "on my main account" alarm. The unique,
proven source is `dumpsys activity activities`' topResumedActivity (checked both ways on the
phone: u11 musically in front, then u0 after `am switch-user 0`).
"""

from robotapp.adb import AdbPhone

FOCUS_CMD = "dumpsys activity activities | grep -m1 topResumedActivity"

REAL_LINE = (
    "    topResumedActivity=ActivityRecord{d7f682f u11 "
    "com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity} t1100032}"
)


class StubPhone(AdbPhone):
    def __init__(self, answers: dict[str, str]) -> None:
        super().__init__("adb-fake", "fake")
        self.answers = answers

    def shell(self, command: str, timeout: int = 60) -> str:
        return self.answers.get(command, "")

    def current_user(self) -> int:
        return 0


def test_the_resumed_activity_names_the_space_app() -> None:
    phone = StubPhone({FOCUS_CMD: REAL_LINE})
    assert phone.fore_app() == ("com.zhiliaoapp.musically", 11)


def test_a_phone_that_does_not_answer_is_not_blamed() -> None:
    """No topResumedActivity line: ('', user), so callers trust the screen instead of guessing."""
    phone = StubPhone({})
    assert phone.fore_app() == ("", 0)
